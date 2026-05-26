"""End-to-end integration test: DXF -> CLI -> IFC validated by ifcopenshell."""

import os
import subprocess
import sys
from pathlib import Path

import ezdxf
import ifcopenshell
import ifcopenshell.validate

from dwg2ifc.core.ifc_writer import convert_dxf
from dwg2ifc.profiles.loader import load_default_profile


def _write_single_line_dxf(path: Path, layer: str) -> None:
    doc = ezdxf.new("R2010")
    doc.layers.add(name=layer)
    msp = doc.modelspace()
    msp.add_line((0.0, 0.0, 0.0), (5000.0, 0.0, 0.0), dxfattribs={"layer": layer})
    doc.saveas(str(path))


def _write_closed_lwpolyline_dxf(path: Path, layer: str) -> None:
    doc = ezdxf.new("R2010")
    doc.layers.add(name=layer)
    msp = doc.modelspace()
    pts = [(0.0, 0.0), (4000.0, 0.0), (4000.0, 3000.0), (0.0, 3000.0)]
    msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": layer})
    doc.saveas(str(path))


def _write_block_insert_dxf(
    path: Path, *, layer: str, block_name: str, insertion: tuple[float, float]
) -> None:
    doc = ezdxf.new("R2010")
    doc.layers.add(name=layer)
    block = doc.blocks.new(name=block_name)
    block.add_line((0.0, 0.0), (900.0, 0.0))
    msp = doc.modelspace()
    msp.add_blockref(block_name, insertion, dxfattribs={"layer": layer})
    doc.saveas(str(path))










def test_lt_imu_roundtrip_produces_ifcpipesegment(tmp_path: Path):
    dxf = tmp_path / "lt_imu.dxf"
    _write_single_line_dxf(dxf, layer="LT IMU")
    out = tmp_path / "lt_imu.ifc"

    convert_dxf(dxf_path=dxf, output_path=out, profile=load_default_profile())

    ifc = ifcopenshell.open(str(out))
    assert ifc.schema == "IFC4"
    pipes = ifc.by_type("IfcPipeSegment")
    assert len(pipes) == 1
    pipe = pipes[0]
    # IFC4 has no REFRIGERATION enum on IfcPipeSegment — USERDEFINED carries it.
    assert pipe.PredefinedType == "USERDEFINED"
    assert pipe.ObjectType == "REFRIGERATION"

    types = ifc.by_type("IfcPipeSegmentType")
    assert any(t.ElementType == "REFRIGERATION" for t in types)

    # Plan H Task 14: refrigerant pipes are TATE-domain → RAVA-LVI.
    refs = ifc.by_type("IfcClassificationReference")
    rava = [r for r in refs if r.Identification == "T-LVI-02"]
    assert len(rava) == 1
    assert rava[0].ReferencedSource.Name == "RAVA-LVI"

    logger = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(ifc, logger=logger)
    errors = [e for e in logger.statements if e.get("level") == "ERROR"]
    assert errors == [], f"IFC validation errors: {errors}"


def test_kyl_viemari_lattia_roundtrip_produces_drainpipe(tmp_path: Path):
    dxf = tmp_path / "kyl_viemari.dxf"
    _write_single_line_dxf(dxf, layer="KYL-VIEMARI-LATTIA")
    out = tmp_path / "kyl_viemari.ifc"

    convert_dxf(dxf_path=dxf, output_path=out, profile=load_default_profile())

    ifc = ifcopenshell.open(str(out))
    assert ifc.schema == "IFC4"
    pipes = ifc.by_type("IfcPipeSegment")
    assert len(pipes) == 1
    pipe = pipes[0]
    assert pipe.PredefinedType == "USERDEFINED"
    assert pipe.ObjectType == "DRAINPIPE"

    drain_types = [t for t in ifc.by_type("IfcPipeSegmentType") if t.ElementType == "DRAINPIPE"]
    assert len(drain_types) == 1

    # Plan H Task 14: drainpipe is TATE-domain → RAVA-LVI T-LVI-04-01-001.
    refs = ifc.by_type("IfcClassificationReference")
    rava = [r for r in refs if r.Identification == "T-LVI-04-01-001"]
    assert len(rava) == 1
    assert rava[0].ReferencedSource.Name == "RAVA-LVI"

    logger = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(ifc, logger=logger)
    errors = [e for e in logger.statements if e.get("level") == "ERROR"]
    assert errors == [], f"IFC validation errors: {errors}"




def test_kaapelihylly_roundtrip_produces_cable_carrier_segment(tmp_path: Path):
    dxf = tmp_path / "kaapelihylly.dxf"
    _write_single_line_dxf(dxf, layer="KAAPELIHYLLY")
    out = tmp_path / "kaapelihylly.ifc"

    convert_dxf(dxf_path=dxf, output_path=out, profile=load_default_profile())

    ifc = ifcopenshell.open(str(out))
    assert ifc.schema == "IFC4"
    segments = ifc.by_type("IfcCableCarrierSegment")
    assert len(segments) == 1
    assert segments[0].PredefinedType == "CABLETRUNKINGSEGMENT"

    types = ifc.by_type("IfcCableCarrierSegmentType")
    assert any(t.PredefinedType == "CABLETRUNKINGSEGMENT" for t in types)

    # Plan H Task 14: cable carrier is TATE-domain → RAVA-TATE.
    refs = ifc.by_type("IfcClassificationReference")
    rava = [r for r in refs if r.Identification == "T-TATE-01-01-001"]
    assert len(rava) == 1
    assert rava[0].ReferencedSource.Name == "RAVA-TATE"

    logger = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(ifc, logger=logger)
    errors = [e for e in logger.statements if e.get("level") == "ERROR"]
    assert errors == [], f"IFC validation errors: {errors}"




def test_hoyrystin_roundtrip_produces_ifcevaporator_with_talo2000_2510(tmp_path: Path):
    dxf = tmp_path / "hoyrystin.dxf"
    _write_block_insert_dxf(
        dxf,
        layer="KYL-HOYRYSTIN-CR-30",
        block_name="HOYRYSTIN",
        insertion=(1500.0, 1500.0),
    )
    out = tmp_path / "hoyrystin.ifc"

    convert_dxf(dxf_path=dxf, output_path=out, profile=load_default_profile())

    ifc = ifcopenshell.open(str(out))
    assert ifc.schema == "IFC4"
    evaps = ifc.by_type("IfcEvaporator")
    assert len(evaps) == 1
    assert evaps[0].Name == "KYL-HOYRYSTIN-CR-30"

    # Plan H Task 13: cooling equipment is TATE-domain → RAVA-LVI.
    refs = ifc.by_type("IfcClassificationReference")
    rava = [r for r in refs if r.Identification == "T-LVI-01-01-023"]
    assert len(rava) == 1
    assert rava[0].ReferencedSource.Name == "RAVA-LVI"

    logger = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(ifc, logger=logger)
    errors = [e for e in logger.statements if e.get("level") == "ERROR"]
    assert errors == [], f"IFC validation errors: {errors}"


def test_convert_dxf_returns_systems_dict_grouped_by_system_name(tmp_path: Path):
    """Plan C Task 9: convert_dxf collects produced IFC products into a
    dict keyed by Rule.system_name when the rule supplied one."""
    dxf = tmp_path / "two_systems.dxf"
    doc = ezdxf.new("R2010")
    doc.layers.add(name="LT IMU")
    doc.layers.add(name="KYL-VIEMARI-LATTIA")
    msp = doc.modelspace()
    msp.add_line((0.0, 0.0, 0.0), (1000.0, 0.0, 0.0), dxfattribs={"layer": "LT IMU"})
    msp.add_line(
        (0.0, 1000.0, 0.0),
        (1000.0, 1000.0, 0.0),
        dxfattribs={"layer": "KYL-VIEMARI-LATTIA"},
    )
    doc.saveas(str(dxf))
    out = tmp_path / "two_systems.ifc"

    systems, report = convert_dxf(dxf_path=dxf, output_path=out, profile=load_default_profile())

    assert report is None
    assert isinstance(systems, dict)
    assert set(systems.keys()) >= {"Kylmä - suorahöyrysteinen", "Kylmäjärjestelmä"}
    assert len(systems["Kylmä - suorahöyrysteinen"]) == 1
    assert len(systems["Kylmäjärjestelmä"]) == 1
    assert systems["Kylmä - suorahöyrysteinen"][0].is_a("IfcPipeSegment")
    assert systems["Kylmäjärjestelmä"][0].is_a("IfcPipeSegment")


def test_convert_dxf_creates_ifcsystem_and_assigns_products(tmp_path: Path):
    """Plan C Task 10: convert_dxf creates one IfcSystem per system_name
    and assigns the matching products via IfcRelAssignsToGroup."""
    dxf = tmp_path / "two_systems.dxf"
    doc = ezdxf.new("R2010")
    doc.layers.add(name="LT IMU")
    doc.layers.add(name="KYL-VIEMARI-LATTIA")
    msp = doc.modelspace()
    msp.add_line((0.0, 0.0, 0.0), (1000.0, 0.0, 0.0), dxfattribs={"layer": "LT IMU"})
    msp.add_line(
        (0.0, 1000.0, 0.0),
        (1000.0, 1000.0, 0.0),
        dxfattribs={"layer": "KYL-VIEMARI-LATTIA"},
    )
    doc.saveas(str(dxf))
    out = tmp_path / "two_systems.ifc"

    convert_dxf(dxf_path=dxf, output_path=out, profile=load_default_profile())

    ifc = ifcopenshell.open(str(out))
    systems_by_name = {s.Name: s for s in ifc.by_type("IfcSystem")}
    assert {"Kylmä - suorahöyrysteinen", "Kylmäjärjestelmä"}.issubset(systems_by_name.keys())

    rels = ifc.by_type("IfcRelAssignsToGroup")
    members_by_system = {
        rel.RelatingGroup.Name: list(rel.RelatedObjects)
        for rel in rels
        if rel.RelatingGroup.is_a("IfcSystem")
    }
    assert len(members_by_system["Kylmä - suorahöyrysteinen"]) == 1
    assert members_by_system["Kylmä - suorahöyrysteinen"][0].is_a("IfcPipeSegment")
    assert len(members_by_system["Kylmäjärjestelmä"]) == 1
    assert members_by_system["Kylmäjärjestelmä"][0].is_a("IfcPipeSegment")


def test_convert_dxf_system_gets_fi_jarjestelma_pset_with_rava_code(tmp_path: Path):
    from ifcopenshell.api import run as ifc_run

    from dwg2ifc.core.ifc_writer.builders import add_system

    ifc = ifcopenshell.file(schema="IFC4")
    ifc_run("root.create_entity", ifc, ifc_class="IfcProject", name="t")
    system = add_system(ifc, name="Refrigeration plant", system_code="J-LVI-09-02")
    pset = None
    for rel in (system.IsDefinedBy or []):
        if rel.is_a("IfcRelDefinesByProperties"):
            pd = rel.RelatingPropertyDefinition
            if pd and pd.is_a("IfcPropertySet") and pd.Name == "FI_Järjestelmä":
                pset = pd
                break
    assert pset is not None
    by_name = {
        p.Name: (p.NominalValue.wrappedValue if p.NominalValue else None)
        for p in (pset.HasProperties or [])
    }
    assert by_name["03 Järjestelmätyypin koodi"] == "J-LVI-09-02"
    assert by_name["06 Järjestelmän nimi"] == "Refrigeration plant"
