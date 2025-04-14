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

basedir = os.path.dirname(__file__)
parentdir = os.path.dirname(basedir)
prepsheetdir = lims.config.file_paths.prepsheet_directory
sdg = '25SL0023'
print(basedir, parentdir)

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
            'PercentRecovery': 'float64',
            'Aliquot': 'float64', # Results
            'AliquotUnits': 'string', # Results
            'MDA': 'float64',
            'LCSValue': 'float64',
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

            print("Trying to query limits.")

            limits_query = self.session.query(
                tables.LIMSLimits.Method,
                tables.LIMSLimits.Matrix,
                tables.LIMSLimits.ResultType,
                tables.LIMSLimits.Analyte,
                tables.LIMSLimits.LowerLimit,
                tables.LIMSLimits.UpperLimit,
                tables.LIMSLimits.DL,
                tables.LIMSLimits.LOD,
                tables.LIMSLimits.LOQ,
                tables.LIMSLimits.EffectiveDate
            ).all()

            if limits_query:
                columns = [
                    'Method', 'Matrix', 'ResultType', 'Analyte',
                    'LowerLimit', 'UpperLimit', 'DL', 'LOD', 'LOQ', 'EffectiveDate'
                ]
                limits_df = pd.DataFrame(limits_query, columns=columns)

                 # Ensure datetime and normalize join keys
                pdr['AnalysisDateTime'] = pd.to_datetime(pdr['AnalysisDateTime'], errors='coerce')
                limits_df['EffectiveDate'] = pd.to_datetime(limits_df['EffectiveDate'], errors='coerce')

                # Get the latest analysis date from pdr
                latest_analysis_date = pdr['AnalysisDateTime'].max()

                # Filter limits to only rows with EffectiveDate <= latest_analysis_date
                limits_df = limits_df[limits_df['EffectiveDate'] <= latest_analysis_date]

                # For each group, keep only the row with the most recent EffectiveDate
                filtered_limits_df = (
                    limits_df
                    .sort_values('EffectiveDate')
                    .groupby(['Method', 'Matrix', 'ResultType', 'Analyte'], as_index=False)
                    .last()
                )

                # Merge filtered limits into pdr based on Method, Matrix, ResultType, Analyte
                pdr = pd.merge(
                    pdr,
                    filtered_limits_df,
                    on=['Method', 'Matrix', 'ResultType', 'Analyte'],
                    how='left'
                )

                limits_columns = ['LowerLimit', 'UpperLimit', 'DL', 'LOD', 'LOQ', 'MDA']

                for column in limits_columns:
                    pdr[column] = pdr[column].astype(float)

        except Exception as e:
            print(f"An exception occurred: {e}")
        finally:
            if self.session:
                self.session.close()

        pdr = implement_flags(pdr)

        # Reorder columns
        column_order = ['SDG', 'SampleID', 'DateReceived', 'AnalysisDateTime', 'BatchID', 'LabID', 'Aliquot', 'AliquotUnits', 
                        'ResultType', 'Analyte', 'Result', 'ResultError', 'ResultUnits', 'PercentRecovery', 'Method', 'LowerLimit', 
                        'UpperLimit', 'DL', 'MDA', 'LOD', 'LOQ', 'Flags', 'Matrix', 'Survey',  'LocationID']
        
        pdr = pdr.reindex(columns=column_order)

        # Sort by Method and ResultType
        pdr = pdr.sort_values(by=['Method', 'ResultType'])

        # Construct the output file path
        output_dir = os.path.join(file_paths.sdg_directory, sdg)
        output_file = os.path.join(output_dir, f"{sdg}-PDR.csv")

        # Ensure the directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Save the file
        pdr.to_csv(output_file, index=False)

        GeneratePDR.generate_pdr_form(pdr)

    def generate_pdr_form(pdr):
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
        column_order = ['SampleID', 'DateReceived', 'AnalysisDateTime', 'BatchID', 'LabID', 'Aliquot', 'AliquotUnits', 
        'ResultType', 'Analyte', 'Result', 'ResultError', 'ResultUnits', 'PercentRecovery', 'Method', 'MDA', 
        'LOD', 'Flags', 'Matrix']

        pdr = pdr.reindex(columns=column_order)

        # Combine MDA and LOD.
        pdr['MDA'] = pdr["MDA"].fillna(pdr["LOD"])
        pdr = pdr.drop(columns='LOD')

        pdr.replace(to_replace=[np.nan, 'NaN', 'NA', 'null', 'NULL', '<NA>'], value='', inplace=True)

        pdr.rename(columns={
            'SampleID': 'Sample ID',
            'DateReceived': 'Received',
            'AnalysisDateTime': 'Analyzed',
            'BatchID': 'Batch ID',
            'LabID': 'Lab ID',
            'AliquotUnits': 'Units',
            'ResultType': 'Sample Type',
            'ResultError': 'Error',
            'ResultUnits': 'Units',
            'PercentRecovery': '% Recovery',
            'MDA': 'MDA/LOD',
        }, inplace=True)

        # Output path
        pdf_name = f"{sdg}-PDR.pdf"
        output_pdf_path = os.path.join(file_paths.sdg_directory, sdg, pdf_name)
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
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),  # You can change this to 'LEFT' if needed
            ('FONTNAME', (0, 0), (-1, 0), 'Leidos Bold Font'),
            ('FONTNAME', (0, 1), (-1, -1), 'Leidos Font'),
            ('FONTSIZE', (0, 0), (-1, 0), 6),   # Header
            ('FONTSIZE', (0, 1), (-1, -1), 7),  # Body
            ('LEFTPADDING', (0, 0), (-1, -1), 1),
            ('RIGHTPADDING', (0, 0), (-1, -1), 1),
            ('TOPPADDING', (0, 0), (-1, -1), 0.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0.5),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
        ]))

        # Header function
        def draw_header(canvas, doc):
            canvas.saveState()
            GeneratePDFLayout.landscape_page_setup(canvas, f"{sdg} Preliminary Data Report")
            canvas.restoreState()

        # Spacer between header and table
        spacer = Spacer(1, 1 * inch)

        # Build document
        doc.build([spacer, table], onFirstPage=draw_header)

        print(f"✅ Generated PDR form: {output_pdf_path}")

    def resource_path(relative_path):
        """Get absolute path to resource, works for dev and for PyInstaller frozen build."""
        try:
            # PyInstaller adds this attribute
            base_path = sys._MEIPASS
        except AttributeError:
            base_path = os.path.abspath(".")

        return os.path.join(base_path, relative_path)

sample_login_df, coc_df, dqo_df, results_df_list, prepsheets_dict = GetData.get_all_data(sdg)

GeneratePDR().generate_pdr(sample_login_df, coc_df, dqo_df, results_df_list, prepsheets_dict)