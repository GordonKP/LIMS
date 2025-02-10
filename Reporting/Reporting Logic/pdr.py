import os
import sys
import config
from get_data import GetData
import pandas as pd
from tables import (
    Base, SampleLogin, DQO, CoC, LIMSLimits, FluorescenceResults, 
    ICPMSResults, GammaSpecResults, GABResults, AlphaSpecResults
)
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker

basedir = os.path.dirname(__file__)
parentdir = os.path.dirname(basedir)
prepsheetdir = os.path.join(os.path.dirname(parentdir), "Prepsheets")

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

        pdr = pd.DataFrame()
        pdr_columns = ['SDG', 'BatchID', 'SampleID', 'Matrix', 'Method', 'ResultType', 'Analyte', 'Result', 
                       'ResultError', 'ResultUnits', 'MDA', 'LOD', 'Aliquot', 'AliquotUnits', 'DateReceived', 
                       'AnalysisDateTime', 'Survey', 'Instrument', 'LabID', 'LocationID']

        # Get the results from each results table into the pdr df
        for batch in results_df_list:
            pdr = pd.concat([batch.reindex(columns=pdr_columns) for batch in results_df_list], ignore_index=True)

        try:
            self.init_session()

            # Get the items from sample login by SDG not by row for efficiency
            # DateReceived and Volume
            date_received_dict = {}
            location_id_dict = {}
            aliquot_dict = {}
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

            for batch in pdr['BatchID'].unique().tolist():
                prepsheet_data = prepsheets_dict[batch]

                sample_ids = prepsheet_data["Samples"]["Sample ID"]
                aliquots = prepsheet_data["Samples"]["Aliquot"]

                paired_data = list(zip(sample_ids, aliquots))

                aliquot_dict[batch] = paired_data

            # Map the dictionaries to the pdr
            pdr['DateReceived'] = pdr['SDG'].map(date_received_dict)
            
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
                    aliquots = prepsheets_data["Samples"][aliquot_key]  # Get the corresponding aliquot list
                    
                    # Find the index of the sample ID in the list
                    try:
                        sample_index = sample_ids.index(row['SampleID'])  # Get index of SampleID
                        pdr.at[index, 'Aliquot'] = aliquots[sample_index]  # Assign the correct Aliquot value
                    except ValueError:
                        row['Aliquot'] = None
 
                # LOD from limits table
                if pd.notna(row['MDA']):
                    pass
                else:
                    limit_query = (
                        self.session.query(LIMSLimits.LOD)
                        .filter(
                            LIMSLimits.Method == row['Method'],
                            LIMSLimits.Matrix == row['Matrix'],
                            LIMSLimits.ResultType == row['ResultType'],
                            LIMSLimits.Analyte == row['Analyte'],
                            LIMSLimits.EffectiveDate <= row['DateReceived']  # Ensure it's before or equal
                        )
                        .order_by(LIMSLimits.EffectiveDate.desc())  # Get the most recent one
                        .first()  # Only retrieve the first result
                    )

                    if limit_query:
                        lod = limit_query.LOD
                    else:
                        lod = None
                    
                    row['LOD'] = lod

                # Instrument
                row['Instrument'] = row['Method']

        except Exception as e:
            print(f"An exception occurred: {e}")
        finally:
            self.session.close()

        pdr.to_csv("PDR.csv")

sample_login_df, coc_df, dqo_df, results_df_list, prepsheets_dict = GetData.get_all_data(sdg)

GeneratePDR().generate_pdr(sample_login_df, coc_df, dqo_df, results_df_list, prepsheets_dict)