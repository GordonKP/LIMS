import os
import sys

# Set the base LIMS directory, depending on if the app is frozen
if getattr(sys, 'frozen', False):
    lims_directory = os.path.join(sys._MEIPASS, "lims")
else:
    lims_directory = os.path.dirname(os.path.dirname(__file__))

# Data processing directory
data_processing_directory = os.path.join(lims_directory, "core")

# Trending Chart directory
chart_directory = r"\\ServerName\Lab Data\Lab\Trending Charts"

# Chain of custody directory
coc_directory = r"\\ServerName\Lab Data\Lab\Sample Receipt\Chain of Custody"

# Raw data directory
raw_data_directory = r"\\ServerName\Lab Data\Lab\Data\Raw Data"

# Processed data directory
processed_data_directory = r"\\ServerName\Lab Data\Lab\Data\Processed Data"

# Prepsheet Template Directory
prepsheet_template_directory = r"\\ServerName\Lab Data\Templates\Prepsheets"

# Prepsheets directory
prepsheet_directory = r"\\ServerName\Lab Data\Lab\Prepsheets"

# SDG directory
sdg_directory = r"\\SLDAFILESERVER\Lab Data\Lab\SDG"

# Reports directory
reports_directory = os.path.join(lims_directory, 'reports')

# Inventory directories for CoA and other instrument files
consumables_inventory_directory = r"\\ServerName\Lab Data\Lab\Inventory\Consumables"
instrument_inventory_directory = r"\\ServerName\Lab Data\Lab\Inventory\Instrumentation"
equipment_inventory_directory = r"\\ServerName\Lab Data\Lab\Inventory\Support Equipment"

# Fonts directory
fonts_directory = os.path.join(lims_directory, "dependencies", "fonts")

# Images directory
images_directory = os.path.join(lims_directory, "images")

# Certificates of Calibration parent directory
calibration_cert_directory = r"\\ServerName\Lab Data\Lab\Inventory\Consumables"