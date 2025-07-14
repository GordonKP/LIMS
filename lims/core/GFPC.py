import sys
import os

# Ensure the package path is set correctly
if getattr(sys, 'frozen', False):  # Running as a bundled .exe
    sys.path.append(os.path.join(sys._MEIPASS, "lims"))
else:
    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    sys.path.append(parent_dir)

from lims.packages.Prepsheet import GetPrepsheetData
from lims.packages.BatchID import GetBatchID
from lims.packages.DQO import MergeDQO
from lims.packages.ResultType import GetResultType
from lims.packages.Analyte import AnalytePreprocessing
from lims.config.config import CONNECTION_STRING
from lims.config.tables import (
    Base, GFPCResults, ConsumableManagement, RADCerts
)
import csv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pandas as pd

class GFPCProcessor:
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
            next(reader, 0)  # Skip the header

            parsed_data = []

            parsed_data = [row for row in reader]

            print(parsed_data)

        columns = ['SampleID', 'Aliquot', 'AliquotUncertainty', 'AnalysisDateTime', 'LiveTime',
                   'AlphaActivityConc', 'AlphaActivityConcUnc', 'AlphaMDAConc', 
                   'BetaActivityConc', 'BetaActivityConcUnc', 'BetaMDAConc', 'PresetLiveTime']
        
        df = pd.DataFrame(parsed_data, columns=columns)

        df = self.create_df(df)

        processed_file_path = self.create_processed_file(df)

        df['ProcessedDataFilePath'] = processed_file_path

        self.upload_data(df)

        return df
    
    def create_processed_file(self, df):
        from lims.config import file_paths
        method = df['Method'].unique()[0]
        batch_id = df['BatchID'].unique()[0]

        processed_data_parent_dir = file_paths.processed_data_directory

        target_parent_dir = os.path.join(processed_data_parent_dir, method)

        # Ensure directory exists
        os.makedirs(target_parent_dir, exist_ok=True)

        file_path = os.path.join(target_parent_dir, f"{batch_id}.csv")

        df.to_csv(file_path, index=False)

        return file_path

    def create_df(self, df):
        from PyQt5.QtWidgets import QApplication, QInputDialog

        alpha_df = df[(df['SampleID'].str[-1:] == 'A') | (df['SampleID'].str.contains("BLK", na=False))].copy()
        beta_df  = df[(df['SampleID'].str[-1:] == 'B') | (df['SampleID'].str.contains("BLK", na=False))].copy()

        alpha_df.insert(0, "Analyte", "GALPHA")
        beta_df.insert(0, "Analyte", "GBETA")

        alpha_df.rename(columns={"AlphaActivityConc":"Result", "AlphaActivityConcUnc":"ResultError", "AlphaMDAConc":"MDA"}, inplace=True)
        beta_df.rename(columns={"BetaActivityConc":"Result", "BetaActivityConcUnc":"ResultError", "BetaMDAConc":"MDA"}, inplace=True)

        print("Alpha columns:", alpha_df.columns.tolist())
        print("Beta columns:", beta_df.columns.tolist())

        df = pd.concat([alpha_df, beta_df], ignore_index=True)

        df = df.drop(columns=['AliquotUncertainty', 'AlphaActivityConc', 'AlphaActivityConcUnc', 'AlphaMDAConc', 
                   'BetaActivityConc', 'BetaActivityConcUnc', 'BetaMDAConc'])

        # Insert GFPC as method
        df.insert(0, 'Method', 'GFPC')
        
        df['AliquotUnits'] = df['Aliquot'].astype(str).str.split().str[1]
        df['Aliquot'] = df['Aliquot'].astype(str).str.split().str[0]
        
        df['ResultUnits'] = df['Result'].astype(str).str.split().str[1]
        df['Result'] = df['Result'].astype(str).str.split().str[0]

        df['ResultError'] = df['ResultError'].astype(str).str.split().str[0]

        df['MDA'] = df['MDA'].astype(str).str.split().str[0]

        df['SampleID']

        df['SampleID'] = df['SampleID'].apply(
            lambda x: str(x)[:-1] if x and str(x)[-1] in ['A', 'B'] and 'LCS' not in str(x) else str(x)
        )

        sample_ids = df['SampleID'].unique().tolist()

        method = 'GFPC'

        # BatchID
        for sample_id in sample_ids:
            print(f"Trying to get batch ID for {sample_id}, {method}")
            batch_id = GetBatchID.get_batch_id(sample_id, method)
            if batch_id is not None:
                break

        df.insert(0, 'BatchID', batch_id)

        # Result Types
        df = GetResultType.get_result_types(df)
        df['ResultType'] = df['ResultType'].apply(lambda x: 'LCS' if 'LCS' in str(x) else x)

        # PrepDate
        df = GetPrepsheetData.get_prep_datetime(batch_id, df)

        # PrepsheetFilePath
        df = GetPrepsheetData.get_prepsheet_path(batch_id, df)
        
        # SDG and Matrix
        df = MergeDQO.merge_dqo(batch_id, df)

        df = AnalytePreprocessing.process(df)

        # Column manipulation
        df['LiveTime'] = df['LiveTime'].str.replace(',', '', regex=True)

        from core import recovery

        prepsheet = GetPrepsheetData.get_prepsheet_data(batch_id)
        print(prepsheet)

        datetime_columns = ['AnalysisDateTime','PrepDateTime']

        for col in datetime_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        df = recovery.get_recovery(df, prepsheet)

        float_columns = ['Aliquot', "Result", "ResultError", "MDA", 'PresetLiveTime', 'PercentRecovery']

        for col in float_columns:
            if col in df.columns:
                df[col] = df[col].astype(float)
        
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

                record = GFPCResults(**row_dict)

                # Check if record already exists
                existing_record = self.session.query(GFPCResults).filter(
                    GFPCResults.SDG == record.SDG,
                    GFPCResults.BatchID == record.BatchID,
                    GFPCResults.SampleID == record.SampleID,
                    GFPCResults.Analyte == record.Analyte,
                    GFPCResults.Reporting == record.Reporting
                ).first()

                # If the record exists
                if existing_record:
                    # Check for exact match, if so do nothing
                    if existing_record:
                        if self.objects_are_identical(record, existing_record, ignore_fields=["Iteration", "Reporting"]):
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

processor = GFPCProcessor()

df = processor.parse_file(file_path)