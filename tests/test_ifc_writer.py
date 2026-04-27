"""Unit tests for core.ifc_writer."""
from pathlib import Path

import ifcopenshell

from dxf2ifc.core.ifc_writer import build_ifc_project_skeleton, write_ifc


def test_build_project_creates_ifc4_file_with_hierarchy(tmp_path: Path):
    ifc = build_ifc_project_skeleton(
        project_name="Test Project", site_name="Site", building_name="Cold Store"
    )
    assert ifc.schema == "IFC4"
    assert len(ifc.by_type("IfcProject")) == 1
    assert len(ifc.by_type("IfcSite")) == 1
    assert len(ifc.by_type("IfcBuilding")) == 1
    assert len(ifc.by_type("IfcBuildingStorey")) == 1


def test_build_project_uses_millimetres():
    ifc = build_ifc_project_skeleton(project_name="MM Test")
    project = ifc.by_type("IfcProject")[0]
    length_units = [
        u
        for u in project.UnitsInContext.Units
        if u.is_a("IfcSIUnit") and u.UnitType == "LENGTHUNIT"
    ]
    assert len(length_units) == 1
    assert length_units[0].Prefix == "MILLI"
    assert length_units[0].Name == "METRE"


def test_write_ifc_produces_file(tmp_path: Path):
    ifc = build_ifc_project_skeleton(project_name="Write Test")
    out = tmp_path / "out.ifc"
    write_ifc(ifc, out)
    assert out.exists()
    assert out.stat().st_size > 0
    reloaded = ifcopenshell.open(str(out))
    assert len(reloaded.by_type("IfcProject")) == 1
