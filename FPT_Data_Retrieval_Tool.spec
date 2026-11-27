# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [
    ('templates', 'templates'),
    ('static', 'static'),
    ('auto_hoan_tat/templates', 'auto_hoan_tat/templates'),
    ('auto_hoan_tat/static', 'auto_hoan_tat/static'),
    ('config.example.json', '.'),
    ('Template_Danh_Sach_Hop_Dong.xlsx', '.'),
]
binaries = []
hiddenimports = [
    'zstandard', 'openpyxl', 'pandas', 'pyotp', 'selenium', 'bs4', 'PIL',
    'sqlalchemy', 'psycopg2',
    'core_login', 'inside_scraper', 'inside_bypass', 'inside_cls',
    'inside_assign', 'inside_signal', 'inside_mybae', 'inside_spampool',
    'inside_bypass_nat', 'inside_port', 'auto_import_routes',
    'auto_import_service', 'auto_import_config', 'inside_report_crawler',
    'google_sheets_tk_writer',
    'auto_hoan_tat', 'auto_hoan_tat.blueprint', 'auto_hoan_tat.config',
    'auto_hoan_tat.sheet_reader', 'auto_hoan_tat.mod1_auth',
    'auto_hoan_tat.mod2_navigator', 'auto_hoan_tat.mod3_validator',
    'auto_hoan_tat.mod4_executor', 'auto_hoan_tat.orchestrator',
    'auto_hoan_tat.web_app',
]
tmp_ret = collect_all('pyzbar')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['server.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='FPT_Data_Retrieval_Tool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
