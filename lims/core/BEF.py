import sys
import os

# Get the absolute path of the parent directory
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the parent directory to sys.path
sys.path.append(parent_dir)

from lims.config.config import CONNECTION_STRING
from lims.config.tables import (
    Base, BEFResults
)
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pandas as pd

class BEFProcessor():
    def __init__(self):
        self.session = None
        self.engine = None

    def init_session(self):
        # Initialize the SQLAlchemy session
        self.engine = create_engine(CONNECTION_STRING)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def ingest_csv(self, file_path):
        file_name, extension = os.path.splitext(file_path)

        # Verify to make sure that the file is .csv
        if "csv" in extension.lower():
            pass
        else:
            from PyQt5.QtWidgets import QMessageBox
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("File Error")
            msg.setText("Invalid file type. Please provide a .CSV file.")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()

        df = pd.read_csv(file_path)

        # Clean up trailing blank lines or rows of commas
        df = df.replace(r'^\s*$', pd.NA, regex=True).dropna(how='all')

        # Optional sanity check
        print(f"After cleanup: {len(df)} rows")

        # Verify that all columns passed are correct
        expected_columns = ['SDG', 'BatchID', 'Method', 'SampleID', 'Matrix', 'ResultType', 'Analyte', 'Result', 'ResultUnits',
                            'PPB', 'RFU', 'Aliquot', 'AliquotUnits', 'CalibrationCurve', 'PrepDateTime', 'AnalysisDateTime', 'PercentRecovery', 'PrepsheetFilePath']
        
        passed_columns = df.columns.tolist()

        for column in passed_columns:
            if column in expected_columns:
                pass
            else:
                from PyQt5.QtWidgets import QMessageBox
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Critical)
                msg.setWindowTitle("Data Error")
                msg.setText("One or more columns in the exported data are incorrect.")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.exec_()

        # Add columns and values to df
        df = self.transform_df(df)

        processed_file_path = df['ProcessedDataFilePath'].unique().tolist()[0]

        df.to_csv(processed_file_path)

        self.upload_data(df)
         
    def transform_df(self, df):
        # Check to make sure there is only one batch id
        df['BatchID'] = df['BatchID'].astype(str).str.strip()

        unique_batch_ids = [bid for bid in df['BatchID'].unique().tolist() if bid.strip() != '']
        print(unique_batch_ids)

        if len(unique_batch_ids) == 1:
            pass
        else:
            from PyQt5.QtWidgets import QMessageBox
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Multiple Batch IDs detected")
            msg.setText(f"Please ensure there is only one BatchID in this export. Look for typos and/or white spaces.\nBatch IDs found: {unique_batch_ids}")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()

        batch_id = unique_batch_ids[0]

        import re
        pattern = re.compile(r"^\d{2}SL\d{4}BEF\d+$")
        if pattern.match(batch_id):
            pass
        else:
            from PyQt5.QtWidgets import QMessageBox
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Batch ID not in correct form.")
            msg.setText(f"The batch ID for this returned as {batch_id}.\nPlease ensure it is of the form: <sdg><BEF><batch iteration>.\nExample: 25SL0001BEF1.")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()

        from lims.config.file_paths import processed_data_directory
        processed_data_filepath = os.path.join(processed_data_directory, 'BEF', f"{batch_id}.csv")

        df['ProcessedDataFilePath'] = str(processed_data_filepath)

        df['Iteration'] = 1
        df['Reporting'] = 1

        # Enforce dtypes
        dtype_map = {
            "SDG": "string",
            "BatchID": "string",
            "Method": "string",
            "SampleID": "string",
            "Matrix": "string",
            "ResultType": "string",
            "Analyte": "string",
            "Result": "float64",
            "ResultUnits": "string",
            "PercentRecovery": "float64",
            "PPB": "float64",
            "RFU": "float64",
            "Aliquot": "float64",
            "AliquotUnits": "string",
            "CalibrationCurve": "float64",
            "PrepDateTime": "datetime64[ns]",
            "AnalysisDateTime": "datetime64[ns]",
            "PrepsheetFilePath": "string",
            "ProcessedDataFilePath": "string",
            "Iteration": "int64",
            "Reporting": "boolean",
        }

        safe_map = {k: v for k, v in dtype_map.items() if not v.startswith("datetime")}
        df = df.astype(safe_map)
        df["PrepDateTime"] = pd.to_datetime(df["PrepDateTime"], errors="coerce")
        df["AnalysisDateTime"] = pd.to_datetime(df["AnalysisDateTime"], errors="coerce")

        # Apply analyte mapping
        from lims.config.lab_lists import analyte_map
        df['Analyte'] = df['Analyte'].map(analyte_map)

        return df
    
    def clean_row(self, row_dict):
        clean = {}
        for k, v in row_dict.items():
            # Convert pandas NaN to None (SQL-safe)
            if pd.isna(v):
                clean[k] = None
            # Coerce numerics safely
            elif isinstance(v, (float, int)):
                # Optional: round to match SQL precision (like DECIMAL(10,5))
                clean[k] = float(round(v, 6))
            else:
                clean[k] = v
        return clean
    
    def upload_data(self, df):
        from sqlalchemy.exc import IntegrityError  # import kept inside the function per your request

        try:
            self.init_session()

            for _, row in df.iterrows():
                row_dict = row.to_dict()

                # Don't preset Iteration/Reporting; we'll decide based on existing rows
                row_dict = self.clean_row(row_dict)

                record = BEFResults(**row_dict)

                # Logical identity (exclude Iteration/Reporting from the match set)
                base_filters = (
                    (BEFResults.SDG == record.SDG),
                    (BEFResults.BatchID == record.BatchID),
                    (BEFResults.SampleID == record.SampleID),
                    (BEFResults.Analyte == record.Analyte),
                )

                # Get all prior versions for this logical record
                existing_rows = (
                    self.session.query(BEFResults)
                    .filter(*base_filters)
                    .all()
                )

                # If an identical row already exists (ignoring Iteration/Reporting), skip inserting
                identical = None
                for ex in existing_rows:
                    if self.objects_are_identical(record, ex, ignore_fields=["Iteration", "Reporting"]):
                        identical = ex
                        break

                if identical:
                    # Optional: ensure the identical row is the "current" one
                    if not identical.Reporting:
                        identical.Reporting = True
                        # flip any other currently-reporting rows to False
                        for ex in existing_rows:
                            if ex is not identical and ex.Reporting:
                                ex.Reporting = False
                                self.session.add(ex)
                        self.session.add(identical)
                    # Nothing new to insert
                    continue

                # Not identical to any existing row -> this is a new version
                max_iter = max([ex.Iteration for ex in existing_rows], default=1)
                record.Iteration = max_iter + 1
                record.Reporting = True

                # Ensure only one Reporting=True per logical record
                for ex in existing_rows:
                    if ex.Reporting:
                        ex.Reporting = False
                        self.session.add(ex)

                # Insert the new current record
                self.session.add(record)

            self.session.commit()
            print("Successfully committed results!")

        except IntegrityError as ie:
            # Likely a PK/unique collision or race; rollback and surface
            print(f"Integrity error (likely PK/unique): {ie}")
            self.session.rollback()

            from PyQt5.QtWidgets import QMessageBox
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Integrity Error")
            msg.setText(f"{ie}")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()

        except Exception as e:
            print(f"An exception occurred: {e}")
            self.session.rollback()

            from PyQt5.QtWidgets import QMessageBox
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("SQL Exception")
            msg.setText(f"{e}")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()

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

processor = BEFProcessor()

df = processor.ingest_csv(file_path)