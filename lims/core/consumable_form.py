import os
import sys

# Get the absolute path of the parent directory
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the parent directory to sys.path
sys.path.append(parent_dir)

from lims.config import file_paths
from lims.packages.report_setup import GeneratePDFLayout
import fitz
from reportlab.platypus import Paragraph, Frame, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import tempfile
import shutil
import re

class GenerateConsumableForm:
    @staticmethod
    def generate_form(data, file_path_list):
        data = {GenerateConsumableForm.split_camel_case(key): value for key, value in data.items()}

        lot_number_list = [value.strip() for value in data['Lot Number'].split(',') if value.strip()]

        # Create a temporary directory for local processing
        with tempfile.TemporaryDirectory() as temp_dir:
            output_pdf_name = f"{data['Consumable ID']}.pdf"
            local_generated_pdf = os.path.join(temp_dir, output_pdf_name)

            valid_pdfs = list(filter(lambda pdf: os.path.exists(pdf) and os.path.getsize(pdf) > 0, file_path_list))
            
            if len(lot_number_list) > 1:
                GenerateConsumableForm.generate_pdf(local_generated_pdf, data)
                valid_pdfs.insert(0, local_generated_pdf)

            # Merge PDFs only if there's something to merge
            if valid_pdfs:
                final_pdf_path = GenerateConsumableForm.merge_pdfs(valid_pdfs, temp_dir)
            else:
                final_pdf_path = None
    
            # Determine the final save path on the server
            server_save_path = GenerateConsumableForm.get_filepath(data['Consumable ID'], data['Type'])

            # Move the final merged PDF to the server in one operation
            if final_pdf_path:
                shutil.move(final_pdf_path, server_save_path)
                print(f"Final PDF saved on server: {server_save_path}")
            else:
                print("Error: Merging process failed.")

    @staticmethod
    def generate_pdf(output_pdf, data):
        """Generate and save a PDF locally."""
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter

        c = canvas.Canvas(output_pdf, pagesize=letter)

        GeneratePDFLayout.page_setup(c, f"{data['Consumable ID']}")

        width, height, left_margin, right_margin = GeneratePDFLayout.get_page_dimensions()

        c.setFont("Leidos Font", 12)

        GeneratePDFLayout.vertical_pair(c, 'Consumable Name', data['Name'], span_x=(width-100)/3, span_y=20, table_x=left_margin, table_y=height-150, alignment='CENTER')
        GeneratePDFLayout.vertical_pair(c, 'Consumable Type', data['Type'], span_x=(width-100)/3, span_y=20, table_x=2*(width-25)/3, table_y=height-150, alignment='CENTER')

        c.setFont("Leidos Bold Font", 12)

        c.drawString(left_margin, height-200, "Applicable Methods:")
        c.drawString(left_margin, height-240, "Consumable Date:")
        c.drawRightString(right_margin-100, height-240, "Expiration Date:")

        c.setFont("Leidos Font", 12)

        text_content = data['Method']

        styles = getSampleStyleSheet()
        text_style = styles["Normal"]

        # Create a wrapped paragraph
        text_paragraph = Paragraph(text_content, text_style)
        text_frame = Frame(left_margin+130, height-230, width-50-(left_margin+130), 40, showBoundary=False, topPadding=0, bottomPadding=0)

        text_frame.addFromList([text_paragraph], c)

        c.drawString(left_margin+130, height-240, data['Start Date'])
        c.drawRightString(right_margin, height-240, data['Expiration Date'])

        # Implement component rows
        # 'LotNumber': 'SRS132105, DI Water', 
        # 'CatalogNumber': 'SRS132105, Cat123', 
        # 'Volume': '0.5, 0.5', 
        # 'Mass': '510.07, 89.93', 
        # 'Concentration': '', 
        # 'Activity': '78.66, 0', 

        component_keys = ['Lot Number', 'Catalog Number', 'Volume', 'Mass', 'Concentration', 'Activity']
        no_components = 0

        # Convert the comma-separated values into lists
        for key in component_keys:
            # Ensure the key exists in data
            if key in data:
                # Convert the string to a list, trimming whitespace
                data[key] = [value.strip() for value in data[key].split(',')] if data[key] else []

                # Determine the maximum number of components
                no_components = max(no_components, len(data[key]))

        # Ensure all component lists are the same length
        for key in component_keys:
            if key in data:
                while len(data[key]) < no_components:
                    data[key].append('')  # Append empty strings

        # Generate the header row
        try:
            from lims.config.tables import Base, ConsumableManagement
            from lims.config.config import CONNECTION_STRING
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker

            # Initialize the SQLAlchemy session
            engine = create_engine(CONNECTION_STRING)
            Base.metadata.create_all(engine)
            Session = sessionmaker(bind=engine)
            session = Session()

            consumable_ids = []

            # Corrected zip operation to pair Lot Number and Catalog Number correctly
            for lot_number, catalog_number in zip(data['Lot Number'], data['Catalog Number']):
                result = session.query(
                    ConsumableManagement.ConsumableID, 
                ).filter(
                    ConsumableManagement.LotNumber == lot_number,
                    ConsumableManagement.CatalogNumber == catalog_number,
                    ConsumableManagement.Status == True
                ).first()[0]

                if result:
                    consumable_id= result  # Unpack only if result is found
                else:
                    consumable_id = None, None  # Handle missing values

                consumable_ids.append(consumable_id)

            data['Component ID'] = consumable_ids

        except Exception as e:
            print(f"An exception occurred: {e}")
            session.rollback()
        finally:
            session.close()

        component_keys.insert(0, 'Component ID')

        # Create a list of rows: First row is headers, rest are transposed data
        table_data = [component_keys]  # First row: Headers
        
        num_rows = max(len(data[key]) for key in component_keys)

        # Transpose the data (row-wise instead of column-wise)
        for i in range(num_rows):
            row = [data[key][i] if i < len(data[key]) else '' for key in component_keys]
            table_data.append(row)

        print(table_data)

        # Define the available page width
        available_width = width - 100  # Leave some margin space

        # Use a base font and size for measurement
        font_name = "Leidos Font"
        font_size = 12

        from reportlab.pdfbase.pdfmetrics import stringWidth

        # Calculate text width for each header
        header_widths = [stringWidth(header, font_name, font_size) for header in component_keys]

        # Normalize widths to fit within the available page width
        scale_factor = available_width / sum(header_widths)  # Scale to fit within available width
        colWidths = [w * scale_factor for w in header_widths]  # Adjust each column width

        # Create the table with dynamically calculated column widths
        table = Table(table_data, colWidths=colWidths)

        # Add style
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),  # Header background
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),  # Header text color
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Center align text
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Bold headers
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),  # Padding for headers
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),  # Add grid lines
        ]))

        # Build PDF with table
        table.wrapOn(c, width-100, -height-250)  # Wrap table to fit canvas
        table.drawOn(c, left_margin, height-300)  # Adjust height

        c.save()
        print(f"Generated PDF saved locally: {output_pdf}")

    @staticmethod
    def merge_pdfs(pdf_list, temp_dir):
        """Merge PDFs efficiently using PyMuPDF (fitz)."""
        if not pdf_list:
            print("Error: No valid PDFs to merge.")
            return None

        merged_output = os.path.join(temp_dir, "merged_output.pdf")

        try:
            merged_doc = fitz.open()

            for pdf in pdf_list:
                if os.path.exists(pdf) and os.path.getsize(pdf) > 0:
                    merged_doc.insert_pdf(fitz.open(pdf))
                else:
                    print(f"Skipping {pdf}, it is missing or empty.")

            merged_doc.save(merged_output)
            merged_doc.close()

            print(f"Merged PDF saved locally: {merged_output}")
            return merged_output

        except Exception as e:
            print(f"Critical Error during PDF merging: {e}")
            return None

    @staticmethod
    def get_filepath(consumable_id, consumable_type):
        """Determine the correct server file path."""
        base_dir = file_paths.consumables_inventory_directory
        matching_dirs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d)) and consumable_type in d]

        if not matching_dirs:
            print(f"Error: No matching directory found for '{consumable_type}' in '{base_dir}'")
            return None

        selected_dir = os.path.join(base_dir, matching_dirs[0], consumable_id)
        os.makedirs(selected_dir, exist_ok=True)

        return os.path.join(selected_dir, f"{consumable_id}.pdf")
    
    def split_camel_case(text):
        return re.sub(r'([a-z])([A-Z])', r'\1 \2', text)    