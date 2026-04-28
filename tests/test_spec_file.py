"""Validate the PyInstaller .spec file shape without invoking PyInstaller."""

from __future__ import annotations

from pathlib import Path

SPEC_PATH = Path(__file__).resolve().parents[1] / "build" / "dxf2ifc.spec"


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
        "src/dxf2ifc/profiles/default_kylmalaite_talo2000.toml",
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
        assert f"'{module}'" in text or f'"{module}"' in text, (
            f"hiddenimports missing: {module}"
        )


def test_spec_excludes_dev_only_packages() -> None:
    """tkinter, pytest et al. should not bloat the bundle."""
    text = _spec_text()
    expected = [
        "tkinter",
        "pytest",
        "unittest",
        "numpy.distutils",
        "setuptools._distutils",
        "pip",
    ]
    for module in expected:
        assert f"'{module}'" in text or f'"{module}"' in text, (
            f"excludes missing: {module}"
        )
