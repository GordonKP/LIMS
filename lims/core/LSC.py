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

        from lims.core.upload_results import UploadResults
        uploader = UploadResults()
        uploader.check_results(df)

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
        
        from lims.data_transformations.data_processing import data_processing
        df = data_processing.process_df(df)

        batch_id_list = df['BatchID'].unique().tolist()

        if len(batch_id_list) > 1:
            from lims.core.popups import Popup
            Popup.debugger("Multiple Batches Detected", "More than one analytical batch was detected, this is not a supported feature as of 11/26/2025.\nThis feature is coming soon.")
            return None
        else:
            batch_id = batch_id_list[0]

        # # SDG and Matrix
        # df = MergeDQO.merge_dqo(batch_id, df)

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

        print(df['Aliquot'])

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

        # Apply analyte mapping
        from lims.config.lab_lists import analyte_map
        df['Analyte'] = df['Analyte'].map(analyte_map).fillna(df['Analyte'])

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
        elif analyte in ["Y90", 'SR90']:
            return "LSCSR"
        elif analyte == 'AB':
            return 'LSCAB'
        else:
            return None
                     
    def upload_data(self, df):
        from sqlalchemy import func
        from sqlalchemy.exc import IntegrityError
        try:
            self.init_session()

            for _, row in df.iterrows():
                row_dict = row.to_dict()
                # Don't set Iteration/Reporting yet; we'll decide below.
                base_filters = (
                    (LSCResults.SDG == row_dict["SDG"]),
                    (LSCResults.BatchID == row_dict["BatchID"]),
                    (LSCResults.SampleID == row_dict["SampleID"]),
                    (LSCResults.Analyte == row_dict["Analyte"]),
                )

                # Pull all existing rows for this logical record
                existing_rows = (
                    self.session.query(LSCResults)
                    .filter(*base_filters)
                    .all()
                )

                # Build a provisional record (Iteration/Reporting will be set later)
                record = LSCResults(**{**row_dict})

                # If an identical row (ignoring Iteration/Reporting) already exists, skip
                for ex in existing_rows:
                    if self.objects_are_identical(record, ex, ignore_fields=["Iteration", "Reporting"]):
                        # ensure one latest Reporting=True remains (optional)
                        if not ex.Reporting:
                            ex.Reporting = True
                            self.session.add(ex)
                        break
                else:
                    # Not identical to any → create a new iteration
                    max_iter = max([ex.Iteration for ex in existing_rows], default=0)
                    record.Iteration = max_iter + 1
                    record.Reporting = True
                    # Flip any previous "current" records to Reporting=False
                    for ex in existing_rows:
                        if ex.Reporting:
                            ex.Reporting = False
                            self.session.add(ex)
                    self.session.add(record)

            self.session.commit()
            print("Successfully committed results!")

        except IntegrityError as ie:
            self.session.rollback()
            print(f"Integrity error (likely PK/unique): {ie}")
            # optional: log details or re-raise
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