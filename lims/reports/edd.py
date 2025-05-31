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

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import letter, portrait
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import stringWidth

import numpy as np
import pandas as pd

prepsheetdir = lims.config.file_paths.prepsheet_directory


class GenerateEDD:
    def __init__(self):
        self.session = None
        self.engine = None

    def init_session(self):
        # Initialize the SQLAlchemy session
        self.engine = create_engine(CONNECTION_STRING)
        tables.Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def generate_edd(self, sample_login_df, coc_df, dqo_df, results_df_list, prepsheets_dict):
        print("sample_login_df:", sample_login_df)
        print("coc_df:", coc_df)
        print("dqo_df:", dqo_df)
        print("results_df_list:", results_df_list)
        print("prepsheets_dict:", prepsheets_dict)
        print("---------------------------------------------")

        df = pd.DataFrame()

        # Define column data types
        df_dtypes = {
            'AFIID': 'string',
            'LOCID': 'string', # SampleLogin, LocationID
            'LOGDATE': 'string', # SampleLogin, SampleDate
            'LOGTIME': 'string', # SampleLogin, SampleTime
            'Matrix': 'string', # Results, Matrix
            'SBD': 'Float64', # None
            'SED': 'Float64', # None
            'SACODE': 'string', # Determine if a sample is QC or not. (Either 'QC' or 'NO')
            'SAMPNO': 'Int64', # None
            'LOGCODE': 'string', # ''
            'SMCODE': 'string', # ''
            'SampleID': 'string', # Results, SampleID
            'COCID': 'string', # CoCID
            'COOLER': 'string', # ''
            'ABLOT': 'string', # ''
            'EBLOT': 'string', # ''
            'TBLOT': 'string', # ''
            'REMARKS': 'string', # ''
            'SDG': 'string', # SDG
            'LABCODE': 'string', # LabCode
            'ANMCODE': 'string', # ANMCode
            'EXMCODE': 'string', # EXMCode
            'LCHMETH': 'string', # ''
            'Iteration': 'Int64', # Iteration
            'LABSAMPID': 'string', # SampleID
            'EXTDATE': 'string', # PrepDate (DD-mmm-YYYY)
            'EXTTIME': 'string', # PrepTime (HHMM)
            'LCHDATE': 'string', # ''
            'LCHTIME': 'string', # ''
            'LCHLOT': 'string', # ''
            'AnalysisDateTime': 'datetime64[ns]',
            'ANADATE': 'string', # AnalysisDate (DD-mmm-YYYY)
            'ANATIME': 'string', # AnalysisTime (HHMM)
            'ANALOT': 'string', # BatchID
            'BatchID': 'string', # BatchID
            'CALREFID': 'string', # ''
            'RTTYPE': 'string', # ''
            'BASIS': 'string', # ''
            'Analyte': 'string', # Analyte
            'PRCCODE': 'string', # ORG, MET, RN (radionuclide), STD
            'PARVQ': 'string', # Coded value qualifying the analytical results field (TR, ND (not detected), =)
            'Result': 'Float64', # Result
            'PARUN': 'Float64',
            'ResultError': 'Float64', # ResultError
            'PRECISION_': 'Int64', # Number of digits after the decimal point for PARVAL
            'EXPECTED': 'Float64', # Target result for Spikes, Blanks, LCS
            'EVPREC': 'Int64', # Number of digits after decimal point for EXPECTED
            'MDL': 'Float64', # MDL
            'RL': 'Float64', # Reporting Limit
            'ResultUnits': 'string', # ResultUnits
            'VQ_1C': 'string', # ''
            'VAL_1C': 'Float64', # ''
            'FCVALPREC': 'Int64', # None
            'VQ_CONFIRM': 'string', # ''
            'VAL_CONFIRM': 'Float64', # None
            'CNFVALPREC': 'Int64', # None
            'DilutionFactor': 'Float64', # DilutionFactor (1 for anything that doesnt have one)
            'PRIME_DQT': 'string', # ''
            'PRIME_FLAG': 'string', # ''
            'LAB_DQT': 'string', # ''
            'Flag': 'string', # Flag
            'BEST_RESULT': 'string', # 'Y' yes because we always report the iteration with the best result
            'REASON_CODE': 'string', # ''
            'PercentRecovery': 'Float64', # PercentRecovery
            'RPD': 'Float64', # RPD
            'UPPER_RPD': 'Float64', # RPD Upper Limit
            'UpperLimit': 'Float64', # Upper limit for percent recovery
            'LowerLimit': 'Float64', # Lower limit for percent recovery
            'SPIKE_ADDED': 'Float64', # known value
            'SPIKE_ADDED_PREC': 'Int64', # None
            'VALCODE': 'string', # ''
            'TIC_NAME': 'string', # ''
            'RETENTION_TIME': 'string', # ''
            'LOD': 'Float64', # LOD
            'Method': 'string',
            'ResultType': 'string',
            'MDA': 'Float64'
        }

        # Create an empty DataFrame with the correct dtypes
        df = pd.DataFrame({col: pd.Series(dtype=dtype) for col, dtype in df_dtypes.items()})

        # Get the results from each results table into the df
        for batch in results_df_list:
            df = pd.concat([batch.reindex(columns=df_dtypes.keys()) for batch in results_df_list], ignore_index=True)

        # Enforce dtypes
        df = df.astype(df_dtypes)

        print(df)

        # Keep only rows where result type is in the result types to keep
        df = df[df['ResultType'].isin(lab_lists.pdr_result_type_list)]

        # Get rid of ICPMS internal standards
        df = df[~df['Analyte'].isin(lab_lists.internal_standards)]

        from datetime import datetime

        try:
            self.init_session()

            # Get the items from sample login by SDG not by row for efficiency
            # DateReceived and Volume
            location_id_dict = {}
            coc_id_dict = {}
            sample_date_dict = {}
            sample_time_dict = {}

            for sdg in df['SDG'].unique().tolist():
                coc_query = self.session.query(tables.CoC.CoCID).filter(tables.CoC.SDG == sdg).first()
                
                # Handle cases where no result is found
                if coc_query:
                    coc_id_dict[sdg] = coc_query.CoCID
                else:
                    coc_id_dict[sdg] = None

            for sdg in df['SDG'].unique().tolist():
                sample_login_query = self.session.query(tables.SampleLogin.SampleDate, tables.SampleLogin.SampleTime).filter(tables.SampleLogin.SDG == sdg).first()
                
                # Handle cases where no result is found
                if sample_login_query:
                    # Format SampleDate as-is or leave it raw if you're handling it elsewhere
                    sample_date_dict[sdg] = sample_login_query.SampleDate

                    # Format SampleTime from HH:MM:SS to HHMM
                    sample_time = sample_login_query.SampleTime
                    if sample_time:
                        try:
                            formatted_time = datetime.strptime(str(sample_time), '%H:%M:%S').strftime('%H%M')
                        except ValueError:
                            formatted_time = None
                    else:
                        formatted_time = None

                    sample_time_dict[sdg] = formatted_time
                else:
                    sample_date_dict[sdg] = None
                    sample_time_dict[sdg] = None

            for sample in df['SampleID'].unique().tolist():
                sample_login_query = self.session.query(tables.SampleLogin.LocationID).filter(tables.SampleLogin.SampleID == sample).first()

                if sample_login_query:
                    location_id_dict[sample] = sample_login_query.LocationID
                else:
                    location_id_dict[sample] = 'Lab'

            # Map the dictionaries to the df
            df['LOCID'] = df['SampleID'].map(location_id_dict)
            df['LOGDATE'] = df['SDG'].map(sample_date_dict)
            df['LOGTIME'] = df['SDG'].map(sample_time_dict)
            df['COCID'] = df['SDG'].map(coc_id_dict)

            # For MET, we need to remove the (matrix) from the method column
            df['Method'] = df['Method'].str.replace(r'\s*\(.*?\)', '', regex=True)

        except Exception as e:
            print(f"An exception occurred: {e}")
        finally:
            if self.session:
                self.session.close()

        # Get the EXTDATE and EXTTIME (Prep date and time) from prepsheets
        print(prepsheets_dict)

        for batch_id in df['BatchID'].unique().tolist():
            prepsheet = prepsheets_dict[batch_id]

            prep_data_list = prepsheet['Prep Data']
            prep_date_entry = next((entry for entry in prep_data_list if entry.get('Event Name') == 'Prep Date'), None)

            if prep_date_entry:
                prep_date = prep_date_entry['Prep Date']
                prep_time = prep_date_entry['Prep Time']

                df.loc[df['BatchID'] == batch_id, 'EXTDATE'] = prep_date
                df.loc[df['BatchID'] == batch_id, 'EXTTIME'] = prep_time

        # Query the limits table and grab limits closest to analysis date
        from lims.core.limits import GetLimits

        # Fill the blank DilutionFactor with 1
        df['DilutionFactor'] = df['DilutionFactor'].replace(['', np.nan, None, 0], 1)

        # Get the limits
        df = GetLimits.query_limits(df)

        # Implement flags
        df = implement_flags(df)

        # Assign values to columns
        df['AFIID'] = 'SLDA'
        df['LABCODE'] = 'SLDA'
        df['BEST_RESULT'] = 'Y'
        df['LAB_QC_FLAG'] = df['Flag']
        df['PERCENT_RECOVERY'] = df['PercentRecovery']
        df['LABSAMPID'] = df['SampleID']
        df['ANALOT'] = df['BatchID']
        df['LABLOTCTL'] = df['BatchID']
        df['LAB_QC_FLAG'] = df['Flags']

        # Fill in UPPER_RPD
        cond_dup_stable = df['ResultType'].str.contains('DUP', na=False) & (df['Method'].isin(lab_lists.stable_methods))
        cond_dup_rad = df['ResultType'].str.contains('DUP', na=False) & (df['Method'].isin(lab_lists.rad_methods))
        rpd_uppers = [20, 3]
        df['UPPER_RPD'] = np.select([cond_dup_stable, cond_dup_rad], rpd_uppers, default=np.nan)

        # Combine RPD and DER columns
        df['RPD'] = df['RPD'].fillna(df['DER'])

        mask = (df['UPPER_RPD'].isna()) & (df['RPD'] == 0)
        df.loc[mask, 'RPD'] = np.nan

        # UPPER and LOWER ACCURACY
        df['UpperLimit'] = df['UpperLimit'].replace(['', None, 0], np.nan)
        df['LowerLimit'] = df['LowerLimit'].replace(['', None, 0], np.nan)

        # PERCENT_RECOVERY
        df['PERCENT_RECOVERY'] = df['PERCENT_RECOVERY'].replace(['', None, 0], np.nan)

        #PARUN
        df['PARUN'] = df['ResultError']

        # Set SACODE
        df = df.apply(GenerateEDD.set_sacode, axis=1)

        # Method codes
        df['ANMCODE'] = df['Method'].map(lambda method: lab_lists.methods_codes_dict.get(method, {}).get('ANMCode'))
        df['EXMCODE'] = df['Method'].map(lambda method: lab_lists.methods_codes_dict.get(method, {}).get('EXCode'))

        # Get date and time from AnalysisDateTime
        df['ANADATE'] = df['AnalysisDateTime'].dt.strftime('%d-%b-%Y')
        df['ANATIME'] = df['AnalysisDateTime'].dt.strftime('%H%M')

        # Ensure LOGDATE and EXTDATE are in datetime format before formatting
        df['LOGDATE'] = pd.to_datetime(df['LOGDATE'], errors='coerce').dt.strftime('%d-%b-%Y')
        df['EXTDATE'] = pd.to_datetime(df['EXTDATE'], errors='coerce').dt.strftime('%d-%b-%Y')

        # Format EXTTIME to HHMM (ensure they're strings first)
        df['EXTTIME'] = df['EXTTIME'].astype(str).str.replace(":", "").str.zfill(4)

        # Round everything
        df = df.apply(GenerateEDD.round_row, axis=1)
        
        df['PRECISION_'] = df.apply(GenerateEDD.get_precision, axis=1)

        # Rename columns
        df = df.rename(columns={
            'Matrix': 'MATRIX',
            'SampleID': 'FLDSAMPID',
            'Iteration': 'RUN_NUMBER',
            'Analyte': 'PARLABEL',
            'ResultUnits': 'UNITS',
            'DilutionFactor': 'DILUTION',
            'UpperLimit': 'UPPER_ACCURACY',
            'LowerLimit': 'LOWER_ACCURACY',
            'Result': 'PARVAL',
        })

        df = df.drop(columns=['BatchID', 'Flags', 'DER', 'AnalysisDateTime', 'PercentRecovery', 'ResultError', 'Method', 
                              'ResultType', 'MDA', 'DL', 'LOQ', 'ParentResult'])
        
        df = df[lab_lists.EDD_columns.keys()]

        df['MDL'] = df['MDL'].replace([0, None, ''], np.nan)
        df['LOD'] = df['LOD'].replace([0, None, ''], np.nan)

        df.to_csv("EDDTEST.csv")

        # # Reorder columns
        # column_order = ['SDG', 'SampleID', 'AnalysisDateTime', 'BatchID', 'Aliquot', 'AliquotUnits', 
        #                 'ResultType', 'Analyte', 'Result', 'ResultError', 'ResultUnits', 'PercentRecovery', 
        #                 'Method', 'DL', 'MDA', 'LOD', 'LOQ', 'Flags', 'Matrix', 'RPD', 'DER', 'UpperLimit', 'LowerLimit', 'ParentResult']
        
        # df = df.reindex(columns=column_order)

        # # Sort by Method and ResultType
        # df = df.sort_values(by=['Method', 'ResultType'])

        # # Construct the output file path
        # output_dir = os.path.join(file_paths.sdg_directory, sdg)
        # output_file = os.path.join(output_dir, f"{sdg}-Form1.csv")

        # # Ensure the directory exists
        # os.makedirs(output_dir, exist_ok=True)

        # # Save the file
        # df.to_csv(output_file, index=False)

    def get_precision(row):
        method = row['Method']
        matrix = row['Matrix']
        
        value = lab_lists.rounding_key.get(method)
        
        if isinstance(value, dict):  # e.g., if method is 'MET'
            return value.get(matrix, None)
        return value

    def round_row(row):
        rounding_key = lab_lists.rounding_key
        method = row['Method']
        decimals = 3  # Default
        if method == 'MET':
            matrix = row.get('Matrix', '')
            decimals = rounding_key.get('MET', {}).get(matrix, 3)
        else:
            decimals = rounding_key.get(method, 3)
        
        # Format Result with trailing zeros
        try:
            val = row['Result']
            row['Result'] = f"{val:.{decimals}f}"
        except (ValueError, TypeError):
            pass

        try:
            val = row['ParentResult']
            row['ParentResult'] = f"{val:.{decimals}f}"
        except (ValueError, TypeError):
            pass

        # Format ResultError
        try:
            val = row['ResultError']
            row['ResultError'] = '' if val == 0 else f"{val:.{decimals}f}"
        except (ValueError, TypeError):
            pass

        limit_columns = ['LowerLimit', 'UpperLimit', 'DL', 'MDA', 'LOD', 'LOQ']
        # Format limit columns
        for col in limit_columns:
            val = row.get(col, None)
            if pd.notnull(val):
                try:
                    if 'LCS' in row['ResultType'] or 'MS' in row['ResultType']:
                        row[col] = '' if val == 0 else f"{val:.2f}"
                    else:
                        row[col] = '' if val == 0 else f"{val:.{decimals}f}"
                except (ValueError, TypeError):
                    pass

        # Format PercentRecovery
        try:
            val = row['PercentRecovery']
            row['PercentRecovery'] = '' if val == 0 else f"{val:.2f}"
        except (ValueError, TypeError):
            pass

        try:
            val = row['RPD']
            row['RPD'] = '' if val == 0 else f"{val:.2f}"
        except (ValueError, TypeError):
            pass

        return row

    def set_sacode(row):
        if row['ResultType'] != 'REG':
            row['SACODE'] = 'QC'
        else:
            row['SACODE'] = 'NO'
        return row

    def resource_path(relative_path):
        """Get absolute path to resource, works for dev and for PyInstaller frozen build."""
        try:
            # PyInstaller adds this attribute
            base_path = sys._MEIPASS
        except AttributeError:
            base_path = os.path.abspath(".")

        return os.path.join(base_path, relative_path)
    
sdg = '25SL0001'

sample_login_df, coc_df, dqo_df, results_df_list, prepsheets_dict = GetData.get_all_data(sdg)

GenerateEDD().generate_edd(sample_login_df, coc_df, dqo_df, results_df_list, prepsheets_dict)