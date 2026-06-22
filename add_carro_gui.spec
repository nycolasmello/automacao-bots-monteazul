# -*- mode: python ; coding: utf-8 -*-
import certifi

a = Analysis(
    ['add_carro_gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Inclui os certificados SSL do certifi para HTTPS funcionar no exe
        (certifi.where(), 'certifi'),
    ],
    hiddenimports=[
        'certifi',
        'packaging',
        'packaging.version',
        'packaging.specifiers',
        'packaging.requirements',
    ],
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
    name='MonteAzul-Automation',
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
)
