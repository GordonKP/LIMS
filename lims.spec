# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import os

pathex = [os.path.abspath('.')]

# Automatically gather all submodules and data files from your lims package
hiddenimports = [
    'win32com.shell',
    'win32event',
    'fitz',
    'pyodbc',
    'sip',
    'bcrypt',
    *collect_submodules('PyQt5'),
    *collect_submodules('openpyxl'),
    *collect_submodules('lims'),  # ← grabs everything under lims.*
]

datas = [
    # Include static resource files and templates
    ('dist/updater.exe', 'dist/'),
    ('odbc_driver_install.py', '.'),
    ('lims/images/*.svg', 'images/'),
    ('lims/images/*.ico', 'images/'),
    ('lims/dependencies/fonts/*.ttf', 'dependencies/fonts/'),

    # Collect all non-code data files (e.g., CSVs, JSON, Excel) from openpyxl
    *collect_data_files('openpyxl'),

    # Collect any .txt, .json, .xlsx, etc., from within lims
    *collect_data_files('lims', include_py_files=False),
]

a = Analysis(
    ['lims.py'],
    pathex=pathex,
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
