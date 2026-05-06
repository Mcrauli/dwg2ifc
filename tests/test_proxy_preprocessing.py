"""MagiCAD/ACAD_PROXY_ENTITY preprocessing pipeline.

Covers the public surface of ``dxf2ifc.core.proxy_preprocessing``
without requiring an actual accoreconsole / Object Enabler install:

- :func:`bbox_to_cuboid_mesh` produces a topologically valid 12-tri
  cuboid that any IFC mesh-builder can consume.
- :func:`extract_proxy_geometry` short-circuits gracefully on:
  * non-existent input file
  * DXFs with no proxies
  * monkeypatched ``find_accoreconsole`` returning None.
- The artifact-manifest jsonl format round-trips cleanly so the
  manifest can be inspected (or future-extended into a saved file
  when end-to-end debugging needs persistence).

The accoreconsole-EXPLODE round-trip itself is gated behind a
``pytest.mark.requires_accoreconsole`` marker (skipped when the
binary is missing), exercised against Lauri's local
``magicad_1krs.dxf``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dxf2ifc.core.proxy_preprocessing import (
    ProxyArtifact,
    ProxyArtifacts,
    artifacts_from_jsonl,
    artifacts_to_jsonl,
    bbox_to_cuboid_mesh,
    detect_object_enabler,
    extract_proxy_geometry,
)


# ---------------------------------------------------------------------------
# bbox → cuboid mesh
# ---------------------------------------------------------------------------


def test_bbox_to_cuboid_mesh_yields_8_vertices_12_faces():
    mesh = bbox_to_cuboid_mesh(((0.0, 0.0, 0.0), (1000.0, 500.0, 200.0)))
    assert len(mesh.vertices) == 8
    assert len(mesh.faces) == 12
    # All vertices fall on the bbox corners
    xs = {v[0] for v in mesh.vertices}
    ys = {v[1] for v in mesh.vertices}
    zs = {v[2] for v in mesh.vertices}
    assert xs == {0.0, 1000.0}
    assert ys == {0.0, 500.0}
    assert zs == {0.0, 200.0}
    # Every triangle has exactly 3 distinct indices in [0,8)
    for face in mesh.faces:
        assert len(face) == 3
        assert len(set(face)) == 3
        assert all(0 <= idx < 8 for idx in face)


def test_bbox_to_cuboid_mesh_handles_negative_extents():
    """Below-grade bounds (basement equipment) must still tessellate."""
    mesh = bbox_to_cuboid_mesh(((-500.0, -300.0, -1500.0), (500.0, 300.0, 0.0)))
    assert len(mesh.vertices) == 8
    assert len(mesh.faces) == 12


# ---------------------------------------------------------------------------
# extract_proxy_geometry — short-circuits
# ---------------------------------------------------------------------------


def test_extract_proxy_geometry_missing_file_returns_empty(tmp_path: Path):
    result = extract_proxy_geometry(tmp_path / "does_not_exist.dxf")
    assert isinstance(result, ProxyArtifacts)
    assert result.artifacts == {}
    assert result.meshes == {}


def test_extract_proxy_geometry_no_proxies_returns_empty(tmp_path: Path):
    """A plain LINE-only DXF must return an empty bundle without
    invoking accoreconsole. Non-MagiCAD workflows pay zero cost."""
    import ezdxf

    dxf = tmp_path / "simple.dxf"
    doc = ezdxf.new("R2010")
    doc.modelspace().add_line((0, 0, 0), (1000, 0, 0))
    doc.saveas(str(dxf))

    result = extract_proxy_geometry(dxf)
    assert result.artifacts == {}
    assert result.meshes == {}
    assert result.object_enabler_detected in (True, False)


def test_extract_proxy_geometry_no_accoreconsole_falls_back_gracefully(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When accoreconsole is unavailable AND no proxies exist, the
    function still returns the empty bundle without raising."""
    import dxf2ifc.core.proxy_preprocessing as pp

    monkeypatch.setattr(pp, "find_accoreconsole", lambda: None)

    import ezdxf

    dxf = tmp_path / "simple.dxf"
    doc = ezdxf.new("R2010")
    doc.modelspace().add_line((0, 0, 0), (1000, 0, 0))
    doc.saveas(str(dxf))

    result = extract_proxy_geometry(dxf)
    assert result.artifacts == {}


# ---------------------------------------------------------------------------
# Manifest jsonl round-trip
# ---------------------------------------------------------------------------


def test_artifact_jsonl_roundtrip():
    arts = {
        "DEAD": ProxyArtifact(
            original_handle="DEAD",
            original_layer="KYL-JV1",
            stl_file=None,
            bbox=((0.0, 0.0, 0.0), (1000.0, 500.0, 200.0)),
            face_count=12,
            fallback_reason="no_object_enabler",
        ),
        "BEEF": ProxyArtifact(
            original_handle="BEEF",
            original_layer="MUUT_OSAT",
            stl_file=Path("/tmp/foo.stl"),
            bbox=None,
            face_count=420,
            fallback_reason=None,
        ),
    }
    text = artifacts_to_jsonl(arts)
    parsed = artifacts_from_jsonl(text)
    assert set(parsed) == set(arts)
    for h, a in arts.items():
        p = parsed[h]
        assert p.original_handle == a.original_handle
        assert p.original_layer == a.original_layer
        assert p.face_count == a.face_count
        assert p.fallback_reason == a.fallback_reason
        assert p.bbox == a.bbox


# ---------------------------------------------------------------------------
# Object Enabler detection
# ---------------------------------------------------------------------------


def test_detect_object_enabler_returns_bool():
    """Whatever the host's registry state, the function returns a
    plain bool — never raises, never returns ``None``."""
    result = detect_object_enabler()
    assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# End-to-end (gated)
# ---------------------------------------------------------------------------


@pytest.mark.requires_accoreconsole
def test_extract_proxy_geometry_lauri_magicad_dxf():
    """Round-trip on Lauri's reference MagiCAD DXF. Skipped in CI
    because it depends on a local file outside the repo."""
    from dxf2ifc.core.preprocessing import find_accoreconsole

    if find_accoreconsole() is None:
        pytest.skip("accoreconsole.exe not installed")
    fixture = Path(
        r"C:\Users\LauriRekola\Downloads\suunnittelutyokalut\magicad_1krs.dxf"
    )
    if not fixture.is_file():
        pytest.skip("Lauri's local MagiCAD DXF is not present")
    result = extract_proxy_geometry(fixture)
    # 145 proxies expected on this DXF
    assert len(result.artifacts) >= 100
