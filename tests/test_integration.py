"""End-to-end integration test: DXF -> CLI -> IFC validated by ifcopenshell."""

import os
import subprocess
import sys
from pathlib import Path

import ezdxf
import ifcopenshell
import ifcopenshell.validate

from dxf2ifc.core.ifc_writer import convert_dxf
from dxf2ifc.profiles.loader import load_default_profile


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


def test_simple_wall_roundtrip(fixtures_dir: Path, tmp_path: Path):
    dxf = fixtures_dir / "simple_wall.dxf"
    out = tmp_path / "simple_wall.ifc"

    env = os.environ.copy()
    src_path = str(Path(__file__).resolve().parent.parent / "src")
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        [sys.executable, "-m", "dxf2ifc", "convert", str(dxf), str(out)],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr

    ifc = ifcopenshell.open(str(out))

    assert ifc.schema == "IFC4"
    walls = ifc.by_type("IfcWall")
    assert len(walls) == 1, f"expected 1 wall, got {len(walls)}"
    wall = walls[0]
    assert wall.PredefinedType == "STANDARD"

    refs = ifc.by_type("IfcClassificationReference")
    talo = [r for r in refs if r.Identification == "1241"]
    assert len(talo) >= 1
    assert talo[0].ReferencedSource.Name == "Talo2000"

    assert wall.Representation is not None

    logger = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(ifc, logger=logger)
    errors = [e for e in logger.statements if e.get("level") == "ERROR"]
    assert errors == [], f"IFC validation errors: {errors}"


def test_alapohja_roundtrip_produces_floor_ifcslab(tmp_path: Path):
    dxf = tmp_path / "alapohja.dxf"
    _write_closed_lwpolyline_dxf(dxf, layer="KYL-ALAPOHJA")
    out = tmp_path / "alapohja.ifc"

    convert_dxf(dxf_path=dxf, output_path=out, profile=load_default_profile())

    ifc = ifcopenshell.open(str(out))
    assert ifc.schema == "IFC4"
    slabs = ifc.by_type("IfcSlab")
    assert len(slabs) == 1
    assert slabs[0].PredefinedType == "FLOOR"

    refs = ifc.by_type("IfcClassificationReference")
    talo = [r for r in refs if r.Identification == "1221"]
    assert len(talo) == 1
    assert talo[0].ReferencedSource.Name == "Talo2000"

    logger = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(ifc, logger=logger)
    errors = [e for e in logger.statements if e.get("level") == "ERROR"]
    assert errors == [], f"IFC validation errors: {errors}"


def test_ovi_ulko_roundtrip_produces_ifcdoor_with_talo2000_1243(tmp_path: Path):
    dxf = tmp_path / "ovi_ulko.dxf"
    _write_block_insert_dxf(
        dxf,
        layer="KYL-OVET-ULKO",
        block_name="OVI-ULKO",
        insertion=(1500.0, 2500.0),
    )
    out = tmp_path / "ovi_ulko.ifc"

    convert_dxf(dxf_path=dxf, output_path=out, profile=load_default_profile())

    ifc = ifcopenshell.open(str(out))
    assert ifc.schema == "IFC4"
    doors = ifc.by_type("IfcDoor")
    assert len(doors) == 1
    door = doors[0]
    assert door.PredefinedType == "DOOR"
    assert door.OverallHeight is not None
    assert door.OverallWidth is not None

    refs = ifc.by_type("IfcClassificationReference")
    talo = [r for r in refs if r.Identification == "1243"]
    assert len(talo) == 1
    assert talo[0].ReferencedSource.Name == "Talo2000"

    logger = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(ifc, logger=logger)
    errors = [e for e in logger.statements if e.get("level") == "ERROR"]
    assert errors == [], f"IFC validation errors: {errors}"


def test_ikkuna_roundtrip_produces_ifcwindow_with_talo2000_1242(tmp_path: Path):
    dxf = tmp_path / "ikkuna.dxf"
    _write_block_insert_dxf(
        dxf,
        layer="KYL-IKKUNA-MUOVI",
        block_name="IKKUNA",
        insertion=(800.0, 1200.0),
    )
    out = tmp_path / "ikkuna.ifc"

    convert_dxf(dxf_path=dxf, output_path=out, profile=load_default_profile())

    ifc = ifcopenshell.open(str(out))
    assert ifc.schema == "IFC4"
    windows = ifc.by_type("IfcWindow")
    assert len(windows) == 1
    window = windows[0]
    assert window.PredefinedType == "WINDOW"
    assert window.OverallHeight is not None
    assert window.OverallWidth is not None

    refs = ifc.by_type("IfcClassificationReference")
    talo = [r for r in refs if r.Identification == "1242"]
    assert len(talo) == 1
    assert talo[0].ReferencedSource.Name == "Talo2000"

    logger = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(ifc, logger=logger)
    errors = [e for e in logger.statements if e.get("level") == "ERROR"]
    assert errors == [], f"IFC validation errors: {errors}"


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

    # Plan H Task 14: refrigerant pipes are TATE-domain → no Talo2000
    # classification. RAVA-LVI classification arrives in Plan H Tasks 15-17.
    refs = ifc.by_type("IfcClassificationReference")
    assert all(r.Identification != "2151" for r in refs)

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

    # Plan H Task 14: drainpipe is TATE-domain → no Talo2000.
    refs = ifc.by_type("IfcClassificationReference")
    assert all(r.Identification != "2160" for r in refs)

    logger = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(ifc, logger=logger)
    errors = [e for e in logger.statements if e.get("level") == "ERROR"]
    assert errors == [], f"IFC validation errors: {errors}"


def test_kyl_levyhylly_roundtrip_produces_ifcfurniture_with_talo2000_1331(tmp_path: Path):
    dxf = tmp_path / "kyl_levyhylly.dxf"
    _write_block_insert_dxf(
        dxf,
        layer="KYL-LEVYHYLLY",
        block_name="KLHYLLY-LEVY",
        insertion=(2000.0, 1500.0),
    )
    out = tmp_path / "kyl_levyhylly.ifc"

    convert_dxf(dxf_path=dxf, output_path=out, profile=load_default_profile())

    ifc = ifcopenshell.open(str(out))
    assert ifc.schema == "IFC4"
    furnitures = ifc.by_type("IfcFurniture")
    assert len(furnitures) == 1
    assert furnitures[0].Name == "KYL-LEVYHYLLY"

    refs = ifc.by_type("IfcClassificationReference")
    talo = [r for r in refs if r.Identification == "1331"]
    assert len(talo) == 1
    assert talo[0].ReferencedSource.Name == "Talo2000"

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

    # Plan H Task 14: cable carrier is TATE-domain → no Talo2000.
    refs = ifc.by_type("IfcClassificationReference")
    assert all(r.Identification != "2380" for r in refs)

    logger = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(ifc, logger=logger)
    errors = [e for e in logger.statements if e.get("level") == "ERROR"]
    assert errors == [], f"IFC validation errors: {errors}"


def test_kyl_levy_roundtrip_produces_building_element_proxy(tmp_path: Path):
    dxf = tmp_path / "kyl_levy.dxf"
    _write_closed_lwpolyline_dxf(dxf, layer="KYL-LEVY")
    out = tmp_path / "kyl_levy.ifc"

    convert_dxf(dxf_path=dxf, output_path=out, profile=load_default_profile())

    ifc = ifcopenshell.open(str(out))
    assert ifc.schema == "IFC4"
    proxies = ifc.by_type("IfcBuildingElementProxy")
    assert len(proxies) == 1
    assert proxies[0].Name == "KYL-LEVY"

    refs = ifc.by_type("IfcClassificationReference")
    talo = [r for r in refs if r.Identification == "1352"]
    assert len(talo) == 1
    assert talo[0].ReferencedSource.Name == "Talo2000"

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

    # Plan H Task 13: cooling equipment is TATE-domain → no Talo2000.
    refs = ifc.by_type("IfcClassificationReference")
    assert all(r.Identification != "2510" for r in refs)

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
    assert set(systems.keys()) >= {"Refrigeration LT", "Drainage"}
    assert len(systems["Refrigeration LT"]) == 1
    assert len(systems["Drainage"]) == 1
    assert systems["Refrigeration LT"][0].is_a("IfcPipeSegment")
    assert systems["Drainage"][0].is_a("IfcPipeSegment")


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
    assert {"Refrigeration LT", "Drainage"}.issubset(systems_by_name.keys())

    rels = ifc.by_type("IfcRelAssignsToGroup")
    members_by_system = {
        rel.RelatingGroup.Name: list(rel.RelatedObjects)
        for rel in rels
        if rel.RelatingGroup.is_a("IfcSystem")
    }
    assert len(members_by_system["Refrigeration LT"]) == 1
    assert members_by_system["Refrigeration LT"][0].is_a("IfcPipeSegment")
    assert len(members_by_system["Drainage"]) == 1
    assert members_by_system["Drainage"][0].is_a("IfcPipeSegment")


def test_partition_wall_roundtrip_produces_partitioning_ifcwall(tmp_path: Path):
    dxf = tmp_path / "partition_wall.dxf"
    _write_single_line_dxf(dxf, layer="KYL-VALISEINA")
    out = tmp_path / "partition_wall.ifc"

    convert_dxf(dxf_path=dxf, output_path=out, profile=load_default_profile())

    ifc = ifcopenshell.open(str(out))
    assert ifc.schema == "IFC4"
    walls = ifc.by_type("IfcWall")
    assert len(walls) == 1
    assert walls[0].PredefinedType == "PARTITIONING"

    refs = ifc.by_type("IfcClassificationReference")
    talo = [r for r in refs if r.Identification == "1311"]
    assert len(talo) == 1
    assert talo[0].ReferencedSource.Name == "Talo2000"

    logger = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(ifc, logger=logger)
    errors = [e for e in logger.statements if e.get("level") == "ERROR"]
    assert errors == [], f"IFC validation errors: {errors}"
