import sys
import os

# Get the absolute path of the parent directory
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the parent directory to sys.path
sys.path.append(parent_dir)

from packages.Prepsheet import GetPrepsheetData
from packages.DQO import MergeDQO
from packages.ResultType import GetResultType
from config.config import CONNECTION_STRING
from config.patterns import batch_id_pattern, result_type_pattern
from packages.tables import (
    Base, FluorescenceResults
)
import csv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pandas as pd

class FluorescenceProcessor:
    def __init__(self):
        self.session = None
        self.engine = None

    def init_session(self):
        # Initialize the SQLAlchemy session
        self.engine = create_engine(CONNECTION_STRING)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def parse_file(self, file_path):
        df = pd.read_excel(file_path)

        file_name = os.path.basename(file_path)
        file_name = os.path.splitext(file_name)[0]

        df = self.create_df(df, file_name)

        # self.upload_data(df)

        return df
                    
    def create_df(self, df, file_name):
        df.columns = ['FluorescenceSampleID', 'RFU', 'ResultUnits']

        df = df.drop(columns='ResultUnits')

        import re
        # Get the batch ID
        if re.match(batch_id_pattern, file_name):
            batch_id = file_name
        else:
            print("File name is not a valid Batch ID")

        df.insert(0, 'BatchID', batch_id)

        df.insert(1, 'SampleID', '')

        df.insert(2, 'AnalysisDateTime', '')

        prepsheet_data = GetPrepsheetData.get_prepsheet_data(batch_id)

        # Assign the calibration sample IDs
        cal_list = [0, 0.05, 2, 10, 40]

        for i in range(len(cal_list)):
            df.iloc[i, 1] = f"{batch_id}CAL{cal_list[i]}"

        # Starting at index 5, the sample IDs should be in order with the prepsheet
        sample_id_list = prepsheet_data['Samples']['Sample ID']

        from datetime import datetime, timedelta

        datetime_list = [
            datetime.strptime(f"{date} {time}", "%m/%d/%Y %H:%M:%S")
            for date, time in zip(prepsheet_data['Samples']['Analysis Date'], prepsheet_data['Samples']['Analysis Time'])
        ]

        # Now set the rest of the rows (non-calibration samples) using the datetime_list
        for i in range(5, len(df)):
            df.iloc[i, 1] = sample_id_list[i-5]
            df.iloc[i, 2] = datetime_list[i-5]

        # Drop the FluorescenceSampleID
        df = df.drop(columns='FluorescenceSampleID')

        cal_ppb_list = [0, 0.05, 2, 10, 40]

        for index, row in df.iterrows():
            if 'CAL' in row['SampleID']:
                df.at[index, 'PPB'] = cal_ppb_list[index]
            else:
                df.at[index, 'PPB'] = round((row['RFU'] - 870.25) / 3084.1, 5)

            # Result in MicroGrams per 100cm^3
            df.at[index, 'Result'] = round(df.at[index, 'PPB'] / 10, 5)

        # Insert Result Units
        df.insert(0, 'ResultUnits', 'ug/100cm^2')

        # Get the SDG and Matrix
        df = MergeDQO.merge_dqo(batch_id, df)

        df = GetPrepsheetData.get_aliquot_amounts(batch_id, df)

        df = GetPrepsheetData.get_aliquot_units(batch_id, df)

        df = GetResultType.get_result_types(df)

        df = GetPrepsheetData.get_prepsheet_path(batch_id, df)

        df = GetPrepsheetData.get_prep_datetime(batch_id, df)

        # Assign adjusted datetime to the first five rows (calibration samples)
        for i in range(5):
            df.iloc[i, 3] = df['PrepDateTime'].unique()[0]

        df = self.get_calibration_curve(df)

        df.insert(0, 'Analyte', 'Beryllium')

        self.upload_data(df)

        return df
    
    def get_calibration_curve(self, df):
        from sklearn.linear_model import LinearRegression
        from sklearn.metrics import r2_score

        model = LinearRegression()

        x = df[['PPB']]  # Independent variable
        y = df[['RFU']]  # Dependent variable

        # Fit the model
        model.fit(x, y)

        # Make predictions
        predictions = model.predict(x)

        # Calculate R2 score
        r2 = round(r2_score(y, predictions), 5)

        # Add the R2 score to the DataFrame
        df.loc[:4, 'CalibrationCurve'] = r2
        df['CalibrationCurve'] = df['CalibrationCurve'].fillna(0)

        return df
                     
    def upload_data(self, df):
        try:
            self.init_session()

            for index, row in df.iterrows():
                # Convert row to dictionary
                row_dict = row.to_dict()

                # Set default iteration and reporting values
                row_dict.setdefault("Iteration", 1)
                row_dict.setdefault("Reporting", True) 

                record = FluorescenceResults(**row_dict)

                # Check if record already exists
                existing_record = self.session.query(FluorescenceResults).filter(
                    FluorescenceResults.SDG == record.SDG,
                    FluorescenceResults.BatchID == record.BatchID,
                    FluorescenceResults.SampleID == record.SampleID,
                    FluorescenceResults.Analyte == record.Analyte,
                    FluorescenceResults.Reporting == record.Reporting
                ).first()

                # If the record exists
                if existing_record:
                    # Check for exact match, if so do nothing
                    if existing_record:
                        if self.objects_are_identical(record, existing_record, ignore_fields=["Iteration"]):
                            print("Identical row exists (ignoring Iteration), continuing...")
                            continue  # Skip insertion
                    else:
                        print("Non-identical record exists, adding new iteration...")
                        # Set iteration to existing_record iteration + 1
                        record.Iteration = existing_record.Iteration + 1
        
                        # Set existing_record.Reporting to False
                        existing_record.Reporting = False

                        # Update the existing record in the database
                        self.session.add(existing_record)

                self.session.add(record)

                self.session.commit()
                print(f"Successfully committed results!")

        except Exception as e:
            print(f"An exception occurred: {e}")
            self.session.rollback()
        finally:
            self.session.close()

    def objects_are_identical(self, obj1, obj2, ignore_fields=None):
        from sqlalchemy.inspection import inspect

        if ignore_fields is None:
            ignore_fields = []

        obj1_dict = {c.key: getattr(obj1, c.key) for c in inspect(obj1).mapper.column_attrs if c.key not in ignore_fields}
        obj2_dict = {c.key: getattr(obj2, c.key) for c in inspect(obj2).mapper.column_attrs if c.key not in ignore_fields}

        if obj1_dict != obj2_dict:
            print("\nMISMATCH DETECTED:")
            for key in obj1_dict.keys():
                if obj1_dict[key] != obj2_dict[key]:
                    print(f"  🔹 Column: {key}")
                    print(f"     Record: {obj1_dict[key]}")
                    print(f"     Existing: {obj2_dict[key]}\n")
            return False

        return True  # No mismatches found
         
file_path = r"\\sldafileserver\Lab Data\Lab\Data\Raw Data\Fluorescence\25SLB0003.xlsx"
    
processor = FluorescenceProcessor()

df = processor.parse_file(file_path)