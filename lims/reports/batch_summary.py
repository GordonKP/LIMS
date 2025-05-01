import sys
import os

# Get the absolute path to the root "LIMS" directory
current_file = os.path.abspath(__file__)
lims_root = os.path.abspath(os.path.join(current_file, "../../.."))

# Insert it at the start of sys.path
sys.path.insert(0, lims_root)

from lims.config import file_paths
from lims.packages.report_setup import GeneratePDFLayout
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import pandas as pd

class GenerateBatchSummary:
    @staticmethod
    def generate_batch_summary(coc, batch_summary):
        pdfmetrics.registerFont(TTFont("Leidos Font", os.path.join(file_paths.fonts_directory, "AvenirNextCyr-Regular.ttf")))
        pdfmetrics.registerFont(TTFont("Leidos Bold Font", os.path.join(file_paths.fonts_directory, "AvenirNextCyr-Bold.ttf")))
        from reportlab.pdfbase.pdfmetrics import registerFontFamily
        # This maps <b> to the bold font when used in Paragraphs
        registerFontFamily("Leidos Font", normal="Leidos Font", bold="Leidos Bold Font")

        leidos_styles = getSampleStyleSheet()
        leidos_styles.add(ParagraphStyle(
            name='Leidos',
            fontName='Leidos Font',
            fontSize=10,
            leading=12,
            alignment=TA_LEFT,
        ))

        leidos_styles.add(ParagraphStyle(
            name='LeidosRight',
            fontName='Leidos Font',
            fontSize=10,
            leading=12,
            alignment=TA_RIGHT,
        ))

        date_received = batch_summary['DateReceived'].unique().tolist()[0]
        time_received = batch_summary['TimeReceived'].unique().tolist()[0]

        column_order = [
            "SampleID", "Matrix", 'SampleDate', 'SampleTime', "HG", "ISOAM", "ISOTH", "ISOU", "ISOPU", "GAMMA", "GFPC",
            "LSCPU", "LSCAB", "LSCSR", "MET", "TCLP", "BEF", "SIO2", 'FLUOR', "NH3", "NO3", "NO2", "CRVI",
            "CL", "PH", "TSS", "TSP"
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
            max_len = stringWidth(str(col), font_name, font_size)
            for val in batch_summary[col].astype(str):
                val_width = stringWidth(val, font_name, font_size)
                if val_width > max_len:
                    max_len = val_width
            max_widths.append(max_len)

        # Normalize widths
        total_width = sum(max_widths)
        scale_factor = available_width / total_width
        col_widths = [w * scale_factor for w in max_widths]

        # Create table
        table = Table(table_data, colWidths=col_widths, repeatRows=1)

        table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#901588')),
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
        ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
        ]))

        # Header
        def draw_header(canvas, doc):
            canvas.saveState()
            GeneratePDFLayout.landscape_page_setup(canvas, f"SLDA FUSRAP Laboratory Batch Summary")
            canvas.restoreState()

        sample_count = len(table_data) - 1

        header_data = [
            [Paragraph(f"<b>SDG:</b> {sdg}", leidos_styles['Leidos']),
            Paragraph(f"<b>Chain of Custody:</b> {coc}", leidos_styles['Leidos']),
            Paragraph(f"<b>CoC Received:</b> {date_received} {time_received}", leidos_styles['LeidosRight'])],
        ]

        header_table = Table(header_data, colWidths=[3 * inch, 3 * inch, 3 * inch])

        # Create flowables
        elements = [
            Spacer(1, 1 * inch),
            header_table,
            Spacer(1, 0.2 * inch),
            table,
            Spacer(1, 0.2 * inch),
            Paragraph(f"Batch contains {sample_count} samples.", leidos_styles['Leidos'])
        ]

        doc.build(elements, onFirstPage=draw_header)

        print(f"✅ Generated Batch Summary: {output_pdf_path}")