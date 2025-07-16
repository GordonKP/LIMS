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

        sample_id = df[df['ResultType'] == 'REG'].iloc[0]['SampleID']

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
                
        df['BatchID'] = batch_id

        df = MergeDQO.merge_dqo(batch_id, df)

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

        # List of numeric columns that should be floats
        float_columns = [
            'SampleWeightVolume', 'FinalWeightVolume', 'DilutionMultiplier', 'DilutionFactor', 'ISTDRefMass', 'Result', 'ResultRSD', 'CPSMean',
            'CPSRSD' 'Aliquot', 'TuneStep', 'PercentRecovery', 'LOD'
        ]

        datetime_columns = [
           'AnalysisDateTime', 'AnalysisDateTime'
        ]

        import numpy as np

        print("About to convert to float and DT")

        for col in float_columns:
            print(col)
            if col in df.columns:
                df[col] = df[col].replace('', 0)
                df[col] = df[col].replace('N/A', 0)
                df[col] = df[col].replace(np.nan, 0)
                df[col] = df[col].astype(float)
                df[col] = pd.to_numeric(df[col], errors='coerce')

        for col in datetime_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        
        print("Finished converting to float and DT")
        
        for index, row in df.iterrows():
            try:
                lod = float(row['LOD'])
                multiplier = float(row['DilutionFactor'])
                aliquot = float(row['Aliquot'])

                if pd.notna(lod) and pd.notna(multiplier) and pd.notna(aliquot) and aliquot != 0:
                    adjusted_lod = round((lod * multiplier) / aliquot, 4)
                    df.at[index, 'LOD'] = adjusted_lod
                else:
                    df.at[index, 'LOD'] = 0  # ✅ Ensure invalid calc results in SQL-safe NULL
                    print(f"Skipped row {index} due to invalid LOD calc: lod={lod}, multiplier={multiplier}, aliquot={aliquot}")
            except Exception as e:
                print(f"Error on row {index}: {e}")
                df.at[index, 'LOD'] = 0  # Ensure row gets cleaned even on error

        print("Finished doing LOD stuff")

        return df
                     
    def upload_data(self, df):
        try:
            self.init_session()

            rejected_samples = []
            rows_to_commit = []

            for index, row in df.iterrows():
                row_dict = row.to_dict()

                row_dict.setdefault("Iteration", 1)
                row_dict.setdefault("Reporting", True)

                valid_columns = set(c.name for c in METResults.__table__.columns)
                filtered_row_dict = {k: v for k, v in row_dict.items() if k in valid_columns}

                # Check for CPSRep rejection count
                rep_columns = [f'CPSRep{i}' for i in range(1, 6)]
                rejected_count = sum(1 for col in rep_columns if str(row_dict.get(col, '')).strip().upper() == 'REJECTED')

                if rejected_count > 2:
                    reject_info = [
                        str(row_dict.get('SampleID', '')),
                        str(row_dict.get('METFileName', '')),
                        str(row_dict.get('METBatchName', '')),
                        str(row_dict.get('Analyte', ''))
                    ]
                    rejected_samples.append(reject_info)

                # Fetch all matching rows for SDG, BatchID, SampleID, Analyte, and AnalysisDateTime
                existing_versions = self.session.query(METResults).filter(
                    METResults.SDG == row_dict["SDG"],
                    METResults.BatchID == row_dict["BatchID"],
                    METResults.SampleID == row_dict["SampleID"],
                    METResults.Analyte == row_dict["Analyte"],
                    METResults.AnalysisDateTime == row_dict["AnalysisDateTime"]
                ).all()

                # Check for identical match
                identical_found = False
                for existing in existing_versions:
                    temp_record = METResults(**filtered_row_dict)
                    if self.objects_are_identical(temp_record, existing, ignore_fields=["Iteration", "Reporting"]):
                        print("Identical row exists (ignoring Iteration), skipping upload.")
                        identical_found = True
                        break

                if identical_found:
                    continue

                # Mark old ones as Reporting = False
                for existing in existing_versions:
                    existing.Reporting = False
                    self.session.add(existing)

                self.session.commit()  # Must commit old deactivation before insert

                # Add new record with incremented iteration
                latest_iter = max((r.Iteration for r in existing_versions), default=0)
                filtered_row_dict["Iteration"] = latest_iter + 1
                filtered_row_dict["Reporting"] = True

                new_record = METResults(**filtered_row_dict)
                self.session.add(new_record)
                rows_to_commit.append(new_record)

            # Show rejected message if needed
            if rejected_samples:
                from PyQt5.QtWidgets import QMessageBox
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Information)
                msg.setWindowTitle("Rejections Detected")
                text = ""

                for sample_row in rejected_samples:
                    row_str = ", ".join(sample_row)
                    text += f"{row_str}\n"

                msg.setText(f"{text}\nContains more than two CPS Rep Rejections. Would you like to proceed?")
                msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                msg.setDefaultButton(QMessageBox.No)

                result = msg.exec_()
                if result == QMessageBox.Yes:
                    self.session.commit()
                    print("Successfully committed results including rejected samples.")
                else:
                    self.session.rollback()
                    print("Rejected samples rolled back. No results committed.")
            else:
                # No rejections, safe to commit all at once
                self.session.commit()
                print("All results committed successfully.")

        except Exception as e:
            print(f"An exception occurred: {e}")
            self.session.rollback()
        finally:
            self.session.close()

    def objects_are_identical(self, obj1, obj2, ignore_fields=None):
        from sqlalchemy.inspection import inspect
        import datetime

        def normalize(value):
            import datetime

            if value in [None, '', 'nan', 'NaN', 'NULL', '<NA>']:
                return None

            if isinstance(value, str):
                value = value.strip()
                # Try numeric conversion
                try:
                    return float(value)
                except ValueError:
                    return value  # It's a real string

            if isinstance(value, float):
                return round(value, 6)

            if isinstance(value, datetime.datetime):
                return value.replace(microsecond=0)

            return value

        if ignore_fields is None:
            ignore_fields = []

        obj1_dict = {
            c.key: normalize(getattr(obj1, c.key))
            for c in inspect(obj1).mapper.column_attrs
            if c.key not in ignore_fields
        }

        obj2_dict = {
            c.key: normalize(getattr(obj2, c.key))
            for c in inspect(obj2).mapper.column_attrs
            if c.key not in ignore_fields
        }

        if obj1_dict != obj2_dict:
            return False

        return True

processor = METProcessor()

df = processor.parse_file(file_path)