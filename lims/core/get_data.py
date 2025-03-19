import os
import json
import pandas as pd
from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker

from lims.config.tables import (
    Base, SampleLogin, DQO, CoC
)
from lims.config.config import CONNECTION_STRING
from lims.config.file_paths import prepsheet_directory
from lims.config.methods_tables import methods_tables

class GetData:
    @staticmethod
    def get_all_data(sdg):
        engine = create_engine(CONNECTION_STRING)
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            dqo_df = pd.DataFrame()

            for sdg_value in sdg.split(', '):  # Split on ', ' to get individual SDGs
                dqo_query = session.query(DQO).filter(DQO.SDG.like(f"%{sdg_value}%")).all()
                
                if dqo_query:  # Only process if query returns results
                    temp_df = pd.DataFrame([row.__dict__ for row in dqo_query])
                    dqo_df = pd.concat([dqo_df, temp_df], ignore_index=True)  # Append results

            dqo_df.drop_duplicates(inplace=True)

            dqo_df.drop(columns=['_sa_instance_state'], errors='ignore', inplace=True)

            coc_df = pd.DataFrame()
            sample_login_df = pd.DataFrame()

            for sdg in dqo_df['SDG'].unique().tolist():
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
            
            results_df_list = []
            prepsheets_dict = {}

            # Get unique combinations of BatchID and Method
            unique_combinations = dqo_df[['BatchID', 'Method']].drop_duplicates().values.tolist()

            for batch_id, method in unique_combinations:
                print(batch_id, method)  # Example processing

                table = methods_tables[method]

                results_query = session.query(table).filter(getattr(table, "BatchID") == batch_id, getattr(table, "Reporting") == 1).all()

                results_df = pd.DataFrame([row.__dict__ for row in results_query])

                results_df.drop(columns=['_sa_instance_state'], errors='ignore', inplace=True)

                results_df_list.append(results_df)
            
                # Get the prepsheet data
                json_path = os.path.join(prepsheet_directory, f"Prep-{batch_id}.json")
                with open(json_path, "r", encoding='utf-8') as file:
                    prepsheet_data = json.load(file)
                    prepsheets_dict[batch_id] = prepsheet_data

            return sample_login_df, coc_df, dqo_df, results_df_list, prepsheets_dict

        except Exception as e:
            print(f"An error occurred: {e}")
            return None, None, None, None, None
        finally:
            session.close()

sample_login_df, coc_df, dqo_df, results_df_list, prepsheets_dict = GetData.get_all_data("25SL0001")

print(sample_login_df, coc_df, dqo_df, results_df_list, prepsheets_dict)

from lims.config import lab_lists

sample_login_df = sample_login_df.drop(columns=lab_lists.method_list)

# Concatenate DataFrames while maintaining column order
big_df = pd.concat(results_df_list, ignore_index=True, sort=False)

big_df = pd.merge(big_df, sample_login_df, on=['SDG', 'SampleID', 'Matrix'], how='outer')

print(big_df)

column_dict = {
    "_____": "AFIID",
    "_____": "LOCID",
    "_____": "LOGDATE",
    "_____": "LOGTIME",
    "_____": "MATRIX",
    "_____": "SBD",
    "_____": "SED",
    "_____": "SACODE",
    "_____": "SAMPNO",
    "_____": "LOGCODE",
    "_____": "SMCODE",
    "_____": "FLDSAMPID",
    "_____": "COCID",
    "_____": "COOLER",
    "_____": "ABLOT",
    "_____": "EBLOT",
    "_____": "TBLOT",
    "_____": "REMARKS",
    "_____": "SDG",
    "_____": "LABCODE",
    "_____": "ANMCODE",
    "_____": "EXMCODE",
    "_____": "LCHMETH",
    "_____": "RUN_NUMBER",
    "_____": "LABSAMPID",
    "_____": "EXTDATE",
    "_____": "EXTTIME",
    "_____": "LCHDATE",
    "_____": "LCHTIME",
    "_____": "LCHLOT",
    "_____": "ANADATE",
    "_____": "ANATIME",
    "_____": "ANALOT",
    "_____": "LABLOTCTL",
    "_____": "CALREFID",
    "_____": "RTTYPE",
    "_____": "BASIS",
    "_____": "PARLABEL",
    "_____": "PRCCODE",
    "_____": "PARVQ",
    "_____": "PARVAL",
    "_____": "PARUN",
    "_____": "PRECISION",
    "_____": "EXPECTED",
    "_____": "EVPREC",
    "_____": "MDL",
    "_____": "RL",
    "_____": "UNITS",
    "_____": "VQ_1C",
    "_____": "VAL_1C",
    "_____": "FCVALPREC",
    "_____": "VQ_CONFIRM",
    "_____": "VAL_CONFIRM",
    "_____": "CNFVALPREC",
    "_____": "DILUTION",
    "_____": "PRIME_DQT",
    "_____": "PRIME_FLAG",
    "_____": "LAB_DQT",
    "_____": "LAB_QC_FLAG",
    "_____": "BEST_RESULT",
    "_____": "REASON_CODE",
    "_____": "PERCENT_RECOVERY",
    "_____": "RPD",
    "_____": "UPPER_RPD",
    "_____": "UPPER_ACCURACY",
    "_____": "LOWER_ACCURACY",
    "_____": "SPIKE_ADDED",
    "_____": "SPIKE_ADDED_PREC",
    "_____": "VALCODE",
    "_____": "TC_NAME",
    "_____": "RETENTION_TIME",
    "_____": "LOD",
}

big_df.to_csv("big_df.csv", index=False)