import os
import sys
import config
import config.file_paths
from get_data import GetData
import pandas as pd
from lims.config.tables import (
    Base, SampleLogin, DQO, CoC, LIMSLimits, FluorescenceResults, 
    ICPMSResults, GammaSpecResults, GABResults, AlphaSpecResults
)
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker

basedir = os.path.dirname(__file__)
parentdir = os.path.dirname(basedir)
prepsheetdir = config.file_paths.prepsheet_directory

print(basedir, parentdir)

# Remove this after finishing
sdg = "25SL0001"

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
            'SDG': 'string',
            'BatchID': 'string',
            'SampleID': 'string',
            'Matrix': 'string',
            'Method': 'string',
            'ResultType': 'string',
            'Analyte': 'string',
            'Result': 'float64',
            'ResultError': 'float64',
            'ResultUnits': 'string',
            'MDA': 'float64',
            'MDL': 'float64',
            'LOD': 'float64',
            'LOQ': 'float64',
            'LowerLimit': 'float64',
            'UpperLimit': 'float64',
            'Aliquot': 'float64', 
            'AliquotUnits': 'string', 
            'DateReceived': 'datetime64[ns]',
            'AnalysisDateTime': 'datetime64[ns]',
            'Survey': 'string',
            'LabID': 'string',
            'LocationID': 'string'
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
                sample_login_query = self.session.query(SampleLogin.DateReceived).filter(SampleLogin.SDG == sdg).first()
                
                # Handle cases where no result is found
                if sample_login_query:
                    date_received_dict[sdg] = sample_login_query.DateReceived
                else:
                    date_received_dict[sdg] = None

            for sample in pdr['SampleID'].unique().tolist():
                sample_login_query = self.session.query(SampleLogin.LocationID).filter(SampleLogin.SampleID == sample).first()

                if sample_login_query:
                    location_id_dict[sample] = sample_login_query.LocationID
                else:
                    location_id_dict[sample] = 'Lab'

            # Map the dictionaries to the pdr
            pdr['DateReceived'] = pdr['SDG'].map(date_received_dict)
            pdr['LocationID'] = pdr['SampleID'].map(location_id_dict)
            
            # LabID is a constant
            pdr['LabID'] = 'SLDA'

            for index, row in pdr.iterrows():
                # Get the prep sheet data for the batch
                prepsheets_data = prepsheets_dict[row['BatchID']]
                
                # Extract sample IDs
                sample_ids = prepsheets_data["Samples"]["Sample ID"]
                
                # Find the key that contains "Aliquot"
                aliquot_key = next((key for key in prepsheets_data["Samples"] if "Aliquot" in key), None)

                if aliquot_key:
                    aliquot_units = aliquot_key.split(" (")[1][:-1]
                    aliquots = prepsheets_data["Samples"][aliquot_key]  # Get corresponding aliquot list
                    
                    # Check if SampleID is in sample_ids before trying to find its index
                    if row['SampleID'] in sample_ids:
                        sample_index = sample_ids.index(row['SampleID'])  # Get index of SampleID
                        pdr.at[index, 'Aliquot'] = float(aliquots[sample_index])
                        pdr.at[index, 'AliquotUnits'] = str(aliquot_units)
                    else:
                        pdr.at[index, 'Aliquot'] = 1.0  # Assign None if SampleID not found
                        pdr.at[index, 'AliquotUnits'] = "Sample"

                limit_query = (
                        self.session.query(LIMSLimits.MDL, LIMSLimits.LOD, LIMSLimits.LOQ, 
                                           LIMSLimits.LowerLimit, LIMSLimits.UpperLimit)
                        .filter(
                            LIMSLimits.Method == row['Method'],
                            LIMSLimits.Matrix == row['Matrix'],
                            LIMSLimits.ResultType == row['ResultType'],
                            LIMSLimits.Analyte == row['Analyte'],
                            LIMSLimits.EffectiveDate <= row['AnalysisDateTime']  # Ensure it's before or equal
                        )
                        .order_by(LIMSLimits.EffectiveDate.desc())  # Get the most recent one
                        .first()  # Only retrieve the first result
                    )

                if limit_query:
                    pdr.at[index, 'MDL'] = limit_query.MDL
                    pdr.at[index, 'LOD'] = limit_query.LOD
                    pdr.at[index, 'LOQ'] = limit_query.LOQ
                    pdr.at[index, 'LowerLimit'] = limit_query.LowerLimit
                    pdr.at[index, 'UpperLimit'] = limit_query.UpperLimit

        except Exception as e:
            print(f"An exception occurred: {e}")
        finally:
            self.session.close()

        pdr.to_csv("PDR.csv", index=False)

sample_login_df, coc_df, dqo_df, results_df_list, prepsheets_dict = GetData.get_all_data(sdg)

GeneratePDR().generate_pdr(sample_login_df, coc_df, dqo_df, results_df_list, prepsheets_dict)