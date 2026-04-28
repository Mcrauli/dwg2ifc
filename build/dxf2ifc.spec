# PyInstaller .spec for dxf2ifc — Section 1 (base, no datas/hidden_imports yet).
# Build: uv run pyinstaller build/dxf2ifc.spec --clean --noconfirm
# Datas, hidden_imports, excludes and version_info are added in Plan E Section 2.

block_cipher = None

a = Analysis(
    ['src/dxf2ifc/gui/__main__.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ('src/dxf2ifc/profiles/default_kylmalaite_talo2000.toml', 'dxf2ifc/profiles'),
        ('src/dxf2ifc/gui/style.qss', 'dxf2ifc/gui'),
        ('assets/fonts/Inter-Regular.ttf', 'dxf2ifc/gui/fonts'),
        ('assets/fonts/Inter-Medium.ttf', 'dxf2ifc/gui/fonts'),
        ('assets/fonts/Inter-SemiBold.ttf', 'dxf2ifc/gui/fonts'),
        ('assets/fonts/Inter-Bold.ttf', 'dxf2ifc/gui/fonts'),
        ('assets/fonts/SpaceGrotesk-Medium.ttf', 'dxf2ifc/gui/fonts'),
        ('assets/fonts/SpaceGrotesk-Bold.ttf', 'dxf2ifc/gui/fonts'),
        ('assets/fonts/JetBrainsMono-Medium.ttf', 'dxf2ifc/gui/fonts'),
        ('assets/fonts/LICENSES.md', 'dxf2ifc/gui/fonts'),
        ('assets/fonts/Inter-LICENSE.txt', 'dxf2ifc/gui/fonts'),
        ('assets/fonts/SpaceGrotesk-LICENSE.txt', 'dxf2ifc/gui/fonts'),
        ('assets/fonts/JetBrainsMono-LICENSE.txt', 'dxf2ifc/gui/fonts'),
    ],
    hiddenimports=[
        'ifcopenshell',
        'ifcopenshell.api',
        'ifcopenshell.geom',
        'ifcopenshell.guid',
        'ifcopenshell.template',
        'ezdxf',
        'ezdxf.entities',
        'PySide6.QtSvg',
        'PySide6.QtSvgWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'pytest',
        'unittest',
        'numpy.distutils',
        'setuptools._distutils',
        'pip',
    ],
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
    version='build/version_info.py',
    # TODO: replace with assets/dxf2ifc.ico once the brand icon ships.
    # See docs/packaging.md "Icon TODO" for the design brief.
    icon=None,
)
