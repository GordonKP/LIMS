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
from PyQt5.QtWidgets import QMessageBox

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
            # with open(file_path, mode='r') as file:
            #     reader = csv.reader(file)
            #     next(reader, 0)  # Skip the header

            #     parsed_data = []

            #     parsed_data = [row for row in reader]

            #     df = pd.DataFrame(parsed_data, columns=columns)
            QMessageBox.warning(None, "Wrong file type", "Please upload the file in .xlsx format.")
        elif file_ext in [".xls", ".xlsx"]:
            df = pd.read_excel(file_path, header=None, skiprows=1, names=columns, engine="openpyxl")
        else:
            raise ValueError("Unsupported file type. Only CSV and Excel files are supported.")

        df = df.drop(columns=['S#'])

        print(df)

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

        df['Analyte'] = df.apply(lambda row: 'SR-90' if row['Analyte'] == 'Y90' or row['Analyte'] == 'SR90' else row['Analyte'], axis=1)

        print(df)

        print("Made it past generate analyte column")

        # ResultType 
        df = GetResultType.get_result_types(df)

        print("Made it past get result types")

        df = AnalytePreprocessing.process(df)

        print("Made it to analyte preprocessing")

        method = df['Method'].unique().tolist()[0]

        batch_id = None
        sample_ids = df[df['ResultType'] == 'REG']['SampleID'].unique().tolist()

        for sample_id in sample_ids:
            print(f"Trying to get batch ID for {sample_id}, {method}")
            batch_id = GetBatchID.get_batch_id(sample_id, method)
            if batch_id is not None:
                break

        if batch_id is None:
            raise ValueError("No valid BatchID found for any REG sample.")
        
        print("got batch id")
        df['BatchID'] = batch_id
        print(df)

        # SDG and Matrix
        df = MergeDQO.merge_dqo(batch_id, df)

        print("Merged DQO")

        # PrepDate
        df = GetPrepsheetData.get_prep_datetime(batch_id, df)

        # PrepsheetFilePath
        df = GetPrepsheetData.get_prepsheet_path(batch_id, df)

        print("got prepsheet data")

        df['AnalysisDateTime'] = pd.to_datetime(df['AnalysisDate'].astype(str) + ' ' + df['AnalysisTime'].astype(str), errors='coerce')

        df = df.drop(columns=['AnalysisDate', 'AnalysisTime'])

        from core import recovery

        prepsheet = GetPrepsheetData.get_prepsheet_data(batch_id)

        df = recovery.get_recovery(df, prepsheet)

        # Change the LCS Aliquot units to grams
        df.loc[df['ResultType'] == 'LCS', 'AliquotUnits'] = 'g'
        
        from config import lab_lists
        df['AliquotUnits'] = (
            df['AliquotUnits']
            .astype(str)
            .str.strip()
            .str.lower()
            .map(lab_lists.aliquot_unit_mapping)
            .fillna(df['AliquotUnits'])  # Keep original if not found in mapping
        )

        dtype_dict = {
            'SDG': 'string',
            'BatchID': 'string',
            'Method': 'string',
            'SampleID': 'string',
            'Matrix': 'string',
            'ResultType': 'string',
            'Analyte': 'string',
            'Result': 'float64',
            'ResultUnits': 'string',
            'ResultError': 'float64',
            'Aliquot': 'float64',
            'AliquotUnits': 'string',
            'CPM': 'float64',
            'LiveTime': 'float64',
            'BKGCPM': 'float64',
            'BKGLiveTime': 'float64',
            'NCPM': 'float64',
            'tSIE': 'float64',
            'PercentRecovery': 'float64',
            'MDA': 'float64',
            'DL': 'float64',
            'Efficiency': 'float64',
            'PrepDateTime': 'datetime64[ns]',
            'AnalysisDateTime': 'datetime64[ns]',
            'PrepsheetFilePath': 'string',
            'ProcessedDataFilePath': 'string',
            'Iteration': 'int64',
            'Reporting': 'boolean',
        }

        for col, dtype in dtype_dict.items():
            if col in df.columns:
                df[col] = df[col].astype(dtype)

        float_columns = [
            'Result', 'ResultError', 'PercentRecovery', 'Aliquot',
            'CPM', 'LiveTime', 'BKGCPM', 'BKGLiveTime', 'NCPM',
            'tSIE', 'MDA', 'DL', 'Efficiency'
        ]
        import numpy as np
        for col in float_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')  # Make sure everything is float or NaN
                df[col] = df[col].replace([np.inf, -np.inf], np.nan)  # Replace infinities with NaN
                df[col] = df[col].fillna(0)

        return df
    
    def generate_analyte_column(self, row):
        analyte = row["Analyte"].upper()
        print("iterating through analytes")
        print(analyte)
        if "PU" in analyte:
            return "LSCPU"
        elif "GALPHA" in analyte:
            return "LSCAB"
        elif "GBETA" in analyte:
            return "LSCAB"
        elif "RA" in analyte:
            return "LSCRa"
        elif analyte in ["Y90", 'SR90']:
            return "LSCSR"
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
             
processor = LSCProcessor() 

df = processor.parse_file(file_path)