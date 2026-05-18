"""Regression tests for the STLOUT positive-Z-shift correction.

AutoCAD's STLOUT command refuses to write geometry below Z=0: it
translates a solid up in +Z so the exported STL has min Z == 0. A
koneikko drawn at Z=-5000 therefore came back tessellated at Z=0 and
every piece of equipment below the storey datum collapsed onto the
storey elevation. ``preprocessing._undo_stlout_z_shift`` reverses that
using each body's true world min Z read from the DXF via ezdxf.

The arithmetic + the ezdxf ACIS-decode path run as pure-Python unit
tests. The real accoreconsole round-trip is ``@pytest.mark.accoreconsole``
(skipped when AutoCAD's headless core is not installed).
"""

from __future__ import annotations

from pathlib import Path

import ezdxf
import pytest
from ezdxf.acis import api as acis_api
from ezdxf.render import MeshBuilder

from dxf2ifc.core.preprocessing import (
    AcisMeshData,
    _undo_stlout_z_shift,
    _world_min_z_by_handle,
    extract_acis_meshes,
    find_accoreconsole,
)


def _box_body(sx=600.0, sy=400.0, sz=300.0, oz=0.0):
    """An axis-aligned box ACIS body, min corner at (0, 0, oz)."""
    mb = MeshBuilder()
    c = [
        (0, 0, oz), (sx, 0, oz), (sx, sy, oz), (0, sy, oz),
        (0, 0, oz + sz), (sx, 0, oz + sz), (sx, sy, oz + sz), (0, sy, oz + sz),
    ]
    for f in [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1),
              (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]:
        mb.add_face([c[i] for i in f])
    return acis_api.body_from_mesh(mb)


# --- _undo_stlout_z_shift arithmetic -----------------------------------


def _flat_mesh(zmin: float) -> AcisMeshData:
    """A trivial 1-triangle mesh whose lowest vertex sits at ``zmin``."""
    return AcisMeshData(
        vertices=((0.0, 0.0, zmin), (1.0, 0.0, zmin), (0.0, 1.0, zmin + 10.0)),
        faces=((0, 1, 2),),
    )


def test_undo_shift_restores_negative_z():
    """STLOUT signature: STL min Z ~0, true world min Z negative."""
    mesh = _flat_mesh(0.0)  # STLOUT shifted it up to the datum
    out = _undo_stlout_z_shift("ABC", mesh, {"ABC": -5000.0})
    zs = [v[2] for v in out.vertices]
    assert min(zs) == -5000.0
    assert max(zs) == -4990.0  # 10 mm span preserved
    assert out.faces == mesh.faces


def test_undo_shift_leaves_positive_z_untouched():
    """A solid STLOUT never shifted (STL min Z well above 0) is identity —
    zero regression risk for normal above-datum geometry."""
    mesh = _flat_mesh(1000.0)
    out = _undo_stlout_z_shift("ABC", mesh, {"ABC": 1000.0})
    assert out is mesh


def test_undo_shift_noop_when_handle_absent():
    mesh = _flat_mesh(0.0)
    assert _undo_stlout_z_shift("ZZZ", mesh, {"ABC": -5000.0}) is mesh


def test_undo_shift_noop_when_geometry_genuinely_at_datum():
    """A body genuinely sitting at Z~0 must not be dragged anywhere."""
    mesh = _flat_mesh(0.0)
    assert _undo_stlout_z_shift("ABC", mesh, {"ABC": 0.0}) is mesh


# --- _world_min_z_by_handle (ezdxf ACIS decode, no accoreconsole) -------


@pytest.mark.parametrize("dxfversion", ["R2010", "R2018"])
def test_world_min_z_raw_solid(tmp_path: Path, dxfversion: str):
    """A raw modelspace 3DSOLID at world Z=-5000 reports min Z=-5000,
    decoded from both SAT (R2010) and SAB (R2018) ACIS encodings."""
    doc = ezdxf.new(dxfversion)
    doc.layers.add(name="KYL-TIKASHYLLY")
    solid = doc.modelspace().add_3dsolid(dxfattribs={"layer": "KYL-TIKASHYLLY"})
    acis_api.export_dxf(solid, [_box_body(oz=-5000.0)])
    handle = solid.dxf.handle.upper()
    p = tmp_path / "raw.dxf"
    doc.saveas(str(p))

    world_min_z = _world_min_z_by_handle(ezdxf.readfile(str(p)))
    assert handle in world_min_z
    assert abs(world_min_z[handle] - (-5000.0)) < 1.0


@pytest.mark.parametrize("dxfversion", ["R2010", "R2018"])
def test_world_min_z_insert_carries_block_solid(tmp_path: Path, dxfversion: str):
    """A 3DSOLID sealed in a block, INSERTed at Z=-5000, reports the
    INSERT handle's world min Z as -5000 — the block transform is applied."""
    doc = ezdxf.new(dxfversion)
    doc.layers.add(name="KYL-TIKASHYLLY")
    blk = doc.blocks.new(name="KONEIKKO")
    bsolid = blk.add_3dsolid(dxfattribs={"layer": "KYL-TIKASHYLLY"})
    acis_api.export_dxf(bsolid, [_box_body(oz=0.0)])
    ins = doc.modelspace().add_blockref(
        "KONEIKKO", (5000.0, 4000.0, -5000.0),
        dxfattribs={"layer": "KYL-TIKASHYLLY"},
    )
    handle = ins.dxf.handle.upper()
    p = tmp_path / "block.dxf"
    doc.saveas(str(p))

    world_min_z = _world_min_z_by_handle(ezdxf.readfile(str(p)))
    assert handle in world_min_z
    assert abs(world_min_z[handle] - (-5000.0)) < 1.0


# --- accoreconsole round-trip ------------------------------------------


@pytest.mark.accoreconsole
def test_extract_acis_meshes_restores_negative_z(tmp_path: Path):
    """End-to-end: a 3DSOLID block INSERTed at Z=-5000 must come back from
    accoreconsole+STLOUT at its true world Z, not shifted onto the datum."""
    if find_accoreconsole() is None:
        pytest.skip("accoreconsole.exe not found")

    doc = ezdxf.new("R2018")
    doc.layers.add(name="KYL-TIKASHYLLY")
    blk = doc.blocks.new(name="KONEIKKO")
    bsolid = blk.add_3dsolid(dxfattribs={"layer": "KYL-TIKASHYLLY"})
    acis_api.export_dxf(bsolid, [_box_body(oz=0.0)])
    doc.modelspace().add_blockref(
        "KONEIKKO", (5000.0, 4000.0, -5000.0),
        dxfattribs={"layer": "KYL-TIKASHYLLY"},
    )
    p = tmp_path / "koneikko_negz.dxf"
    doc.saveas(str(p))

    meshes = extract_acis_meshes(p)
    assert meshes, "STLOUT produced no meshes"
    mesh = next(iter(meshes.values()))
    zs = [v[2] for v in mesh.vertices]
    # Without the correction STLOUT returns z 0..300; with it, the true
    # world placement (-5000..-4700) is restored.
    assert abs(min(zs) - (-5000.0)) < 2.0, f"min Z not restored: {min(zs)}"
    assert abs(max(zs) - (-4700.0)) < 2.0, f"max Z not restored: {max(zs)}"
