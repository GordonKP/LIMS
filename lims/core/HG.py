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
    Base, HGResults
)
import csv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pandas as pd

class HGProcessor:
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
            data = []

            for row in reader:
                data.append(row)

            columns = ['SampleID', 'AnalysisDate', 'AnalysisTime', 'InitialWeightVolume', 
                       'PrepVolume', 'VolumeUnits', 'SampleUnits', 'WeightUnits', 'Analyte',
                       'CalResult', 'CalResultUnits', 'Result', 'ResultUnits',
                       'RSD', 'PercentRecovery', 'Rep1', 'Date1', 'Time1', 'CalResult1', 'Result1',
                       'Rep2', 'Date2', 'Time2', 'CalResult2', 'Result2', 'Rep3', 'Date3', 'Time3',
                       'CalResult3', 'Result3']
            
            sample_rows = []

            for row in data[1::]:
                sample_rows.append(row)

            print(sample_rows)
            
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

        method = 'HG'

        df.insert(0, 'Method', method)

        # ResultType 
        df.insert(0, 'ResultType', '')
        df = GetResultType.get_result_types(df)

        df['Analyte'] = 'MERCURY'

        sample_id = df[df['ResultType'] == 'REG'].iloc[0]['SampleID']

        batch_id = None
        sample_ids = df[df['ResultType'] == 'REG']['SampleID'].unique().tolist()

        for sample_id in sample_ids:
            print(f"Trying to get batch ID for {sample_id}, {method}")
            batch_id = GetBatchID.get_batch_id(sample_id, method)
            if batch_id is not None:
                break

        if batch_id is None:
            raise ValueError("No valid BatchID found for any REG sample.")
                
        df.insert(0, "BatchID", batch_id)

        df = MergeDQO.merge_dqo(batch_id, df)

        # Get aliquot
        df = GetPrepsheetData.get_aliquot_amounts(batch_id, df)

        # AliquotUnits
        df = GetPrepsheetData.get_aliquot_units(batch_id, df)

        # PrepDate
        df = GetPrepsheetData.get_prep_datetime(batch_id, df)

        # PrepsheetFilePath
        df = GetPrepsheetData.get_prepsheet_path(batch_id, df)

        df = AnalytePreprocessing.process(df)

        import numpy as np
        
        from core import recovery

        prepsheet = GetPrepsheetData.get_prepsheet_data(batch_id)

        df = recovery.get_recovery(df, prepsheet)

        from lims.core import limits

        try:
            df['AnalysisDateTime'] = pd.to_datetime(
                df['AnalysisDate'] + ' ' + df['AnalysisTime'],
                format='%m/%d/%Y %I:%M:%S %p',
                errors='coerce'
            )
            
            df['Rep1DateTime'] = pd.to_datetime(
                df['Date1'] + ' ' + df['Time1'],
                format='%m/%d/%Y %I:%M:%S %p',
                errors='coerce'
            )

            df['Rep2DateTime'] = pd.to_datetime(
                df['Date2'] + ' ' + df['Time2'],
                format='%m/%d/%Y %I:%M:%S %p',
                errors='coerce'
            )

            df['Rep3DateTime'] = pd.to_datetime(
                df['Date3'] + ' ' + df['Time3'],
                format='%m/%d/%Y %I:%M:%S %p',
                errors='coerce'
            )

            df = df.drop(columns= ['AnalysisDate', 'AnalysisTime', 'Date1', 'Time1', 'Date2', 'Time2', 'Date3', 'Time3'])
        except Exception as e:
            print(f"An exception occurred: {e}")

        df = limits.GetLimits.query_limits(df)


        # List of numeric columns that should be floats
        float_columns = [
            'InitialWeightVolume', 'PrepVolume', 'CalResult', 'Result',
            'RSD', 'PercentRecovery', 'CalResult1', 'Result1',
            'CalResult2', 'Result2', 'CalResult3', 'Result3'
        ]

        datetime_columns = [
           'AnalysisDateTime', 'PrepDateTime', 'Rep1DateTime', 'Rep2DateTime', 'Rep3DateTime'
        ]

        import numpy as np

        for col in float_columns:
            print(col)
            if col in df.columns:
                df[col] = df[col].replace(['', ' ', 'N/A', np.nan], 0)
                df[col] = df[col].astype(float)
                df[col] = pd.to_numeric(df[col], errors='coerce')

        for col in datetime_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        return df
                     
    def upload_data(self, df):
        try:
            self.init_session()

            rejected_samples = []

            for index, row in df.iterrows():
                # Convert row to dictionary
                row_dict = row.to_dict()

                # Set default iteration and reporting values
                row_dict.setdefault("Iteration", 1)
                row_dict.setdefault("Reporting", True) 

                valid_columns = set(c.name for c in HGResults.__table__.columns)
                filtered_row_dict = {k: v for k, v in row_dict.items() if k in valid_columns}
                record = HGResults(**filtered_row_dict)
                    
                # Check if record already exists
                existing_record = self.session.query(HGResults).filter(
                    HGResults.SDG == record.SDG,
                    HGResults.BatchID == record.BatchID,
                    HGResults.SampleID == record.SampleID,
                    HGResults.Analyte == record.Analyte,
                    HGResults.Reporting == record.Reporting
                ).first()

                # If the record exists
                if existing_record:
                    # Check for exact match, if so do nothing
                    if existing_record:
                        if self.objects_are_identical(record, existing_record, ignore_fields=["Iteration", "Reporting"]):
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
                    print(f"Column: {key}")
                    print(f"Record: {obj1_dict[key]}")
                    print(f"Existing: {obj2_dict[key]}\n")
            return False

        return True  # No mismatches found

processor = HGProcessor()

df = processor.parse_file(file_path)