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
