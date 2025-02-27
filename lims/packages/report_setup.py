import os
import sys

# Get the absolute path of the parent directory
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the parent directory to sys.path
sys.path.append(parent_dir)

from config import file_paths
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle

class GeneratePDFLayout:
    def page_setup(c, header_text):
        # Font
        pdfmetrics.registerFont(TTFont("Leidos Font", os.path.join(file_paths.fonts_directory, "AvenirNextCyr-Regular.ttf")))
        pdfmetrics.registerFont(TTFont("Leidos Bold Font", os.path.join(file_paths.fonts_directory, "AvenirNextCyr-Bold.ttf")))

        width, height = letter
        
        # Image
        image_path = os.path.join(file_paths.images_directory, 'transparent_leidos.png')

        img = ImageReader(image_path)

        # Get original image dimensions
        img_width, img_height = img.getSize()

        # Scale down while maintaining aspect ratio
        max_width = 150  # Maximum width allowed
        max_height = 75  # Maximum height allowed

        scale_factor = min(max_width / img_width, max_height / img_height)
        new_width = img_width * scale_factor
        new_height = img_height * scale_factor

        # **Move Image to Top-Left**
        c.drawImage(image_path, 50, height - new_height - 20, width=new_width, height=new_height, mask='auto')

        # Header
        c.setFont("Leidos Bold Font", 16)
        c.drawCentredString(width / 2, height - 110, f"{header_text}")

    def vertical_pair(c, label, value, span_x, span_y, table_x, table_y, alignment):
        table = Table([[label], [value]], colWidths=['*'])
        table.setStyle(TableStyle([
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),  # Header text color to black
            ('ALIGN', (0, 0), (-1, -1), alignment),  # Center align all text
            ('FONTNAME', (0, 0), (-1, 0), 'Leidos Bold Font'),  # Header font for first row (header)
            ('FONTNAME', (0, 1), (-1, -1), 'Leidos Font'),  # Different font for values (data rows)
            ('FONTSIZE', (0, 0), (-1, -1), 12),  # Font size for all
            ('BOTTOMPADDING', (0, 0), (-1, 0), 5),  # Space in header

            ('BACKGROUND', (0, 1), (0, 1), colors.whitesmoke),
        ]))

        # Draw Table on Canvas
        table.wrapOn(c, span_x, span_y)  # Wrap table to fit canvas
        table.drawOn(c, table_x, table_y - 20)  # Adjust height