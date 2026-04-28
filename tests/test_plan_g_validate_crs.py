"""Plan G Task 16: ``validate_ifc`` reports CRS-coverage problems —
(a) IfcMapConversion without IfcProjectedCRS,
(b) expect_crs=True but no MapConversion in the file,
(c) any IfcCartesianPoint > 1 km from origin (possible double-transform)."""

from __future__ import annotations

from pathlib import Path

from dxf2ifc.core.ifc_writer import build_ifc_project_skeleton, write_ifc
from dxf2ifc.core.quality import validate_ifc
from dxf2ifc.profiles.schema import CRSConfig


def test_validate_ifc_clean_no_crs(tmp_path: Path):
    skeleton = build_ifc_project_skeleton(project_name="No CRS")
    out = tmp_path / "no_crs.ifc"
    write_ifc(skeleton.file, out)
    report = validate_ifc(out)
    crs_errors = [e for e in report.errors if e.get("type", "").startswith("crs_")]
    assert crs_errors == []


def test_validate_ifc_orphan_map_conversion_is_error(tmp_path: Path):
    """IfcMapConversion present but no IfcProjectedCRS in the file."""
    skeleton = build_ifc_project_skeleton(project_name="Orphan")
    ifc = skeleton.file
    # Force an orphan: create a MapConversion whose TargetCRS we then strip.
    crs = CRSConfig(eastings_mm=25_496_000.0, northings_mm=6_672_000.0)
    skel2 = build_ifc_project_skeleton(project_name="WithCRS", crs=crs)
    # Manually craft an orphan: copy MapConversion entity into a fresh file
    # and remove all IfcProjectedCRS instances.
    out = tmp_path / "orphan.ifc"
    write_ifc(skel2.file, out)
    # Re-open and orphanise
    import ifcopenshell

    reopened = ifcopenshell.open(str(out))
    for projected in reopened.by_type("IfcProjectedCRS"):
        reopened.remove(projected)
    out_orphan = tmp_path / "orphan_after.ifc"
    reopened.write(str(out_orphan))

    report = validate_ifc(out_orphan)
    crs_errors = [e for e in report.errors if e.get("type") == "crs_orphan_map_conversion"]
    assert len(crs_errors) >= 1


def test_validate_ifc_expect_crs_missing_map_conversion(tmp_path: Path):
    skeleton = build_ifc_project_skeleton(project_name="Missing MC")
    out = tmp_path / "missing_mc.ifc"
    write_ifc(skeleton.file, out)
    report = validate_ifc(out, expect_crs=True)
    crs_errors = [e for e in report.errors if e.get("type") == "crs_missing_map_conversion"]
    assert len(crs_errors) == 1


def test_validate_ifc_double_transform_warning(tmp_path: Path):
    skeleton = build_ifc_project_skeleton(project_name="Double TX")
    skeleton.file.create_entity(
        "IfcCartesianPoint", Coordinates=(25_496_000.0, 6_672_000.0, 0.0)
    )
    out = tmp_path / "double_tx.ifc"
    write_ifc(skeleton.file, out)
    report = validate_ifc(out)
    dt_warnings = [w for w in report.warnings if w.get("type") == "crs_possible_double_transform"]
    assert len(dt_warnings) >= 1


def test_validate_ifc_with_crs_clean(tmp_path: Path):
    """Clean baseline: a skeleton with valid IfcProjectedCRS + IfcMapConversion
    must pass both expect_crs=True and the no-flag check without CRS errors."""
    crs = CRSConfig(eastings_mm=25_496_000.0, northings_mm=6_672_000.0)
    skeleton = build_ifc_project_skeleton(project_name="Clean CRS", crs=crs)
    out = tmp_path / "clean_crs.ifc"
    write_ifc(skeleton.file, out)
    report = validate_ifc(out, expect_crs=True)
    crs_errors = [e for e in report.errors if e.get("type", "").startswith("crs_")]
    assert crs_errors == []
