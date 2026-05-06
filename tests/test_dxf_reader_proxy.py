"""ACAD_PROXY_ENTITY (MagiCAD-object) handling in dxf_reader.

We test two layers:

1. The ``_record_from_entity`` helper handles ``layer_override`` and
   ``handle_override`` correctly, since the proxy expansion path forces
   both for every virtual entity. A synthetic ezdxf LINE / LWPOLYLINE
   covers the geometry-mapping side. The helper returns
   ``list[EntityRecord]`` (0/1/N records); open polylines fan out to
   one LineGeometry per consecutive vertex pair.

2. The full ``read_dxf`` pipeline routes proxy entities through
   ``__virtual_entities__()``. Constructing a real ACAD_PROXY_ENTITY
   with embedded graphics from scratch is painful — ezdxf does not ship
   an encoder for the proxy_graphic byte stream. We fall back to a
   minimal mock-style test that wires a known list of virtual entities
   onto the proxy via monkey-patching.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import ezdxf

from dxf2ifc.core.dxf_reader import _record_from_entity, read_dxf
from dxf2ifc.core.types import LineGeometry, PolygonGeometry


def _line_entity(start, end, layer="0"):
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    return msp.add_line(start, end, dxfattribs={"layer": layer})


def _lwpolyline_entity(points, layer="0", closed=True):
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    pl = msp.add_lwpolyline(points, dxfattribs={"layer": layer})
    pl.close(closed)
    return pl


def test_record_from_entity_passes_through_native_line():
    line = _line_entity((0.0, 0.0, 0.0), (1000.0, 0.0, 0.0), layer="LT IMU")
    records = _record_from_entity(
        line, layer_override=None, handle_override=None,
        mesh_priority_layers=set(), acis_meshes={},
    )
    assert len(records) == 1
    record = records[0]
    assert record.layer == "LT IMU"
    assert record.dxf_type == "LINE"
    assert isinstance(record.geometry, LineGeometry)
    assert record.geometry.start.x == 0.0
    assert record.geometry.end.x == 1000.0


def test_record_from_entity_layer_override_wins():
    """Proxy expansion must be able to force the virtual entity's layer
    onto the resulting record (so the profile mapper sees the proxy's
    authored layer, not the virtual primitive's default '0')."""
    line = _line_entity((0.0, 0.0, 0.0), (1000.0, 0.0, 0.0), layer="0")
    records = _record_from_entity(
        line, layer_override="LT IMU", handle_override=None,
        mesh_priority_layers=set(), acis_meshes={},
    )
    assert len(records) == 1
    assert records[0].layer == "LT IMU"


def test_record_from_entity_handle_override_propagates():
    """The proxy's handle propagates to its virtual children so warnings
    can still trace back to the AutoCAD entity the user authored."""
    line = _line_entity((0.0, 0.0, 0.0), (1000.0, 0.0, 0.0))
    records = _record_from_entity(
        line, layer_override=None, handle_override="DEADBEEF",
        mesh_priority_layers=set(), acis_meshes={},
    )
    assert len(records) == 1
    assert records[0].handle == "DEADBEEF"


def test_record_from_entity_drops_unsupported_dxftype():
    """CIRCLE / TEXT / ARC are intentionally not handled in v0.1.15;
    the helper returns an empty list instead of raising so the caller
    can simply skip the entity."""
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    circle = msp.add_circle((0.0, 0.0), 100.0)
    records = _record_from_entity(
        circle, layer_override=None, handle_override=None,
        mesh_priority_layers=set(), acis_meshes={},
    )
    assert records == []


def test_record_from_entity_lwpolyline_closed_yields_polygon():
    pl = _lwpolyline_entity(
        [(0.0, 0.0), (1000.0, 0.0), (1000.0, 500.0), (0.0, 500.0)],
        layer="KYL-LEVY",
    )
    records = _record_from_entity(
        pl, layer_override=None, handle_override=None,
        mesh_priority_layers=set(), acis_meshes={},
    )
    assert len(records) == 1
    record = records[0]
    assert record.dxf_type == "LWPOLYLINE"
    assert isinstance(record.geometry, PolygonGeometry)
    assert len(record.geometry.vertices) == 4


def test_record_from_entity_polyline_closed_yields_polygon():
    """ProxyGraphic streams emit POLYLINE for closed n-gons (older DXF
    flavour) instead of LWPOLYLINE — the helper handles both."""
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    pl = msp.add_polyline2d(
        [(0.0, 0.0), (1000.0, 0.0), (1000.0, 500.0), (0.0, 500.0)],
        close=True,
        dxfattribs={"layer": "MAG_PROXY"},
    )
    records = _record_from_entity(
        pl, layer_override=None, handle_override=None,
        mesh_priority_layers=set(), acis_meshes={},
    )
    assert len(records) == 1
    record = records[0]
    assert record.dxf_type == "POLYLINE"
    assert isinstance(record.geometry, PolygonGeometry)
    assert len(record.geometry.vertices) == 4


# ---------------------------------------------------------------------------
# Open polyline → LineGeometry segment fan-out (v0.1.19, MagiCAD-proxy fix)
# ---------------------------------------------------------------------------


def test_record_from_entity_open_lwpolyline_yields_line_segments():
    """A 4-vertex open LWPOLYLINE (e.g. a MagiCAD proxy pipe centreline
    with three bends) should fan out to 3 LineGeometry records — one per
    consecutive vertex pair — instead of being silently dropped as in
    v0.1.18."""
    pl = _lwpolyline_entity(
        [(0.0, 0.0), (1000.0, 0.0), (1000.0, 500.0), (2000.0, 500.0)],
        layer="KYL-JV1",
        closed=False,
    )
    records = _record_from_entity(
        pl, layer_override=None, handle_override=None,
        mesh_priority_layers=set(), acis_meshes={},
    )
    assert len(records) == 3
    assert all(r.dxf_type == "LWPOLYLINE" for r in records)
    assert all(isinstance(r.geometry, LineGeometry) for r in records)
    assert records[0].geometry.start.x == 0.0 and records[0].geometry.end.x == 1000.0
    assert records[1].geometry.start.y == 0.0 and records[1].geometry.end.y == 500.0
    assert records[2].geometry.start.x == 1000.0 and records[2].geometry.end.x == 2000.0


def test_record_from_entity_open_polyline_yields_line_segments():
    """ProxyGraphic streams may emit legacy POLYLINE (not LWPOLYLINE) for
    open paths. Same fan-out rule applies."""
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    pl = msp.add_polyline2d(
        [(0.0, 0.0), (1000.0, 0.0), (1000.0, 500.0)],
        close=False,
        dxfattribs={"layer": "MAG_PROXY"},
    )
    records = _record_from_entity(
        pl, layer_override=None, handle_override=None,
        mesh_priority_layers=set(), acis_meshes={},
    )
    assert len(records) == 2
    assert all(r.dxf_type == "POLYLINE" for r in records)
    assert all(isinstance(r.geometry, LineGeometry) for r in records)


def test_record_from_entity_open_polyline_propagates_handle_to_every_segment():
    """When a proxy has handle DEADBEEF and emits one open polyline of
    5 vertices via virtual_entities(), all 4 resulting LineGeometry
    records must carry the proxy's handle so warnings + Solibri's
    "select original entity" can trace each segment back."""
    pl = _lwpolyline_entity(
        [(0.0, 0.0), (100.0, 0.0), (200.0, 0.0), (300.0, 0.0), (400.0, 0.0)],
        layer="0",
        closed=False,
    )
    records = _record_from_entity(
        pl, layer_override="KYL-JV1", handle_override="DEADBEEF",
        mesh_priority_layers=set(), acis_meshes={},
    )
    assert len(records) == 4
    assert all(r.handle == "DEADBEEF" for r in records)
    assert all(r.layer == "KYL-JV1" for r in records)


def test_record_from_entity_single_vertex_open_polyline_drops_silently():
    """Degenerate 1-vertex polyline (no segments to emit) yields zero
    records — not an exception."""
    pl = _lwpolyline_entity([(0.0, 0.0)], layer="0", closed=False)
    records = _record_from_entity(
        pl, layer_override=None, handle_override=None,
        mesh_priority_layers=set(), acis_meshes={},
    )
    assert records == []
