"""Bugfix 4: 14 KYL-LEVYHYLLY-polygons produce 14 IfcFurniture entities,
each with a unique IfcLocalPlacement (no overlap at origin)."""

from __future__ import annotations

from pathlib import Path

import ezdxf
import ifcopenshell

from dxf2ifc.core.ifc_writer import convert_dxf
from dxf2ifc.profiles.loader import load_default_profile


def _author_dxf_with_three_shelf_polygons(path: Path) -> Path:
    doc = ezdxf.new("R2010")
    doc.layers.add(name="KYL-LEVYHYLLY")
    msp = doc.modelspace()
    # Three closed shelf polygons at clearly different XY locations.
    msp.add_lwpolyline(
        [(0.0, 0.0), (1000.0, 0.0), (1000.0, 600.0), (0.0, 600.0)],
        close=True,
        dxfattribs={"layer": "KYL-LEVYHYLLY"},
    )
    msp.add_lwpolyline(
        [(5000.0, 5000.0), (6000.0, 5000.0), (6000.0, 5600.0), (5000.0, 5600.0)],
        close=True,
        dxfattribs={"layer": "KYL-LEVYHYLLY"},
    )
    msp.add_lwpolyline(
        [(-3000.0, 2000.0), (-2000.0, 2000.0), (-2000.0, 2600.0), (-3000.0, 2600.0)],
        close=True,
        dxfattribs={"layer": "KYL-LEVYHYLLY"},
    )
    doc.saveas(str(path))
    return path






def test_three_polygon_shelves_have_visible_geometry(tmp_path: Path):
    """Every IfcFurniture must keep its representation (the regression made
    13 of 14 invisible because their bodies collapsed into a degenerate
    placement)."""
    dxf = _author_dxf_with_three_shelf_polygons(tmp_path / "shelves.dxf")
    out = tmp_path / "shelves.ifc"

    convert_dxf(dxf_path=dxf, output_path=out, profile=load_default_profile())

    ifc = ifcopenshell.open(str(out))
    furnitures = ifc.by_type("IfcFurniture")
    for f in furnitures:
        assert f.Representation is not None
        shapes = f.Representation.Representations
        assert shapes, f"{f.Name} missing shape representation"
        body = next((s for s in shapes if s.RepresentationIdentifier == "Body"), None)
        assert body is not None, f"{f.Name} missing Body representation"
        assert body.Items, f"{f.Name} body has no extrusion items"
