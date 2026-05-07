"""Tests for INSERT-block 3DFACE aggregation — Lauri's KYL-LISP
shelves now emit dynamic block references (anonymous *U* blocks)
that contain 3DFACE primitives in block coordinates. dxf2ifc
expands them via INSERT.virtual_entities() and aggregates the
3DFACE faces into a single MeshGeometry per shelf.
"""

from __future__ import annotations

from pathlib import Path

import ezdxf

from dxf2ifc.core.dxf_reader import read_dxf
from dxf2ifc.core.types import BlockInstance, MeshGeometry


def _save_and_read(doc, tmp_path: Path):
    p = tmp_path / "fixture.dxf"
    doc.saveas(str(p))
    return read_dxf(p)


def test_insert_with_3dface_block_yields_mesh(tmp_path: Path):
    """An INSERT pointing at a block that carries 3DFACEs should
    return a MeshGeometry with all 3DFACEs aggregated, transformed
    into world coordinates."""
    doc = ezdxf.new("R2010")
    doc.layers.add(name="KYL-TIKASHYLLY")
    blk = doc.blocks.new(name="HYLLY_BASE")
    # Two 3DFACE quads side-by-side in block-local coords.
    blk.add_3dface(
        [(0.0, 0.0, 0.0), (1000.0, 0.0, 0.0), (1000.0, 100.0, 0.0), (0.0, 100.0, 0.0)]
    )
    blk.add_3dface(
        [(0.0, 0.0, 60.0), (1000.0, 0.0, 60.0), (1000.0, 100.0, 60.0), (0.0, 100.0, 60.0)]
    )
    msp = doc.modelspace()
    msp.add_blockref(
        "HYLLY_BASE",
        (5000.0, 4000.0, 0.0),
        dxfattribs={"layer": "KYL-TIKASHYLLY"},
    )

    records = _save_and_read(doc, tmp_path)

    insert_records = [r for r in records if r.dxf_type == "INSERT"]
    assert len(insert_records) == 1
    rec = insert_records[0]
    # Aggregated MeshGeometry, not a BlockInstance fallback.
    assert isinstance(rec.geometry, MeshGeometry)
    assert rec.geometry.source == "3dface"
    assert rec.layer == "KYL-TIKASHYLLY"
    # Two faces, vertices deduplicated where adjacent (here 8 unique).
    assert len(rec.geometry.faces) == 2
    assert len(rec.geometry.vertices) == 8


def test_insert_3dface_world_coordinates_apply_translation(tmp_path: Path):
    """ezdxf's virtual_entities() must apply the INSERT's translation
    so the mesh lands at the world-space placement, not at block (0,0,0)."""
    doc = ezdxf.new("R2010")
    doc.layers.add(name="KYL-LEVYHYLLY")
    blk = doc.blocks.new(name="LEVY_BASE")
    blk.add_3dface(
        [(0.0, 0.0, 100.0), (500.0, 0.0, 100.0), (500.0, 200.0, 100.0), (0.0, 200.0, 100.0)]
    )
    msp = doc.modelspace()
    msp.add_blockref(
        "LEVY_BASE",
        (12000.0, 8000.0, 0.0),
        dxfattribs={"layer": "KYL-LEVYHYLLY"},
    )

    records = _save_and_read(doc, tmp_path)

    insert_records = [
        r for r in records if r.dxf_type == "INSERT"
        and isinstance(r.geometry, MeshGeometry)
    ]
    assert len(insert_records) == 1
    rec = insert_records[0]
    # All four vertices should be offset by (12000, 8000, 0) from
    # block coords. Z stays at 100 (from block geometry, not affected
    # by INSERT.insert.z=0).
    xs = [v.x for v in rec.geometry.vertices]
    ys = [v.y for v in rec.geometry.vertices]
    zs = [v.z for v in rec.geometry.vertices]
    assert min(xs) == 12000.0
    assert max(xs) == 12500.0
    assert min(ys) == 8000.0
    assert max(ys) == 8200.0
    assert all(z == 100.0 for z in zs)


def test_insert_3dface_rotation_applies(tmp_path: Path):
    """INSERT rotation must rotate the block 3DFACE in world space."""
    doc = ezdxf.new("R2010")
    doc.layers.add(name="KYL-TIKASHYLLY")
    blk = doc.blocks.new(name="ROT_BASE")
    # Single 3DFACE along block-X axis, 1000 mm long.
    blk.add_3dface(
        [(0.0, 0.0, 0.0), (1000.0, 0.0, 0.0), (1000.0, 50.0, 0.0), (0.0, 50.0, 0.0)]
    )
    msp = doc.modelspace()
    # Rotate 90° → block-X points along world-Y.
    msp.add_blockref(
        "ROT_BASE",
        (0.0, 0.0, 0.0),
        dxfattribs={"layer": "KYL-TIKASHYLLY", "rotation": 90.0},
    )

    records = _save_and_read(doc, tmp_path)

    insert_records = [
        r for r in records if r.dxf_type == "INSERT"
        and isinstance(r.geometry, MeshGeometry)
    ]
    assert len(insert_records) == 1
    rec = insert_records[0]
    # After 90° rotation, block-X axis maps to world-Y axis. Allow
    # tiny floating-point drift from sin/cos.
    xs = [v.x for v in rec.geometry.vertices]
    ys = [v.y for v in rec.geometry.vertices]
    assert abs(max(ys) - 1000.0) < 0.001
    assert abs(max(xs) - 0.0) < 0.001  # block min-X → world X≈0
    assert abs(min(xs) - (-50.0)) < 0.001  # block max-Y rotated → -X


def test_insert_without_3dface_falls_back_to_blockinstance(tmp_path: Path):
    """If a block has no 3DFACE entities, INSERT must still yield a
    BlockInstance — the existing fallback path for height-extrusion
    rules and bbox-cuboid proxies."""
    doc = ezdxf.new("R2010")
    doc.layers.add(name="KALUSTEET")
    blk = doc.blocks.new(name="POSITIO")
    # Block contains only 2D primitives — no 3DFACE.
    blk.add_lwpolyline([(0.0, 0.0), (1000.0, 0.0), (1000.0, 500.0), (0.0, 500.0)])
    blk.add_text("LABEL", dxfattribs={"height": 100.0})
    msp = doc.modelspace()
    msp.add_blockref(
        "POSITIO",
        (5000.0, 5000.0, 0.0),
        dxfattribs={"layer": "KALUSTEET"},
    )

    records = _save_and_read(doc, tmp_path)

    insert_records = [r for r in records if r.dxf_type == "INSERT"]
    assert len(insert_records) == 1
    # Should fall back to BlockInstance (raw transform) rather than
    # MeshGeometry.
    assert isinstance(insert_records[0].geometry, BlockInstance)
