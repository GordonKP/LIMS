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
    Base, METResults, SampleLogin
)
import csv
import numpy as np
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
        print(file_ext)
        if file_ext == '.csv':
            with open(file_path, mode='r', encoding='utf-8-sig', newline='') as f:
                reader = csv.reader(f)
                data = list(reader)

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

        df['Method'] = 'MET'

        # ResultType 
        df = GetResultType.get_result_types(df)

        # Isotope is analyte+mass, analyte is the element full name
        df['Isotope'] = df['Analyte'].astype(str)+'-'+df['Mass'].astype(str)
        print(df['Isotope'])

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

        print("Before Recovery")
        df = recovery.get_recovery(df, prepsheet)
        print("After Recovery")

        from lims.core import limits

        df = limits.GetLimits.query_limits(df)

        for index, row in df.iterrows():
            try:
                lod = float(row['LOD'])
                multiplier = float(row['DilutionFactor'])
                aliquot = float(row['Aliquot'])

                if pd.notna(lod) and pd.notna(multiplier) and pd.notna(aliquot) and aliquot != 0:
                    adjusted_lod = round((lod * multiplier), 4)
                    df.at[index, 'LOD'] = adjusted_lod
                    df.at[index, 'DL'] = adjusted_lod/2
                    df.at[index, 'LOQ'] = adjusted_lod*2
                else:
                    df.at[index, 'LOD'] = 0  # ✅ Ensure invalid calc results in SQL-safe NULL
            except Exception as e:
                print(f"Error on row {index}: {e}")
                df.at[index, 'LOD'] = 0  # Ensure row gets cleaned even on error

        # Make a temporary column
        df.insert(0, 'AirVolume', 1.0)

        df = df.rename(columns={'Result': 'InitialResult'})
        df['InitialResult'] = pd.to_numeric(df['InitialResult'], errors='coerce')

        df.insert(0, 'Result', df['InitialResult'])

        matrix = df['Matrix'].unique().tolist()[0]

        # Check SampleLogin if the method is AF
        if matrix == 'AF':
            # Get SampleLogin Data
            air_volume_dict = {}
            try:
                self.init_session()
                for sdg, sample_id in df[['SDG', 'SampleID']].drop_duplicates().itertuples(index=False):
                    sample_login_query = (
                        self.session.query(SampleLogin.SampleVolume)
                        .filter(
                            SampleLogin.SDG == sdg,
                            SampleLogin.SampleID == sample_id
                        )
                        .first()
                    )

                    if sample_login_query:
                        air_volume_dict[(sdg, sample_id)] = sample_login_query.SampleVolume
                    else:
                        air_volume_dict[(sdg, sample_id)] = 1.0

                df['AirVolume'] = df[['SDG', 'SampleID']].apply(
                    lambda row: air_volume_dict.get((row['SDG'], row['SampleID']), 1.0),
                    axis=1
                )

                df['Notes'] = df['AirVolume']

                df.loc[df['Notes'] != 1.0, 'ResultUnits'] = 'ug/m3'

                mask = df['AirVolume'] != 1.0
                df.loc[mask, 'Result'] = df.loc[mask, 'InitialResult'] / (df.loc[mask, 'AirVolume'] * 0.001)

                df.loc[mask, 'Aliquot'] = (df.loc[mask, 'AirVolume'] * 0.001)
                df.loc[mask, 'AliquotUnits'] = 'm3'

                for column in ['DL', 'LOD', 'LOQ']:
                    df.loc[mask, column] = df.loc[mask, column] / (df.loc[mask, 'AirVolume'] * 0.001)
            finally:
                self.session.close()
        else:
            df['Result'] = df['InitialResult']

        df.drop(columns=['AirVolume'])

        # List of numeric columns that should be floats
        float_columns = [
            'SampleWeightVolume', 'FinalWeightVolume', 'DilutionMultiplier', 'DilutionFactor', 'ISTDRefMass', 'InitialResult', 'Result', 'ResultRSD', 'CPSMean',
            'CPSRSD' 'Aliquot', 'TuneStep', 'PercentRecovery', 'LOD', 'DL', 'LOQ'
        ]

        datetime_columns = [
           'AnalysisDateTime', 'PrepDateTime'
        ]

        import numpy as np

        for col in float_columns:
            print(col)
            if col in df.columns:
                # df[col] = df[col].replace('', 0)
                # df[col] = df[col].replace(' ', 0)
                # df[col] = df[col].replace('N/A', 0)
                # df[col] = df[col].replace(np.nan, 0)
                # df[col] = df[col].replace('nan', 0)
                # df[col] = df[col].astype(float)
                df[col] = pd.to_numeric(df[col], errors='coerce')

        for col in datetime_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        for col in ['CPSRep1', 'CPSRep2', 'CPSRep3', 'CPSRep4', 'CPSRep5']:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: str(x) if pd.notna(x) else '')

        return df
                     
    def upload_data(self, df):
        from sqlalchemy.exc import IntegrityError  # keep import inside the function
        import numpy as np
        import pandas as pd

        try:
            self.init_session()

            rejected_samples = []
            rows_to_commit = []  # keep pending inserts to handle same-batch duplicates safely

            # Precompute model columns
            valid_columns = set(c.name for c in METResults.__table__.columns)

            # Helper: key used for versioning in METResults
            def version_key(d):
                return (d["SDG"], d["BatchID"], d["SampleID"], d["Analyte"], d["AnalysisDateTime"])

            for _, row in df.iterrows():
                row_dict = row.to_dict()

                # Default fields (provisional)
                row_dict.setdefault("Iteration", 1)
                row_dict.setdefault("Reporting", True)

                # Keep only model columns & convert NaNs to None
                filtered = {k: v for k, v in row_dict.items() if k in valid_columns}
                filtered = {
                    k: (None if (isinstance(v, float) and (pd.isna(v) or (isinstance(v, float) and np.isnan(v))))
                        else v)
                    for k, v in filtered.items()
                }

                # CPSRep rejection check (uses the original row’s values)
                rep_columns = [f"CPSRep{i}" for i in range(1, 5 + 1)]
                rejected_count = sum(
                    1 for col in rep_columns
                    if str(row_dict.get(col, "")).strip().upper() == "REJECTED"
                )
                if rejected_count > 2:
                    rejected_samples.append([
                        str(row_dict.get("SampleID", "")),
                        str(row_dict.get("METFileName", "")),
                        str(row_dict.get("METBatchName", "")),
                        str(row_dict.get("Analyte", "")),
                    ])

                # Build a candidate instance (Iteration/Reporting will be finalized later)
                candidate = METResults(**filtered)
                key = version_key(filtered)

                # Fetch existing versions for this logical key from DB
                existing_versions = (
                    self.session.query(METResults)
                    # Uncomment if you need race safety in multi-writer environments:
                    # .with_for_update()
                    .filter(
                        METResults.SDG == key[0],
                        METResults.BatchID == key[1],
                        METResults.SampleID == key[2],
                        METResults.Analyte == key[3],
                        METResults.AnalysisDateTime == key[4],
                    )
                    .all()
                )

                # Also consider rows we’re about to insert in this session for the same key
                pending_versions = [r for r in rows_to_commit if version_key({
                    "SDG": r.SDG,
                    "BatchID": r.BatchID,
                    "SampleID": r.SampleID,
                    "Analyte": r.Analyte,
                    "AnalysisDateTime": r.AnalysisDateTime
                }) == key]

                # If any (existing or pending) is identical (ignoring Iteration/Reporting), skip insert
                identical_found = False
                for ex in existing_versions + pending_versions:
                    if self.objects_are_identical(candidate, ex, ignore_fields=["Iteration", "Reporting"]):
                        print("Identical row exists (ignoring Iteration/Reporting), skipping upload.")
                        identical_found = True
                        break
                if identical_found:
                    continue

                # Demote previous current rows (both DB + pending)
                for ex in existing_versions + pending_versions:
                    if ex.Reporting:
                        ex.Reporting = False
                        self.session.add(ex)

                # Compute next iteration safely: consider both DB + pending
                latest_iter = 0
                if existing_versions:
                    latest_iter = max(latest_iter, max(ev.Iteration for ev in existing_versions))
                if pending_versions:
                    latest_iter = max(latest_iter, max(pv.Iteration for pv in pending_versions))

                candidate.Iteration = latest_iter + 1
                candidate.Reporting = True

                # Stage insert
                self.session.add(candidate)
                rows_to_commit.append(candidate)

            # After preparing all rows, handle “too many CPS rejections” prompt
            if rejected_samples:
                from PyQt5.QtWidgets import QMessageBox
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Information)
                msg.setWindowTitle("Rejections Detected")

                text = ""
                for sample_row in rejected_samples:
                    text += ", ".join(sample_row) + "\n"

                msg.setText(f"{text}\nContains more than two CPS Rep rejections. Would you like to proceed?")
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
                # No flagged rejections: single atomic commit
                self.session.commit()
                print("All results committed successfully.")

        except IntegrityError as ie:
            self.session.rollback()
            print(f"Integrity error (likely PK/unique): {ie}")
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