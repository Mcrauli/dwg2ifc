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
