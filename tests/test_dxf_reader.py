"""Unit tests for core.dxf_reader."""

from pathlib import Path

import ezdxf

from dxf2ifc.core.dxf_reader import read_dxf
from dxf2ifc.core.types import LineGeometry, PolygonGeometry, Point3D


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


def _write_closed_lwpolyline_dxf(path: Path, layer: str, points: list[tuple[float, float]]):
    doc = ezdxf.new("R2010")
    doc.layers.add(name=layer)
    msp = doc.modelspace()
    msp.add_lwpolyline(points, close=True, dxfattribs={"layer": layer})
    doc.saveas(str(path))


def test_read_closed_lwpolyline_returns_polygon_geometry(tmp_path: Path):
    dxf = tmp_path / "slab.dxf"
    pts = [(0.0, 0.0), (4000.0, 0.0), (4000.0, 3000.0), (0.0, 3000.0)]
    _write_closed_lwpolyline_dxf(dxf, "KYL-ALAPOHJA", pts)

    records = read_dxf(dxf)
    assert len(records) == 1
    rec = records[0]
    assert rec.layer == "KYL-ALAPOHJA"
    assert rec.dxf_type == "LWPOLYLINE"
    assert isinstance(rec.geometry, PolygonGeometry)
    assert rec.geometry.closed is True
    assert len(rec.geometry.vertices) == 4
    assert rec.geometry.vertices[0] == Point3D(0.0, 0.0, 0.0)
    assert rec.geometry.vertices[2] == Point3D(4000.0, 3000.0, 0.0)


def test_read_skips_open_lwpolyline(tmp_path: Path):
    dxf = tmp_path / "open.dxf"
    pts = [(0.0, 0.0), (1000.0, 0.0), (1000.0, 1000.0)]
    doc = ezdxf.new("R2010")
    doc.layers.add(name="KYL-ALAPOHJA")
    doc.modelspace().add_lwpolyline(pts, close=False, dxfattribs={"layer": "KYL-ALAPOHJA"})
    doc.saveas(str(dxf))
    records = read_dxf(dxf)
    assert records == []
