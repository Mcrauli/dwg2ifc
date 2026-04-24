"""Unit tests for core.dxf_reader."""
from pathlib import Path

from dxf2ifc.core.dxf_reader import read_dxf
from dxf2ifc.core.types import LineGeometry, Point3D


def test_read_simple_wall_returns_one_entity(fixtures_dir: Path):
    records = read_dxf(fixtures_dir / "simple_wall.dxf")
    assert len(records) == 1


def test_read_simple_wall_captures_layer(fixtures_dir: Path):
    records = read_dxf(fixtures_dir / "simple_wall.dxf")
    assert records[0].layer == "KYL-ULKOSEINA"


def test_read_simple_wall_is_line(fixtures_dir: Path):
    records = read_dxf(fixtures_dir / "simple_wall.dxf")
    rec = records[0]
    assert rec.dxf_type == "LINE"
    assert isinstance(rec.geometry, LineGeometry)


def test_read_simple_wall_line_endpoints(fixtures_dir: Path):
    records = read_dxf(fixtures_dir / "simple_wall.dxf")
    line = records[0].geometry
    assert line.start == Point3D(0.0, 0.0, 0.0)
    assert line.end == Point3D(5000.0, 0.0, 0.0)
