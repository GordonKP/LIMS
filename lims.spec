# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['lims.py'],
    pathex=[],
    binaries=[],
    datas=[
    ('lims/resources_rc.py', 'lims/'),
    ('lims/dependencies/fonts/', 'dependencies/fonts/'),
    ('lims/core/*.py', 'core/'),
    ('lims/packages/*.py', 'packages/'),  # ✅ Explicitly include packages
],
    hiddenimports=[
    'pyodbc',
    'lims.packages.Prepsheet',   # ✅ Ensure this module is included
    'lims.packages.BatchID',
    'lims.packages.DQO',
    'lims.packages.ResultType',
],
  # Ensure pyodbc is included
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
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
    icon=['lims\\images\\leidos_logo.ico'],
)