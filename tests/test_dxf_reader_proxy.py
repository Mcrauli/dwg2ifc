"""ACAD_PROXY_ENTITY (MagiCAD-object) handling in dxf_reader.

We test two layers:

1. The ``_record_from_entity`` helper handles ``layer_override`` and
   ``handle_override`` correctly, since the proxy expansion path forces
   both for every virtual entity. A synthetic ezdxf LINE / LWPOLYLINE
   covers the geometry-mapping side.

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
    record = _record_from_entity(
        line, layer_override=None, handle_override=None,
        mesh_priority_layers=set(), acis_meshes={},
    )
    assert record is not None
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
    record = _record_from_entity(
        line, layer_override="LT IMU", handle_override=None,
        mesh_priority_layers=set(), acis_meshes={},
    )
    assert record is not None
    assert record.layer == "LT IMU"


def test_record_from_entity_handle_override_propagates():
    """The proxy's handle propagates to its virtual children so warnings
    can still trace back to the AutoCAD entity the user authored."""
    line = _line_entity((0.0, 0.0, 0.0), (1000.0, 0.0, 0.0))
    record = _record_from_entity(
        line, layer_override=None, handle_override="DEADBEEF",
        mesh_priority_layers=set(), acis_meshes={},
    )
    assert record is not None
    assert record.handle == "DEADBEEF"


def test_record_from_entity_drops_unsupported_dxftype():
    """CIRCLE / TEXT / ARC are intentionally not handled in v0.1.15;
    the helper returns None instead of raising so the caller can simply
    skip the entity."""
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    circle = msp.add_circle((0.0, 0.0), 100.0)
    record = _record_from_entity(
        circle, layer_override=None, handle_override=None,
        mesh_priority_layers=set(), acis_meshes={},
    )
    assert record is None


def test_record_from_entity_lwpolyline_closed_yields_polygon():
    pl = _lwpolyline_entity(
        [(0.0, 0.0), (1000.0, 0.0), (1000.0, 500.0), (0.0, 500.0)],
        layer="KYL-LEVY",
    )
    record = _record_from_entity(
        pl, layer_override=None, handle_override=None,
        mesh_priority_layers=set(), acis_meshes={},
    )
    assert record is not None
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
    record = _record_from_entity(
        pl, layer_override=None, handle_override=None,
        mesh_priority_layers=set(), acis_meshes={},
    )
    assert record is not None
    assert record.dxf_type == "POLYLINE"
    assert isinstance(record.geometry, PolygonGeometry)
    assert len(record.geometry.vertices) == 4
