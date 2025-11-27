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
from lims.config import lab_lists
from lims.config.tables import (
    Base, GAMMAResults
)
from lims.data_transformations.data_processing import data_processing
import csv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pandas as pd

class GAMMAProcessor:
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
                row_type = row[0]

                if row_type == 'A':
                    a = row

                elif row_type == 'B':
                    b = row

                elif row_type == 'C':
                    c = row
                    row_data = {'A': a, 'B': b, 'C': c}
                    parsed_data.append(row_data)

            columns = [
                "SampleID", "Detector", "Geometry", "AcquisitionDateTime", 
                "AnalysisDateTime", "Livetime", "EnergyCalibrationDateTime", 
                "EfficiencyCalibrationDateTime", 
                
                "SampleDateTime", "Aliquot", "AliquotUnits", 
                "ResultUnits", "ErrorMultiplier", 
                
                "Analyte", "NuclideDetected", "Result", 
                "ResultError", "MDA", "MDAError", 
                "ResultMDARatio"
            ]

            # Initialize a list to store all sample rows
            sample_rows = []

            for sample in parsed_data:
                sample_data = [sample['A'][1], sample['A'][2], sample['A'][3], sample['A'][4], sample['A'][5], sample['A'][6], sample['A'][7], sample['A'][8], 
                sample['B'][2], sample['B'][3], sample['B'][4], sample['B'][5], sample['B'][6], sample['C'][1], sample['C'][2], sample['C'][3], sample['C'][4], sample['C'][5], 
                sample['C'][6], sample['C'][7]]

                sample_rows.append(sample_data)
            
            df = pd.DataFrame(sample_rows, columns=columns)

            df['Livetime'] = df['Livetime'].astype(str).str.split('.').str[0].astype(float)

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
        df.insert(0, 'Method', 'GAMMA')

        # BatchID, SDG, Matrix
        df = data_processing.process_df(df)

        batch_id = df['BatchID'].unique().tolist()[0]

        # PrepDate
        df = GetPrepsheetData.get_prep_datetime(batch_id, df)

        # PrepsheetFilePath
        df = GetPrepsheetData.get_prepsheet_path(batch_id, df)

        # ResultType 
        df = GetResultType.get_result_types(df)

        df = AnalytePreprocessing.process(df)

        from core import recovery

        prepsheet = GetPrepsheetData.get_prepsheet_data(batch_id)

        df = recovery.get_recovery(df, prepsheet)

        print("Converting aliquot units...")
        df['AliquotUnits'] = (
            df['AliquotUnits']
            .astype(str)
            .str.strip()
            .str.lower()
            .map(lab_lists.aliquot_unit_mapping)
            .fillna(df['AliquotUnits'])  # Keep original if not found in mapping
        )

        df['ResultUnits'] = df['ResultUnits'].astype(str).str.strip() + "/" + df['AliquotUnits'].astype(str).str.strip()

        # List of numeric columns that should be floats
        float_columns = [
            'Aliquot', 'LiveTime', 'ErrorMultiplier', 'Result', 'ResultError', 'MDA', 'MDAError', 'ResultMDARatio', 'PercentRecovery'
        ]

        datetime_columns = [
           'AcquisitionDateTime', 'AnalysisDateTime', 'EnergyCalibrationDateTime', 'EfficiencyCalibrationDateTime', 'SampleDateTime', 'PrepDateTime'
        ]

        matrix = df['Matrix'].unique().tolist()[0]

        if matrix == 'SO':
            # Copy any AC-228 for each corresponding analyte in the list, then remove the AC-228 rows.
            replacement_analytes = ['TH-232', 'RA-228']

            # Filter rows where Analyte == "AC-228"
            ac_rows = df[df['Analyte'] == "AC-228"]

            # Duplicate these rows for each new analyte
            expanded_rows = pd.concat(
                [ac_rows.assign(Analyte=new_analyte) for new_analyte in replacement_analytes],
                ignore_index=True
            )

            # Append expanded rows back to original dataframe
            df = pd.concat([df, expanded_rows], ignore_index=True)

        # # Remove all rows where Analyte == "AC-228"
        # df = df[df['Analyte'] != "AC-228"].reset_index(drop=True)

        from pandas.api.types import is_string_dtype, is_object_dtype

        for col in float_columns:
            if col not in df.columns:
                continue

            s = df[col].astype(str)

            s = (
                s.str.replace(r"[^\d\.\-eE+]", "", regex=True)  # keep numeric chars only
                .str.replace(r"\.$", "", regex=True)          # remove trailing dots (e.g., "3600.")
                .replace("", pd.NA)
            )

            df[col] = pd.to_numeric(s, errors='coerce').astype("Float64")
            
        for col in datetime_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        return df
                     
    def upload_data(self, df):
        from sqlalchemy.exc import IntegrityError  # keep import inside function

        try:
            self.init_session()

            for _, row in df.iterrows():
                row_dict = row.to_dict()

                # Provisional values so record can be built
                row_dict.setdefault("Iteration", 1)
                row_dict.setdefault("Reporting", True)

                candidate = GAMMAResults(**row_dict)

                # Logical key excludes Iteration/Reporting
                base_filters = (
                    (GAMMAResults.SDG == candidate.SDG),
                    (GAMMAResults.BatchID == candidate.BatchID),
                    (GAMMAResults.SampleID == candidate.SampleID),
                    (GAMMAResults.Analyte == candidate.Analyte),
                )

                existing_rows = (
                    self.session.query(GAMMAResults)
                    # add `.with_for_update()` here if you need concurrency safety
                    .filter(*base_filters)
                    .all()
                )

                # Check for an identical row (ignoring Iteration, Reporting)
                identical = None
                for ex in existing_rows:
                    if self.objects_are_identical(candidate, ex, ignore_fields=["Iteration", "Reporting"]):
                        identical = ex
                        break

                if identical:
                    # If we already have this exact row, skip inserting
                    if not identical.Reporting:
                        identical.Reporting = True
                        # Demote any other Reporting=True rows
                        for ex in existing_rows:
                            if ex is not identical and ex.Reporting:
                                ex.Reporting = False
                                self.session.add(ex)
                        self.session.add(identical)
                    continue

                # New version → bump iteration, make it current
                max_iter = max([ex.Iteration for ex in existing_rows], default=0)
                candidate.Iteration = max_iter + 1
                candidate.Reporting = True

                # Demote previous current rows
                for ex in existing_rows:
                    if ex.Reporting:
                        ex.Reporting = False
                        self.session.add(ex)

                self.session.add(candidate)

            self.session.commit()
            print("Successfully committed results!")

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
             
processor = GAMMAProcessor()

df = processor.parse_file(file_path)