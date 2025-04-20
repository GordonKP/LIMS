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
from lims.config import file_paths
from lims.core.flagging import implement_flags
from lims.packages.report_setup import GeneratePDFLayout

prepsheetdir = lims.config.file_paths.prepsheet_directory


class GenerateForm1:
    def __init__(self):
        self.session = None
        self.engine = None

    def init_session(self):
        # Initialize the SQLAlchemy session
        self.engine = create_engine(CONNECTION_STRING)
        tables.Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def generate_form_1(self, sample_login_df, coc_df, dqo_df, results_df_list, prepsheets_dict):
        print("sample_login_df:", sample_login_df)
        print("coc_df:", coc_df)
        print("dqo_df:", dqo_df)
        print("results_df_list:", results_df_list)
        print("prepsheets_dict:", prepsheets_dict)
        print("---------------------------------------------")

        df = pd.DataFrame()

        # Define column data types
        df_dtypes = {
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
            'PercentRecovery': 'float64',
            'Aliquot': 'float64', # Results
            'AliquotUnits': 'string', # Results
            'LOD': 'float64',
            'MDA': 'float64',
            'LCSValue': 'float64',
            'DateReceived': 'datetime64[ns]', # SampleLogin
            'AnalysisDateTime': 'datetime64[ns]', # Results
            'Survey': 'string', # CoC
            'LabID': 'string', # SLDA
            'LocationID': 'string' # SampleLogin
        }

        # Create an empty DataFrame with the correct dtypes
        df = pd.DataFrame({col: pd.Series(dtype=dtype) for col, dtype in df_dtypes.items()})

        # Get the results from each results table into the df
        for batch in results_df_list:
            df = pd.concat([batch.reindex(columns=df_dtypes.keys()) for batch in results_df_list], ignore_index=True)

        # Enforce dtypes
        df = df.astype(df_dtypes)

        try:
            self.init_session()

            # Get the items from sample login by SDG not by row for efficiency
            # DateReceived and Volume
            date_received_dict = {}
            location_id_dict = {}
            survey_dict = {}

            for sdg in df['SDG'].unique().tolist():
                coc_query = self.session.query(tables.CoC.Survey).filter(tables.CoC.SDG == sdg).first()
                
                # Handle cases where no result is found
                if coc_query:
                    survey_dict[sdg] = coc_query.Survey
                else:
                    survey_dict[sdg] = None

            for sdg in df['SDG'].unique().tolist():
                sample_login_query = self.session.query(tables.SampleLogin.DateReceived).filter(tables.SampleLogin.SDG == sdg).first()
                
                # Handle cases where no result is found
                if sample_login_query:
                    date_received_dict[sdg] = sample_login_query.DateReceived
                else:
                    date_received_dict[sdg] = None

            for sample in df['SampleID'].unique().tolist():
                sample_login_query = self.session.query(tables.SampleLogin.LocationID).filter(tables.SampleLogin.SampleID == sample).first()

                if sample_login_query:
                    location_id_dict[sample] = sample_login_query.LocationID
                else:
                    location_id_dict[sample] = 'Lab'

            # Map the dictionaries to the df
            df['DateReceived'] = df['SDG'].map(date_received_dict)
            df['Survey'] = df['SDG'].map(survey_dict)
            df['LocationID'] = df['SampleID'].map(location_id_dict)
            
            # LabID is a constant
            df['LabID'] = 'SLDA'

            # For MET, we need to remove the (matrix) from the method column
            df['Method'] = df['Method'].str.replace(r'\s*\(.*?\)', '', regex=True)

        except Exception as e:
            print(f"An exception occurred: {e}")
        finally:
            if self.session:
                self.session.close()

        # Keep only rows where result type is in the result types to keep
        df = df[df['ResultType'].isin(lab_lists.pdr_result_type_list)]

        # Query the limits table and grab limits closest to analysis date
        from lims.core.limits import GetLimits

        print(df["LOD"].isna().sum())

        df = GetLimits.query_limits(df)

        print(df["LOD"].isna().sum())

        df = implement_flags(df)

        # Reorder columns
        column_order = ['SDG', 'SampleID', 'AnalysisDateTime', 'BatchID', 'Aliquot', 'AliquotUnits', 
                        'ResultType', 'Analyte', 'Result', 'ResultError', 'ResultUnits', 'PercentRecovery', 
                        'Method', 'DL', 'MDA', 'LOD', 'LOQ', 'Flags', 'Matrix']
        
        df = df.reindex(columns=column_order)

        # Sort by Method and ResultType
        df = df.sort_values(by=['Method', 'ResultType'])

        # Construct the output file path
        output_dir = os.path.join(file_paths.sdg_directory, sdg)
        output_file = os.path.join(output_dir, f"{sdg}-Form1.csv")

        # Ensure the directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Save the file
        df.to_csv(output_file, index=False)

    def generate_pdf(self, df):
        page_list = df[df['ResultType'] == 'REG'].unique().tolist()

        chemistry_categories = lab_lists.chemistry_categories