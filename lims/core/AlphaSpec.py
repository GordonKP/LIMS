import sys
import os

# Get the absolute path of the parent directory
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the parent directory to sys.path
sys.path.append(parent_dir)

from Packages.Prepsheet import GetPrepsheetData
from Packages.BatchID import GetBatchID
from Packages.SDG import GetSDG
from Packages.ResultType import GetResultType
from Config.config import CONNECTION_STRING
from Packages.tables import (
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

        self.upload_data(df)

        return df
                    
    def create_df(self, parsed_data):
        columns = [
            "AlphaBatchID", "Detector", "AnalysisDateTime", "SampleDate", "Aliquot", "SampleID",
            "ResultUnits", "AliquotUnits", "TracerAliquot", "FileName", "PercentAbundance",
            "MDAConfidenceFactor", "MDALLDConstant", "Matrix",
            "EnergycalibrationDateTime", "EfficiencyCalibrationDateTime", "BackgroundFile",
            "TracerRecovery", "AlphaChamber", "ChamberEfficiency", "AcquisitionDateTime",
            "ElapsedLiveTime", "TracerFWHM", "Analyte", "NetArea", "BackgroundArea", "Result", "ResultError", "MDA"
        ]

        sample_rows = []

        for sample in parsed_data:
            sample_row = [sample['A'][1], sample['A'][2], sample['A'][3], sample['A'][4], sample['A'][5], sample['A'][6],
                          sample['A'][9], sample['A'][10], sample['A'][11], sample['A'][12], sample['A'][13], sample['A'][14], sample['A'][15], sample['A'][16],
                          sample['B'][4], sample['B'][5], sample['B'][6], sample['B'][8], sample['B'][10], sample['B'][11], sample['B'][12], sample['B'][13], sample['B'][14],
                          sample['C'][4], sample['C'][5], sample['C'][6], sample['C'][7], sample['C'][8], sample['C'][9]]
            sample_rows.append(sample_row)

        df = pd.DataFrame(sample_rows, columns=columns)

        # Method
        df['Method'] = df.apply(self.generate_analyte_column, axis=1)

        # BatchID
        batch_id = GetBatchID.get_batch_id(sample_id=df.iloc[0]['SampleID'], method=df.iloc[0]['Method'])

        df['BatchID'] = batch_id

        # SDG
        df = GetSDG.get_sdg(batch_id, df)

        # AliquotUnits
        df = GetPrepsheetData.get_aliquot_units(batch_id, df)

        # PrepDate
        df = GetPrepsheetData.get_prep_datetime(batch_id, df)

        # PrepsheetFilePath
        df = GetPrepsheetData.get_prepsheet_path(batch_id, df)

        # ResultType 
        df = GetResultType.get_result_types(df)

        df.loc[~df['Analyte'].str.contains("-", na=False), 'ResultType'] = "Tracer"

        print(df.columns)

        

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
         return
         
file_path = r"C:\Users\kgmon\OneDrive\Desktop\LIMS\Data\Raw Data\Alpha Spectroscopy\YU02_2024Oct03132848.res"
    
processor = AlphaSpecProcessor()

df = processor.parse_file(file_path)