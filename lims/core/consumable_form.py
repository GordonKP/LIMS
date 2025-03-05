import os
import sys

# Get the absolute path of the parent directory
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the parent directory to sys.path
sys.path.append(parent_dir)

from config import file_paths
from packages.report_setup import GeneratePDFLayout
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from PyPDF2 import PdfMerger

class GenerateConsumableForm:
    @staticmethod

    def generate_form(data, file_path_list):
        # Make save path for consumable file inside of the proper directory
        save_path = GenerateConsumableForm.get_filepath(consumable_id=data['ConsumableID'], consumable_type=data['Type'])

        # Generate canvas
        c = canvas.Canvas(save_path, pagesize=letter)

        GeneratePDFLayout.page_setup(c, f"{data['ConsumableID']}")

        # Save canvas
        c.save()

        for pdf in file_path_list:
            print(f"Checking: {pdf}")
            if not os.path.exists(pdf):
                print(f"ERROR: File {pdf} does not exist!")
            elif os.path.getsize(pdf) == 0:
                print(f"ERROR: File {pdf} is empty!")
            else:
                print(f"File {pdf} is ready for merging.")

        GenerateConsumableForm.merge_pdfs(save_path, file_path_list)

    def get_filepath(consumable_id, consumable_type):
        base_dir = file_paths.consumables_inventory_directory  # Root directory
        print("LOOK HERE", consumable_id, consumable_type)
        
        # Get all directories inside base_dir
        matching_dirs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d)) and consumable_type in d]

        print(matching_dirs)
        
        if not matching_dirs:
            print(f"Error: No matching directory found for '{consumable_type}' in '{base_dir}'")
            return None

        # Select the first matching directory (or modify logic if multiple matches should be handled differently)
        selected_dir = os.path.join(base_dir, matching_dirs[0], consumable_id)
        
        # Ensure the target directory exists
        os.makedirs(selected_dir, exist_ok=True)

        # Define PDF filename and path
        filename = f"{consumable_id}.pdf"
        filepath = os.path.join(selected_dir, filename)

        return filepath
    
    def merge_pdfs(output_pdf, pdf_list):
        """ Merges output_pdf with all PDFs in pdf_list sequentially with error handling. """
        merger = PdfMerger()

        try:
            # Check if the newly generated PDF exists before merging
            if os.path.exists(output_pdf) and os.path.getsize(output_pdf) > 0:
                merger.append(output_pdf)
            else:
                print(f"Error: Generated PDF '{output_pdf}' is missing or empty.")
                return

            # Append existing PDFs sequentially
            for pdf in pdf_list:
                if os.path.exists(pdf) and os.path.getsize(pdf) > 0:
                    try:
                        merger.append(pdf)
                    except Exception as e:
                        print(f"Error: Could not append '{pdf}'. Skipping. ({e})")
                else:
                    print(f"Warning: File '{pdf}' not found or is empty. Skipping.")

            # Write the merged PDF back to the output path
            merger.write(output_pdf)
            merger.close()

            print(f"Merged PDF successfully saved at: {output_pdf}")

        except Exception as e:
            print(f"Critical Error during PDF merging: {e}")

data = {'ConsumableID': 'SRS132105 12-19-24', 'Name': 'SRS132105', 'Compound': '1M HCF', 'Method': '', 'Type': 'Tracer', 'StartDate': 'datetime.date(2024, 12, 19)', 'ExpirationDate': 'datetime.date(2025, 12, 19)', 'LotNumber': 'SRS132105', 'CatalogNumber': 'SRS132105', 'Volume': '0.5', 'Mass': '510.07', 'Concentration': '', 'Activity': '78.66', 'Status': True, 'FilePath': '//sldafileserver/Lab Data/Lab/Inventory/Consumables/Tracers/Certificates of Calibration/132105.pdf'}

GenerateConsumableForm.generate_form(data, ['//sldafileserver/Lab Data/Lab/Inventory/Consumables/Tracers/Certificates of Calibration/132105.pdf'])