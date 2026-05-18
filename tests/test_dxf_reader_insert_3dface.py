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


def test_insert_3d_rotated_polyline_extrudes_along_block_local_z(tmp_path: Path):
    """KLHV (vertical TIKAS) rotates KLHYLLY-TIKAS 90° around X via
    INSERT.extrusion=(0,-1,0). Block-local LWPOLYLINE+3DFACE pairs must
    extrude along the extrusion vector (block-local +Z), not WCS +Z —
    otherwise every rung collapses onto the same WCS-Y plane and the
    whole shelf renders as one tall slab instead of a ladder.

    Block layout: two parallel rungs (1000×30 closed polylines at
    elev=0) with matching 3DFACE caps at z=30 (rung thickness 30mm).
    The block is then INSERTed with extrusion=(0,-1,0), which in OCS
    means the block-local +Z axis points along world -Y.

    Expected world-space mesh:
    * Rungs lie in the world XZ plane (their long axis = block-X = world-X,
      their thickness extrudes along block-Z = world -Y).
    * The two rungs must remain separated in block-Y (= world Z), not
      collapsed onto each other.
    """
    import math

    doc = ezdxf.new("R2010")
    doc.layers.add(name="KYL-TIKASHYLLY")
    blk = doc.blocks.new(name="TIKAS_VERT")
    # Rung 1: closed polyline at z=0 + 3DFACE cap at z=30
    blk.add_lwpolyline(
        [(0.0, 0.0), (1000.0, 0.0), (1000.0, 30.0), (0.0, 30.0)],
        close=True,
    )
    blk.add_3dface(
        [(0.0, 0.0, 30.0), (1000.0, 0.0, 30.0), (1000.0, 30.0, 30.0), (0.0, 30.0, 30.0)]
    )
    # Rung 2: same shape, offset along block-Y by 200mm
    blk.add_lwpolyline(
        [(0.0, 200.0), (1000.0, 200.0), (1000.0, 230.0), (0.0, 230.0)],
        close=True,
    )
    blk.add_3dface(
        [(0.0, 200.0, 30.0), (1000.0, 200.0, 30.0), (1000.0, 230.0, 30.0), (0.0, 230.0, 30.0)]
    )

    msp = doc.modelspace()
    msp.add_blockref(
        "TIKAS_VERT",
        (0.0, 0.0, 0.0),
        dxfattribs={
            "layer": "KYL-TIKASHYLLY",
            "extrusion": (0.0, -1.0, 0.0),
        },
    )

    records = _save_and_read(doc, tmp_path)
    insert_records = [
        r for r in records if r.dxf_type == "INSERT"
        and isinstance(r.geometry, MeshGeometry)
    ]
    assert len(insert_records) == 1
    mesh = insert_records[0].geometry
    xs = [v.x for v in mesh.vertices]
    ys = [v.y for v in mesh.vertices]
    zs = [v.z for v in mesh.vertices]

    # Block-X (= rung length) maps to world-X
    assert max(xs) - min(xs) > 999.0
    # The two rungs are separated by 200mm along block-Y, which under
    # extrusion=(0,-1,0) maps to world-Z. So the Z spread must reflect
    # both the rung width (30mm each) AND the 200mm gap between them.
    assert max(zs) - min(zs) > 200.0, (
        f"Rungs collapsed in world-Z. zs range = {min(zs)}..{max(zs)}"
    )
    # Thickness (30mm) extrudes along block-Z = world -Y, so the Y
    # spread should be ~30mm (not 0, not collapsed, not extruded vertically).
    y_spread = max(ys) - min(ys)
    assert 25.0 < y_spread < 35.0, (
        f"Thickness extruded wrong direction. y_spread={y_spread} "
        f"(expected ~30mm along world -Y from extrusion=(0,-1,0))"
    )


def test_insert_kotelo_thin_rim_extrudes_to_3dface_top_not_polyline_default(tmp_path: Path):
    """Mixed-elevation polylines + 3DFACEs (the KYL-KOTELO block shape)
    must extrude thin-rim side walls to the 3DFACE-defined block top, not
    to ``max(polyline_elev) + DEFAULT_TOP_OFFSET_MM`` — the latter
    overshoots whenever a polyline sits high in the block (kotelo's top
    slab is a polyline at elev=118.2, so the +9 fallback would push the
    side walls up to z=127.2 instead of the real top z=120).
    """
    doc = ezdxf.new("R2018")
    doc.layers.add(name="KYL-KOTELO")
    blk = doc.blocks.new(name="KOTELO")
    # Wide bottom slab — full footprint, thin Z extent
    p = blk.add_lwpolyline([(0, 0), (1000, 0), (1000, 305), (0, 305)], close=True)
    p.dxf.thickness = 1.8
    # Wide top slab — full footprint, elev=118.2 (the elevation that trips the bug)
    p = blk.add_lwpolyline([(0, 0), (1000, 0), (1000, 305), (0, 305)], close=True)
    p.dxf.elevation = 118.2
    p.dxf.thickness = 1.8
    # Thin side wall — qualifies as "thin rim" (min side 1.8 mm <= 5 mm)
    p = blk.add_lwpolyline([(0, 0), (1000, 0), (1000, 1.8), (0, 1.8)], close=True)
    p.dxf.thickness = 120
    # Thin side wall opposite
    p = blk.add_lwpolyline(
        [(0, 303.2), (1000, 303.2), (1000, 305), (0, 305)], close=True
    )
    p.dxf.thickness = 120
    # 3DFACEs define the kotelo's true block top at z=120
    blk.add_3dface([(0, 0, 0), (1000, 0, 0), (1000, 305, 0), (0, 305, 0)])
    blk.add_3dface([(0, 0, 1.8), (1000, 0, 1.8), (1000, 305, 1.8), (0, 305, 1.8)])
    blk.add_3dface(
        [(0, 0, 118.2), (1000, 0, 118.2), (1000, 305, 118.2), (0, 305, 118.2)]
    )
    blk.add_3dface([(0, 0, 120), (1000, 0, 120), (1000, 305, 120), (0, 305, 120)])
    doc.modelspace().add_blockref(
        "KOTELO", (0, 0, 0), dxfattribs={"layer": "KYL-KOTELO"}
    )

    records = _save_and_read(doc, tmp_path)
    insert_records = [
        r for r in records if r.dxf_type == "INSERT"
        and isinstance(r.geometry, MeshGeometry)
    ]
    assert len(insert_records) == 1
    zs = [v.z for v in insert_records[0].geometry.vertices]
    # The mesh top must match the 3DFACE-defined real top (120), not the
    # polyline-elevation fallback (118.2 + 9 = 127.2).
    assert abs(max(zs) - 120.0) < 0.01, (
        f"thin-rim side walls overshot block top: max Z = {max(zs)} (expected 120)"
    )


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
