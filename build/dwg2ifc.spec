# PyInstaller .spec for dwg2ifc — Section 1 (base, no datas/hidden_imports yet).
# Build: uv run pyinstaller build/dwg2ifc.spec --clean --noconfirm
# Datas, hidden_imports, excludes and version_info are added in Plan E Section 2.

import os
from PyInstaller.utils.hooks import (
    collect_submodules,
    collect_data_files,
)

# PyInstaller resolves relative paths from SPECPATH (the .spec file's dir).
# This spec lives in build/, so anchor every repo-relative path to ROOT = build/..
ROOT = os.path.abspath(os.path.join(SPECPATH, os.pardir))

# ifcopenshell.api lazily imports submodules at runtime — PyInstaller cannot see
# them statically. Same applies to ifcopenshell.express.rules.{IFC4,IFC4X3,…}
# loaded via importlib.import_module from entity_instance.py.
_ifcopenshell_api_submodules = collect_submodules('ifcopenshell.api')
_ifcopenshell_express_submodules = collect_submodules('ifcopenshell.express')
_ezdxf_submodules = collect_submodules('ezdxf')

# ifcopenshell ships JSON schema/mapping data files alongside the python code
# (e.g. entity_to_type_map_2x3.json, IFC4.json). Bundle every non-py asset.
_ifcopenshell_datas = collect_data_files('ifcopenshell')

# ACIS preprocessing is now done by shelling out to accoreconsole.exe
# from the user's AutoCAD install (no in-process COM, no pywin32). The
# subprocess driver lives in dwg2ifc.core.preprocessing and uses only
# stdlib modules — nothing extra to bundle here.

block_cipher = None

# Brand icon is optional during MVP — assets/dwg2ifc.ico is wired automatically
# once the file exists. PyInstaller falls back to its bootloader icon otherwise.
_icon_path = os.path.join(ROOT, 'assets', 'dwg2ifc.ico')
_icon = _icon_path if os.path.exists(_icon_path) else None

a = Analysis(
    [os.path.join(ROOT, 'src/dwg2ifc/gui/__main__.py')],
    pathex=[os.path.join(ROOT, 'src')],
    binaries=[],
    datas=[
        (os.path.join(ROOT, 'src/dwg2ifc/profiles/default_kylmalaite.toml'), 'dwg2ifc/profiles'),
        (os.path.join(ROOT, 'src/dwg2ifc/gui/style.qss'), 'dwg2ifc/gui'),
        (os.path.join(ROOT, 'assets/dwg2ifc.ico'), 'dwg2ifc/gui'),
        (os.path.join(ROOT, 'assets/dwg2ifc.png'), 'dwg2ifc/gui'),
        (os.path.join(ROOT, 'assets/fonts/Inter-Regular.ttf'), 'dwg2ifc/gui/fonts'),
        (os.path.join(ROOT, 'assets/fonts/Inter-Medium.ttf'), 'dwg2ifc/gui/fonts'),
        (os.path.join(ROOT, 'assets/fonts/Inter-SemiBold.ttf'), 'dwg2ifc/gui/fonts'),
        (os.path.join(ROOT, 'assets/fonts/Inter-Bold.ttf'), 'dwg2ifc/gui/fonts'),
        (os.path.join(ROOT, 'assets/fonts/SpaceGrotesk-Medium.ttf'), 'dwg2ifc/gui/fonts'),
        (os.path.join(ROOT, 'assets/fonts/SpaceGrotesk-Bold.ttf'), 'dwg2ifc/gui/fonts'),
        (os.path.join(ROOT, 'assets/fonts/JetBrainsMono-Medium.ttf'), 'dwg2ifc/gui/fonts'),
        (os.path.join(ROOT, 'assets/fonts/LICENSES.md'), 'dwg2ifc/gui/fonts'),
        (os.path.join(ROOT, 'assets/fonts/Inter-LICENSE.txt'), 'dwg2ifc/gui/fonts'),
        (os.path.join(ROOT, 'assets/fonts/SpaceGrotesk-LICENSE.txt'), 'dwg2ifc/gui/fonts'),
        (os.path.join(ROOT, 'assets/fonts/JetBrainsMono-LICENSE.txt'), 'dwg2ifc/gui/fonts'),
    ] + _ifcopenshell_datas,
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
    ] + _ifcopenshell_api_submodules + _ifcopenshell_express_submodules + _ezdxf_submodules,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
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
    name='dwg2ifc',
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
    version=os.path.join(SPECPATH, 'version_info.py'),
    icon=_icon,
)
