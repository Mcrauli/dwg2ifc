"""Tests for the direct mesh readers added for MAGIEXPLODE output —
POLYLINE polyface mesh and 3DFACE."""

from __future__ import annotations

from pathlib import Path

import ezdxf

from dwg2ifc.core.dxf_reader import read_dxf
from dwg2ifc.core.types import MeshGeometry


def _save_and_read(doc, tmp_path: Path):
    p = tmp_path / "fixture.dxf"
    doc.saveas(str(p))
    return read_dxf(p)


def test_polyface_mesh_pyramid(tmp_path: Path):
    """A simple pyramid encoded as a POLYLINE polyface mesh round-trips
    into a MeshGeometry(source="polyface")."""
    doc = ezdxf.new("R2010")
    doc.layers.add(name="MAGI_OUT")
    msp = doc.modelspace()

    # 4-vertex pyramid: base triangle + apex.
    vertices = [(0.0, 0.0, 0.0), (1000.0, 0.0, 0.0), (500.0, 1000.0, 0.0), (500.0, 500.0, 1000.0)]
    faces = [(0, 1, 2), (0, 1, 3), (1, 2, 3), (2, 0, 3)]
    polyface = msp.add_polyface(dxfattribs={"layer": "MAGI_OUT"})
    polyface.append_faces(
        [[vertices[i] for i in face] for face in faces]
    )

    records = _save_and_read(doc, tmp_path)

    polyface_records = [
        r for r in records if isinstance(r.geometry, MeshGeometry)
        and r.geometry.source == "polyface"
    ]
    assert len(polyface_records) == 1
    rec = polyface_records[0]
    assert rec.layer == "MAGI_OUT"
    assert rec.dxf_type == "POLYFACE"
    # Pyramid has 4 unique vertices (or possibly more after dedup —
    # ezdxf may not dedupe; just assert ≥4) and 4 faces.
    assert len(rec.geometry.vertices) >= 4
    assert len(rec.geometry.faces) == 4
    # Each face is a triangle (3 indices).
    for face in rec.geometry.faces:
        assert len(face) == 3


def test_3dface_quad(tmp_path: Path):
    """A 3DFACE quad becomes a single MeshGeometry with one quad face."""
    doc = ezdxf.new("R2010")
    doc.layers.add(name="MAGI_QUAD")
    msp = doc.modelspace()
    msp.add_3dface(
        [
            (0.0, 0.0, 0.0),
            (1000.0, 0.0, 0.0),
            (1000.0, 500.0, 0.0),
            (0.0, 500.0, 0.0),
        ],
        dxfattribs={"layer": "MAGI_QUAD"},
    )

    records = _save_and_read(doc, tmp_path)
    face_records = [
        r for r in records if isinstance(r.geometry, MeshGeometry)
        and r.geometry.source == "3dface"
    ]
    assert len(face_records) == 1
    rec = face_records[0]
    assert rec.dxf_type == "3DFACE"
    assert rec.layer == "MAGI_QUAD"
    assert len(rec.geometry.vertices) == 4
    assert rec.geometry.faces == ((0, 1, 2, 3),)


def test_3dface_triangle_collapses_quad_to_three_vertices(tmp_path: Path):
    """When vtx2 == vtx3 the AutoCAD encoding represents a triangle."""
    doc = ezdxf.new("R2010")
    doc.layers.add(name="MAGI_TRI")
    msp = doc.modelspace()
    third = (1000.0, 500.0, 0.0)
    msp.add_3dface(
        [(0.0, 0.0, 0.0), (1000.0, 0.0, 0.0), third, third],
        dxfattribs={"layer": "MAGI_TRI"},
    )

    records = _save_and_read(doc, tmp_path)
    face_records = [
        r for r in records if isinstance(r.geometry, MeshGeometry)
        and r.geometry.source == "3dface"
    ]
    assert len(face_records) == 1
    rec = face_records[0]
    assert len(rec.geometry.vertices) == 3
    assert rec.geometry.faces == ((0, 1, 2),)


def test_open_polyline_still_emits_lines(tmp_path: Path):
    """A regular open POLYLINE (NOT polyface) keeps the existing
    LineGeometry behaviour. Regression guard so adding the polyface
    branch doesn't swallow ordinary 3D-polylines."""
    from dwg2ifc.core.types import LineGeometry

    doc = ezdxf.new("R2010")
    doc.layers.add(name="LT IMU")
    msp = doc.modelspace()
    msp.add_polyline3d(
        [(0.0, 0.0, 0.0), (1000.0, 0.0, 0.0), (2000.0, 0.0, 0.0)],
        dxfattribs={"layer": "LT IMU"},
    )

    records = _save_and_read(doc, tmp_path)
    line_records = [r for r in records if isinstance(r.geometry, LineGeometry)]
    # Open 3-vertex polyline → 2 line segments
    assert len(line_records) == 2
