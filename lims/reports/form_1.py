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


class GenerateForm1:
    def __init__(self):
        self.session = None
        self.engine = None
        self.files_to_merge = []

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
            'ParentResult': 'float64',
            'ResultError': 'float64', # Results
            'ResultUnits': 'string', # Results
            'PercentRecovery': 'float64',
            'Aliquot': 'float64', # Results
            'AliquotUnits': 'string', # Results
            'DL': 'float64',
            'MDA': 'float64',
            'LOD': 'float64',
            'LOQ': 'float64',
            'UpperLimit': 'float64',
            'LowerLimit': 'float64',
            'LCSValue': 'float64',
            'SampleDate': 'datetime64[ns]',
            'DateReceived': 'datetime64[ns]', # SampleLogin
            'AnalysisDateTime': 'datetime64[ns]', # Results
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

        # Get rid of ICPMS internal standards
        df = df[~df['Analyte'].isin(lab_lists.internal_standards)]

        # Query the limits table and grab limits closest to analysis date
        from lims.core.limits import GetLimits

        print(df["LOD"].isna().sum())

        df = GetLimits.query_limits(df)

        print(df["LOD"].isna().sum())

        print(df['ResultType'].unique().tolist())

        df = implement_flags(df)

        print(df['ParentResult'].unique().tolist())

        # Reorder columns
        column_order = ['SDG', 'SampleID', 'AnalysisDateTime', 'BatchID', 'Aliquot', 'AliquotUnits', 
                        'ResultType', 'Analyte', 'Result', 'ResultError', 'ResultUnits', 'PercentRecovery', 
                        'Method', 'DL', 'MDA', 'LOD', 'LOQ', 'Flags', 'Matrix', 'RPD', 'DER', 'UpperLimit', 'LowerLimit', 'ParentResult']
        
        df = df.reindex(columns=column_order)

        # Sort by Method and ResultType
        df = df.sort_values(by=['Method', 'ResultType'])

        # Construct the output file path
        output_dir = os.path.join(file_paths.sdg_directory, sdg)

        # Ensure the directory exists
        os.makedirs(output_dir, exist_ok=True)

        self.generate_page_content(df)

    def generate_page_content(self, df):
        page_list = df[df['ResultType'] == 'REG']['SampleID'].unique().tolist()
        page_list.append(f"QC")

        chemistry_categories = lab_lists.chemistry_categories

        method_to_category = {method: category for category, methods in chemistry_categories.items() for method in methods}

        # Map the Method column using this new dictionary
        df['Category'] = df['Method'].map(method_to_category)

        df['AdjustedMethod'] = df.apply(
            lambda row: f"{row['Method']} ({row['Matrix']})" if row['Method'] == 'MET' else row['Method'],
            axis=1
        )

        anmcode_map = {k: v.get('ANMCode') for k, v in lab_lists.methods_codes_dict.items()}
        excode_map = {k: v.get('EXCode') for k, v in lab_lists.methods_codes_dict.items()}

        df['ANMCode'] = df['AdjustedMethod'].map(anmcode_map)
        df['EXCode'] = df['AdjustedMethod'].map(excode_map)

        df.drop(columns=['AdjustedMethod'], inplace=True) 

        df['MSRecovery'] = df['ParentResult']
        df['LCSRecovery'] = df['ParentResult']
        df['MSDUPRecovery'] = df['PercentRecovery']
        df['LCSDUPRecovery'] = df['PercentRecovery']

        sdg = df['SDG'].unique().tolist()[0]

        from datetime import datetime

        def get_sample_date(sample_id):
            try:
                self.init_session()

                result = self.session.query(
                    tables.SampleLogin.SampleDate,
                    tables.SampleLogin.SampleTime
                ).filter(
                    tables.SampleLogin.SDG == sdg,
                    tables.SampleLogin.SampleID == sample_id
                ).first()

                if result:
                    sample_date, sample_time = result.SampleDate, result.SampleTime

                    # Combine date and time into a single datetime string
                    if sample_date and sample_time:
                        sample_datetime = datetime.combine(sample_date, sample_time)
                        return sample_datetime.strftime("%Y-%m-%d %H:%M:%S")
                    elif sample_date:
                        return sample_date.strftime("%Y-%m-%d")
                    else:
                        return "No date available"
                else:
                    return "No result found"
            except Exception as e:
                return f"Error: {e}"

        for page in page_list:
            if page == 'QC':
                page_samples = df[df['ResultType'] != 'REG']
                sample_date = None
            else:
                page_samples = df[df['SampleID'] == page]
                sample_date = get_sample_date(page)
            self.generate_pdf(page, page_samples, sdg, sample_date)

        pdf_name = f"{sdg} Form 1.pdf"
        output_pdf_path = os.path.join(file_paths.sdg_directory, sdg, pdf_name)

        self.merge_pdfs(self.files_to_merge, output_pdf_path)

        print(f"✅ Generated Form 1: {output_pdf_path}")

    def generate_pdf(self, page, page_samples, sdg, sample_date):
        from reportlab.platypus import KeepTogether
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
        pdfmetrics.registerFont(TTFont("Leidos Font", os.path.join(file_paths.fonts_directory, "AvenirNextCyr-Regular.ttf")))
        pdfmetrics.registerFont(TTFont("Leidos Bold Font", os.path.join(file_paths.fonts_directory, "AvenirNextCyr-Bold.ttf")))

        # Output path
        pdf_name = f"{sdg} {page} Form 1.pdf"
        output_pdf_path = os.path.join(file_paths.sdg_directory, sdg, pdf_name)
        os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)

        # Page setup
        pagesize = portrait(letter)
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

        available_width = width - left_margin - right_margin

        # Define custom styles
        method_style = ParagraphStyle(
            name="MethodStyle",
            fontName="Leidos Font",
            fontSize=9,
            alignment=TA_LEFT,
        )
        anmcode_style = ParagraphStyle(
            name="ANMCodeStyle",
            fontName="Leidos Font",
            fontSize=9,
            alignment=TA_RIGHT,
        )
        category_style = ParagraphStyle(
            name="CategoryStyle",
            fontName="Leidos Bold Font",
            fontSize=10,
            alignment=TA_LEFT,
        )

        elements = []
        elements.append(Spacer(1, 1 * inch))

        for category in page_samples['Category'].unique().tolist():
            first_table_rendered = False

            columns = []

            category_heading = [
            Paragraph(f"<b>{category}</b>", category_style),
            Spacer(1, 0.2 * inch)
            ]
            category_samples = page_samples[page_samples['Category'] == category]

            def render_group_table(group_df, label, result_type=None, suffix=None):
                nonlocal first_table_rendered  # this lets the inner function modify the outer variable
                if group_df.empty:
                    return
                if result_type:
                    if result_type == 'DUP':
                        suffix = 'Precision'
                    elif result_type == 'BLK':
                        suffix = 'Blanks'
                    elif result_type == 'LCS':
                        suffix = 'Accuracy'
                    else: 
                        suffix = result_type
                else:
                    suffix = None

                rounding_key = lab_lists.rounding_key
                limit_columns = ['LowerLimit', 'UpperLimit', 'DL', 'MDA', 'LOD', 'LOQ']

                def round_row(row):
                    method = row['Method']
                    matrix = row['Matrix']
                    # if method in lab_lists.rad_methods:
                    #     if matrix != 'AQ':
                    #         aliquot = float(row['Aliquot'])
                    #         row['Aliquot'] = f"{aliquot:.4f}"
                    #     else:
                    #         aliquot = float(row['Aliquot'])
                    #         if row['ResultType'] == 'LCS':
                    #             row['Aliquot'] = f"{aliquot:.4f}"

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

                group_df = group_df.apply(round_row, axis=1)

                group_df.replace(to_replace=[np.nan, 'nan', 'NaN', 'NA', 'null', 'NULL', '<NA>'], value='', inplace=True)
                
                methods = ", ".join(sorted(group_df['Method'].unique()))
                anm_codes = ", ".join(sorted(group_df['ANMCode'].unique()))
                result_suffix = f" - <b>{suffix}</b>" if suffix else ""
                
                if category == 'Wet Chemistry':
                    label_text = f"<i>Wet Chemistry{result_suffix}</i>"
                    method_para = Paragraph(label_text, method_style)
                    label_table = Table([[method_para]], colWidths=[available_width])
                elif category == 'Elemental Analysis':
                    label_text = f"<i>Elemental Analysis{result_suffix}</i>"
                    method_para = Paragraph(label_text, method_style)
                    label_table = Table([[method_para]], colWidths=[available_width])
                elif category == 'Radiological Chemistry':
                    label_text = f"<i>Radiological Chemistry{result_suffix}</i>"
                    if 'ISO' in methods:
                        label_text = f"<i>ISO{result_suffix}</i>"
                    elif 'LSC' in methods:
                        label_text = f"<i>LSC{result_suffix}</i>"
                    else:
                        label_text = f"<i>{methods}{result_suffix}</i>"
                    method_para = Paragraph(label_text, method_style)
                    label_table = Table([[method_para]], colWidths=[available_width])
                
                # Determine chemistry type
                chemistry = "Stable" if category in ["Elemental Analysis", "Wet Chemistry"] else "RAD"

                # Change method to ANMCode
                group_df['Method'] = group_df['ANMCode']

                # Determine columns based on ResultType (for QC pages only)
                if page == "QC" and result_type:
                    result_type_upper = result_type.upper()
                    if result_type_upper == "DUP":
                        if chemistry == "Stable":
                            columns = ["Analyte", "Method", "AnalysisDateTime", "Result", 'ParentResult', "RPD", "Flags"]
                        else:
                            columns = ["Analyte", "Method", "AnalysisDateTime", "Result", 'ParentResult', "DER", "Flags"]
                    elif result_type_upper == "LCS":
                        columns = ["Analyte", "Method", "AnalysisDateTime", "PercentRecovery", "LowerLimit", "UpperLimit", "Flags"]
                    elif result_type_upper == "MS":
                        columns = ["Analyte", "Method", "AnalysisDateTime", "PercentRecovery", "LowerLimit", "UpperLimit", "Flags"]
                    elif result_type_upper == "LCSDUP":
                        columns = ["Analyte", "Method", "AnalysisDateTime", "LCSDUPRecovery", "LCSRecovery", "RPD", "LowerLimit", "UpperLimit", "Flags"]
                    elif result_type_upper == "MSDUP":
                        columns = ["Analyte", "Method", "AnalysisDateTime", "MSDUPRecovery", "MSRecovery", "RPD", "LowerLimit", "UpperLimit", "Flags"]
                    elif result_type_upper == 'BLK':
                        if chemistry == "Stable":
                            columns = ["Analyte", "Method", "AnalysisDateTime", "ResultUnits", "Result", "DL", "LOD", "LOQ", "Flags"]
                        else:
                            columns = ["Analyte", "Method", "AnalysisDateTime", "ResultUnits", "Result", "ResultError", "DL", "MDA", "Flags"]
                else:
                    # Default to full column set by chemistry type if not a QC page
                    if chemistry == "Stable":
                        columns = ["Analyte", "Method", "AnalysisDateTime", "ResultUnits", "Result", "DL", "LOD", "LOQ", "Flags"]
                    else:
                        columns = ["Analyte", "Method", "AnalysisDateTime", "ResultUnits", "Result", "ResultError", "DL", "MDA",  "Flags"]
                if page == 'QC':
                    footer_data = [[
                        Paragraph(f"SDG: {sdg}", method_style),
                        Paragraph(f"Quality Control", method_style),
                    ]]
                    footer_table = Table(footer_data, colWidths=[available_width / 2.0] * 2)
                    footer_table.setStyle(TableStyle([
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                        ('TOPPADDING', (0, 0), (-1, -1), 0),
                    ]))
                else:
                    footer_data = [[
                    Paragraph(f"SDG: {sdg}", method_style),
                    Paragraph(f"Sample ID: {page}", method_style),
                    Paragraph(f"Received: {sample_date}", method_style)
                    ]]
                    footer_table = Table(footer_data, colWidths=[available_width / 3.0] * 3)
                    footer_table.setStyle(TableStyle([
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                        ('TOPPADDING', (0, 0), (-1, -1), 0),
                    ]))

                content_block = [
                    label_table,
                    Spacer(1, 0.1 * inch),
                    self.generate_table(group_df, columns, available_width),
                    Spacer(1, 0.1 * inch),
                    footer_table,
                    Spacer(1, 0.5 * inch),
                ]
                if not first_table_rendered:
                    elements.append(KeepTogether(category_heading + content_block))
                    first_table_rendered = True
                else:
                    elements.append(KeepTogether(content_block))

            if page == "QC":
                for result_type in category_samples['ResultType'].unique():
                    result_type_samples = category_samples[category_samples['ResultType'] == result_type]

                    # Grouped ISO and LSC
                    iso_group = result_type_samples[result_type_samples['Method'].str.contains("ISO", case=False, na=False)]
                    lsc_group = result_type_samples[result_type_samples['Method'].str.contains("LSC", case=False, na=False)]
                    handled_indices = iso_group.index.union(lsc_group.index)

                    render_group_table(iso_group, "ISO", result_type)
                    render_group_table(lsc_group, "LSC", result_type)

                    # Wet Chemistry: combine all methods
                    if category == 'Wet Chemistry':
                        remaining = result_type_samples.loc[~result_type_samples.index.isin(handled_indices)]
                        render_group_table(remaining, "", result_type)
                    else:
                        # Render remaining individual methods
                        remaining = result_type_samples.loc[~result_type_samples.index.isin(handled_indices)]
                        for method in remaining['Method'].unique():
                            method_df = remaining[remaining['Method'] == method]
                            render_group_table(method_df, "", result_type)
            else:
                # Non-QC logic, with ISO/LSC grouping
                iso_group = category_samples[category_samples['Method'].str.contains("ISO", case=False, na=False)]
                lsc_group = category_samples[category_samples['Method'].str.contains("LSC", case=False, na=False)]
                handled_indices = iso_group.index.union(lsc_group.index)

                render_group_table(iso_group, "ISO")
                render_group_table(lsc_group, "LSC")

                if category == 'Wet Chemistry':
                    remaining = category_samples.loc[~category_samples.index.isin(handled_indices)]
                    render_group_table(remaining, "")
                else:
                    remaining = category_samples.loc[~category_samples.index.isin(handled_indices)]
                    for method in remaining['Method'].unique():
                        method_df = remaining[remaining['Method'] == method]
                        render_group_table(method_df, "")

        def draw_header(canvas, doc):
            canvas.saveState()

            # Draw header
            GeneratePDFLayout.page_setup(canvas, f"{sdg} {page} Form 1")

            canvas.restoreState()

        # Build document
        doc.build(elements, onFirstPage=draw_header)
        self.files_to_merge.append(output_pdf_path)

    def generate_table(self, table_data, columns, available_width):
        # Calculate max text width per column (considering both headers and values)
        font_name = "Leidos Font"
        font_size = 7

        table_data = table_data[columns]

        data = [table_data.columns.tolist()] + table_data.astype(str).values.tolist()

        max_widths = []
        for col_index, col in enumerate(table_data.columns):
            # Measure header
            max_len = stringWidth(str(col), font_name, font_size)
            
            # Measure each value in the column
            for val in table_data[col].astype(str):
                val_width = stringWidth(val, font_name, font_size)
                if val_width > max_len:
                    max_len = val_width
            
            max_widths.append(max_len)

        # Normalize widths to fit available page width
        total_width = sum(max_widths)
        scale_factor = available_width / total_width
        col_widths = [w * scale_factor for w in max_widths]
        
        # Create table with wrapped headers
        table = Table(data, colWidths=col_widths, repeatRows=1)

        # Table style
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#901588')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),  # You can change this to 'LEFT' if needed
            ('FONTNAME', (0, 0), (-1, 0), 'Leidos Bold Font'),
            ('FONTNAME', (0, 1), (-1, -1), 'Leidos Font'),
            ('FONTSIZE', (0, 0), (-1, 0), 6),   # Header
            ('FONTSIZE', (0, 1), (-1, -1), 7),  # Body
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0.5),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
        ]))

        return table
    
    def merge_pdfs(self, pdf_list, output_path):
        from PyPDF2 import PdfMerger
        merger = PdfMerger()
        try:
            for pdf in pdf_list:
                print(f"Adding {pdf} to merger.")
                merger.append(pdf)
            print("Made it to write.")
            merger.write(output_path)
            print("Write successful.")
            merger.close()
            print("Merge saved.")

            for pdf in pdf_list:
                os.remove(pdf)
                print(f"{pdf} removed.")
        except Exception as e:
            print(f"An exception occurred merging pdfs: {e}")

    def resource_path(relative_path):
        """Get absolute path to resource, works for dev and for PyInstaller frozen build."""
        try:
            # PyInstaller adds this attribute
            base_path = sys._MEIPASS
        except AttributeError:
            base_path = os.path.abspath(".")

        return os.path.join(base_path, relative_path)
