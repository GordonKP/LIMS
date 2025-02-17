from grab_prepsheet import GetPrepsheetData
from grab_batch_id import GetBatchID
import config
import patterns
from tables import (
    Base, SampleLogin, DQO, CoC, LIMSLimits, FluorescenceResults, 
    ICPMSResults, GammaSpecResults, GABResults, AlphaSpecResults
)
import csv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import pandas as pd

# head, tail = os.path.split(file_path)

class AlphaSpecProcessor:
    def __init__(self):
        self.session = None
        self.engine = None

    def init_session(self):
        # Initialize the SQLAlchemy session
        self.engine = create_engine(config.CONNECTION_STRING)
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
        batch_id = GetBatchID.get_batch_id(self, sample_id=df.iloc[0]['SampleID'], method=df.iloc[0]['Method'])

        df['BatchID'] = batch_id

        # Prepsheet
        prepsheet_data = GetPrepsheetData().get_prepsheet_data(batch_id)

        import re

        # AliquotUnits
        aliquot_key = next((key for key in prepsheet_data["Samples"] if "Aliquot" in key), None)
        unit_match = re.search(r"\((.*?)\)", aliquot_key) if aliquot_key else None
        aliquot_unit = unit_match.group(1) if unit_match else None

        df['AliquotUnits'] = aliquot_unit

        # PrepDate
        prep_date = prepsheet_data.get("Prep Data")[0]['Prep Date']
        prep_time = prepsheet_data.get("Prep Data")[0]['Prep Time']

        from datetime import datetime

        prep_datetime = datetime.strptime(f"{prep_date} {prep_time}", "%d-%m-%Y %H:%M")

        df['PrepDateTime'] = prep_datetime

        # PrepsheetFilePath
        prepsheet_file_path = f"Prep-{batch_id}.json"

        df['PrepsheetFilePath'] = prepsheet_file_path

        print(prepsheet_data)

        print(df)

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

df.to_csv("alpha.csv")


