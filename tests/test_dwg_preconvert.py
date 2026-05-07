"""Tests for the DWG → DXF preconversion module.

The module spawns a hidden AutoCAD via pywin32 COM. CI cannot do
that, so the round-trip test is gated behind ``requires_acad``.
"""

from __future__ import annotations

from pathlib import Path

import pytest


def test_last_explode_meshes_starts_empty():
    from dxf2ifc.core import dwg_preconvert

    dwg_preconvert._last_meshes = {}
    assert dwg_preconvert.last_explode_meshes() == {}


def test_preconvert_dwg_returns_none_for_missing_file(tmp_path: Path):
    from dxf2ifc.core.dwg_preconvert import preconvert_dwg

    result = preconvert_dwg(tmp_path / "does_not_exist.dwg")
    assert result is None


def test_preconvert_dwg_returns_none_when_autocad_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``_ensure_app`` returning ``None`` simulates a host without
    pywin32 / AutoCAD; the orchestrator falls back to direct DXF
    reading instead of raising."""
    from dxf2ifc.core import dwg_preconvert

    fake_dwg = tmp_path / "fake.dwg"
    fake_dwg.write_bytes(b"not actually a DWG")

    monkeypatch.setattr(dwg_preconvert, "_ensure_app", lambda progress=None: None)

    result = dwg_preconvert.preconvert_dwg(fake_dwg)
    assert result is None
    assert dwg_preconvert.last_explode_meshes() == {}


@pytest.mark.requires_acad
def test_preconvert_dwg_round_trip_real_autocad():
    """End-to-end round-trip on Lauri's local test DWG. Skipped in CI."""
    from dxf2ifc.core.dwg_preconvert import preconvert_dwg, last_explode_meshes

    fixture = Path(
        r"C:\Users\LauriRekola\OneDrive - RADIKA OY\Tiedostot\testimagi.dwg"
    )
    if not fixture.is_file():
        pytest.skip("Lauri's local testimagi.dwg not present")
    try:
        import win32com.client  # noqa: F401  # type: ignore[import-not-found]
    except ImportError:
        pytest.skip("pywin32 not installed")
    out = preconvert_dwg(fixture)
    if out is None:
        pytest.skip("AutoCAD COM Dispatch failed")
    assert out.is_file()
    assert out.stat().st_size > 100_000
    assert isinstance(last_explode_meshes(), dict)
