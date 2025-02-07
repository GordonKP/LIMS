import os
import sys
import config
from get_data import GetData
import pandas as pd
from tables import (
    Base, SampleLogin, DQO, CoC, LIMSLimits, BeFinderResults, 
    ICPMSResults, GammaSpecResults, GABResults, AlphaSpecResults
)
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker

basedir = os.path.dirname(__file__)
parentdir = os.path.dirname(basedir)
prepsheetdir = os.path.join(os.path.dirname(parentdir), "Prepsheets")

print(basedir, parentdir)

# Remove this after finishing
batch_id = "25LLB0001"

class GeneratePDR:
    def __init__(self):
        self.session = None
        self.engine = None

    def init_session(self):
            # Initialize the SQLAlchemy session
            self.engine = create_engine(config.CONNECTION_STRING)
            Base.metadata.create_all(self.engine)
            Session = sessionmaker(bind=self.engine)
            self.session = Session()

    def generate_pdr(self, sample_login_df, coc_df, dqo_df, results_df, prepsheet_data):
        for arg_name, arg_value in locals().items():
            print(f"Processing {arg_name}:")
            print(arg_value)
    
        # Get result units
        if results_df['ResultUnits']:
            pass
        else:
            results_df.insert('ResultUnits', '')

        # Get result error
        if results_df['ResultError']:
            pass
        else:
            results_df.insert('ResultError', '')

        if results_df['MDA']:
                pass
        else:
            results_df.insert('LOD', '')

        analyte_lod_dict = {}

        for index, row in results_df.iterrows():

            # Get instrument type
            method = row['Method'] 

            if "ISO" in method:
                instrument = 'Alpha Spectrometer'
            elif method == 'BeFinder':
                instrument = 'BeFinder'
            elif "Metal" in method:
                instrument = 'ICPMS'
            elif 'Gamma' in method:
                instrument = 'Gamma Spectrometer'
            elif 'GAB' in method:
                instrument = 'GFPC'
            else:
                instrument = method
            
            row['Instrument Type'] = instrument

            # Need to get the date of the analysis so we can 
            if results_df['LOD']:
                if row['Analyte'] in analyte_lod_dict.keys():
                    row['LOD'] = analyte_lod_dict[row['Analyte']]
                    pass
                else:
                    lod = self.get_lod(method, row['Matrix'], row['ResultType'], row['Analyte'])

            
    def get_lod(self, method, matrix, result_type, analyte):
        try:
            self.init_session()

            lod_query = self.session.query(LIMSLimits.LOD).filter(
                LIMSLimits.Method == method,
                LIMSLimits.Matrix == matrix,
                LIMSLimits.ResultType == result_type,
                LIMSLimits.Analyte == analyte
            ).order_by(desc(LIMSLimits.EffectiveDate)).first()

            return lod_query

        except Exception as e:
            print(f"An exception occurred: {e}")

        finally:
            self.session.close()

sample_login_df, coc_df, dqo_df, results_df, prepsheet_data = GetData.get_all_data(batch_id)

GeneratePDR().generate_pdr(sample_login_df, coc_df, dqo_df, results_df, prepsheet_data)