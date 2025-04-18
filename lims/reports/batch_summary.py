import sys
import os

# Get the absolute path to the root "LIMS" directory
current_file = os.path.abspath(__file__)
lims_root = os.path.abspath(os.path.join(current_file, "../../.."))

# Insert it at the start of sys.path
sys.path.insert(0, lims_root)

from lims.config import file_paths
from lims.packages.report_setup import GeneratePDFLayout
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import pandas as pd

class GenerateBatchSummary:
    @staticmethod

    def generate_batch_summary(batch_summary):
        pdfmetrics.registerFont(TTFont("Leidos Font", os.path.join(file_paths.fonts_directory, "AvenirNextCyr-Regular.ttf")))
        pdfmetrics.registerFont(TTFont("Leidos Bold Font", os.path.join(file_paths.fonts_directory, "AvenirNextCyr-Bold.ttf")))

        column_order = [
                "SampleID",
                "Matrix",
                "FIMS",
                "ISOAm",
                "ISOTh",
                "ISOU",
                "ISOPu",
                "GAMMA",
                "GFPC",
                "LSCPu",
                "LSCTotal",
                "Metals",
                "Fluorescence",
                "XRD",
                "Fluoride",
                "Ammonia",
                "Nitrates",
                "Nitrites",
                "Cyanide",
                "Chloride",
                "pH",
                "TSS",
                "DateReceived",
                "TimeReceived"
            ]
        
        sdg = batch_summary['SDG'].unique().tolist()[0]

        # Output path
        pdf_name = f"{sdg}-BatchSummary.pdf"
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

        batch_summary = batch_summary.reindex(columns=column_order)

        from reportlab.pdfbase.pdfmetrics import stringWidth

        # Convert to string-based table data
        table_data = [batch_summary.columns.tolist()] + batch_summary.astype(str).values.tolist()

        # Calculate max text width per column (considering both headers and values)
        font_name = "Leidos Font"
        font_size = 7
        available_width = width - left_margin - right_margin

        max_widths = []
        for col_index, col in enumerate(batch_summary.columns):
            # Measure header
            max_len = stringWidth(str(col), font_name, font_size)
            
            # Measure each value in the column
            for val in batch_summary[col].astype(str):
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
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0.5),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
        ]))

        # Header function
        def draw_header(canvas, doc):
            canvas.saveState()
            GeneratePDFLayout.landscape_page_setup(canvas, f"{sdg} Batch Summary")
            canvas.restoreState()

        # Spacer between header and table
        spacer = Spacer(1, 1 * inch)

        # Build document
        doc.build([spacer, table], onFirstPage=draw_header)

        print(f"✅ Generated PDR form: {output_pdf_path}")