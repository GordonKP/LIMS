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
        
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        # Prompt user for LCSA SRS and LCSB SRS
        lcsasrs, ok1 = QInputDialog.getText(None, "Input SRS", "LCSA SRS:")
        lcsbsrs, ok2 = QInputDialog.getText(None, "Input SRS", "LCSB SRS:")

        # If user cancels, set default values or handle accordingly
        if not ok1:
            lcsasrs = ""
        if not ok2:
            lcsbsrs = ""

        # Reshape data for Alpha and Beta
        alpha_df = df[["SampleID", "Aliquot", "AnalysisDateTime", "LiveTime", 
                    "AlphaActivityConc", "AlphaActivityConcUnc", "AlphaMDAConc", 
                    "PresetLiveTime"]].copy()
        
        alpha_df.columns = ["SampleID", "Aliquot", "AnalysisDateTime", "LiveTime", 
                            "Result", "ResultError", "MDA", 
                            "PresetLiveTime"]
        
        alpha_df = alpha_df[~alpha_df["SampleID"].str.contains("LCSB", na=False)]
        
        alpha_df["Analyte"] = "GALPHA"

        beta_df = df[["SampleID", "Aliquot", "AnalysisDateTime", "LiveTime", 
                    "BetaActivityConc", "BetaActivityConcUnc", "BetaMDAConc", 
                    "PresetLiveTime"]].copy()
        
        beta_df.columns = ["SampleID", "Aliquot", "AnalysisDateTime", "LiveTime", 
                            "Result", "ResultError", "MDA", 
                            "PresetLiveTime"]
        
        beta_df = beta_df[~beta_df["SampleID"].str.contains("LCSA", na=False)]

        beta_df["Analyte"] = "GBETA"

        df = pd.concat([alpha_df, beta_df], ignore_index=True)

        df.insert(0, 'SRS', '')

        # Result Types
        df = GetResultType.get_result_types(df)

        df.loc[df['ResultType'] == 'LCSA', 'SRS'] = lcsasrs
        df.loc[df['ResultType'] == 'LCSB', 'SRS'] = lcsbsrs

        # Insert GFPC as method
        df.insert(0, 'Method', 'GFPC')
        
        df['AliquotUnits'] = df['Aliquot'].astype(str).str.split().str[1]
        df['Aliquot'] = df['Aliquot'].astype(str).str.split().str[0]
        
        df['ResultUnits'] = df['Result'].astype(str).str.split().str[1]
        df['Result'] = df['Result'].astype(str).str.split().str[0]

        df['ResultError'] = df['ResultError'].astype(str).str.split().str[0]

        df['MDA'] = df['MDA'].astype(str).str.split().str[0]

        # BatchID
        batch_id = GetBatchID.get_batch_id(sample_id=df.iloc[0]['SampleID'], method=df.iloc[0]['Method'])
        print(f"Batch ID: {batch_id}")

        df.insert(0, 'BatchID', batch_id)

        # PrepDate
        df = GetPrepsheetData.get_prep_datetime(batch_id, df)

        # PrepsheetFilePath
        df = GetPrepsheetData.get_prepsheet_path(batch_id, df)
        
        # SDG and Matrix
        df = MergeDQO.merge_dqo(batch_id, df)

        df = AnalytePreprocessing.process(df)

        # Column manipulation
        df['LiveTime'] = df['LiveTime'].str.replace(',', '', regex=True)

        from lims.core import recovery

        prepsheet = GetPrepsheetData.get_prepsheet_data(batch_id)

        srs_list = df['SRS'].unique().tolist()

        datetime_columns = ['AnalysisDateTime','PrepDateTime']

        for col in datetime_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        from datetime import datetime

        for srs in srs_list:
            lcs_df = df[df['SRS'] == srs]
            for index, row in lcs_df.iterrows():
                if 'LCS' in row['ResultType']:
                    try:
                        self.init_session()

                        half_life, activity_date = self.session.query(RADCerts.HalfLife, RADCerts.SourceActivityDate).filter(RADCerts.SRS == srs).first()

                        # Need to backdate the activity to solution
                        activity_datetime = datetime.combine(activity_date, datetime.min.time())

                        days_passed = (row['AnalysisDateTime'] - activity_datetime).days

                        backdated_activity = round(float(row['Result'])/(0.5**(float(days_passed)/float(half_life))), 4)

                        df.at[index, 'Result'] = backdated_activity
                        
                    except Exception as e:
                        print(f"An exception occurred getting SRS data: {e}")
                    finally:
                        if self.session:
                            self.session.close()

        # Handle recoveries
        # Initialize LCS and MS dictionaries and lists
        lcs_list = list(prepsheet.get('LCSs', {}).values())

        print("LCS List")
        print(lcs_list)

        # LCSs dictionary population
        lcs_dict = {}
        if lcs_list:
            known_value_dict = {}
            for lcs_data in lcs_list:
                lot_number = lcs_data.get('lot_number')
                print(lot_number)
                amount = lcs_data.get('amount', 0)
                print(amount)
                try:
                    amount = float(amount)
                except (ValueError, TypeError):
                    amount = 0

                if amount == 0:
                    continue

                try:
                    session = self.init_session()

                    lcs_query = self.session.query(ConsumableManagement).filter(
                        ConsumableManagement.LotNumber == lot_number
                    ).first()

                    if lcs_query:
                        analytes = lcs_query.Component
                        analyte_list = [a.strip() for a in analytes.split(",")]

                        known_value = lcs_query.Activity

                        known_value_list = [float(k.strip()) for k in known_value.split(",")]

                        if len(known_value_list) != len(analyte_list):
                            print(f"Consumable {lot_number} input incorrectly!")
                        else:
                            known_value_dict = dict(zip(analyte_list, known_value_list))
                            known_value_dict = {key: {'LCSValue': value * amount} for key, value in known_value_dict.items()}

                        lcs_dict.update(known_value_dict)

                        print(lcs_dict)

                except Exception as e:
                    print(f"An exception occurred getting LCSs: {e}")
                finally:
                    if session:
                        session.close()

        # Iterate over DataFrame rows and calculate recovery
        for index, row in df.iterrows():
            result_type = row['ResultType']
            sample_id = row['SampleID']
            analyte = row['Analyte']
            srs = row['SRS']

            # Default values for parent_id and known_value
            parent_id = None
            known_value = None

            # Set parent_id and known_value based on result type
            if result_type == 'LCSA':
                parent_id_series = df[(df['ResultType'] == 'REG') & (df['Analyte'] == analyte) & (df['SRS'] == srs)]['SampleID']
                parent_id = parent_id_series.iloc[0] if not parent_id_series.empty else None
                print(parent_id)
                if analyte in lcs_dict:
                    known_value = lcs_dict[analyte]['LCSValue']
                    print(known_value)
            elif result_type == 'LCSB':
                parent_id = df[(df['ResultType'] == 'REG') & (df['Analyte'] == analyte) & (df['SRS'] == srs)]['SampleID']
                if analyte in lcs_dict:
                    known_value = lcs_dict[analyte]['LCSValue']

            # If known_value is not found, set recovery to 0.0
            if known_value is not None:
                # Check if parent row exists and calculate recovery
                if "LCS" in result_type:
                    recovery = round((float(row['Result']) * float(row['Aliquot'])) / (float(known_value)) * 100, 2)
                else:
                    recovery = 0.0
            else:
                recovery = 0.0

            # Assign recovery to the DataFrame
            df.at[index, 'PercentRecovery'] = recovery

        # Ensure the PercentRecovery column is of float type
        df['PercentRecovery'] = df['PercentRecovery'].astype(float)

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

processor = GFPCProcessor()

df = processor.parse_file(file_path)