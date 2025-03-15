import sys
import os

# Get the absolute path of the parent directory
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the parent directory to sys.path
sys.path.append(parent_dir)

from packages.Prepsheet import GetPrepsheetData
from packages.BatchID import GetBatchID
from packages.DQO import MergeDQO
from packages.ResultType import GetResultType
from config.config import CONNECTION_STRING
from packages.tables import (
    Base, GammaSpecResults
)
import csv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pandas as pd

class GammaSpecProcessor:
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
        parsed_data = []
        with open(file_path, mode='r') as file:
            reader = csv.reader(file)
            for row in reader:
                row_type = row[0]

                if row_type == 'A':
                    a = row

                elif row_type == 'B':
                    b = row

                elif row_type == 'C':
                    c = row
                    row_data = {'A': a, 'B': b, 'C': c}
                    parsed_data.append(row_data)

            columns = [
                "SampleID", "Detector", "Geometry", "AcquisitionDateTime", 
                "AnalysisDateTime", "Livetime", "EnergyCalibrationDateTime", 
                "EfficiencyCalibrationDateTime", 
                
                "SampleDateTime", "SampleSize", "SampleSizeUnits", 
                "ResultUnits", "ErrorMultiplier", 
                
                "Analyte", "NuclideDetected", "Result", 
                "ResultError", "MDA", "MDAError", 
                "ResultMDARatio"
            ]

            # Initialize a list to store all sample rows
            sample_rows = []

            for sample in parsed_data:
                sample_data = [sample['A'][1], sample['A'][2], sample['A'][3], sample['A'][4], sample['A'][5], sample['A'][6], sample['A'][7], sample['A'][8], 
                sample['B'][2], sample['B'][3], sample['B'][4], sample['B'][5], sample['B'][6], sample['C'][1], sample['C'][2], sample['C'][3], sample['C'][4], sample['C'][5], 
                sample['C'][6], sample['C'][7]]

                sample_rows.append(sample_data)
            
            df = pd.DataFrame(sample_rows, columns=columns)

            df = self.create_df(df)

            self.upload_data(df)

        return df
                    
    def create_df(self, df):
        # Method
        df.insert(0, 'Method', 'GammaSpec')

        # BatchID
        batch_id = GetBatchID.get_batch_id(sample_id=df.iloc[0]['SampleID'], method=df.iloc[0]['Method'])

        df['BatchID'] = batch_id

        # SDG and Matrix
        df = MergeDQO.merge_dqo(batch_id, df)

        # Get aliquot
        df = GetPrepsheetData.get_aliquot_amounts(batch_id, df)

        # AliquotUnits
        df = GetPrepsheetData.get_aliquot_units(batch_id, df)

        # PrepDate
        df = GetPrepsheetData.get_prep_datetime(batch_id, df)

        # PrepsheetFilePath
        df = GetPrepsheetData.get_prepsheet_path(batch_id, df)

        # ResultType 
        df = GetResultType.get_result_types(df)

        # List of numeric columns that should be floats
        float_columns = [
            'Aliquot', 'LiveTime', 'SampleSize', 'ErrorMultiplier', 'Result', 'ResultError', 'MDA', 'MDAError', 'ResultMDARatio'
        ]

        datetime_columns = [
           'AcquisitionDateTime', 'AnalysisDateTime', 'EnergyCalibrationDateTime', 'EfficiencyCalibrationDateTime', 'SampleDateTime', 'PrepDateTime'
        ]

        for col in float_columns:
            if col in df.columns:
                df[col] = df[col].astype(float)

        for col in datetime_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

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

                record = GammaSpecResults(**row_dict)

                # Check if record already exists
                existing_record = self.session.query(GammaSpecResults).filter(
                    GammaSpecResults.SDG == record.SDG,
                    GammaSpecResults.BatchID == record.BatchID,
                    GammaSpecResults.SampleID == record.SampleID,
                    GammaSpecResults.Analyte == record.Analyte,
                    GammaSpecResults.Reporting == record.Reporting
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
             
processor = GammaSpecProcessor()

df = processor.parse_file(file_path)