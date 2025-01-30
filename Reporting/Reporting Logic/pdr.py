import os
import sys
import config
from tables import Base, SampleLogin, DQO, CoC, BeFinderResults, ICPMSResults, GammaSpecResults, GABResults, AlphaSpecResults
from sqlalchemy import create_engine, Column, Integer, Boolean, String, Float, DateTime, desc, and_, Date, Time
from sqlalchemy.orm import sessionmaker
import json
import pandas as pd

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
            Session = sessionmaker(bind=self.engine)
            self.session = Session()

    def get_all_data(self, batch_id):
        try:
            self.init_session()

            dqo_query = self.session.query(DQO).filter(DQO.BatchID == batch_id).all()

            dqo_df = pd.DataFrame([row.__dict__ for row in dqo_query])
            dqo_df.drop(columns=['_sa_instance_state'], errors='ignore', inplace=True)

            unique_sdgs = dqo_df['SDG'].unique()

            coc_df = pd.DataFrame()

            sample_login_df = pd.DataFrame()

            for sdg in unique_sdgs:
                # If its a compound sdg, just skip it, the SDGs are already in the df on their own
                if "," in sdg:
                    continue
                else:
                    # Get all CoC information within sdg from CoC
                    coc_query = self.session.query(CoC).filter(CoC.SDG == sdg).all()

                    coc_temp_df = pd.DataFrame([row.__dict__ for row in coc_query])
                    coc_temp_df.drop(columns=['_sa_instance_state'], errors='ignore', inplace=True)

                    coc_df = pd.concat([coc_df, coc_temp_df], ignore_index=True)

                    # Get all samples within SDG from sample login
                    sample_login_query = self.session.query(SampleLogin).filter(SampleLogin.SDG == sdg).all()

                    sample_login_temp_df = pd.DataFrame([row.__dict__ for row in sample_login_query])
                    sample_login_temp_df.drop(columns=['_sa_instance_state'], errors='ignore', inplace=True)

                    sample_login_df = pd.concat([sample_login_df, sample_login_temp_df], ignore_index=True)

            # Get the results from the appropriate table
            method = dqo_df['Method'].unique().tolist()[0]

            if method == 'BeFinder':
                table = BeFinderResults
            elif method == 'GammaSpec':
                table = GammaSpecResults
            elif method == 'GAB':
                table = GABResults
            elif "Metal" in method:
                table = ICPMSResults
            elif 'ISO' in method:
                table = AlphaSpecResults

            results_query = self.session.query(table).filter(getattr(table, "BatchID") == batch_id).all()

            results_df = pd.DataFrame([row.__dict__ for row in results_query])
            results_df.drop(columns=['_sa_instance_state'], errors='ignore', inplace=True)

            # Get the prepsheet data
            json_path = os.path.join(prepsheetdir, f"Prep-{batch_id}.json")

            with open(json_path, "r", encoding='utf-8') as file:
                prepsheet_data = json.load(file)

            self.generate_pdr(sample_login_df, coc_df, dqo_df, results_df, prepsheet_data)

        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
             self.session.close()

    def generate_pdr(self, sample_login_df, coc_df, dqo_df, results_df, prepsheet_data):
        for arg_name, arg_value in locals().items():
            print(f"Processing {arg_name}:")
            print(arg_value)
        return

GeneratePDR().get_all_data(batch_id)