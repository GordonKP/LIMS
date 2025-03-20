import os
import sys
import lims.config.file_paths 
import pandas as pd
import lims.config.tables as tables
from lims.core.get_data import GetData
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker

basedir = os.path.dirname(__file__)
parentdir = os.path.dirname(basedir)
prepsheetdir = lims.config.file_paths.prepsheet_directory

print(basedir, parentdir)

# Remove this after finishing
sdg = "25SL0001"

class GeneratePDR:
    def __init__(self):
        self.session = None
        self.engine = None

    def init_session(self):
            # Initialize the SQLAlchemy session
            self.engine = create_engine(lims.config.CONNECTION_STRING)
            tables.Base.metadata.create_all(self.engine)
            Session = sessionmaker(bind=self.engine)
            self.session = Session()

    def generate_pdr(self, sample_login_df, coc_df, dqo_df, results_df_list, prepsheets_dict):
        print("sample_login_df:", sample_login_df)
        print("coc_df:", coc_df)
        print("dqo_df:", dqo_df)
        print("results_df_list:", results_df_list)
        print("prepsheets_dict:", prepsheets_dict)
        print("---------------------------------------------")

        pdr = pd.DataFrame()

        # Define column data types
        pdr_dtypes = {
            'SDG': 'string', # Results
            'BatchID': 'string', # Results
            'SampleID': 'string', # Results
            'Matrix': 'string', # Results
            'Method': 'string', # Results
            'ResultType': 'string', # Results
            'Analyte': 'string', # Results
            'Result': 'float64', # Results
            'ResultError': 'float64', # Results
            'ResultUnits': 'string', # Results
            'MDA': 'float64', # Results
            'MDL': 'float64', # Limits
            'LOD': 'float64', # Limits
            'LOQ': 'float64', # Limits
            'LowerLimit': 'float64', # Limits
            'UpperLimit': 'float64', # Limits
            'Aliquot': 'float64', # Results
            'AliquotUnits': 'string', # Results
            'DateReceived': 'datetime64[ns]', # SampleLogin
            'AnalysisDateTime': 'datetime64[ns]', # Results
            'Survey': 'string', # CoC
            'LabID': 'string', # SLDA
            'LocationID': 'string' # SampleLogin
        }

        # Create an empty DataFrame with the correct dtypes
        pdr = pd.DataFrame({col: pd.Series(dtype=dtype) for col, dtype in pdr_dtypes.items()})

        # Get the results from each results table into the pdr df
        for batch in results_df_list:
            pdr = pd.concat([batch.reindex(columns=pdr_dtypes.keys()) for batch in results_df_list], ignore_index=True)

        # Enforce dtypes
        pdr = pdr.astype(pdr_dtypes)

        try:
            self.init_session()

            # Get the items from sample login by SDG not by row for efficiency
            # DateReceived and Volume
            date_received_dict = {}
            location_id_dict = {}

            for sdg in pdr['SDG'].unique().tolist():
                sample_login_query = self.session.query(tables.SampleLogin.DateReceived).filter(tables.SampleLogin.SDG == sdg).first()
                
                # Handle cases where no result is found
                if sample_login_query:
                    date_received_dict[sdg] = sample_login_query.DateReceived
                else:
                    date_received_dict[sdg] = None

            for sample in pdr['SampleID'].unique().tolist():
                sample_login_query = self.session.query(tables.SampleLogin.LocationID).filter(tables.SampleLogin.SampleID == sample).first()

                if sample_login_query:
                    location_id_dict[sample] = sample_login_query.LocationID
                else:
                    location_id_dict[sample] = 'Lab'

            # Map the dictionaries to the pdr
            pdr['DateReceived'] = pdr['SDG'].map(date_received_dict)
            pdr['LocationID'] = pdr['SampleID'].map(location_id_dict)
            
            # LabID is a constant
            pdr['LabID'] = 'SLDA'

        except Exception as e:
            print(f"An exception occurred: {e}")
        finally:
            self.session.close()

        pdr.to_csv("PDR.csv", index=False)

sample_login_df, coc_df, dqo_df, results_df_list, prepsheets_dict = GetData.get_all_data(sdg)

GeneratePDR().generate_pdr(sample_login_df, coc_df, dqo_df, results_df_list, prepsheets_dict)