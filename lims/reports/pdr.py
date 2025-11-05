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
            'InitialResult': 'float64',
            'Result': 'float64', # Results
            'ResultError': 'float64', # Results
            'ResultUnits': 'string', # Results
            'PercentRecovery': 'float64',
            'Aliquot': 'float64', # Results
            'AliquotUnits': 'string', # Results
            'LOQ': 'float64',
            'DL': 'float64',
            'MDL': 'float64',
            'LOD': 'float64',
            'MDA': 'float64',
            'LCSValue': 'float64',
            'DateReceived': 'datetime64[ns]', # SampleLogin
            'AnalysisDateTime': 'datetime64[ns]', # Results
            'SampleDateTime': 'datetime64[ns]',
            'PrepDateTime': 'datetime64[ns]',
            'Survey': 'string', # CoC
            'LabID': 'string', # SLDA
            'FieldID': 'string' # SampleLogin
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
            field_id_dict = {}
            survey_dict = {}
            sample_datetime_dict = {}
            from datetime import datetime

            # Iterate over unique (SDG, SampleID) pairs
            for sdg, sample_id in pdr[['SDG', 'SampleID']].drop_duplicates().itertuples(index=False):

                # Query both SampleDate, SampleTime, and LocationID in one go
                sample_login_query = (
                    self.session.query(
                        tables.SampleLogin.SampleDate,
                        tables.SampleLogin.SampleTime,
                        tables.SampleLogin.LocationID
                    )
                    .filter(
                        tables.SampleLogin.SDG == sdg,
                        tables.SampleLogin.SampleID == sample_id
                    )
                    .first()
                )

                if sample_login_query:
                    # Handle SampleDateTime
                    sample_date = sample_login_query.SampleDate
                    sample_time = sample_login_query.SampleTime

                    if sample_date and sample_time:
                        sample_datetime = datetime.combine(sample_date, sample_time)
                    elif sample_date:
                        sample_datetime = datetime.combine(sample_date, datetime.min.time())
                    else:
                        sample_datetime = None

                    sample_datetime_dict[(sdg, sample_id)] = sample_datetime

                    # Handle LocationID
                    field_id_dict[(sdg, sample_id)] = sample_login_query.LocationID
                else:
                    sample_datetime_dict[(sdg, sample_id)] = None
                    field_id_dict[(sdg, sample_id)] = sample_id  # fallback like your original

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

            # Map the dictionaries to the pdr
            pdr['SampleDateTime'] = pdr[['SDG', 'SampleID']].apply(
                lambda row: sample_datetime_dict.get((row['SDG'], row['SampleID'])),
                axis=1
            )

            pdr['SampleDateTime'] = pdr['SampleDateTime'].fillna(pdr['PrepDateTime'])

            pdr = pdr.drop(columns=['PrepDateTime'])

            pdr['FieldID'] = pdr[['SDG', 'SampleID']].apply(
                lambda row: field_id_dict.get((row['SDG'], row['SampleID'])),
                axis=1
            )

            pdr['DateReceived'] = pdr['SDG'].map(date_received_dict)
            pdr['Survey'] = pdr['SDG'].map(survey_dict)
            
            # LabID is a constant
            pdr['LabID'] = 'SLDA'

            # For MET, we need to remove the (matrix) from the method column
            pdr['Method'] = pdr['Method'].str.replace(r'\s*\(.*?\)', '', regex=True)

        except Exception as e:
            print(f"An exception occurred: {e}")
        finally:
            if self.session:
                self.session.close()

        # Keep only rows where result type is in the result types to keep
        pdr = pdr[pdr['ResultType'].isin(lab_lists.pdr_result_type_list)]

        # Get rid of ICPMS internal standards
        pdr = pdr[~pdr['Analyte'].isin(lab_lists.internal_standards)]

        # Get rid of U-235 and TH-230
        remove_analytes = ['TH-230', 'U-235', 'PU-238']
        mask = (pdr['Method'].str.contains('ISO')) & (pdr['Analyte'].isin(remove_analytes) & pdr['ResultType'].str.contains('LCS'))

        pdr = pdr[~mask]

        # Query the limits table and grab limits closest to analysis date
        from lims.core.limits import GetLimits

        pdr = GetLimits.query_limits(pdr)

        pdr = implement_flags(pdr)

        pdr['InitialResult'] = pdr['InitialResult'].fillna(pdr['Result'])

        mask = (pdr['Flags'] == 'U') & (pdr['Method'].isin(lab_lists.stable_methods))
        pdr.loc[mask, 'Result'] = pdr.loc[mask, 'LOD']

        rounding_key = lab_lists.rounding_key
        limit_columns = ['LowerLimit', 'UpperLimit', 'DL', 'MDA', 'LOD', 'LOQ']

        def round_row(row):
            import re
            rounding_key = lab_lists.rounding_key  # {method: {matrix: {"Aliquot": int, "Numeric": int}}}
            method = row['Method']
            matrix = row['Matrix']

            result_columns = ['InitialResult', 'Result', 'ResultError']
            limit_columns = ['LowerLimit', 'UpperLimit', 'DL', 'MDA', 'LOD', 'LOQ']

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
        
        # Convert from 1 sigma to 2 sigma error
        # pdr['ResultError'] = pdr['ResultError']*1.96

        pdr = pdr.apply(round_row, axis=1)

        # Rename the Aliquot Units
        pdr['AliquotUnits'] = (
            pdr['AliquotUnits']
            .astype(str)
            .str.strip()
            .str.lower()
            .map(lab_lists.aliquot_unit_mapping)
            .fillna(pdr['AliquotUnits'])  # Keep original if not found in mapping
        )

        # Reorder columns
        column_order = ['SDG', 'SampleID', 'DateReceived', 'SampleDateTime', 'InitialResult', 'AnalysisDateTime', 'BatchID', 'LabID', 'Aliquot', 'AliquotUnits', 
                        'ResultType', 'Analyte', 'Result', 'ResultError', 'ResultUnits', 'PercentRecovery', 'Method', 'LowerLimit', 
                        'UpperLimit', 'DL', 'MDA', 'LOD', 'LOQ', 'Flags', 'Matrix', 'Survey', 'FieldID']
        
        pdr = pdr.reindex(columns=column_order)

        sdg = pdr['SDG'].unique().tolist()[0]

        # Construct the output file path
        output_dir = os.path.join(file_paths.sdg_directory, sdg)

        # Ensure the directory exists
        os.makedirs(output_dir, exist_ok=True)

        GeneratePDR.generate_pdr_form(pdr, sdg)

        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(None, "Success", f"PDR successfully generated in the SDG folder.")

    def generate_pdr_form(pdr, sdg):
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        import numpy as np
        import pandas as pd

        pdfmetrics.registerFont(TTFont("Leidos Font", os.path.join(file_paths.fonts_directory, "AvenirNextCyr-Regular.ttf")))
        pdfmetrics.registerFont(TTFont("Leidos Bold Font", os.path.join(file_paths.fonts_directory, "AvenirNextCyr-Bold.ttf")))

        # Clean data
        column_order = ['SampleID', 'FieldID', 'DateReceived', 'SampleDateTime', 'AnalysisDateTime', 'BatchID', 'Aliquot', 'AliquotUnits', 
        'ResultType', 'Analyte', 'ResultUnits', 'InitialResult', 'Result', 'ResultError', 'Flags', 'DL', 'MDA/LOD', 'MDA', 
        'LOD', 'LOQ', 'PercentRecovery', 'Method']

        matrix = pdr['Matrix'].unique().tolist()[0]
        lab_code = pdr['LabID'].unique().tolist()[0]

        # Sort first for consistency
        pdr = pdr.sort_values(by=['BatchID', 'SampleID', 'Analyte']).reset_index(drop=True)

        # Build lookup table and used set
        sample_lookup = {
            (row['BatchID'], row['SampleID'], row['Analyte']): idx
            for idx, row in pdr.iterrows()
        }
        new_order = []
        used_indices = set()

        # Ordered list of suffixes from most specific to most general
        dup_suffixes = ['MSDUP', 'LCSDUP', 'MS', 'DUP']

        # Reorder rows
        for idx, row in pdr.iterrows():
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
        pdr = pdr.loc[new_order].reset_index(drop=True)

        pdr.insert(0, 'MDA/LOD', 0)

        pdr = pdr.reindex(columns=column_order)

        # Combine MDA and LOD.
        method_to_category = {}
        for category, methods in lab_lists.chemistry_categories.items():
            for method in methods:
                method_to_category[method] = category

            # Map the 'Method' column to 'ChemistryCategory'
            pdr['ChemistryCategory'] = pdr['Method'].map(method_to_category)

            # Create the new column based on category
            pdr['MDA/LOD'] = pdr.apply(
                lambda row: row['MDA'] if row['ChemistryCategory'] == 'Radiological Chemistry' else row['LOD'],
                axis=1
            )

        pdr = pdr.drop(columns=['MDA', 'LOD', 'ChemistryCategory', 'Method', 'AnalysisDateTime', 'BatchID', 'DateReceived'])

        pdr.replace(to_replace=[np.nan, 'nan', 'NaN', 'NA', 'null', 'NULL', '<NA>'], value='', inplace=True)

        columns_to_clean = ['DL', 'MDA/LOD', 'LOQ', 'PercentRecovery']

        pdr[columns_to_clean] = pdr[columns_to_clean].replace([0, 0.0, '0', '0.0'], "")

        pdr.rename(columns={
            'SampleDateTime': 'Sample Date/Time',
            'InitialResult': 'Init. Result',
            'SampleID': 'Sample ID',
            'FieldID': 'Field ID',
            'AliquotUnits': 'A. Units',
            'ResultType': 'Sample Type',
            'ResultError': 'Error (2SD)',
            'ResultUnits': 'R. Units',
            'PercentRecovery': '% Recovery',
        }, inplace=True)

        # Output path
        pdf_name = f"{sdg} - Data Report.pdf"
        excel_name = f"{sdg} - Data Report.xlsx"
        output_pdf_path = os.path.join(file_paths.sdg_directory, sdg, pdf_name)
        output_excel_path = os.path.join(file_paths.sdg_directory, sdg, excel_name)

        os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)

        # Page setup
        pagesize = landscape(letter)
        width, height = pagesize
        left_margin = 0.25 * inch
        right_margin = 0.25 * inch

        doc = SimpleDocTemplate(
            output_pdf_path,
            pagesize=pagesize,
            leftMargin=left_margin,
            rightMargin=right_margin,
            topMargin=0.75 * inch,
            bottomMargin=0.25 * inch
        )

        from reportlab.pdfbase.pdfmetrics import stringWidth

        # Convert to string-based table data
        table_data = [pdr.columns.tolist()] + pdr.astype(str).values.tolist()

        # Calculate max text width per column (considering both headers and values)
        font_name = "Leidos Font"
        font_size = 7
        available_width = width - left_margin - right_margin

        max_widths = []
        for col_index, col in enumerate(pdr.columns):
            # Measure header
            max_len = stringWidth(str(col), font_name, font_size)
            
            # Measure each value in the column
            for val in pdr[col].astype(str):
                val_width = stringWidth(val, font_name, font_size)
                if val_width > max_len:
                    max_len = val_width
            
            max_widths.append(max_len)

        # Normalize widths to fit available page width
        total_width = sum(max_widths)
        scale_factor = available_width / total_width
        col_widths = [w * scale_factor for w in max_widths]

        # Create table with wrapped headers
        table = Table(table_data, colWidths=col_widths, repeatRows=1)

        # Table style
        style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#901588')),  # Header background
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Leidos Bold Font'),
            ('FONTNAME', (0, 1), (-1, -1), 'Leidos Font'),
            ('FONTSIZE', (0, 0), (-1, 0), 6),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0.5),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#f0f0f0'))  # soft gray grid
        ]

        # Add alternating background colors for rows starting from row 1 (excluding header at 0)
        num_rows = len(table_data)

        for row in range(1, num_rows):
            bg_color = colors.HexColor('#f0f0f0') if row % 2 == 0 else colors.white
            style.append(('BACKGROUND', (0, row), (-1, row), bg_color))

        # Apply style
        table.setStyle(TableStyle(style))

        from reportlab.lib.styles import ParagraphStyle

        leidos_header_style = ParagraphStyle(
            name='LeidosHeaderStyle',
            fontName="Leidos Font",
            fontSize=7,
            leading=9,
            spaceAfter=6,
            alignment=0  # Left align; use 1 for center if preferred
        )

        # Header function
        def draw_header(canvas, doc):
            canvas.saveState()

            page_number = doc.page
            if page_number == 1:
                GeneratePDFLayout.landscape_page_setup(canvas, f"{sdg} Data Report")
            else:
                header_text = f"{sdg} Data Report — Page {doc.page}"
                p = Paragraph(header_text, leidos_header_style)
                w, h = p.wrap(doc.width, doc.topMargin)
                p.drawOn(canvas, doc.leftMargin, doc.height + doc.topMargin - h + 5)

            canvas.restoreState()

        matrix_paragraph = Paragraph(f"Sample Matrix: {matrix}")
        labcode_paragraph = Paragraph(f"Lab Code: {lab_code}")

        # Build document
        doc.build([Spacer(1, 1 * inch), matrix_paragraph, labcode_paragraph, Spacer(1, 0.1 * inch), table], onFirstPage=draw_header, onLaterPages=draw_header)

        print(f"✅ Generated PDR form: {output_pdf_path}")

        pdr.to_excel(output_excel_path, index=False)
        print(f"✅ Generated PDR excel doc: {output_excel_path}")

    def resource_path(relative_path):
        """Get absolute path to resource, works for dev and for PyInstaller frozen build."""
        try:
            # PyInstaller adds this attribute
            base_path = sys._MEIPASS
        except AttributeError:
            base_path = os.path.abspath(".")

        return os.path.join(base_path, relative_path)
    