# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Raccogli tutti i dati dei moduli Flask
flask_datas = collect_data_files('flask')
wtf_datas = collect_data_files('wtforms')
sqlalchemy_datas = collect_data_files('sqlalchemy')

# Dati specifici dell'applicazione
datas = [
    ('templates', 'templates'),
    ('static', 'static'),
    ('requirements.txt', '.'),
    ('config.py', '.'),
    ('generate_certs.py', '.'),
]

# Aggiungi i dati dei moduli Flask
datas.extend(flask_datas)
datas.extend(wtf_datas)
datas.extend(sqlalchemy_datas)

# Moduli nascosti che potrebbero non essere rilevati automaticamente
hiddenimports = [
    'flask',
    'flask_login',
    'flask_wtf',
    'flask_sqlalchemy',
    'flask_migrate',
    'flask_cors',
    'wtforms',
    'wtforms.fields',
    'wtforms.widgets',
    'wtforms.validators',
    'sqlalchemy',
    'sqlalchemy.ext.declarative',
    'sqlalchemy.orm',
    'sqlalchemy.sql',
    'pymysql',
    'pymysql.cursors',
    'cryptography',
    'cryptography.hazmat.primitives',
    'cryptography.hazmat.primitives.asymmetric',
    'cryptography.hazmat.primitives.serialization',
    'cryptography.x509',
    'jinja2',
    'jinja2.ext',
    'itsdangerous',
    'click',
    'reportlab',
    'reportlab.pdfgen',
    'reportlab.lib',
    'email_validator',
    'dotenv',
    'logging.handlers',
    'datetime',
    'ipaddress',
    're',
    'socket',
    'subprocess',
    'threading',
    'json',
    'base64',
    'hashlib',
    'uuid',
    'decimal',
    'collections',
    'collections.abc',
]

# Raccogli tutti i submoduli di Flask e SQLAlchemy
hiddenimports.extend(collect_submodules('flask'))
hiddenimports.extend(collect_submodules('sqlalchemy'))
hiddenimports.extend(collect_submodules('wtforms'))

block_cipher = None

a = Analysis(
    ['main_service.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DBLogiX',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Cambia a True se vuoi vedere la console per debug
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='static/favicon.ico' if os.path.exists('static/favicon.ico') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DBLogiX',
) 