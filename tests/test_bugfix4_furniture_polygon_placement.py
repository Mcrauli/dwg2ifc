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


def test_three_polygon_shelves_produce_three_unique_placements(tmp_path: Path):
    dxf = _author_dxf_with_three_shelf_polygons(tmp_path / "shelves.dxf")
    out = tmp_path / "shelves.ifc"

    convert_dxf(dxf_path=dxf, output_path=out, profile=load_default_profile())

    ifc = ifcopenshell.open(str(out))
    furnitures = ifc.by_type("IfcFurniture")
    assert len(furnitures) == 3, f"expected 3 IfcFurniture, got {len(furnitures)}"

    coords = []
    for f in furnitures:
        placement = f.ObjectPlacement
        assert placement is not None
        loc = placement.RelativePlacement.Location
        coords.append(tuple(loc.Coordinates))

    # Each shelf must have its own world-space anchor (no collapse to origin).
    assert len(set(coords)) == 3, f"expected 3 unique placements, got {coords}"

    # And no shelf should be sitting at (0,0,0) AND duplicated — explicit guard
    # against the regression where 13/14 collapsed to origin.
    origin_count = sum(1 for c in coords if c == (0.0, 0.0, 0.0))
    assert origin_count <= 1


def test_lwpolyline_with_flipped_extrusion_reads_world_coords(tmp_path: Path):
    """AutoCAD often saves LWPOLYLINEs with extrusion=(0,0,-1) when the
    polyline was drawn after a UCS flip or imported from an xref. The
    polyline's get_points() then yields OCS coordinates that differ
    from world coordinates. dxf2ifc must convert to WCS so each shelf
    lands at its actual XY position."""
    doc = ezdxf.new("R2010")
    doc.layers.add(name="KYL-LEVYHYLLY")
    msp = doc.modelspace()
    # Two polygons with FLIPPED extrusion direction. In OCS they are at
    # different locations than in WCS.
    msp.add_lwpolyline(
        [(0.0, 0.0), (1000.0, 0.0), (1000.0, 600.0), (0.0, 600.0)],
        close=True,
        dxfattribs={"layer": "KYL-LEVYHYLLY", "extrusion": (0.0, 0.0, -1.0)},
    )
    msp.add_lwpolyline(
        [(5000.0, 5000.0), (6000.0, 5000.0), (6000.0, 5600.0), (5000.0, 5600.0)],
        close=True,
        dxfattribs={"layer": "KYL-LEVYHYLLY", "extrusion": (0.0, 0.0, -1.0)},
    )
    dxf_path = tmp_path / "flipped.dxf"
    doc.saveas(str(dxf_path))

    out = tmp_path / "flipped.ifc"
    convert_dxf(dxf_path=dxf_path, output_path=out, profile=load_default_profile())

    ifc = ifcopenshell.open(str(out))
    furnitures = ifc.by_type("IfcFurniture")
    assert len(furnitures) == 2

    coords = sorted(
        tuple(f.ObjectPlacement.RelativePlacement.Location.Coordinates)
        for f in furnitures
    )
    # Expected WCS anchors (bbox min) after OCS→WCS conversion. The
    # extrusion=(0,0,-1) flip mirrors X, so OCS x in [0..1000] becomes
    # WCS x in [-1000..0], and the bbox min lands at -1000 (or -6000 for
    # the second polygon).
    assert coords[0][0] == -6000.0, coords
    assert coords[1][0] == -1000.0, coords


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
