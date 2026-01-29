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

    def _tmp_sibling_path(self, final_path: str) -> str:
        """
        Create a temp filename in the same directory as final_path
        (best for atomic replace on shares).
        """
        import time
        out_dir = os.path.dirname(final_path)
        os.makedirs(out_dir, exist_ok=True)

        base, ext = os.path.splitext(os.path.basename(final_path))
        return os.path.join(out_dir, f"~{base}__tmp_{os.getpid()}_{int(time.time())}{ext}")

    def _safe_finalize_file(self, tmp_path: str, final_path: str, retries: int = 3, retry_wait: float = 0.75):
        """
        Atomically replace final_path with tmp_path.
        If final_path is locked, ask user whether to create a copy (timestamped).
        Returns the path actually written, or None if user declines.
        """
        import time
        from datetime import datetime
        from lims.core.popups import Popup

        out_dir = os.path.dirname(final_path)
        os.makedirs(out_dir, exist_ok=True)

        base, ext = os.path.splitext(os.path.basename(final_path))

        # Try normal overwrite first
        for _ in range(retries + 1):
            try:
                os.replace(tmp_path, final_path)
                return final_path
            except (PermissionError, OSError):
                time.sleep(retry_wait)

        # Locked: ask user if they want a copy
        choice = Popup.choice(
            "File is Open",
            "This file is open somewhere, would you like to create a copy?\n"
            "The copy will contain the current timestamp at the end of the file name.",
            ["Yes", "No"]
        )

        if str(choice).strip().lower() == "yes":
            stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            fallback_path = os.path.join(out_dir, f"{base} ({stamp}){ext}")
            os.replace(tmp_path, fallback_path)
            return fallback_path

        # User said no: cleanup temp and return None
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        return None


    def _safe_write_csv(self, df: pd.DataFrame, final_path: str) -> str:
        """
        Write CSV to temp, then commit safely.
        Returns the final path written, or None if user declined creating a copy.
        """
        tmp_path = self._tmp_sibling_path(final_path)
        wrote_path = None
        try:
            df.to_csv(tmp_path, index=False)
            wrote_path = self._safe_finalize_file(tmp_path, final_path)
            return wrote_path
        finally:
            # If user declined or something failed before commit, clean up the temp file.
            if wrote_path is None:
                try:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                except Exception:
                    pass

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
            'PrepDateTime': 'datetime64[ns]',
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
            'DL': 'Float64',
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
            'MDA': 'Float64',
            'Aliquot': 'Float64',
            'LOQ': 'Float64'
        }

        # Create an empty DataFrame with the correct dtypes
        df = pd.DataFrame({col: pd.Series(dtype=dtype) for col, dtype in df_dtypes.items()})

        # Get the results from each results table into the df
        for batch in results_df_list:
            df = pd.concat([batch.reindex(columns=df_dtypes.keys()) for batch in results_df_list], ignore_index=True)

        # Enforce dtypes
        df = df.astype(df_dtypes)

        # Keep only rows where result type is in the result types to keep
        df = df[df['ResultType'].isin(lab_lists.pdr_result_type_list)]

        # Get rid of ICPMS internal standards
        df = df[~df['Analyte'].isin(lab_lists.internal_standards)]

        # Get rid of U-235 and TH-230
        remove_analytes = ['TH-230', 'U-235', 'PU-238']
        mask = (df['Method'].str.contains('ISO')) & (df['Analyte'].isin(remove_analytes) & df['ResultType'].str.contains('LCS'))

        df = df[~mask]

        from datetime import datetime

        try:
            self.init_session()

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

            df['COCID'] = df['SDG'].map(coc_id_dict)

            from lims.core.get_sample_login_data import GetSampleLoginData
            sample_login_data = GetSampleLoginData()

            df = sample_login_data.fill_field_id(df)
            df['LOCID'] = df['FieldID']
            df.drop(columns='FieldID')

            df["SampleID"] = df["SampleID"].astype(str)
            df["LOCID"] = df["LOCID"].astype(str)

            mask = (
                df["SampleID"].notna() &
                df["LOCID"].notna() &
                (df["SampleID"] == df["LOCID"])
            )

            df.loc[mask, "LOCID"] = "LAB"

            df = sample_login_data.fill_sample_date_time(df)
            df["LOGDATE"] = df["SampleDateTime"].dt.date
            df["LOGTIME"] = df["SampleDateTime"].dt.time
            df.drop(columns='SampleDateTime')

            # For MET, we need to remove the (matrix) from the method column
            df['Method'] = df['Method'].str.replace(r'\s*\(.*?\)', '', regex=True)

        except Exception as e:
            print(f"An exception occurred: {e}")
        finally:
            if self.session:
                self.session.close()

        df['EXTDATE'] = df['PrepDateTime'].dt.date
        df['EXTTIME'] = df['PrepDateTime'].dt.time

        df['LOGDATE'] = df['LOGDATE'].fillna(df['EXTDATE'])
        
        df['EXTTIME_HHMM'] = df['PrepDateTime'].dt.strftime('%H%M')

        df['LOGTIME'] = df['LOGTIME'].fillna(df['EXTTIME_HHMM'])

        df.drop(columns=['PrepDateTime', 'EXTTIME_HHMM'])

        # Query the limits table and grab limits closest to analysis date
        from lims.core.limits import GetLimits

        # Fill the blank DilutionFactor with 1
        df['DilutionFactor'] = df['DilutionFactor'].replace(['', np.nan, None, 0], 1)

        # Get the limits
        df = GetLimits.query_limits(df)

        # Implement flags
        df = implement_flags(df)

        # For EDD purposes, use DL for MDL
        df['MDL'] = df['MDL'].fillna(df['DL'])

        df['Analyte'] = df['Analyte'].replace({
            'BERYLLIUM': 'BE',
            'LEAD': 'PB'
        })

        mask = (
            df['Flags'].str.contains('U', na=False)
            & df['Method'].isin(lab_lists.stable_methods)
        )
        df.loc[mask, 'Result'] = df.loc[mask, 'LOD']

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
        df = df.apply(GenerateEDD.parvq, axis=1)
        df = df.apply(GenerateEDD.prc_code, axis=1)

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

        if df.empty:
            print("df is empty right before rounding")
        else:
            print("Not empty")

        # Already in 2 sigma
        # df['ResultError'] = df['ResultError']

        # Round everything
        df = df.apply(GenerateEDD.round_row, axis=1)
        
        df['PRECISION_'] = df.apply(GenerateEDD.get_precision, axis=1)

        df = self.spikes(df, prepsheets_dict)

        # Sort first for consistency
        df = df.sort_values(by=['BatchID', 'SampleID', 'Analyte']).reset_index(drop=True)

        # Build lookup table and used set
        sample_lookup = {
            (row['BatchID'], row['SampleID'], row['Analyte']): idx
            for idx, row in df.iterrows()
        }
        new_order = []
        used_indices = set()

        # Ordered list of suffixes from most specific to most general
        dup_suffixes = ['MSDUP', 'LCSDUP', 'MS', 'DUP']

        # Reorder rows
        for idx, row in df.iterrows():
            if idx in used_indices:
                continue

            sample_id = row['SampleID']
            batch_id = row['BatchID']
            analyte = row['Analyte']

            # Add parent
            new_order.append(idx)
            used_indices.add(idx)

            # Check for each possible child in order of specificity
            for suffix in dup_suffixes:
                child_id = sample_id + suffix
                child_key = (batch_id, child_id, analyte)

                if child_key in sample_lookup:
                    child_idx = sample_lookup[child_key]
                    if child_idx not in used_indices:
                        new_order.append(child_idx)
                        used_indices.add(child_idx)

        # Reorder the DataFrame
        df = df.loc[new_order].reset_index(drop=True)

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

        df['MDL'] = df['MDL'].replace([0, None, ''], np.nan)
        df['LOD'] = df['LOD'].replace([0, None, ''], np.nan)

        # Make it so that MDA/LOD go into LOD
        df['LOD'] = df['LOD'].fillna(df['MDA'])

        # Make it so that DL goes into MDL
        df['MDL'] = df['MDL'].fillna(df['DL'])

        df = df.drop(columns=['BatchID', 'Flags', 'DER', 'AnalysisDateTime', 'PercentRecovery', 'ResultError', 'Method', 
                              'ResultType', 'MDA', 'DL', 'LOQ', 'ParentResult'])
        
        df = df[lab_lists.EDD_columns.keys()]
        
        sdg = df['SDG'].unique().tolist()[0]

        # Construct the output file path
        output_dir = os.path.join(file_paths.sdg_directory, sdg)
        output_file = os.path.join(output_dir, f"{sdg}-EDD.csv")

        # Ensure the directory exists
        os.makedirs(output_dir, exist_ok=True)

        final_csv_path = self._safe_write_csv(df, output_file)

        from PyQt5.QtWidgets import QMessageBox
        if final_csv_path:
            print(f"✅ Generated EDD: {final_csv_path}")
            QMessageBox.information(None, "Success", f"EDD successfully generated in the SDG folder.")
        else:
            print("⚠️ EDD output was locked; user declined creating a copy. No file written.")
            QMessageBox.information(None, "Canceled", "EDD was not generated because the file was open and you chose not to create a copy.")

        from PyQt5.QtWidgets import QMessageBox

    def get_precision(row):
        method = row['Method']
        matrix = row['Matrix']
        
        value = lab_lists.rounding_key.get(method)
        
        # Case: nested { method -> { matrix -> {Aliquot, Numeric} } }
        if isinstance(value, dict):
            inner = value.get(matrix)
            if isinstance(inner, dict):
                # return Numeric precision only
                return inner.get("Numeric", None)
            # if someone structured it as method->dict directly
            return inner
        
        # Case: straight numeric value
        return value

    def round_row(row):
        import re
        rounding_key = lab_lists.rounding_key  # {method: {matrix: {"Aliquot": int, "Numeric": int}}}
        method = row['Method']
        matrix = row['Matrix']

        result_columns = ['InitialResult', 'Result', 'ResultError', 'PARUN']
        limit_columns = ['LowerLimit', 'UpperLimit', 'DL', 'MDA', 'LOD', 'LOQ', 'MDL']

        # ints everywhere; default to 1 if missing
        aliquot_decimals = rounding_key.get(method, {}).get(matrix, {}).get("Aliquot", 1)
        # numeric_decimals = rounding_key.get(method, {}).get(matrix, {}).get("Numeric", 1)

        # ---- Aliquot (fixed-point) ----
        try:
            val = row.get('Aliquot', None)
            if val is None or (isinstance(val, str) and val.strip() == '') or pd.isna(val):
                pass
            else:
                v = float(val)
                row['Aliquot'] = '' if v == 0 else f"{v:.{aliquot_decimals}f}"
        except (ValueError, TypeError):
            # Non-numeric (e.g., 'ND') -> leave as-is
            pass

        # # ---- Numeric columns (scientific notation) ----
        # for col in numeric_columns:
        #     val = row.get(col, None)

        #     if val is None or (isinstance(val, str) and val.strip() == "") or pd.isna(val):
        #         continue

        #     try:
        #         v = float(val)

        #         if v == 0:
        #             row[col] = 0
        #             continue

        #         # Format with 3 significant figures
        #         row[col] = f"{v:.3g}"

        #     except (ValueError, TypeError):
        #         # Not a number, leave it alone
        #         pass

        def sci3(v, coltype):
            if coltype == 'result':
                if v == 0:
                    return "0.00E+00"
                elif pd.isna(v):
                    return ""
                else:
                    return f"{float(v):.2E}"
            else:
                if v == 0:
                    return ""
                elif pd.isna(v):
                    return ""
                else:
                    return f"{float(v):.2E}"

        for col in result_columns:
            val = row.get(col, None)

            if val is None or (isinstance(val, str) and val.strip() == "") or pd.isna(val):
                continue

            try:
                v = float(val)
                row[col] = sci3(v, 'result')

            except (ValueError, TypeError):
                # Not a number, leave it alone
                pass

        for col in limit_columns:
            val = row.get(col, None)

            if val is None or (isinstance(val, str) and val.strip() == "") or pd.isna(val):
                continue

            try:
                v = float(val)
                if col in ['LowerLimit', 'UpperLimit']:
                    if any(x in row['ResultType'] for x in ['LCS', 'MS']):
                        row[col] = f"{v:.2f}"
                    else:
                        row[col] = sci3(v, 'limit')
                else:
                    row[col] = sci3(v, 'limit')

            except (ValueError, TypeError):
                # Not a number, leave it alone
                pass

        # ---- PercentRecovery / RPD / DER (two decimals) ----
        for col, zero_fmt in [('PercentRecovery', ''), ('RPD', '0.00'), ('DER', '0.00')]:
            try:
                v = row.get(col, None)
                if v is None or pd.isna(v):
                    continue
                v = float(v)
                row[col] = zero_fmt if v == 0 else f"{v:.2f}"
            except (ValueError, TypeError):
                pass

        return row

    def set_sacode(row):
        type = row['ResultType']
        if type == 'REG':
            row['SACODE'] = 'N'
        elif type == 'BLK':
            row['SACODE'] = 'LB'
        elif type == 'DUP':
            row['SACODE'] = 'LR'
        elif type == 'LCS':
            row['SACODE'] = 'BS'
        elif type == 'LCSDUP':
            row['SACODE'] = 'BD'
        elif type == 'MS':
            row['SACODE'] = 'MS'
        elif type == 'MSDUP':
            row['SACODE'] = 'MSD'
        else:
            row['SACODE'] = ''

        return row
    
    def parvq(row):
        if row['ResultType'] == 'TRACER':
            row['PARVQ'] = 'TR'
        elif 'U' in row['Flags']:
            row['PARVQ'] = 'ND'
        else:
            row['PARVQ'] = '='

        return row
    
    def prc_code(row):
        if row['ResultType'] == 'TRACER':
            row['ResultType'] = 'TRC'
            row['PRCCODE'] = 'STD'
        elif row['Method'] in lab_lists.rad_methods:
            row['PRCCODE'] = 'RN'
        elif row['Method'] == 'MET':
            row['PRCCODE'] = 'MET'
        else:
            row['PRCCODE'] = 'ORG'

        return row
    
    def spikes(self, df, prepsheets_dict):
        batch_ids = df['BatchID'].unique().tolist()

        try:
            self.init_session()

            # Query all active consumables (Status == 1) once
            active_consumables = self.session.query(tables.ConsumableManagement) \
                .filter(tables.ConsumableManagement.Status == 1) \
                .order_by(desc(tables.ConsumableManagement.StartDate)) \
                .all()

            # Convert to DataFrame and keep latest by LotNumber
            active_df = pd.DataFrame([{
                "LotNumber": c.LotNumber,
                "Component": c.Component,
                "Concentration": c.Concentration,
                "Activity": c.Activity,
                "Type": c.Type,
                "StartDate": c.StartDate,
            } for c in active_consumables]).drop_duplicates(subset='LotNumber', keep='first')

        except Exception as e:
            print(f"Error initializing session or querying consumables: {e}")
            return df

        for batch_id in batch_ids:
            active_prepsheet = prepsheets_dict[batch_id]

            # Merge LCS and Standard data
            consumable_dict = active_prepsheet["LCSs"] | active_prepsheet["Standards"]
            lot_info = {
                k: {"lot_number": v["lot_number"], "amount": v["amount"]}
                for k, v in consumable_dict.items()
            }

            chemistry_category = (
                "Stable"
                if df[df['BatchID'] == batch_id]['Method'].unique().tolist()[0] in lab_lists.stable_methods
                else "RAD"
            )

            for consumable in lot_info.values():
                lot_number = consumable["lot_number"]
                amount = float(consumable["amount"]) if consumable["amount"].strip() != "" else 0.0

                try:
                    query_row = active_df[active_df['LotNumber'] == lot_number]
                    if query_row.empty:
                        continue

                    query = query_row.iloc[0]
                    components = [component.strip() for component in query.Component.split(',')]

                    if chemistry_category == 'Stable':
                        values = [float(value.strip()) for value in query.Concentration.split(',')]
                    else:
                        values = [float(value.strip()) for value in query.Activity.split(',')]

                    analyte_value_dict = dict(zip(components, values))
                    result_type = 'MS' if query.Type == 'Standard' else 'LCS'

                    for analyte in analyte_value_dict:
                        analyte_value_dict[analyte] *= amount

                        update_index = df[
                            (df['BatchID'] == batch_id) &
                            (df['ResultType'].isin([result_type, f"{result_type}DUP"])) &
                            (df['Analyte'] == analyte)
                        ].index

                        for idx in update_index:
                            precision = df.loc[idx, 'PRECISION_']

                            if amount != 0:
                                if 'MS' in result_type:
                                    sample_id = df.loc[idx, 'SampleID']

                                    if 'MSDUP' in sample_id:
                                        parent_id = sample_id.replace('MSDUP', '')
                                    else:
                                        parent_id = sample_id.replace('MS', '')

                                    parent_index =  df[
                                        (df['SampleID'] == parent_id) &
                                        (df['BatchID'] == batch_id) &
                                        (df['ResultType'] == 'REG') &
                                        (df['Analyte'] == analyte)
                                    ].index
                                    
                                    if not parent_index.empty:
                                        parent_result = float(df.loc[parent_index[0], 'Result'])
                                    else:
                                        parent_result = 0.0

                                    expected_value = (analyte_value_dict[analyte] / amount) + parent_result
                                    print(sample_id, parent_id, parent_result, expected_value)
                                    df.at[idx, 'EXPECTED'] = round(expected_value, precision)
                                    df.at[idx, 'SPIKE_ADDED'] = round((analyte_value_dict[analyte] / amount), precision)
                                    df.at[idx, 'EVPREC'] = precision
                                else:
                                    expected_value = analyte_value_dict[analyte] / amount
                                    df.at[idx, 'EXPECTED'] = round(expected_value, precision)
                                    df.at[idx, 'SPIKE_ADDED'] = round(expected_value, precision)
                                    df.at[idx, 'EVPREC'] = precision

                except Exception as e:
                    print(f"An exception occurred for lot {lot_number}: {e}")

        return df

    def resource_path(relative_path):
        """Get absolute path to resource, works for dev and for PyInstaller frozen build."""
        try:
            # PyInstaller adds this attribute
            base_path = sys._MEIPASS
        except AttributeError:
            base_path = os.path.abspath(".")

        return os.path.join(base_path, relative_path)
