"""Tests for the IFC quality / validation gate (Plan F Section 1)."""

from __future__ import annotations

from pathlib import Path

from dxf2ifc.core.ifc_writer import (
    add_wall,
    build_ifc_project_skeleton,
    convert_dxf,
    write_ifc,
)
from dxf2ifc.core.quality import ValidationReport, validate_ifc
from dxf2ifc.core.types import LineGeometry, MappedEntity, Point3D
from dxf2ifc.profiles.loader import load_default_profile


def test_validation_report_is_dataclass_with_errors_and_warnings():
    report = ValidationReport(errors=[], warnings=[], summary="ok")
    assert report.errors == []
    assert report.warnings == []
    assert report.summary == "ok"


def test_validate_ifc_returns_report_for_full_fixture(full_kylmaelement_dxf: Path, tmp_path: Path):
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


def test_validate_ifc_accepts_string_path(full_kylmaelement_dxf: Path, tmp_path: Path):
    out = tmp_path / "full_kylmaelement.ifc"
    convert_dxf(
        dxf_path=full_kylmaelement_dxf,
        output_path=out,
        profile=load_default_profile(),
    )

    report = validate_ifc(str(out))
    assert report.errors == []


def _build_ifc_with_unclassified_wall(out_path: Path) -> None:
    """Construct a minimal IFC4 project with a single IfcWall and no
    IfcRelAssociatesClassification. Used to exercise the YTV warning path."""
    ifc = build_ifc_project_skeleton(project_name="Quality Warning Test")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    mapped = MappedEntity(
        layer="UNCLASSIFIED-WALL",
        dxf_type="LINE",
        geometry=LineGeometry(start=Point3D(0, 0, 0), end=Point3D(5000, 0, 0)),
        ifc_type="IfcWall",
        predefined_type="STANDARD",
        talo2000_code="",
        talo2000_name="",
        extra_props={"default_height_mm": 3000, "default_thickness_mm": 200},
    )
    add_wall(ifc, mapped, parent_storey=storey)
    write_ifc(ifc, out_path)


def test_validate_ifc_warns_when_wall_lacks_talo2000_classification(tmp_path: Path):
    out = tmp_path / "unclassified_wall.ifc"
    _build_ifc_with_unclassified_wall(out)

    report = validate_ifc(out)

    assert any(
        "missing Talo2000 classification" in w.get("message", "") for w in report.warnings
    ), f"expected Talo2000 warning, got: {report.warnings}"
    assert report.errors == [], f"unexpected errors: {report.errors}"


def test_validate_ifc_full_fixture_has_no_talo2000_warnings(
    full_kylmaelement_dxf: Path, tmp_path: Path
):
    """Plan B's full-profile fixture classifies every IfcWall/IfcSlab/IfcDoor/
    IfcWindow, so the YTV warning gate must stay clean."""
    out = tmp_path / "full_kylmaelement.ifc"
    convert_dxf(
        dxf_path=full_kylmaelement_dxf,
        output_path=out,
        profile=load_default_profile(),
    )

    report = validate_ifc(out)

    talo_warnings = [
        w for w in report.warnings if "missing Talo2000 classification" in w.get("message", "")
    ]
    assert talo_warnings == [], f"unexpected Talo2000 warnings: {talo_warnings}"


def test_convert_dxf_default_returns_tuple_with_none_report(
    full_kylmaelement_dxf: Path, tmp_path: Path
):
    out = tmp_path / "full_kylmaelement.ifc"
    result = convert_dxf(
        dxf_path=full_kylmaelement_dxf,
        output_path=out,
        profile=load_default_profile(),
    )
    assert isinstance(result, tuple)
    systems, report = result
    assert isinstance(systems, dict)
    assert report is None


def test_convert_dxf_validate_true_returns_validation_report(
    full_kylmaelement_dxf: Path, tmp_path: Path
):
    out = tmp_path / "full_kylmaelement.ifc"
    systems, report = convert_dxf(
        dxf_path=full_kylmaelement_dxf,
        output_path=out,
        profile=load_default_profile(),
        validate=True,
    )
    assert isinstance(systems, dict)
    assert isinstance(report, ValidationReport)
    assert report.errors == []
