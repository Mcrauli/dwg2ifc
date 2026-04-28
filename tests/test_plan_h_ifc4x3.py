"""Plan H Task 1: build_ifc_project_skeleton accepts schema kwarg and
emits IFC4X3-flavoured project files. Plan H Task 2: convert_dxf
forwards the schema kwarg and the full-fixture pipeline produces a
valid IFC4X3 file."""

from __future__ import annotations

from pathlib import Path

import ifcopenshell
import ifcopenshell.validate

from dxf2ifc.core.ifc_writer import build_ifc_project_skeleton, convert_dxf
from dxf2ifc.profiles.loader import load_default_profile


def test_skeleton_default_schema_is_ifc4():
    ifc = build_ifc_project_skeleton(project_name="default schema")
    assert ifc.schema == "IFC4"


def test_skeleton_schema_ifc4x3_yields_ifc4x3_file():
    ifc = build_ifc_project_skeleton(project_name="ifc4x3 schema", schema="IFC4X3")
    assert ifc.schema == "IFC4X3"
    assert len(ifc.by_type("IfcProject")) == 1
    assert len(ifc.by_type("IfcSite")) == 1
    assert len(ifc.by_type("IfcBuilding")) == 1
    assert len(ifc.by_type("IfcBuildingStorey")) == 1


def test_convert_dxf_emits_ifc4x3_when_schema_passed(
    full_kylmaelement_dxf: Path, tmp_path: Path
):
    out = tmp_path / "full_ifc4x3.ifc"
    convert_dxf(
        dxf_path=full_kylmaelement_dxf,
        output_path=out,
        profile=load_default_profile(),
        schema="IFC4X3",
    )
    ifc = ifcopenshell.open(str(out))
    assert ifc.schema == "IFC4X3"


def test_convert_dxf_ifc4x3_full_fixture_validates_clean(
    full_kylmaelement_dxf: Path, tmp_path: Path
):
    out = tmp_path / "full_ifc4x3.ifc"
    convert_dxf(
        dxf_path=full_kylmaelement_dxf,
        output_path=out,
        profile=load_default_profile(),
        schema="IFC4X3",
    )
    ifc = ifcopenshell.open(str(out))
    logger = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(ifc, logger=logger)
    errors = [e for e in logger.statements if e.get("level") == "ERROR"]
    assert errors == [], f"IFC4X3 validation errors: {errors}"


def test_convert_dxf_ifc4x3_full_fixture_emits_each_ifc_class(
    full_kylmaelement_dxf: Path, tmp_path: Path
):
    out = tmp_path / "full_ifc4x3.ifc"
    convert_dxf(
        dxf_path=full_kylmaelement_dxf,
        output_path=out,
        profile=load_default_profile(),
        schema="IFC4X3",
    )
    ifc = ifcopenshell.open(str(out))
    for ifc_class in (
        "IfcWall",
        "IfcSlab",
        "IfcDoor",
        "IfcWindow",
        "IfcPipeSegment",
        "IfcFurniture",
        "IfcCableCarrierSegment",
        "IfcBuildingElementProxy",
        "IfcEvaporator",
    ):
        assert ifc.by_type(ifc_class), f"no {ifc_class} entities in IFC4X3 fixture"
