from grab_prepsheet import GetPrepsheetData
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

head, tail = os.path.split(file_path)

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
        with open(file_path, mode='r') as file:
            reader = csv.reader(file)

            for row in reader:
                if row[0] == "A":
                    
                     
    def upload_data(self, df):
         return
         
file_path = "\\sldafileserver\lims\LIMS\Data\Raw Data\Alpha Spectroscopy\YU02_2024Oct03132848.res"
    
processor = AlphaSpecProcessor()

df = processor.parse_alpha_file(file_path)

processor.upload_to_database(df)


