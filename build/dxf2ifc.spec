# PyInstaller .spec for dxf2ifc — Section 1 (base, no datas/hidden_imports yet).
# Build: uv run pyinstaller build/dxf2ifc.spec --clean --noconfirm
# Datas, hidden_imports, excludes and version_info are added in Plan E Section 2.

block_cipher = None

a = Analysis(
    ['src/dxf2ifc/gui/__main__.py'],
    pathex=['src'],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='dxf2ifc',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
