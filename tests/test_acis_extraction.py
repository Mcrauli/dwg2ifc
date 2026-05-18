"""Tests for the accoreconsole+STLOUT ACIS extraction path.

The actual subprocess invocation is exercised under
``@pytest.mark.accoreconsole`` (skipped when AutoCAD is not installed).
The STL parser, the dxf_reader integration and the priority filter are
verified in pure-Python unit tests with synthetic fixtures.
"""

from __future__ import annotations

import math
import struct
from pathlib import Path

import ezdxf
import pytest

from dwg2ifc.core.dxf_reader import read_dxf
from dwg2ifc.core.preprocessing import (
    AcisMeshData,
    _parse_stl,
    _parse_stl_ascii,
    _parse_stl_binary,
    dxf_contains_acis_bodies,
    extract_acis_meshes,
    find_accoreconsole,
)
from dwg2ifc.core.types import MeshGeometry


# --- STL parser ---------------------------------------------------------


def _make_binary_stl(triangles: list[tuple[tuple[float, float, float], ...]]) -> bytes:
    header = b"\x00" * 80
    body = struct.pack("<I", len(triangles))
    for tri in triangles:
        # Normal (zeros — not used by our parser)
        body += struct.pack("<3f", 0.0, 0.0, 0.0)
        for v in tri:
            body += struct.pack("<3f", *v)
        body += struct.pack("<H", 0)  # attribute byte count
    return header + body


def test_parse_stl_binary_single_triangle(tmp_path: Path):
    raw = _make_binary_stl([
        ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
    ])
    stl = tmp_path / "single.stl"
    stl.write_bytes(raw)
    mesh = _parse_stl(stl)
    assert len(mesh.vertices) == 3
    assert len(mesh.faces) == 1
    assert mesh.faces[0] == (0, 1, 2)


def test_parse_stl_binary_dedups_shared_vertices(tmp_path: Path):
    # Two triangles sharing edge (0,0,0)-(1,0,0) — 4 unique vertices, 2 faces
    raw = _make_binary_stl([
        ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
    ])
    stl = tmp_path / "shared.stl"
    stl.write_bytes(raw)
    mesh = _parse_stl_binary(stl.read_bytes())
    assert len(mesh.vertices) == 4
    assert len(mesh.faces) == 2


def test_parse_stl_binary_skips_degenerate_triangle(tmp_path: Path):
    raw = _make_binary_stl([
        ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (1.0, 0.0, 0.0)),  # degenerate
        ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
    ])
    mesh = _parse_stl_binary(raw)
    assert len(mesh.faces) == 1


def test_parse_stl_ascii():
    text = (
        "solid test\n"
        "  facet normal 0 0 1\n"
        "    outer loop\n"
        "      vertex 0 0 0\n"
        "      vertex 1 0 0\n"
        "      vertex 0 1 0\n"
        "    endloop\n"
        "  endfacet\n"
        "endsolid test\n"
    )
    mesh = _parse_stl_ascii(text)
    assert len(mesh.vertices) == 3
    assert mesh.faces == ((0, 1, 2),)


def test_parse_stl_too_small_returns_empty(tmp_path: Path):
    stl = tmp_path / "tiny.stl"
    stl.write_bytes(b"\x00" * 50)
    mesh = _parse_stl(stl)
    assert mesh.vertices == ()
    assert mesh.faces == ()


# --- dxf_reader 3DSOLID integration ------------------------------------


def _make_3dsolid_dxf(path: Path, layer: str = "KYL-TIKASHYLLY") -> str:
    """Create a tiny DXF carrying a single 3DSOLID body on ``layer``.

    Uses :func:`ezdxf.acis.body_from_mesh` + :func:`acis.export_dxf` to
    persist a real ACIS body that survives the save/readfile round-trip.
    The body is a 4-face tetrahedron — geometry irrelevant for the
    reader test, only the entity's presence and handle matter. Returns
    the saved entity's DXF handle (upper-case hex).
    """
    from ezdxf.acis import api as acis_api
    from ezdxf.render import MeshBuilder

    doc = ezdxf.new("R2018")
    doc.layers.add(name=layer)
    msp = doc.modelspace()
    solid = msp.add_3dsolid(dxfattribs={"layer": layer})
    mb = MeshBuilder()
    mb.add_face([(0, 0, 0), (1, 0, 0), (0, 1, 0)])
    mb.add_face([(0, 0, 0), (1, 0, 0), (0, 0, 1)])
    mb.add_face([(1, 0, 0), (0, 1, 0), (0, 0, 1)])
    mb.add_face([(0, 0, 0), (0, 1, 0), (0, 0, 1)])
    acis_api.export_dxf(solid, [acis_api.body_from_mesh(mb)])
    handle = solid.dxf.handle
    doc.saveas(str(path))
    return handle


def test_read_dxf_yields_mesh_geometry_for_3dsolid_with_supplied_mesh(tmp_path: Path):
    dxf = tmp_path / "solid.dxf"
    handle = _make_3dsolid_dxf(dxf)

    mesh = AcisMeshData(
        vertices=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        faces=((0, 1, 2), (0, 1, 3), (1, 2, 3), (0, 2, 3)),
    )
    records = read_dxf(dxf, acis_meshes={handle.upper(): mesh})

    assert len(records) == 1
    rec = records[0]
    assert rec.dxf_type == "3DSOLID"
    assert rec.layer == "KYL-TIKASHYLLY"
    assert isinstance(rec.geometry, MeshGeometry)
    assert len(rec.geometry.vertices) == 4
    assert len(rec.geometry.faces) == 4


def test_read_dxf_drops_3dsolid_when_no_mesh_supplied(tmp_path: Path):
    dxf = tmp_path / "solid_no_mesh.dxf"
    _make_3dsolid_dxf(dxf)

    records = read_dxf(dxf)  # default acis_meshes is None
    assert records == []


def test_read_dxf_priority_filter_drops_lwpolyline_when_3dsolid_meshed(tmp_path: Path):
    """KYL-LEVYHYLLY blocks emit BOTH a 2D LWPOLYLINE outline and a 3DSOLID
    body on the same layer. Without the priority filter we'd publish the
    shelf twice; with it, the faceted mesh wins and the polyline is dropped."""
    dxf = tmp_path / "shelf.dxf"
    layer = "KYL-LEVYHYLLY"
    doc = ezdxf.new("R2018")
    doc.layers.add(name=layer)
    msp = doc.modelspace()
    from ezdxf.acis import api as acis_api
    from ezdxf.render import MeshBuilder

    msp.add_lwpolyline(
        [(0.0, 0.0), (1000.0, 0.0), (1000.0, 200.0), (0.0, 200.0)],
        close=True,
        dxfattribs={"layer": layer},
    )
    solid = msp.add_3dsolid(dxfattribs={"layer": layer})
    mb = MeshBuilder()
    mb.add_face([(0, 0, 0), (1, 0, 0), (0, 1, 0)])
    mb.add_face([(0, 0, 0), (1, 0, 0), (0, 0, 1)])
    mb.add_face([(1, 0, 0), (0, 1, 0), (0, 0, 1)])
    mb.add_face([(0, 0, 0), (0, 1, 0), (0, 0, 1)])
    acis_api.export_dxf(solid, [acis_api.body_from_mesh(mb)])
    handle = solid.dxf.handle
    doc.saveas(str(dxf))

    mesh = AcisMeshData(
        vertices=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        faces=((0, 1, 2),),
    )
    records = read_dxf(dxf, acis_meshes={handle.upper(): mesh})
    # Only the 3DSOLID-derived MeshGeometry should remain.
    assert len(records) == 1
    assert records[0].dxf_type == "3DSOLID"


def test_read_dxf_priority_filter_keeps_lwpolyline_when_3dsolid_unmeshed(tmp_path: Path):
    """If accoreconsole was unavailable and no mesh got extracted, the 2D
    fallback (LWPOLYLINE → extruded) is still emitted instead of nothing."""
    dxf = tmp_path / "shelf_fallback.dxf"
    layer = "KYL-LEVYHYLLY"
    doc = ezdxf.new("R2018")
    doc.layers.add(name=layer)
    msp = doc.modelspace()
    from ezdxf.acis import api as acis_api
    from ezdxf.render import MeshBuilder

    msp.add_lwpolyline(
        [(0.0, 0.0), (1000.0, 0.0), (1000.0, 200.0), (0.0, 200.0)],
        close=True,
        dxfattribs={"layer": layer},
    )
    solid = msp.add_3dsolid(dxfattribs={"layer": layer})
    mb = MeshBuilder()
    mb.add_face([(0, 0, 0), (1, 0, 0), (0, 1, 0)])
    mb.add_face([(0, 0, 0), (1, 0, 0), (0, 0, 1)])
    mb.add_face([(1, 0, 0), (0, 1, 0), (0, 0, 1)])
    mb.add_face([(0, 0, 0), (0, 1, 0), (0, 0, 1)])
    acis_api.export_dxf(solid, [acis_api.body_from_mesh(mb)])
    doc.saveas(str(dxf))

    records = read_dxf(dxf, acis_meshes={})  # extraction produced nothing
    # 3DSOLID gets dropped (no mesh), but the LWPOLYLINE survives.
    assert len(records) == 1
    assert records[0].dxf_type == "LWPOLYLINE"


# --- Extraction driver behaviours ---------------------------------------


def test_extract_acis_meshes_returns_empty_when_dxf_has_no_acis(tmp_path: Path):
    dxf = tmp_path / "lines_only.dxf"
    doc = ezdxf.new("R2018")
    doc.modelspace().add_line((0, 0, 0), (1, 0, 0))
    doc.saveas(str(dxf))

    # No accoreconsole call at all — the early-exit path returns {} and
    # doesn't even attempt to find the binary.
    assert extract_acis_meshes(dxf) == {}


def test_lisp_phase2_under_accoreconsole_line_buffer():
    """accoreconsole's .scr line buffer hard-caps at 2048 chars per Enter-
    terminated input line — past that the parser hangs in a multi-paren
    prompt forever. Phase 2 grows when skip_magicad is enabled (extra
    wildcard patterns substitute into the wcmatch skip list); verify it
    stays safely under the cap."""
    from dwg2ifc.core.preprocessing import _LISP_PHASE2

    p2_magicad = _LISP_PHASE2.format(
        skip_blocks="*POSITIO*,MAGI*,*MAGICAD*,MAG_*"
    )
    assert len(p2_magicad) < 2048


def test_lisp_phase2_skip_magicad_includes_all_magicad_patterns():
    """When skip_magicad is requested the wcmatch pattern must match the
    block-name conventions MagiCAD uses in DXF — MAGI* (native types),
    *MAGICAD* (vendor block libraries), MAG_* (legacy prefix)."""
    from dwg2ifc.core.preprocessing import _LISP_PHASE2

    p2_magicad = _LISP_PHASE2.format(
        skip_blocks="*POSITIO*,MAGI*,*MAGICAD*,MAG_*"
    )
    # The two occurrences must both carry the extended skip list.
    assert p2_magicad.count("*POSITIO*,MAGI*,*MAGICAD*,MAG_*") == 2


# --- worthlist literal (alpha32 Phase-2 EXPLODE skip) -------------------


def test_worthlist_literal_all_ascii_names_included():
    from dwg2ifc.core.preprocessing import _worthlist_literal

    lit = _worthlist_literal({"KONEIKKO", "VPUTKI-32", "F31HC325"})
    assert lit.startswith("'(") and lit.endswith(")")
    assert '"KONEIKKO"' in lit
    assert '"VPUTKI-32"' in lit
    assert '"F31HC325"' in lit
    assert lit.isascii()


def test_worthlist_literal_excludes_non_ascii_block_names():
    """Regression (alpha32 → alpha33): the worthlist literal carried
    Finnish block names (Höyrystin/Säädin) verbatim. The .scr is written
    UTF-8 but accoreconsole reads it in the ANSI codepage, and AutoLISP
    ``strcase`` does not fold ``ö → Ö`` the way Python ``str.upper()``
    does — so ``(member ...)`` never matched and Phase 2 silently skipped
    every Höyrystin INSERT, leaving evaporators with no tessellated mesh.
    Non-ASCII names must be left out of the literal entirely; Phase 2
    explodes them via its ``(not (asciip ...))`` escape instead."""
    from dwg2ifc.core.preprocessing import _worthlist_literal

    lit = _worthlist_literal({"HÖYRYSTIN 1-PUH", "KONEIKKO", "SÄÄDINKESKUS"})
    assert lit.isascii(), f"worthlist literal must be ASCII-only, got {lit!r}"
    assert "HÖYRYSTIN 1-PUH" not in lit
    assert "SÄÄDINKESKUS" not in lit
    assert '"KONEIKKO"' in lit


def test_worthlist_literal_nil_when_no_safe_names():
    from dwg2ifc.core.preprocessing import _worthlist_literal

    assert _worthlist_literal(set()) == "nil"
    # A drawing whose only ACIS-bearing blocks are Finnish-named falls
    # back to "explode everything" rather than emitting a useless literal.
    assert _worthlist_literal({"HÖYRYSTIN 1-PUH"}) == "nil"


def test_worthlist_literal_excludes_names_breaking_lisp_string():
    from dwg2ifc.core.preprocessing import _worthlist_literal

    lit = _worthlist_literal({'BAD"NAME', "GOODNAME"})
    assert '"GOODNAME"' in lit
    assert 'BAD"NAME' not in lit


def test_worthlist_literal_nil_when_too_long():
    from dwg2ifc.core.preprocessing import _worthlist_literal

    many = {f"BLOCK_NAME_NUMBER_{i:04d}" for i in range(200)}
    assert _worthlist_literal(many) == "nil"


def test_lisp_phase2_explodes_non_ascii_named_blocks():
    """Phase 2 must always EXPLODE blocks whose name is non-ASCII: they
    cannot be carried in the worthlist literal, so the guard has to fall
    through to ``(not (asciip ...))``. Both the top-level and the nested
    INSERT guard need it, or evaporators sealed inside Finnish-named
    container blocks would be skipped."""
    from dwg2ifc.core.preprocessing import _LISP_PHASE2, _LISP_SETUP

    assert "(defun asciip" in _LISP_SETUP
    p2 = _LISP_PHASE2.format(skip_blocks="*POSITIO*,MAGI*,*MAGICAD*,MAG_*")
    assert "(not (asciip bname))" in p2
    assert "(not (asciip sbname))" in p2
    # The asciip escape must not push Phase 2 over the .scr line-buffer cap.
    assert len(p2) < 2048


def test_dxf_contains_acis_bodies_true_for_3dsolid(tmp_path: Path):
    dxf = tmp_path / "solid.dxf"
    _make_3dsolid_dxf(dxf)
    assert dxf_contains_acis_bodies(dxf) is True


def test_dxf_contains_acis_bodies_false_for_line_only(tmp_path: Path):
    dxf = tmp_path / "lines.dxf"
    doc = ezdxf.new("R2018")
    doc.modelspace().add_line((0, 0, 0), (1, 0, 0))
    doc.saveas(str(dxf))
    assert dxf_contains_acis_bodies(dxf) is False


@pytest.mark.accoreconsole
def test_extract_acis_meshes_round_trip(tmp_path: Path):
    """End-to-end: drive accoreconsole on a DXF that carries one 3DSOLID,
    confirm a mesh comes back. Skipped when accoreconsole is not installed."""
    if find_accoreconsole() is None:
        pytest.skip("accoreconsole.exe not found")

    # We need a real ACIS body for STLOUT to triangulate. Easiest source
    # is the user's actual fixtures DXF if present; otherwise skip.
    candidate = Path(
        r"C:\Users\LauriRekola\OneDrive - RADIKA OY\Tiedostot\4001_1krs.dxf"
    )
    if not candidate.is_file():
        pytest.skip("no real ACIS-bearing DXF available for round-trip test")

    meshes = extract_acis_meshes(candidate)
    # We don't pin the count (it depends on the user's drawing) — just that
    # at least one mesh comes through and contains real geometry.
    assert len(meshes) > 0
    sample = next(iter(meshes.values()))
    assert len(sample.vertices) >= 3
    assert len(sample.faces) >= 1
