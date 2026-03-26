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
        # Convert the sample ID column to all caps where applicable, this is to accurately generate result type.
        df['SampleID'] = df['SampleID'].str.upper()

        method = 'HG'

        df.insert(0, 'Method', method)

        # ResultType 
        df.insert(0, 'ResultType', '')
        df = GetResultType.get_result_types(df)

        df['Analyte'] = 'HG'

        from lims.data_transformations.data_processing import data_processing
        df = data_processing.process_df(df)

        batch_id_list = df['BatchID'].unique().tolist()

        if len(batch_id_list) > 1:
            from lims.core.popups import Popup
            Popup.debugger("Multiple Batches Detected", "More than one analytical batch was detected, this is not a supported feature as of 11/26/2025.\nThis feature is coming soon.")
            return None
        else:
            batch_id = batch_id_list[0]

        # Get aliquot
        df = GetPrepsheetData.get_aliquot_amounts(batch_id, df)

        print("Made it past aliquots")

        # AliquotUnits
        df = GetPrepsheetData.get_aliquot_units(batch_id, df)

        # PrepDate
        df = GetPrepsheetData.get_prep_datetime(batch_id, df)

        # PrepsheetFilePath
        df = GetPrepsheetData.get_prepsheet_path(batch_id, df)

        df = AnalytePreprocessing.process(df)

        print("Made it past analyte processing")

        import numpy as np
        
        from core import recovery

        prepsheet = GetPrepsheetData.get_prepsheet_data(batch_id)

        print("Made it past get prep data")

        df = recovery.get_recovery(df, prepsheet)

        print("Made it past recovery")

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

        print("Made it past datetime stuff")

        df = limits.GetLimits.query_limits(df)

        print("Made it past limits")

        # List of numeric columns that should be floats
        float_columns = [
            'Aliquot', 'InitialWeightVolume', 'PrepVolume', 'CalResult', 'Result',
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

        df['ResultUnits'] = df['ResultUnits'].apply(
            lambda x: x.replace('Âµ', 'u').replace('µ', 'u') if isinstance(x, str) else x
        )

        return df
                     
processor = HGProcessor()

df = processor.parse_file(file_path)