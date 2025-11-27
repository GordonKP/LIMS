# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
    get_module_file_attribute
)
import os

pathex = [os.path.abspath('.')]

# find correct pyexpat.pyd for this Python version
expat_pyd = os.path.join(os.path.dirname(get_module_file_attribute('pyexpat')), 'pyexpat.pyd')

a = Analysis(
    ['main.py'],
    pathex=pathex,
    binaries=[
        # explicitly include correct pyexpat.pyd in expected location
        (expat_pyd, 'xml/parsers'),
    ],
    datas=[
        ('dist/updater.exe', 'dist/'),
        ('odbc_driver_install.py', '.'),
        ('lims/config/*.py', 'lims/'),
        ('lims/core/*.py', 'core/'),
        ('lims/reports/*.py', 'reports/'),
        ('lims/data_transformations/*.py', 'lims/'),
        ('lims/packages/*.py', 'packages/'),
        ('lims/resources_rc.py', 'lims/'),
        ('lims/images/*.svg', 'lims/images/'),
        ('lims/images/*.ico', 'lims/images/'),
        ('lims/dependencies/fonts/*.ttf', 'lims/dependencies/fonts/'),
        *collect_data_files('openpyxl'),
    ],
    hiddenimports=[
        *collect_submodules('sklearn'),
        'xml.parsers.expat',  # explicitly include
        'pyexpat',
        *collect_submodules('PyPDF2'),
        'pikepdf',
        'win32com.shell',
        'win32event',
        'fitz',
        'pyodbc',
        'sip',
        'bcrypt',
        *collect_submodules('PyQt5'),
        *collect_submodules('openpyxl'),
        # your app modules
        'data_transformations.data_processing',
        'config.config',
        'config.file_paths',
        'config.lab_lists',
        'config.methods_tables',
        'config.patterns',
        'config.tables',
        'core.ALPHA',
        'core.BEF',
        'core.CalibrationCertificate',
        'core.consumable_form',
        'core.GAMMA',
        'core.get_data',
        'core.GFPC',
        'core.limits',
        'core.LSC',
        'core.MET',
        'core.TCLP',
        'core.upload_results',
        'core.preload_modules',
        'core.recovery',
        'core.WetChem',
        'core.popups',
        'packages.Analyte',
        'packages.BatchID',
        'packages.DQO',
        'packages.Prepsheet',
        'packages.report_setup',
        'packages.batch_summary',
        'packages.data_package',
        'reports.edd',
        'reports.excel_prepsheets',
        'reports.form_1',
        'reports.pdr',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['set_excepthook.py'],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='lims',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='lims/images/leidos_logo.ico',
)
