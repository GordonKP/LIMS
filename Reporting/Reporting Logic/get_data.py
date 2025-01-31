import os
import json
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import config
from tables import (
    SampleLogin, DQO, CoC, BeFinderResults, 
    ICPMSResults, GammaSpecResults, GABResults, AlphaSpecResults
)

prepsheetdir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "Prepsheets")


class GetData:
    @staticmethod
    def get_all_data(batch_id):
        engine = create_engine(config.CONNECTION_STRING)
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            # Get DQO data
            dqo_query = session.query(DQO).filter(DQO.BatchID == batch_id).all()
            dqo_df = pd.DataFrame([row.__dict__ for row in dqo_query])
            dqo_df.drop(columns=['_sa_instance_state'], errors='ignore', inplace=True)

            unique_sdgs = dqo_df['SDG'].unique()

            coc_df = pd.DataFrame()
            sample_login_df = pd.DataFrame()

            for sdg in unique_sdgs:
                if "," in sdg:  # Skip compound SDGs
                    continue

                # Get all CoC information within SDG
                coc_query = session.query(CoC).filter(CoC.SDG == sdg).all()
                coc_temp_df = pd.DataFrame([row.__dict__ for row in coc_query])
                coc_temp_df.drop(columns=['_sa_instance_state'], errors='ignore', inplace=True)
                coc_df = pd.concat([coc_df, coc_temp_df], ignore_index=True)

                # Get all samples within SDG from SampleLogin
                sample_login_query = session.query(SampleLogin).filter(SampleLogin.SDG == sdg).all()
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
            else:
                raise ValueError(f"Unknown method: {method}")

            results_query = session.query(table).filter(getattr(table, "BatchID") == batch_id, getattr(table, "Reporting") == 1).all()
            results_df = pd.DataFrame([row.__dict__ for row in results_query])
            results_df.drop(columns=['_sa_instance_state'], errors='ignore', inplace=True)

            # Get the prepsheet data
            json_path = os.path.join(prepsheetdir, f"Prep-{batch_id}.json")
            with open(json_path, "r", encoding='utf-8') as file:
                prepsheet_data = json.load(file)

            return sample_login_df, coc_df, dqo_df, results_df, prepsheet_data

        except Exception as e:
            print(f"An error occurred: {e}")
            return None, None, None, None, None
        finally:
            session.close()
