import os
import sys

# Get the absolute path of the parent directory
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the parent directory to sys.path
sys.path.append(parent_dir)

from config import file_paths
from packages.report_setup import GeneratePDFLayout
import fitz
from reportlab.platypus import Paragraph, Frame
from reportlab.lib.styles import getSampleStyleSheet
import tempfile
import shutil
import re

class GenerateConsumableForm:
    @staticmethod
    def generate_form(data, file_path_list):
        data = {GenerateConsumableForm.split_camel_case(key): value for key, value in data.items()}

        print(data)

        lot_number_list = ', '.split(data['Lot Number'])
        
        # Create a temporary directory for local processing
        with tempfile.TemporaryDirectory() as temp_dir:
            output_pdf_name = f"{data['Consumable ID']}.pdf"
            local_generated_pdf = os.path.join(temp_dir, output_pdf_name)

            if len(lot_number_list) > 1:
                # Generate a new PDF only if multiple lot numbers exist
                GenerateConsumableForm.generate_pdf(local_generated_pdf, data)
                valid_pdfs = [local_generated_pdf] + [
                    pdf for pdf in file_path_list if os.path.exists(pdf) and os.path.getsize(pdf) > 0
                ]
            else:
                # Only merge existing PDFs (without generating a new one)
                valid_pdfs = [
                    pdf for pdf in file_path_list if os.path.exists(pdf) and os.path.getsize(pdf) > 0
                ]

            # Merge PDFs
            final_pdf_path = GenerateConsumableForm.merge_pdfs(valid_pdfs, temp_dir, output_pdf_name)

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
        GeneratePDFLayout.vertical_pair(c, 'Consumable Type', data['Type'], span_x=(width-100)/3, span_y=20, table_x=2*(width-50)/3, table_y=height-150, alignment='CENTER')

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

        

        c.save()
        print(f"Generated PDF saved locally: {output_pdf}")

    @staticmethod
    def merge_pdfs(local_pdf, pdf_list, temp_dir):
        """Merge PDFs efficiently using PyMuPDF (fitz)."""
        if not os.path.exists(local_pdf) or os.path.getsize(local_pdf) == 0:
            print("Error: Local generated PDF is missing or empty.")
            return None

        merged_output = os.path.join(temp_dir, "merged_output.pdf")

        try:
            # Open the base PDF (local PDF that was generated)
            merged_doc = fitz.open(local_pdf)

            # Append additional PDFs
            for pdf in pdf_list:
                if os.path.exists(pdf) and os.path.getsize(pdf) > 0:
                    merged_doc.insert_pdf(fitz.open(pdf))
                else:
                    print(f"Skipping {pdf}, it is missing or empty.")

            # Save the merged document
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

data = {'ConsumableID': 'SRS132105 12-19-24', #
        'Name': 'SRS132105', #
        'Compound': '3M Hydrochloric Acid', 
        'Method': 'ISOTh, ISOU, ISOPu, ISOAm', #
        'Type': 'Tracer', #
        'StartDate': '2024-12-19', #
        'ExpirationDate': '2025-12-19', #
        'LotNumber': 'SRS132105, DI Water', 
        'CatalogNumber': 'SRS132105, Cat123', 
        'Volume': '0.5, 0.5', 
        'Mass': '510.07, 89.93', 
        'Concentration': '', 
        'Activity': '78.66, 0', 
        'Status': True, 
        'FilePath': '//sldafileserver/Lab Data/Lab/Inventory/Consumables/Tracers/Certificates of Calibration/132105.pdf'}

# GenerateConsumableForm.generate_form(data, ['//sldafileserver/Lab Data/Lab/Inventory/Consumables/Tracers/Certificates of Calibration/132105.pdf'])