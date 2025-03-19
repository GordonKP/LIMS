import os
import sys

# Get the absolute path of the parent directory
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the parent directory to sys.path
sys.path.append(parent_dir)

from lims.config import file_paths
from standalone.formula_generator import generate_activity_formula
from lims.packages.report_setup import GeneratePDFLayout
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import Paragraph, Frame
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors

class GenerateCertificate:
    @staticmethod

    def generate_pdf(data):

        # Ensure data is in int format
        for key, value in data.items():
            if isinstance(value, str):
                if value.isdigit():  # Whole numbers
                    data[key] = int(value)
                    print(data[key], int(value)) 
                elif value.replace(".", "", 1).isdigit():  # Decimal numbers
                    data[key] = float(value)
                    print(data[key], float(value))  

        if data['Units'] == 'Bq':
            data['Source Activity (pCi)'] = round(data['Source Activity'] * 27.027, 2)
        elif data['Units'] == 'dpm':
            data['Source Activity (pCi)'] = round(data['Source Activity'] * 2.22, 2)
        elif data['Units'] == 'pCi':
            data['Source Activity (pCi)'] =data['Source Activity']

        # Calculations
        from datetime import datetime
        # Convert date strings to datetime objects
        source_activity_date = datetime.strptime(data['Source Activity Date'], '%m-%d-%Y')
        to_activity_date = datetime.strptime(data['To Activity Date'], '%m-%d-%Y')

        # Calculate delta time in days
        delta = (to_activity_date - source_activity_date).days

        # Compute fraction of half-life elapsed
        half_life_days = data['Half-Life (Days)']

        import math
        final_activity = round((data['Source Activity (pCi)'] * math.e**((-math.log(2)*delta)/half_life_days))/data['Solution Mass (g)'], 2)

        uncertainty = round(0.014*final_activity, 2)

        filepath, exists = GenerateCertificate.get_filepath(data['SRS'], data['Consumable Type'])

        # Generate PDF
        c = canvas.Canvas(filepath, pagesize=letter)

        width, height = letter

        # Header
        GeneratePDFLayout.page_setup(c, f"{data['Consumable Type']} Certificate of Calibration")

        c.setFont("Leidos Font", 12)

        if exists:
            c.drawCentredString(width / 2, height-130, f"Solution re-certified on {data['Solution Prep Date']}")
        else:
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
        c.drawRightString(width-50, height-275, f"{data['Source Activity']} {data['Units']}")
        c.drawRightString(width-50, height-295, f"{data['Source Activity Date']}")

        c.setFont("Leidos Bold Font", 12)

        c.drawString(50, height-320, f"Chemical Composition of Solution:")

        c.setFont("Leidos Font", 12)

        c.drawString(275, height-320, f"{data['Chemical Composition']}")

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

        # Dilution solution box
        styles = getSampleStyleSheet()
        text_style = styles["Normal"]

        # Get text data
        text_content = data["Dilution Solution"] if data["Dilution Solution"] is not None else "No dilution, used as received."

        # Create a wrapped paragraph
        text_paragraph = Paragraph(text_content, text_style)
        text_frame = Frame(width-250, height-455, 200, 60, showBoundary=True)

        text_frame.addFromList([text_paragraph], c)

        # Generate the image dynamically
        img_buffer = generate_activity_formula()

        # Load the image from the BytesIO object
        img = ImageReader(img_buffer)

        # Get original image dimensions
        img_width, img_height = img.getSize()

        # Scale down while maintaining aspect ratio
        max_width = img_width / 4  # Maximum width allowed
        max_height = img_height / 4  # Maximum height allowed

        scale_factor = min(max_width / img_width, max_height / img_height)
        new_width = img_width * scale_factor
        new_height = img_height * scale_factor

        c.drawImage(img, 50, height - new_height - 440, width=new_width, height=new_height, mask='auto')

        c.setFont("Leidos Bold Font", 12)

        c.drawString(width-(width/3)-50, height-510, "Decay Correction:")
        c.drawString(width-(width/3)-50, height-530, "To Activity Date:")
        c.drawString(width-(width/3)-50, height-550, "Final Activity:")
        c.drawString(width-(width/3)-50, height-570, "Uncertainty:")

        c.setFont("Leidos Font", 12)

        c.drawRightString(width-50, height-510, f"{delta} days")
        c.drawRightString(width-50, height-530, f"{data['To Activity Date']}")
        c.drawRightString(width-50, height-550, f"{final_activity} pCi/g")
        c.drawRightString(width-50, height-570, f"{uncertainty} pCi/g")

        c.setFont("Leidos Bold Font", 12)

        c.drawString(50, height-600, "Calculated On:")
        c.drawString(50, height-620, "Expires On:")
        c.drawString(50, height-640, "Verified By:")
        c.drawString(width-(width/3)-50, height-635, "Laboratory Manager")

        c.setFont("Leidos Font", 12)

        c.line(width-(width/3)-50, height-620, width-50, height-620)  # Draw an underline

        # Add an Adobe Sign-compatible hidden text tag
        c.acroForm.textfield(
            name='Sig_es_:signer1',  # Use the Adobe Sign format
            x=(width-(width/3)-50), 
            y=(height-620 + 2),  # Adjust so it overlays the line
            width=(width-50) - (width-(width/3)-50), 
            height=15,  # Small height to remain invisible
            borderWidth=0,  # No border
            fillColor=None,  # Transparent background
            textColor=colors.white,  # White text to make it invisible
            forceBorder=False
        )

        if data['Percent Abundance'] > 1:
            data['Percent Abundance'] = data['Percent Abundance']
        else:
            data['Percent Abundance'] = data['Percent Abundance']*100

        aps = round(data['Percent Abundance']/100 * (final_activity*2.22), 2)

        c.drawRightString(275, height-600, f"{data['Calculation Date']}")
        c.drawRightString(275, height-620, f"{data['Expiration Date']}")
        c.drawRightString(275, height-640, f"{data['Verified By']}")

        text_content = f"""
        The laboratory converts source activity using 27.027 pCi / 1 Bq or 2.22 pCi / 1 dpm.

        The final source activity is {data['Source Activity (pCi)']} pCi. The final activity concentration, {final_activity} pCi/g, is determined by dividing the final activity by the solution mass, with a 1σ (1.4%) uncertainty applied.

        To calculate APEX certification values, the lab factors in percent abundance multiplied by the final activity concentration in dpm. 
        
        {data['Principle Radionuclide']} percent abundance is determined using IAEA percent abundance data for energy lines within the ROI selected for analysis in accordance with LL-004.

        The APEX value is {round(final_activity * 2.22, 2)} dpm × {data['Percent Abundance']}%, yielding {aps} aps/g.

        For reference, the vendor source certificate for SRS{data['SRS']} is on the next page.
        """

        # Create a wrapped paragraph
        text_paragraph = Paragraph(text_content, text_style)
        text_frame = Frame(50, height-800, width-100, 150, showBoundary=False)

        text_frame.addFromList([text_paragraph], c)

        # Save pdf
        c.save()

        print(f"PDF saved at: {filepath}")

    def get_filepath(srs, consumable_type):
        base_dir = file_paths.calibration_cert_directory  # Root directory
        
        # Get all directories inside base_dir
        matching_dirs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d)) and consumable_type in d]
        
        if not matching_dirs:
            print(f"Error: No matching directory found for '{consumable_type}' in '{base_dir}'")
            return None, None

        # Select the first matching directory (or modify logic if multiple matches should be handled differently)
        selected_dir = os.path.join(base_dir, matching_dirs[0], "Certificates of Calibration")
        
        # Ensure the target directory exists
        os.makedirs(selected_dir, exist_ok=True)

        # Define PDF filename and path
        filename = f"{srs}.pdf"
        filepath = os.path.join(selected_dir, filename)

        # Check if the file already exists
        file_exists = os.path.exists(filepath)

        if file_exists:
            from datetime import datetime

            today_str = datetime.today().strftime("%m%d%Y")

            filename = f"{srs}_{today_str}.pdf"
            filepath = os.path.join(selected_dir, filename)

        return filepath, file_exists
    
   
    
data = {'Principle Radionuclide': 'Am-243', 'Half-Life (Days)': '2690000', 'Solution Prep Date': '12-19-2024', 'SRS': '132105', 'Source Activity': '18072', 'Units': 'dpm', 'Source Volume (L)': '0.5', 'Source Activity Date': '11-12-2024', 'Chemical Composition': '1M Hydrochloric Acid', 'Dilution Solution': 'N/A', 'Initial Container Weight (g)': '0', 'Final Container Weight (g)': '0', 'Solution Mass (g)': '510.07', 'Final Activity (pCi/g)': '', 'Percent Abundance': '99.58', 'To Activity Date': '11-12-2024', 'Expiration Date': '12-19-2025', 'Verified By': '', 'Calculation Date': '12-19-2024', 'Consumable Type': 'Tracer'}
GenerateCertificate.generate_pdf(data)