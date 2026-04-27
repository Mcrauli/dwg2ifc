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
