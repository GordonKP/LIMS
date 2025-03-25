import sys
import os

# Get the absolute path to the root "LIMS" directory
current_file = os.path.abspath(__file__)
lims_root = os.path.abspath(os.path.join(current_file, "../../.."))

# Insert it at the start of sys.path
sys.path.insert(0, lims_root)

import lims.config.file_paths 
from lims.config.config import CONNECTION_STRING
import pandas as pd
import lims.config.tables as tables
import lims.config.lab_lists as lab_lists
from lims.core.get_data import GetData
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker

basedir = os.path.dirname(__file__)
parentdir = os.path.dirname(basedir)
prepsheetdir = lims.config.file_paths.prepsheet_directory

print(basedir, parentdir)

# Remove this after finishing
sdg = "25SL0015"

class GeneratePDR:
    def __init__(self):
        self.session = None
        self.engine = None

    def init_session(self):
            # Initialize the SQLAlchemy session
            self.engine = create_engine(CONNECTION_STRING)
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
            'Aliquot': 'float64', # Results
            'AliquotUnits': 'string', # Results
            'MDA': 'float64',
            'DL': 'float64',
            'LOD': 'float64',
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
            survey_dict = {}

            for sdg in pdr['SDG'].unique().tolist():
                coc_query = self.session.query(tables.CoC.Survey).filter(tables.CoC.SDG == sdg).first()
                
                # Handle cases where no result is found
                if coc_query:
                    survey_dict[sdg] = coc_query.Survey
                else:
                    survey_dict[sdg] = None

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
            pdr['Survey'] = pdr['SDG'].map(survey_dict)
            pdr['LocationID'] = pdr['SampleID'].map(location_id_dict)
            
            # LabID is a constant
            pdr['LabID'] = 'SLDA'

            # For ICPMS, we need to remove the (matrix) from the method column
            pdr['Method'] = pdr['Method'].str.replace(r'\s*\(.*?\)', '', regex=True)

        except Exception as e:
            print(f"An exception occurred: {e}")
        finally:
            if self.session:
                self.session.close()

        # Keep only rows where result type is in the result types to keep
        pdr = pdr[pdr['ResultType'].isin(lab_lists.pdr_result_type_list)]

        # Query the limits table and grab limits closest to analysis date
        try:
            self.init_session()

            limits_query = self.session.query(tables.LIMSLimits.DL, tables.LIMSLimits.LOD).all()

            if limits_query:
                limits_df = pd.DataFrame([l.__dict__ for l in limits_query])
                limits_df = limits_df.drop(columns=['_sa_instance_state'])

                # Convert key columns to string (ensures uniformity across DataFrames)
                string_columns = ['Method', 'Matrix', 'ResultType', 'Analyte']
                pdr[string_columns] = pdr[string_columns].astype(str)
                limits_df[string_columns] = limits_df[string_columns].astype(str)

                # Ensure datetime format for merge
                pdr['AnalysisDateTime'] = pd.to_datetime(pdr['AnalysisDateTime'], errors='coerce')
                limits_df['EffectiveDate'] = pd.to_datetime(limits_df['EffectiveDate'], errors='coerce')

                # Drop NaT values if necessary
                pdr.dropna(subset=['AnalysisDateTime'], inplace=True)
                limits_df.dropna(subset=['EffectiveDate'], inplace=True)

                # Sort before merge_asof()
                pdr = pdr.sort_values('AnalysisDateTime')
                limits_df = limits_df.sort_values('EffectiveDate')

                # Perform an asof merge to get the latest valid limit (EffectiveDate <= AnalysisDateTime)
                merged_pdr = pd.merge_asof(
                    pdr,
                    limits_df,
                    left_on='AnalysisDateTime',  # Ensure this is datetime
                    right_on='EffectiveDate',
                    by=string_columns,  # Ensure these columns are string type
                    direction='backward'
                )

                # Now pdr has only the most recent valid limit per row
                pdr = merged_pdr

        except Exception as e:
            print(f"An exception occurred: {e}")
        finally:
            if self.session:
                self.session.close()

        # Reorder columns
        column_order = ['SDG', 'BatchID', 'SampleID', 'Matrix', 'Method', 'ResultType', 
            'Analyte', 'Result', 'ResultError', 'ResultUnits', 'MDA', 'DL', 
            'LOD', 'Aliquot', 'AliquotUnits', 
            'DateReceived', 'AnalysisDateTime', 'Survey', 'LabID', 'LocationID']
        
        pdr = pdr.reindex(columns=column_order)

        # Sort by Method and ResultType
        pdr = pdr.sort_values(by=['Method', 'ResultType'])

        pdr.to_csv("PDR.csv", index=False)

sample_login_df, coc_df, dqo_df, results_df_list, prepsheets_dict = GetData.get_all_data(sdg)

GeneratePDR().generate_pdr(sample_login_df, coc_df, dqo_df, results_df_list, prepsheets_dict)