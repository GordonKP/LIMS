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
import lims.config.tables as tables
from lims.config.file_paths import images_directory
import csv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pandas as pd
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLabel, QLineEdit, QDialogButtonBox

class TracerInputDialog(QDialog):
    def __init__(self, tracer, analytes):
        super().__init__()

        self.setWindowTitle("Enter Tracer Information")
        self.setWindowIcon(QIcon(os.path.join(images_directory, "leidos_logo.ico")))

        self.inputs = {}
        layout = QVBoxLayout()
        form = QFormLayout()

        srs_input = QLineEdit()

        form.addRow(QLabel(f"Input the SRS and known activities for impurities.\n\nActivities should utilize the same units as listed on certificate.\n"))

        form.addRow(QLabel(f"{tracer} SRS:"), srs_input)

        self.inputs["SRS"] = srs_input

        for analyte in analytes:
            input_field = QLineEdit()
            form.addRow(QLabel(f"{analyte} Activity:"), input_field)
            self.inputs[analyte] = input_field

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def get_results(self):
        results = {}
        for analyte, input_field in self.inputs.items():
            text = input_field.text()
            try:
                value = float(text) if text.strip() else 0.0
            except ValueError:
                value = 0.0
            results[analyte] = value
        return results

class AlphaSpecProcessor:
    def __init__(self):
        self.session = None
        self.engine = None

    def init_session(self):
        # Initialize the SQLAlchemy session
        self.engine = create_engine(CONNECTION_STRING)
        tables.Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def parse_file(self, file_path):
        parsed_data = []
        with open(file_path, mode='r') as file:
            reader = csv.reader(file)

            for row in reader:
                if row[0] == "A":
                    a_data = row
                elif row[0] == "B":
                    b_data = row
                elif row[0] == "C":
                    c_data = row
                    sample_data = {"A": a_data, "B": b_data, "C": c_data}
                    parsed_data.append(sample_data)
        
        df = self.create_df(parsed_data)

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

    def create_df(self, parsed_data):
        columns = [
            "AlphaBatchID", "Detector", "AnalysisDateTime", "SampleDate", "Aliquot", "SampleID",
            "ResultUnits", "AliquotUnits", "TracerAliquot", "FileName", "PercentAbundance",
            "MDAConfidenceFactor", "MDALLDConstant",
            "EnergyCalibrationDateTime", "EfficiencyCalibrationDateTime", "BackgroundFile",
            "TracerRecovery", "AlphaChamber", "ChamberEfficiency", "AcquisitionDateTime",
            "LiveTime", "TracerFWHM", "Analyte", "NetArea", "BackgroundArea", "Result", "ResultError", "MDA"
        ]

        sample_rows = []

        for sample in parsed_data:
            sample_row = [sample['A'][1], sample['A'][2], sample['A'][3], sample['A'][4], sample['A'][5], sample['A'][6],
                          sample['A'][9], sample['A'][10], sample['A'][11], sample['A'][12], sample['A'][13], sample['A'][14], sample['A'][15],
                          sample['B'][4], sample['B'][5], sample['B'][6], sample['B'][8], sample['B'][10], sample['B'][11], sample['B'][12], sample['B'][13], sample['B'][14],
                          sample['C'][4], sample['C'][5], sample['C'][6], sample['C'][7], sample['C'][8], sample['C'][9]]
            sample_rows.append(sample_row)

        df = pd.DataFrame(sample_rows, columns=columns)

        print(df)

        # Method
        df['Method'] = df.apply(lambda row: self.generate_analyte_column(row), axis=1)

        # BatchID
        batch_id = GetBatchID.get_batch_id(sample_id=df.iloc[0]['SampleID'], method=df.iloc[0]['Method'])

        df['BatchID'] = batch_id

        # SDG and Matrix
        df = MergeDQO.merge_dqo(batch_id, df)

        # AliquotUnits
        df = GetPrepsheetData.get_aliquot_units(batch_id, df)

        # PrepDate
        df = GetPrepsheetData.get_prep_datetime(batch_id, df)

        # PrepsheetFilePath
        df = GetPrepsheetData.get_prepsheet_path(batch_id, df)

        # ResultType 
        df = GetResultType.get_result_types(df)

        df.loc[~df['Analyte'].str.contains("-", na=False), 'ResultType'] = "TRACER"

        df = AnalytePreprocessing.process(df)
        
        from PyQt5.QtWidgets import QApplication, QInputDialog
        
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        tracer = df.loc[df['ResultType'] == 'TRACER', 'Analyte'].unique().tolist()[0]

        unique_impurity_analytes = df.loc[df['ResultType'] != 'TRACER', 'Analyte'].unique().tolist()

        tracer_data, mass, units = self.fetch_tracer_data(tracer, unique_impurity_analytes)

        if all([tracer_data, mass, units]):
            # Make a copy of the result column before transformation
            df['InitialResult'] = df['Result']

            for index, row in df.iterrows():
                if row['ResultType'] != "TRACER":
                    analyte = row['Analyte']
                    df.loc[index] = self.adjust_results(row, float(tracer_data[analyte]), mass, units)
                else:
                    continue
        else:
            df['InitialResult'] = df['Result']

        # List of numeric columns that should be floats
        float_columns = [
            "Aliquot", "TracerAliquot", "InitialResult", "Result", "ResultError", "TracerRecovery",
            "TracerFWHM", "ChamberEfficiency", "PercentAbundance", "MDAConfidenceFactor",
            "LiveTime", "BackgroundArea", "NetArea", "MDA", "MDALLDConstant"
        ]

        datetime_columns = [
            "SampleDate", "PrepDateTime", "AcquisitionDateTime", "AnalysisDateTime",
            "EnergyCalibrationDateTime", "EfficiencyCalibrationDateTime"
        ]

        for col in float_columns:
            if col in df.columns:
                df[col] = df[col].astype(float)

        for col in datetime_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        return df
    
    def fetch_tracer_data(self, tracer, unique_impurity_analytes):
        tracer_data = {}
        mass = None
        units = None

        if tracer:
            dialog = TracerInputDialog(tracer, unique_impurity_analytes)
            if dialog.exec_() == QDialog.Accepted:
                tracer_data = dialog.get_results()

                try:
                    from sqlalchemy import desc
                    self.init_session()

                    query = (
                        self.session.query(tables.RADCerts)
                        .filter(
                            tables.RADCerts.PrincipleRadionuclide == tracer,
                            tables.RADCerts.SRS == tracer_data['SRS'],
                            tables.RADCerts.ConsumableType == 'Tracer'
                        )
                        .order_by(desc(tables.RADCerts.SolutionPrepDate))
                        .first()
                    )

                    if query:
                        tracer_activity = round(float(query.SourceActivity), 4)
                        mass = float(query.SolutionMass)
                        units = str(query.Units)
                        # Get tracer activity and drop the SRS
                        tracer_data[tracer] = tracer_activity
                        del tracer_data['SRS']

                except Exception as e:
                    print(f"An exception occurred while fetching tracer data: {e}")
            else:
                print("User canceled tracer input.")
                tracer_data = {analyte: 0.0 for analyte in unique_impurity_analytes}

        return tracer_data, mass, units
    
    def adjust_results(self, row, tracer_activity, mass, units):
        if units == 'Bq':
            # Convert to pCi
            tracer_activity = (tracer_activity * 60)/2.22
        elif units == 'dpm':
            # Convert to pCi
            tracer_activity = tracer_activity / 2.22
        else:
            # Units are already pCi
            pass

        # Get pCi/g
        tracer_activity = tracer_activity/mass
        adjusted_activity = float(tracer_activity) * float(row['TracerAliquot']) * (float(row['TracerRecovery'])/100)
        added_activity = adjusted_activity / float(row['Aliquot'])
        final_activity = float(round(float(row['Result']) - added_activity, 4))

        row['Result'] = final_activity

        return row

    def generate_analyte_column(self, row):
        analyte = row["Analyte"].upper()
        if "PU" in analyte:
            return "ISOPu"
        elif "U" in analyte:
            return "ISOU"
        elif "TH" in analyte:
            return "ISOTh"
        elif "AM" in analyte:
            return "ISOAm"
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

                record = tables.AlphaSpecResults(**row_dict)

                # Check if record already exists
                existing_record = self.session.query(tables.AlphaSpecResults).filter(
                    tables.AlphaSpecResults.SDG == record.SDG,
                    tables.AlphaSpecResults.BatchID == record.BatchID,
                    tables.AlphaSpecResults.SampleID == record.SampleID,
                    tables.AlphaSpecResults.Analyte == record.Analyte,
                    tables.AlphaSpecResults.Reporting == record.Reporting
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
             
processor = AlphaSpecProcessor()

df = processor.parse_file(file_path)