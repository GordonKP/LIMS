import sys
import os

# Get the absolute path of the parent directory
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the parent directory to sys.path
sys.path.append(parent_dir)

from packages.Prepsheet import GetPrepsheetData
from packages.BatchID import GetBatchID
from packages.SDG import GetSDG
from packages.ResultType import GetResultType
from config.config import CONNECTION_STRING
from packages.tables import (
    Base, AlphaSpecResults
)
import csv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pandas as pd

class GABProcessor:
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

        with open(file_path, mode='r') as file:
            reader = csv.reader(file)

            parsed_data = []

            for row in reader:
                parsed_data.append(row)

        df = self.create_df(parsed_data)

        # self.upload_data(df)

        return 

    def create_df(self, parsed_data):
        columns = ['SampleID', 'Analyte', 'Procedure', 'AcquisitionDateTime', 
                       'AnalysisDateTime', 'DetectorSN', 'LiveTime', 'Result', 
                       'ResultUnits', 'ResultError', 'MDA', 'Aliquot', 'EfficiencyFactor', 
                       'AliquotUnits', 'EfficiencyCalibrationDateTime']
            
        sample_rows = []

        for sample in parsed_data:
            alpha_sample_data = [sample[0], "GrossAlpha", sample[2], sample[3], sample[4], sample[5], sample[6], sample[9], sample[10], sample[11], sample[12], 
                        sample[13], sample[15], sample[26], sample[28]]
            
            beta_sample_data = [sample[0], "GrossBeta", sample[2], sample[3], sample[4], sample[5], sample[6], sample[21], sample[22], sample[23], sample[24], 
                        sample[25], sample[27], sample[26], sample[28]]

            sample_rows.append(alpha_sample_data)
            sample_rows.append(beta_sample_data)

        df = pd.DataFrame(sample_rows, columns=columns)

        df['Method'] = 'GAB'

        # BatchID
        batch_id = GetBatchID.get_batch_id(sample_id=df.iloc[0]['SampleID'], method=df.iloc[0]['Method'])

        df['BatchID'] = batch_id

        # SDG
        df = GetSDG.get_sdg(batch_id, df)

        # AliquotUnits
        df = GetPrepsheetData.get_aliquot_units(batch_id, df)

        # PrepDate
        df = GetPrepsheetData.get_prep_datetime(batch_id, df)

        # PrepsheetFilePath
        df = GetPrepsheetData.get_prepsheet_path(batch_id, df)

        print(df)

        # Column manipulation

        df['LiveTime'] = df['LiveTime'].str.replace(',', '', regex=True)

        float_columns = ['LiveTime', 'Result',
                'ResultError', 'MDA', 'Aliquot', 'EfficiencyFactor']
        
        datetime_columns = ['AcquisitionDateTime', 'AnalysisDateTime', 'EfficiencyCalibrationDateTime', 'PrepDateTime']
        
        for col in float_columns:
            if col in df.columns:
                df[col] = df[col].astype(float)

        for col in datetime_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        df.to_csv("GABTest.csv")

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

                record = AlphaSpecResults(**row_dict)

                # Check if record already exists
                existing_record = self.session.query(AlphaSpecResults).filter(
                    AlphaSpecResults.SDG == record.SDG,
                    AlphaSpecResults.BatchID == record.BatchID,
                    AlphaSpecResults.SampleID == record.SampleID,
                    AlphaSpecResults.Analyte == record.Analyte,
                    AlphaSpecResults.Reporting == record.Reporting
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

file_path = r"\\ServerName\Lab Data\Lab\Data\Raw Data\GAB\GAB_XLB2CC03_20241003102551.CSV"

processor = GABProcessor()

df = processor.parse_file(file_path)