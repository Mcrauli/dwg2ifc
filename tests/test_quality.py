"""Tests for the IFC quality / validation gate (Plan F Section 1)."""

from __future__ import annotations

from pathlib import Path

from dxf2ifc.core.ifc_writer import convert_dxf
from dxf2ifc.core.quality import ValidationReport, validate_ifc
from dxf2ifc.profiles.loader import load_default_profile


def test_validation_report_is_dataclass_with_errors_and_warnings():
    report = ValidationReport(errors=[], warnings=[], summary="ok")
    assert report.errors == []
    assert report.warnings == []
    assert report.summary == "ok"


def test_validate_ifc_returns_report_for_full_fixture(
    full_kylmaelement_dxf: Path, tmp_path: Path
):
    """The Plan B full-fixture IFC must validate cleanly under
    ifcopenshell.validate — Plan F's automatic gate baseline."""
    out = tmp_path / "full_kylmaelement.ifc"
    convert_dxf(
        dxf_path=full_kylmaelement_dxf,
        output_path=out,
        profile=load_default_profile(),
    )

    report = validate_ifc(out)

    assert isinstance(report, ValidationReport)
    assert report.errors == [], f"expected no errors, got: {report.errors}"
    assert "IFC4" in report.summary or "0 errors" in report.summary


def test_validate_ifc_accepts_string_path(
    full_kylmaelement_dxf: Path, tmp_path: Path
):
    out = tmp_path / "full_kylmaelement.ifc"
    convert_dxf(
        dxf_path=full_kylmaelement_dxf,
        output_path=out,
        profile=load_default_profile(),
    )

    report = validate_ifc(str(out))
    assert report.errors == []
