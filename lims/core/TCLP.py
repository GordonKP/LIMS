import sys
import os

# Get the absolute path of the parent directory
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the parent directory to sys.path
sys.path.append(parent_dir)

from lims.packages.BatchID import GetBatchID
from lims.packages.Prepsheet import GetPrepsheetData
from lims.packages.DQO import MergeDQO
from lims.packages.ResultType import GetResultType
from lims.packages.Analyte import AnalytePreprocessing
from lims.config.config import CONNECTION_STRING
from lims.config.tables import (
    Base, METResults
)
import csv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pandas as pd
from core import recovery

class METProcessor:
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
        data = []
        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext == '.csv':
            with open(file_path, mode='r', encoding='utf-8') as file:
                reader = csv.reader(file)
                for row in reader:
                    data.append(row)

        elif file_ext in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path, header=None)  # No header to keep consistent with csv
            data = df.values.tolist()

        else:
            raise ValueError("Unsupported file type. Only .csv and .xlsx are supported.")

        columns = ['SampleID', 'AnalysisDateTime', 'DilutionFactor', 
                'Notes', 'METFileName', 'METBatchName', 'METPath',
                'Analyst', 'Instrument', 'SampleWeightVolume', 
                'FinalWeightVolume', 'DilutionMultiplier', 'TuneStep', 
                'Analyte', 'ElementName', 'Mass', 'ISTDRefMass', 'Result', 
                'ResultRSD', 'CPSMean', 'CPSRep1', 'CPSRep2', 'CPSRep3', 
                'CPSRep4', 'CPSRep5', 'CPSRSD', 'ResultUnits']

        sample_rows = data[1:]
            
        df = pd.DataFrame(sample_rows, columns=columns)

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
        # Convert the sample ID column to all caps where applicable, this is to accurately generate result type.
        df['SampleID'] = df['SampleID'].str.upper()

        df['Instrument'] = 'ICPMS'

        df['Method'] = 'TCLP'

        # ResultType 
        df = GetResultType.get_result_types(df)

        # Isotope is analyte+mass, analyte is the element full name
        df['Isotope'] = df['Analyte']+'-'+df['Mass']

        df = df.drop(columns=['Mass', 'Analyte'])

        df = df.rename(columns={'ElementName':'Analyte'})
        df['Analyte'] = df['Analyte'].str.upper()

        # Apply analyte mapping
        from lims.config.lab_lists import analyte_map
        df['Analyte'] = df['Analyte'].map(analyte_map).fillna(df['Analyte'])

        from lims.data_transformations.data_processing import data_processing
        df = data_processing.process_df(df)

        batch_id_list = df['BatchID'].unique().tolist()

        if len(batch_id_list) > 1:
            from lims.core.popups import Popup
            Popup.debugger("Multiple Batches Detected", "More than one analytical batch was detected, this is not a supported feature as of 11/26/2025.\nThis feature is coming soon.")
            return None
        else:
            batch_id = batch_id_list[0]

        # Get aliquot
        df = GetPrepsheetData.get_aliquot_amounts(batch_id, df)

        print(df[['SampleID', 'Aliquot']])

        # AliquotUnits
        df = GetPrepsheetData.get_aliquot_units(batch_id, df)

        # PrepDate
        df = GetPrepsheetData.get_prep_datetime(batch_id, df)

        # PrepsheetFilePath
        df = GetPrepsheetData.get_prepsheet_path(batch_id, df)

        df = AnalytePreprocessing.process(df)

        import numpy as np

        prepsheet = GetPrepsheetData.get_prepsheet_data(batch_id)

        df = recovery.get_recovery(df, prepsheet)

        print("Recovery done")

        from lims.core import limits

        df = limits.GetLimits.query_limits(df)

        print("Limits done")

        # # List of numeric columns that should be floats
        # float_columns = [
        #     'SampleWeightVolume', 'FinalWeightVolume', 'DilutionMultiplier', 'DilutionFactor', 'ISTDRefMass', 'Result', 'ResultRSD', 'CPSMean',
        #     'CPSRSD' 'Aliquot', 'TuneStep', 'PercentRecovery', 'LOD'
        # ]

        # datetime_columns = [
        #    'AnalysisDateTime', 'AnalysisDateTime'
        # ]

        # import numpy as np

        # print("About to convert to float and DT")

        # for col in float_columns:
        #     print(col)
        #     if col in df.columns:
        #         df[col] = df[col].replace('', 0)
        #         df[col] = df[col].replace('N/A', 0)
        #         df[col] = df[col].replace(np.nan, 0)
        #         df[col] = df[col].astype(float)
        #         df[col] = pd.to_numeric(df[col], errors='coerce')

        # for col in datetime_columns:
        #     if col in df.columns:
        #         df[col] = pd.to_datetime(df[col], errors="coerce")
        
        print("Finished converting to float and DT")
        
        for index, row in df.iterrows():
            try:
                # Safely convert or replace None/NaN with 0
                dl = float(row['DL']) if pd.notna(row['DL']) else 0
                lod = float(row['LOD']) if pd.notna(row['LOD']) else 0
                loq = float(row['LOQ']) if pd.notna(row['LOQ']) else 0
                multiplier = float(row['DilutionFactor']) if pd.notna(row['DilutionFactor']) else 1

                if all(pd.notna([dl, lod, loq, multiplier])):
                    adjusted_dl = dl * multiplier
                    adjusted_lod = lod * multiplier
                    adjusted_loq = loq * multiplier

                    df.at[index, 'DL'] = adjusted_dl 
                    df.at[index, 'LOD'] = adjusted_lod
                    df.at[index, 'LOQ'] = adjusted_loq 
                else:
                    df.at[index, 'DL'] = 0
                    df.at[index, 'LOD'] = 0
                    df.at[index, 'LOQ'] = 0

            except Exception as e:
                df.at[index, 'DL'] = 0
                df.at[index, 'LOD'] = 0
                df.at[index, 'LOQ'] = 0

        print("Finished doing LOD stuff")

        met_dtypes = {
            "SDG": "string",
            "BatchID": "string",
            "Method": "string",
            "SampleID": "string",
            "Matrix": "string",
            "ResultType": "string",
            "Analyte": "string",
            "Isotope": "string",
            
            "Aliquot": "float",
            "SampleWeightVolume": "float",
            "FinalWeightVolume": "float",
            "DilutionFactor": "float",
            "DilutionMultiplier": "float",
            
            "AliquotUnits": "string",
            
            "Result": "float",
            "ResultRSD": "float",
            "ResultUnits": "string",
            
            "PercentRecovery": "float",
            "LOD": "float",
            "LOQ": "float",
            
            "CPSMean": "float",
            
            "CPSRep1": "string",
            "CPSRep2": "string",
            "CPSRep3": "string",
            "CPSRep4": "string",
            "CPSRep5": "string",
            
            "CPSRSD": "float",
            
            "ISTDRefMass": "float",
            
            "TuneStep": "Int64",  # Pandas nullable integer
            
            "Instrument": "string",
            
            "AnalysisDateTime": "datetime64[ns]",
            "PrepDateTime": "datetime64[ns]",
            
            "Notes": "string",
            
            "METBatchName": "string",
            "METFileName": "string",
            "METPath": "string",
            "PrepsheetFilePath": "string",
            
            "Analyst": "string",
            "ProcessedDataFilePath": "string",
            
            "Iteration": "Int64",  # Pandas nullable int
            "Reporting": "boolean",  # Pandas nullable bool
            
            "InitialResult": "float",
            
            "DL": "float",
            "LOQ": "float",
        }

        for col, dtype in met_dtypes.items():
            if col in df.columns:
                df[col] = df[col].astype(dtype, errors="ignore")

        for col in [
            "Aliquot", "SampleWeightVolume", "FinalWeightVolume",
            "DilutionFactor", "DilutionMultiplier",
            "Result", "ResultRSD", "PercentRecovery",
            "LOD", "LOQ", "InitialResult", "DL",
            "CPSMean", "CPSRSD", "ISTDRefMass"
        ]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")   # converts strings → float or NaN

        df = df.replace({np.nan: None})

        return df
                     
    # def upload_data(self, df):
    #     from sqlalchemy.exc import IntegrityError  # per request: import inside function

    #     try:
    #         self.init_session()

    #         rejected_samples = []
    #         rows_to_commit = []  # track pending inserts for same-batch iteration math

    #         for _, row in df.iterrows():
    #             row_dict = row.to_dict()

    #             # Provisional defaults (final Iteration/Reporting set later)
    #             row_dict.setdefault("Iteration", 1)
    #             row_dict.setdefault("Reporting", True)

    #             # Keep only model columns
    #             valid_columns = set(c.name for c in METResults.__table__.columns)
    #             filtered_row_dict = {k: v for k, v in row_dict.items() if k in valid_columns}

    #             # --- CPSRep rejection count ---
    #             rep_columns = [f"CPSRep{i}" for i in range(1, 6)]
    #             rejected_count = sum(
    #                 1 for col in rep_columns
    #                 if str(row_dict.get(col, '')).strip().upper() == 'REJECTED'
    #             )
    #             if rejected_count > 2:
    #                 reject_info = [
    #                     str(row_dict.get('SampleID', '')),
    #                     str(row_dict.get('METFileName', '')),
    #                     str(row_dict.get('METBatchName', '')),
    #                     str(row_dict.get('Analyte', ''))
    #                 ]
    #                 rejected_samples.append(reject_info)

    #             # Build candidate & logical key (versioned by AnalysisDateTime as in your code)
    #             candidate = METResults(**filtered_row_dict)
    #             key = (
    #                 filtered_row_dict.get("SDG"),
    #                 filtered_row_dict.get("BatchID"),
    #                 filtered_row_dict.get("SampleID"),
    #                 filtered_row_dict.get("Analyte"),
    #                 filtered_row_dict.get("AnalysisDateTime"),
    #             )

    #             # Fetch existing versions from DB
    #             existing_versions = self.session.query(METResults).filter(
    #                 METResults.SDG == key[0],
    #                 METResults.BatchID == key[1],
    #                 METResults.SampleID == key[2],
    #                 METResults.Analyte == key[3],
    #                 METResults.AnalysisDateTime == key[4],
    #             ).all()

    #             # Also consider pending (same key) rows staged in this batch
    #             pending_versions = [
    #                 r for r in rows_to_commit
    #                 if (r.SDG, r.BatchID, r.SampleID, r.Analyte, r.AnalysisDateTime) == key
    #             ]

    #             # If any existing/pending row is identical (ignoring Iteration/Reporting), skip
    #             identical_found = False
    #             for ex in existing_versions + pending_versions:
    #                 if self.objects_are_identical(candidate, ex, ignore_fields=["Iteration", "Reporting"]):
    #                     print("Identical row exists (ignoring Iteration/Reporting), skipping upload.")
    #                     identical_found = True
    #                     break
    #             if identical_found:
    #                 continue

    #             # Demote previous currents (DB + pending)
    #             for ex in existing_versions + pending_versions:
    #                 if ex.Reporting:
    #                     ex.Reporting = False
    #                     self.session.add(ex)

    #             # Compute next iteration from both DB + pending
    #             latest_iter = 0
    #             if existing_versions:
    #                 latest_iter = max(latest_iter, max(ev.Iteration for ev in existing_versions))
    #             if pending_versions:
    #                 latest_iter = max(latest_iter, max(pv.Iteration for pv in pending_versions))

    #             candidate.Iteration = latest_iter + 1
    #             candidate.Reporting = True

    #             # Stage insert
    #             self.session.add(candidate)
    #             rows_to_commit.append(candidate)

    #         # --- Single commit at the end, with your PyQt confirmation if needed ---
    #         if rejected_samples:
    #             from PyQt5.QtWidgets import QMessageBox
    #             msg = QMessageBox()
    #             msg.setIcon(QMessageBox.Information)
    #             msg.setWindowTitle("Rejections Detected")

    #             text = ""
    #             for sample_row in rejected_samples:
    #                 text += ", ".join(sample_row) + "\n"

    #             msg.setText(f"{text}\nContains more than two CPS Rep Rejections. Would you like to proceed?")
    #             msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    #             msg.setDefaultButton(QMessageBox.No)

    #             result = msg.exec_()
    #             if result == QMessageBox.Yes:
    #                 self.session.commit()
    #                 print("Successfully committed results including rejected samples.")
    #             else:
    #                 self.session.rollback()
    #                 print("Rejected samples rolled back. No results committed.")
    #         else:
    #             self.session.commit()
    #             print("All results committed successfully.")

    #     except IntegrityError as ie:
    #         self.session.rollback()
    #         print(f"Integrity error (likely PK/unique): {ie}")
    #     except Exception as e:
    #         print(f"An exception occurred: {e}")
    #         self.session.rollback()
    #     finally:
    #         self.session.close()


    # def objects_are_identical(self, obj1, obj2, ignore_fields=None):
    #     from sqlalchemy.inspection import inspect
    #     import datetime

    #     def normalize(value):
    #         import datetime
    #         if value in [None, '', 'nan', 'NaN', 'NULL', '<NA>']:
    #             return None
    #         if isinstance(value, str):
    #             value = value.strip()
    #             try:
    #                 return float(value)
    #             except ValueError:
    #                 return value
    #         if isinstance(value, float):
    #             return round(value, 6)
    #         if isinstance(value, datetime.datetime):
    #             return value.replace(microsecond=0)
    #         return value

    #     if ignore_fields is None:
    #         ignore_fields = []

    #     obj1_dict = {
    #         c.key: normalize(getattr(obj1, c.key))
    #         for c in inspect(obj1).mapper.column_attrs
    #         if c.key not in ignore_fields
    #     }
    #     obj2_dict = {
    #         c.key: normalize(getattr(obj2, c.key))
    #         for c in inspect(obj2).mapper.column_attrs
    #         if c.key not in ignore_fields
    #     }
    #     return obj1_dict == obj2_dict

processor = METProcessor()

df = processor.parse_file(file_path)