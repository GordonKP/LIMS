# Preload modules to help PyInstaller find them

# lims.packages
from lims.packages import Prepsheet, BatchID, DQO, ResultType, Analyte, patterns, report_setup

# lims.core
from lims.core import CalibrationCertificate, consumable_form
from lims.core import get_data, Version

# lims.config
from lims.config import config, file_paths, lab_lists, methods_tables, patterns as config_patterns, tables