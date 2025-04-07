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
    Base, GABResults
)
import csv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pandas as pd

# Create a log file in the same directory as the .exe
log_file = os.path.join(os.path.dirname(__file__), "debug_log.txt")

# Redirect print output and errors to log file
sys.stdout = open(log_file, "w", encoding="utf-8")
sys.stderr = sys.stdout  # Capture errors too

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
            next(reader, None)  # Skip the header

            parsed_data = []

            parsed_data = [row for row in reader]

        columns = ['SampleID', 'Aliquot', 'AnalysisDateTime', 'LiveTime', 
                   'AlphaActivityConc', 'AlphaActivityConcUnc', 'AlphaMDAConc', 
                   'BetaActivityConc', 'BetaActivityConcUnc', 'BetaMDAConc', 'PresetLiveTime', 'Detector']
        
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
                    "PresetLiveTime", "Detector"]].copy()
        
        alpha_df.columns = ["SampleID", "Aliquot", "AnalysisDateTime", "LiveTime", 
                            "Result", "ResultError", "MDA", 
                            "PresetLiveTime", "Detector"]
        
        alpha_df = alpha_df[~alpha_df["SampleID"].str.contains("LCSB", na=False)]
        
        alpha_df["Analyte"] = "GAlpha"

        beta_df = df[["SampleID", "Aliquot", "AnalysisDateTime", "LiveTime", 
                    "BetaActivityConc", "BetaActivityConcUnc", "BetaMDAConc", 
                    "PresetLiveTime", "Detector"]].copy()
        
        beta_df.columns = ["SampleID", "Aliquot", "AnalysisDateTime", "LiveTime", 
                            "Result", "ResultError", "MDA", 
                            "PresetLiveTime", "Detector"]
        
        beta_df = beta_df[~beta_df["SampleID"].str.contains("LCSA", na=False)]

        beta_df["Analyte"] = "GBeta"

        df = pd.concat([alpha_df, beta_df], ignore_index=True)

        df.insert(0, 'SRS', '')

        # Result Types
        df = GetResultType.get_result_types(df)

        df.loc[df['ResultType'] == 'LCSA', 'SRS'] = lcsasrs
        df.loc[df['ResultType'] == 'LCSB', 'SRS'] = lcsbsrs

        # Insert GAB as method
        df.insert(0, 'Method', 'GAB')

        # BatchID
        batch_id = GetBatchID.get_batch_id(sample_id=df.iloc[0]['SampleID'], method=df.iloc[0]['Method'])

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

        columns_with_units = ['Aliquot', "Result", "ResultError", "MDA"]

        df['AliquotUnits'] = df['Aliquot'].astype(str).str.split().str[1]

        df['ResultUnits'] = df['Result'].astype(str).str.split().str[1]

        from lims.core import recovery

        prepsheet = GetPrepsheetData.get_prepsheet_data(batch_id)

        df = recovery.get_recovery(df, prepsheet)

        float_columns = ['Aliquot', "Result", "ResultError", "MDA", 'PresetLiveTime', 'PercentRecovery']
        
        datetime_columns = ['AnalysisDateTime','PrepDateTime']

        for col in columns_with_units:
            df[col] = df[col].astype(str).str.split().str[0]
        
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

                record = GABResults(**row_dict)

                # Check if record already exists
                existing_record = self.session.query(GABResults).filter(
                    GABResults.SDG == record.SDG,
                    GABResults.BatchID == record.BatchID,
                    GABResults.SampleID == record.SampleID,
                    GABResults.Analyte == record.Analyte,
                    GABResults.Reporting == record.Reporting
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

processor = GABProcessor()

df = processor.parse_file(file_path)