import os 

lims_directory = os.path.dirname(os.path.dirname(__file__))

# Chain of custody directory
coc_directory = r"\\ServerName\Lab Data\Lab\Sample Receipt"

# Raw data directory
raw_data_directory = r"\\ServerName\Lab Data\Lab\Data\Raw Data"

# Processed data directory
processed_data_directory = r"\\ServerName\Lab Data\Lab\Data\Processed Data"

# Prepsheets direcotry
prepsheet_directory = r"\\ServerName\Lab Data\Lab\Prepsheets"

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