import sys
import os

# Get the absolute path of the parent directory
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the parent directory to sys.path
sys.path.append(parent_dir)

from lims.packages.Prepsheet import GetPrepsheetData
from lims.packages.BatchID import GetBatchID
from lims.packages.DQO import MergeDQO
from lims.packages.ResultType import GetResultType
from lims.packages.Analyte import AnalytePreprocessing
from lims.config.config import CONNECTION_STRING
from lims.config.tables import (
    Base, LSCResults
)
import csv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pandas as pd

class LSCProcessor:
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
        file_ext = os.path.splitext(file_path)[1].lower()

        columns = ['S#', 'SampleID', 'Analyte', 'AnalysisDate', 'AnalysisTime', 'LiveTime', 'BKGLiveTime', 'tSIE', 'Efficiency', 'CPM', 'BKGCPM', 'NCPM', 'PercentRecovery',
                    'Aliquot', 'AliquotUnits', 'Result', 'ResultUnits', 'ResultError', 'MDA', 'DL']

        if file_ext == ".csv":
            # Read CSV normally
            df = pd.read_csv(file_path, names=columns, encoding='utf-8')
        elif file_ext in [".xls", ".xlsx"]:
            # Read Excel file
            df = pd.read_excel(file_path, names=columns, engine="openpyxl")
        else:
            raise ValueError("Unsupported file type. Only CSV and Excel files are supported.")

        df = df.drop(columns=['S#'])

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
        # Method
        df['Method'] = df.apply(self.generate_analyte_column, axis=1)

        print(df)

        print(df.iloc[0]['SampleID'])

        print(df.iloc[0]['Method'])

        # BatchID
        batch_id = GetBatchID.get_batch_id(sample_id=df.iloc[0]['SampleID'], method=df.iloc[0]['Method'])

        df['BatchID'] = batch_id

        # SDG and Matrix
        df = MergeDQO.merge_dqo(batch_id, df)

        # PrepDate
        df = GetPrepsheetData.get_prep_datetime(batch_id, df)

        # PrepsheetFilePath
        df = GetPrepsheetData.get_prepsheet_path(batch_id, df)

        # ResultType 
        df = GetResultType.get_result_types(df)

        df = AnalytePreprocessing.process(df)

        df['AnalysisDateTime'] = pd.to_datetime(df['AnalysisDate'].astype(str) + ' ' + df['AnalysisTime'].astype(str), errors='coerce')

        df = df.drop(columns=['AnalysisDate', 'AnalysisTime'])

        # List of numeric columns that should be floats
        float_columns = [
            "Aliquot", "LiveTime", 'BKGLiveTime', 'tSIE', 'CPM', 'BKGCPM', 'NCPM', 'PercentRecovery', 'ResultError', 'MDA', 'DL' "Result", "ResultError"
        ]

        datetime_columns = [
            "PrepDateTime", "AnalysisDateTime"
        ]

        for col in float_columns:
            if col in df.columns:
                df[col] = df[col].astype(float)

        for col in datetime_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        return df
    
    def generate_analyte_column(self, row):
        analyte = row["Analyte"].upper()
        if "PU" in analyte:
            return "LSCPu"
        elif "GALPHA" in analyte:
            return "LSCTotal"
        elif "GBETA" in analyte:
            return "LSCTotal"
        elif "RA" in analyte:
            return "LSCRa"
        else:
            return None
                     
    def upload_data(self, df):
        try:
            self.init_session()

            for index, row in df.iterrows():
                # Convert row to dictionary
                row_dict = row.to_dict()

                # Set default iteration and reporting values
                row_dict.setdefault("Iteration", 1)
                row_dict.setdefault("Reporting", True) 

                record = LSCResults(**row_dict)

                # Check if record already exists
                existing_record = self.session.query(LSCResults).filter(
                    LSCResults.SDG == record.SDG,
                    LSCResults.BatchID == record.BatchID,
                    LSCResults.SampleID == record.SampleID,
                    LSCResults.Analyte == record.Analyte,
                    LSCResults.Reporting == record.Reporting
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
             
processor = LSCProcessor() 

df = processor.parse_file(file_path)