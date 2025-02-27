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
from reportlab.platypus import Paragraph, Frame
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.utils import ImageReader

class GenerateCertificate:
    @staticmethod

    def generate_pdf(data):
        filepath = GenerateCertificate.get_filepath(data['SRS'], data['Consumable Type'])

        # Generate PDF
        c = canvas.Canvas(filepath, pagesize=letter)

        width, height = letter

        # Header
        GeneratePDFLayout.page_setup(c, f"{data['Consumable Type']} Certificate of Calibration")

        c.setFont("Leidos Font", 12)

        c.drawCentredString(width / 2, height-130, f"Solution prepared on {data['Solution Prep Date']}")

        # Source Information
        c.setFont("Leidos Bold Font", 14)

        c.drawString(50, height-160, "Source Information")

        c.setFont("Leidos Font", 12)

        c.line(50, height-165, width-50, height-165)

        GeneratePDFLayout.vertical_pair(c, "Principle Radionuclide", data['Principle Radionuclide'], (width/3), 40, 50, (height-200), 'CENTER')
        GeneratePDFLayout.vertical_pair(c, "Half-Life (Days)", data['Half-Life (Days)'], (width/3), 40, width-(width/3)-50, (height-200), 'CENTER')
        GeneratePDFLayout.vertical_pair(c, "SRS", data['SRS'], (width/3), 40, 50, (height-260), 'CENTER')

        c.setFont("Leidos Bold Font", 12)

        c.drawString(width-(width/3)-50, height-255, f"Source Volume:")
        c.drawString(width-(width/3)-50, height-275, f"Source Activity:")
        c.drawString(width-(width/3)-50, height-295, f"Source Activity Date:")

        c.setFont("Leidos Font", 12)

        c.drawRightString(width-50, height-255, f"{data['Source Volume (L)']} L")
        c.drawRightString(width-50, height-275, f"{data['Source Activity (pCi)']} pCi")
        c.drawRightString(width-50, height-295, f"{data['Source Activity Date']}")

        c.setFont("Leidos Bold Font", 12)

        c.drawString(50, height-320, f"Chemical Composition of Solution:")

        c.setFont("Leidos Font", 12)

        c.drawString(275, height-320, f"{data['Dilution Solution']}")

        # Laboratory Operations
        c.setFont("Leidos Bold Font", 14)

        c.drawString(50, height-370, "Laboratory Operations")

        c.setFont("Leidos Font", 12)

        c.line(50, height-375, width-50, height-375)

        c.setFont("Leidos Bold Font", 12)

        c.drawString(50, height-410, "Initial Container Weight:")
        c.drawString(50, height-430, "Final Container Weight:")
        c.drawString(50, height-450, "Mass of Solution:")

        c.setFont("Leidos Font", 12)

        c.drawRightString(275, height-410, f"{data['Initial Container Weight (g)']} g")
        c.drawRightString(275, height-430, f"{data['Final Container Weight (g)']} g")
        c.drawRightString(275, height-450, f"{data['Solution Mass (g)']} g")

        # Dilution solyution box
        styles = getSampleStyleSheet()
        text_style = styles["Normal"]

        # Get text data
        text_content = data["Dilution Solution"] if data["Dilution Solution"] is not None else "No dilution, used as received."

        # Create a wrapped paragraph
        text_paragraph = Paragraph(text_content, text_style)
        text_frame = Frame(width-250, height-455, 200, 60, showBoundary=True)

        text_frame.addFromList([text_paragraph], c)

        # Formula for activity given decay
        image_path = os.path.join(file_paths.images_directory, 'activity_formula.png')

        img = ImageReader(image_path)

        # Get original image dimensions
        img_width, img_height = img.getSize()

        # Scale down while maintaining aspect ratio
        max_width = img_width/4  # Maximum width allowed
        max_height = img_height/4  # Maximum height allowed

        scale_factor = min(max_width / img_width, max_height / img_height)
        new_width = img_width * scale_factor
        new_height = img_height * scale_factor

        c.drawImage(image_path, 50, height - new_height - 440, width=new_width, height=new_height, mask='auto')

        c.drawRightString(width-50, height-500, "test")

        # Save pdf
        c.save()

        print(f"PDF saved at: {filepath}")

    def get_filepath(srs, consumable_type):
        base_dir = file_paths.calibration_cert_directory  # Root directory
        
        # Get all directories inside base_dir
        matching_dirs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d)) and consumable_type in d]
        
        if not matching_dirs:
            print(f"Error: No matching directory found for '{consumable_type}' in '{base_dir}'")
            return

        # Select the first matching directory (or modify logic if multiple matches should be handled differently)
        selected_dir = os.path.join(base_dir, matching_dirs[0], "Certificates of Calibration")
        
        # Ensure the target directory exists
        os.makedirs(selected_dir, exist_ok=True)

        # Define PDF filename and path
        filename = f"{srs}.pdf"
        filepath = os.path.join(selected_dir, filename)

        return filepath

data = {'Principle Radionuclide': 'Ba-133', #
        'Half-Life (Days)': '100', #
        'Solution Prep Date': '02-26-2025', #
        'SRS': 'SRS0001', #
        'Source Activity (pCi)': '100', #
        'Source Volume (L)': '1', #
        'Source Activity Date': '02-26-2025', #
        'Dilution Solution': 'Test dilution solution text', #
        'Initial Container Weight (g)': '0', 
        'Final Container Weight (g)': '0', 
        'Solution Mass (g)': '100', 
        'Decay Correction (Days)': '0', 
        'Final Activity (pCi/g)': '100', 
        'Uncertainty': '1 sigma', 
        'To Activity Date': '02-26-2025', 
        'Expiration Date': '02-26-2025', 
        'Verified By': '', 
        'Calculation Date': '02-26-2025', 
        'Chemical Composition': 'H2O',
        'Consumable Type': 'LCS'}

GenerateCertificate.generate_pdf(data)

