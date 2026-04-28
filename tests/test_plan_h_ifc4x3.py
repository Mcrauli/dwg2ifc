"""Plan H Task 1: build_ifc_project_skeleton accepts schema kwarg and
emits IFC4X3-flavoured project files."""

from __future__ import annotations

from dxf2ifc.core.ifc_writer import build_ifc_project_skeleton


def test_skeleton_default_schema_is_ifc4():
    ifc = build_ifc_project_skeleton(project_name="default schema")
    assert ifc.schema == "IFC4"


def test_skeleton_schema_ifc4x3_yields_ifc4x3_file():
    ifc = build_ifc_project_skeleton(project_name="ifc4x3 schema", schema="IFC4X3")
    assert ifc.schema == "IFC4X3"
    # Sanity: same spatial structure shape as IFC4 baseline.
    assert len(ifc.by_type("IfcProject")) == 1
    assert len(ifc.by_type("IfcSite")) == 1
    assert len(ifc.by_type("IfcBuilding")) == 1
    assert len(ifc.by_type("IfcBuildingStorey")) == 1
