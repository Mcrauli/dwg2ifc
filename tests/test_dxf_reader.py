"""Unit tests for core.dxf_reader."""

import math
from pathlib import Path

import ezdxf
import pytest

from dwg2ifc.core.dxf_reader import list_layers, read_dxf
from dwg2ifc.core.types import (
    BlockInstance,
    LineGeometry,
    MeshGeometry,
    Point3D,
    PolygonGeometry,
)


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


def test_read_insert_returns_block_instance(tmp_path: Path):
    dxf = tmp_path / "door.dxf"
    doc = ezdxf.new("R2010")
    doc.layers.add(name="KYL-OVET-ULKO")
    block = doc.blocks.new(name="OVI-ULKO")
    block.add_line((0, 0), (900, 0))
    block.add_line((0, 0), (0, 2100))
    msp = doc.modelspace()
    msp.add_blockref(
        "OVI-ULKO",
        (1500, 2500, 0),
        dxfattribs={"layer": "KYL-OVET-ULKO", "rotation": 90},
    )
    doc.saveas(str(dxf))

    records = read_dxf(dxf)
    inserts = [r for r in records if r.dxf_type == "INSERT"]
    assert len(inserts) == 1
    rec = inserts[0]
    assert rec.layer == "KYL-OVET-ULKO"
    assert rec.block_name == "OVI-ULKO"
    assert isinstance(rec.geometry, BlockInstance)
    assert rec.geometry.insertion_point == Point3D(1500.0, 2500.0, 0.0)
    assert rec.geometry.rotation_rad == pytest.approx(math.radians(90))
    assert rec.geometry.scale_x == 1.0


def test_read_open_lwpolyline_yields_line_segments(tmp_path: Path):
    """v0.1.19+: open LWPOLYLINEs (common in MagiCAD proxy graphics for
    pipe centrelines and detail outlines) are no longer dropped — they
    fan out to one LineGeometry record per consecutive vertex pair so
    the profile mapper can route them through the LineGeometry-only
    builders (add_pipe_segment, add_cable_carrier_segment)."""
    from dwg2ifc.core.types import LineGeometry

    dxf = tmp_path / "open.dxf"
    pts = [(0.0, 0.0), (1000.0, 0.0), (1000.0, 1000.0)]
    doc = ezdxf.new("R2010")
    doc.layers.add(name="KYL-ALAPOHJA")
    doc.modelspace().add_lwpolyline(pts, close=False, dxfattribs={"layer": "KYL-ALAPOHJA"})
    doc.saveas(str(dxf))
    records = read_dxf(dxf)
    assert len(records) == 2
    assert all(r.dxf_type == "LWPOLYLINE" for r in records)
    assert all(isinstance(r.geometry, LineGeometry) for r in records)
    assert all(r.layer == "KYL-ALAPOHJA" for r in records)


def test_list_layers_returns_unique_sorted_names_from_modelspace(tmp_path: Path):
    dxf = tmp_path / "two_layers.dxf"
    doc = ezdxf.new("R2010")
    doc.layers.add(name="LT IMU")
    doc.layers.add(name="KYL-VIEMARI-LATTIA")
    msp = doc.modelspace()
    msp.add_line((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), dxfattribs={"layer": "LT IMU"})
    msp.add_line((0.0, 1.0, 0.0), (1.0, 1.0, 0.0), dxfattribs={"layer": "KYL-VIEMARI-LATTIA"})
    msp.add_line((0.0, 2.0, 0.0), (1.0, 2.0, 0.0), dxfattribs={"layer": "LT IMU"})
    doc.saveas(str(dxf))

    layers = list_layers(dxf)
    assert layers == ["KYL-VIEMARI-LATTIA", "LT IMU"]


def test_list_layers_on_simple_wall_fixture(fixtures_dir: Path):
    layers = list_layers(fixtures_dir / "simple_wall.dxf")
    assert "KYL-ULKOSEINA" in layers


def _write_tetrahedron_mesh_dxf(path: Path, layer: str) -> None:
    """Write a synthetic DXF containing a single tetrahedron MESH entity.

    Simulates the output of accoreconsole.exe -MESHSMOOTH on a 3DSOLID:
    4 unique vertices and 4 triangular faces.
    """
    doc = ezdxf.new("R2010")
    doc.layers.add(name=layer)
    msp = doc.modelspace()
    mesh = msp.add_mesh(dxfattribs={"layer": layer})
    with mesh.edit_data() as data:
        data.vertices = [
            (0.0, 0.0, 0.0),
            (1000.0, 0.0, 0.0),
            (500.0, 1000.0, 0.0),
            (500.0, 500.0, 1000.0),
        ]
        data.faces = [
            (0, 1, 2),
            (0, 1, 3),
            (1, 2, 3),
            (0, 2, 3),
        ]
    doc.saveas(str(path))


def test_read_dxf_picks_up_mesh_entity(tmp_path: Path):
    dxf = tmp_path / "tetra.dxf"
    _write_tetrahedron_mesh_dxf(dxf, "KYL-LEVY")

    records = read_dxf(dxf)
    meshes = [r for r in records if r.dxf_type == "MESH"]
    assert len(meshes) == 1
    rec = meshes[0]
    assert isinstance(rec.geometry, MeshGeometry)
    assert len(rec.geometry.vertices) == 4
    assert len(rec.geometry.faces) == 4
    # Every face is a triangle (3 indices).
    assert all(len(f) == 3 for f in rec.geometry.faces)
    # Indices reference valid vertices.
    n = len(rec.geometry.vertices)
    assert all(0 <= i < n for f in rec.geometry.faces for i in f)


def test_read_dxf_skips_degenerate_mesh(tmp_path: Path):
    dxf = tmp_path / "empty_mesh.dxf"
    doc = ezdxf.new("R2010")
    doc.layers.add(name="KYL-LEVY")
    msp = doc.modelspace()
    msp.add_mesh(dxfattribs={"layer": "KYL-LEVY"})  # no vertices, no faces
    doc.saveas(str(dxf))

    records = read_dxf(dxf)
    assert [r for r in records if r.dxf_type == "MESH"] == []


def test_mesh_geometry_preserves_layer(tmp_path: Path):
    dxf = tmp_path / "tetra_layer.dxf"
    _write_tetrahedron_mesh_dxf(dxf, "KYL-HOYRYSTIN-CR-30")

    records = read_dxf(dxf)
    meshes = [r for r in records if r.dxf_type == "MESH"]
    assert len(meshes) == 1
    assert meshes[0].layer == "KYL-HOYRYSTIN-CR-30"


def test_mesh_geometry_handles_quad_faces(tmp_path: Path):
    """DXF MESH supports n-gon faces; verify a quad round-trips with 4 indices."""
    dxf = tmp_path / "quad_mesh.dxf"
    doc = ezdxf.new("R2010")
    doc.layers.add(name="KYL-LEVY")
    msp = doc.modelspace()
    mesh = msp.add_mesh(dxfattribs={"layer": "KYL-LEVY"})
    with mesh.edit_data() as data:
        data.vertices = [
            (0.0, 0.0, 0.0),
            (1000.0, 0.0, 0.0),
            (1000.0, 1000.0, 0.0),
            (0.0, 1000.0, 0.0),
        ]
        data.faces = [(0, 1, 2, 3)]
    doc.saveas(str(dxf))

    records = read_dxf(dxf)
    meshes = [r for r in records if r.dxf_type == "MESH"]
    assert len(meshes) == 1
    geom = meshes[0].geometry
    assert isinstance(geom, MeshGeometry)
    assert len(geom.faces) == 1
    assert len(geom.faces[0]) == 4
    assert geom.faces[0] == (0, 1, 2, 3)
