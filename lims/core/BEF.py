import sys
import os

# Get the absolute path of the parent directory
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the parent directory to sys.path
sys.path.append(parent_dir)

from lims.packages.DQO import MergeDQO
from lims.packages.ResultType import GetResultType
from lims.config.config import CONNECTION_STRING
from lims.config.tables import (
    Base, BEFResults
)
from lims.config import lab_lists
from lims.config.file_paths import prepsheet_directory
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pandas as pd
from lims.config.file_paths import images_directory
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QDialog, QLabel, QVBoxLayout, QFormLayout, QHBoxLayout,
    QWidget, QDialogButtonBox, QScrollArea, QLineEdit, QPushButton
)

class CalibrationCurve(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Enter Calibration Information")
        self.setWindowIcon(QIcon(os.path.join(images_directory, "leidos_logo.ico")))

        self.inputs = []  # Will store list of (expected_edit, result_edit) pairs

        layout = QVBoxLayout()
        form = QFormLayout()

        header_label = QLabel("Input the expected and actual results for calibrations in RFU.")
        form.addRow(header_label)

        header_row = QWidget()
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Expected (PPB)"))
        header_layout.addWidget(QLabel("Result (RFU)"))
        header_row.setLayout(header_layout)
        form.addRow(header_row)

        # === Scroll Area for Dynamic Rows ===
        self.scroll_area = QScrollArea()
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout()

        self.scroll_widget.setLayout(self.scroll_layout)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.scroll_widget)

        layout.addLayout(form)
        layout.addWidget(self.scroll_area)

        # === Add Row Button ===
        add_button = QPushButton("Add Calibration Row")
        add_button.clicked.connect(self.add_row)
        layout.addWidget(add_button)

        # === Dialog Buttons ===
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

        # Add default 5 rows (optional)
        for _ in range(1):
            self.add_row()

    def add_row(self):
        row_widget = QWidget()
        row_layout = QHBoxLayout()

        expected_edit = QLineEdit()
        result_edit = QLineEdit()

        row_layout.addWidget(expected_edit)
        row_layout.addWidget(result_edit)

        row_widget.setLayout(row_layout)
        self.scroll_layout.addWidget(row_widget)

        self.inputs.append((expected_edit, result_edit))

    def get_data(self):
        # Extracts floats from the inputs
        expected = []
        result = []
        for expected_edit, result_edit in self.inputs:
            try:
                e = float(expected_edit.text())
                r = float(result_edit.text())
                expected.append(e)
                result.append(r)
            except ValueError:
                continue  # Skip rows with invalid inputs
        return expected, result

class BEFProcessor:
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
        # Open and read the JSON file
        with open(file_path, 'r') as file:
            json_file = json.load(file)  # Load JSON data into a dictionary

        df = self.create_df(json_file)

        file_path = self.create_processed_file(df)

        df.insert(0, 'ProcessedDataFilePath', file_path)

        self.upload_data(df)

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
    
    def create_df(self, json_file):
        print(json_file)
        batch_id = json_file['batch_id']
        method = 'BEF'
        prepsheet_path = os.path.join(prepsheet_directory, f"{json_file['prepsheet_name']}.json")
        
        prep_date = json_file.get("Prep Data")[0]['Prep Date']
        prep_time = json_file.get("Prep Data")[0]['Prep Time']

        from datetime import datetime

        prep_datetime = datetime.strptime(f"{prep_date} {prep_time}", "%m-%d-%Y %H:%M")

        sample_dict = json_file['Samples']

        df = pd.DataFrame.from_dict(sample_dict)

        df["PrepDateTime"] = prep_datetime

        df.insert(0, 'BatchID', batch_id)

        df.insert(0, 'Method', method)

        df.insert(0, 'ResultUnits', 'ug/100cm2')

        df.insert(0, 'PrepsheetFilePath', prepsheet_path)

        df.columns = [col.replace(" ", "") for col in df.columns]

        # Combine and convert to datetime format
        df["AnalysisDateTime"] = pd.to_datetime(df["AnalysisDate"] + " " + df["AnalysisTime"])

        df = df.drop(columns=['AnalysisDate', 'AnalysisTime', 'Analyst'])

        df = GetResultType.get_result_types(df)

        df = MergeDQO.merge_dqo(batch_id, df)

        df.insert(0, "Analyte", 'BERYLLIUM')

        print(df)

        # Convert RFU to float
        df['RFU'] = df['RFU'].astype(float)

        import numpy as np
        from sklearn.linear_model import LinearRegression
        from sklearn.metrics import r2_score

        dialog = CalibrationCurve()
        if dialog.exec_() == QDialog.Accepted:
            expected, result = dialog.get_data()
            print("Cal Conc. (PPB):", expected)
            print("Results (RFU):", result)

        # Calibration concentrations in known order
        cal_ppb = np.array(expected).reshape(-1, 1)

        # Extract the first 5 RFU values from the df
        cal_rfu = np.array(result).reshape(-1, 1)

        # Fit a linear regression model
        model = LinearRegression()
        model.fit(cal_ppb, cal_rfu)

        # Get slope and intercept
        slope = model.coef_[0][0]
        intercept = model.intercept_[0]

        # Get R^2
        predicted_rfu = model.predict(cal_rfu)
        r_squared = r2_score(cal_ppb, predicted_rfu)

        # convert RFU to PPB
        def rfu_to_ppb(rfu):
            return float((rfu - intercept) / slope)

        # Apply it to the whole dataframe
        df['PPB'] = df['RFU'].apply(rfu_to_ppb)

        # convert PPB to ug/100cm2
        def ppb_to_result(ppb):
            return float(ppb / 10)

        # Apply it to the whole dataframe
        df['Result'] = df['PPB'].apply(ppb_to_result)

        df.insert(0, 'CalibrationCurve', r_squared)
        df.insert(0, 'Slope', r_squared)
        df.insert(0, 'Intercept', r_squared)

        print(df)

        from core import recovery
        from lims.packages.Prepsheet import GetPrepsheetData

        prepsheet = GetPrepsheetData.get_prepsheet_data(batch_id)

        if 'LCS' in df['ResultType'].unique().tolist():
            df = recovery.get_recovery(df, prepsheet)

        # List of numeric columns that should be floats
        float_columns = [
            'Aliquot', 'Result', 'PercentRecovery'
        ]

        datetime_columns = [
           'AnalysisDateTime', 'PrepDateTime'
        ]

        for col in float_columns:
            if col in df.columns:
                df[col] = df[col].astype(float)

        for col in datetime_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        return df
    
    def upload_data(self, df):
        from sqlalchemy.inspection import inspect
        try:
            self.init_session()

            # Get valid columns from the BEFResults model
            valid_columns = {c_attr.key for c_attr in inspect(BEFResults).mapper.column_attrs}

            for index, row in df.iterrows():
                # Convert row to dictionary
                row_dict = row.to_dict()

                # Filter the dictionary to only include valid model columns
                filtered_row_dict = {k: v for k, v in row_dict.items() if k in valid_columns}

                # Set default values
                filtered_row_dict.setdefault("Iteration", 1)
                filtered_row_dict.setdefault("Reporting", True)

                record = BEFResults(**filtered_row_dict)

                # Check if record already exists
                existing_record = self.session.query(BEFResults).filter(
                    BEFResults.SDG == record.SDG,
                    BEFResults.BatchID == record.BatchID,
                    BEFResults.SampleID == record.SampleID,
                    BEFResults.Reporting == record.Reporting
                ).first()

                # If the record exists
                if existing_record:
                    if self.objects_are_identical(record, existing_record, ignore_fields=["Iteration", "Reporting"]):
                        print("Identical row exists (ignoring Iteration), continuing...")
                        continue  # Skip insertion
                    else:
                        print("Non-identical record exists, adding new iteration...")
                        record.Iteration = existing_record.Iteration + 1
                        existing_record.Reporting = False
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
             
processor = BEFProcessor()

df = processor.parse_file(file_path)