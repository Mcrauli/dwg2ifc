"""Validate the PyInstaller .spec file shape without invoking PyInstaller."""

from __future__ import annotations

from pathlib import Path

SPEC_PATH = Path(__file__).resolve().parents[1] / "build" / "dxf2ifc.spec"
VERSION_INFO_PATH = Path(__file__).resolve().parents[1] / "build" / "version_info.py"


def _spec_text() -> str:
    assert SPEC_PATH.exists(), f"missing PyInstaller spec at {SPEC_PATH}"
    return SPEC_PATH.read_text(encoding="utf-8")


def test_spec_invokes_analysis_with_gui_entry_point() -> None:
    text = _spec_text()
    assert "Analysis(" in text
    assert "src/dxf2ifc/gui/__main__.py" in text


def test_spec_names_dxf2ifc_and_is_windowed() -> None:
    text = _spec_text()
    assert "name='dxf2ifc'" in text or 'name="dxf2ifc"' in text
    assert "console=False" in text


def test_spec_bundles_runtime_assets() -> None:
    """Runtime resources (profile TOML, QSS, fonts, font licences) must ship."""
    text = _spec_text()
    expected_sources = [
        "src/dxf2ifc/profiles/default_kylmalaite.toml",
        "src/dxf2ifc/gui/style.qss",
        "assets/fonts/Inter-Regular.ttf",
        "assets/fonts/Inter-Medium.ttf",
        "assets/fonts/Inter-SemiBold.ttf",
        "assets/fonts/Inter-Bold.ttf",
        "assets/fonts/SpaceGrotesk-Medium.ttf",
        "assets/fonts/SpaceGrotesk-Bold.ttf",
        "assets/fonts/JetBrainsMono-Medium.ttf",
        "assets/fonts/LICENSES.md",
        "assets/fonts/Inter-LICENSE.txt",
        "assets/fonts/SpaceGrotesk-LICENSE.txt",
        "assets/fonts/JetBrainsMono-LICENSE.txt",
    ]
    for source in expected_sources:
        assert source in text, f"datas missing source: {source}"

    expected_destinations = [
        "dxf2ifc/profiles",
        "dxf2ifc/gui",
        "dxf2ifc/gui/fonts",
    ]
    for dest in expected_destinations:
        assert dest in text, f"datas missing destination: {dest}"


def test_spec_lists_runtime_hidden_imports() -> None:
    """ifcopenshell submodules and Qt SVG plugins must be hidden_imports."""
    text = _spec_text()
    expected = [
        "ifcopenshell",
        "ifcopenshell.api",
        "ifcopenshell.geom",
        "ifcopenshell.guid",
        "ifcopenshell.template",
        "ezdxf",
        "ezdxf.entities",
        "PySide6.QtSvg",
        "PySide6.QtSvgWidgets",
    ]
    for module in expected:
        assert f"'{module}'" in text or f'"{module}"' in text, f"hiddenimports missing: {module}"






def test_version_info_file_carries_company_and_version() -> None:
    """The Win32 VSVersionInfo block must encode brand metadata + version."""
    assert VERSION_INFO_PATH.exists(), f"missing {VERSION_INFO_PATH}"
    text = VERSION_INFO_PATH.read_text(encoding="utf-8")
    assert "VSVersionInfo" in text
    assert "Lauri Rekola" in text
    assert "dxf2ifc" in text
    from dxf2ifc._version import __version__

    assert __version__ in text


def test_spec_icon_is_ico_or_none() -> None:
    """Icon line must be either icon=None, reference a .ico file directly
    (literal string OR ``os.path.join(...)``), or use a variable whose
    definition resolves to a .ico path."""
    import re

    text = _spec_text()
    if "icon=None" in text:
        return
    string_match = re.search(r"icon\s*=\s*['\"]([^'\"]+)['\"]", text)
    if string_match:
        assert string_match.group(1).endswith(".ico"), (
            f"icon path must end with .ico, got: {string_match.group(1)}"
        )
        return
    join_match = re.search(r"icon\s*=\s*os\.path\.join\([^)]+\)", text)
    if join_match:
        assert ".ico" in join_match.group(0), (
            f"os.path.join expression must reference a .ico file, got: {join_match.group(0)}"
        )
        return
    # Variable form: icon=<identifier>. The variable must be assigned
    # somewhere above with a value containing ".ico".
    var_match = re.search(r"icon\s*=\s*([A-Za-z_][\w]*)\s*,?", text)
    assert var_match, "spec missing an icon= directive (or a placeholder None)"
    var_name = var_match.group(1)
    assignment = re.search(
        rf"^{re.escape(var_name)}\s*=\s*(.+)$", text, re.MULTILINE
    )
    assert assignment, f"icon variable {var_name!r} has no top-level assignment in spec"
    assert ".ico" in assignment.group(1), (
        f"icon variable {var_name!r} assignment does not reference a .ico file: "
        f"{assignment.group(1)!r}"
    )
