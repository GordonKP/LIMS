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
from lims.config.config import CONNECTION_STRING
from lims.config.tables import (
    Base, AlphaSpecResults
)
import csv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pandas as pd

class AlphaSpecProcessor:
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
        df['Method'] = df.apply(self.generate_analyte_column, axis=1)

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

        df.loc[~df['Analyte'].str.contains("-", na=False), 'ResultType'] = "Tracer"

        # List of numeric columns that should be floats
        float_columns = [
            "Aliquot", "TracerAliquot", "Result", "ResultError", "TracerRecovery",
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

                record = AlphaSpecResults(**row_dict)

                # Check if record already exists
                existing_record = self.session.query(AlphaSpecResults).filter(
                    AlphaSpecResults.SDG == record.SDG,
                    AlphaSpecResults.BatchID == record.BatchID,
                    AlphaSpecResults.SampleID == record.SampleID,
                    AlphaSpecResults.Analyte == record.Analyte,
                    AlphaSpecResults.Reporting == record.Reporting
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