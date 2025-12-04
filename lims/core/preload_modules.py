# Preload modules to help PyInstaller find them

# lims.packages
from lims.packages import Prepsheet, BatchID, DQO, ResultType, Analyte, report_setup

# lims.core
from lims.core import CalibrationCertificate, consumable_form
from lims.core import get_data, Version, upload_results, popups, percent_recovery

# lims.data_transformations
from lims.data_transformations import data_processing

# lims.config
from lims.config import config, file_paths, lab_lists, methods_tables, patterns as config_patterns, tables