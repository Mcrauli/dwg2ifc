"""Convert DXF geometry into IFC geometry parameters.

Plan A: 2D line -> WallExtrusion (length, thickness, height, rotation, anchor).
Plan B adds polyline -> slab, 3DSOLID pass-through, block placement.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from dxf2ifc.core.types import LineGeometry, Point3D, PolygonGeometry


@dataclass(frozen=True)
class WallExtrusion:
    """Parameters sufficient to create an IfcWall with IfcExtrudedAreaSolid.

    - anchor: start point of the wall centreline (XY of bottom)
    - angle_rad: rotation around Z from world +X to the wall's length axis
    - length_mm / thickness_mm / height_mm: wall dimensions
    """

    anchor: Point3D
    angle_rad: float
    length_mm: float
    thickness_mm: float
    height_mm: float


def line_to_wall_extrusion(
    line: LineGeometry, *, thickness_mm: float, height_mm: float
) -> WallExtrusion:
    """Treat the line as the wall's centreline at the given thickness and height."""
    dx = line.end.x - line.start.x
    dy = line.end.y - line.start.y
    length = math.hypot(dx, dy)
    angle = math.atan2(dy, dx)
    return WallExtrusion(
        anchor=line.start,
        angle_rad=angle,
        length_mm=length,
        thickness_mm=thickness_mm,
        height_mm=height_mm,
    )


@dataclass(frozen=True)
class SlabExtrusion:
    """Parameters sufficient to create an IfcSlab with IfcExtrudedAreaSolid.

    - outline_xy: ordered (x, y) tuples describing the slab outline in mm
    - base_z: bottom elevation in mm
    - thickness_mm: extrusion depth (downwards) in mm
    """

    outline_xy: tuple[tuple[float, float], ...]
    base_z: float
    thickness_mm: float


def polygon_to_slab_extrusion(
    polygon: PolygonGeometry, *, thickness_mm: float
) -> SlabExtrusion:
    """Convert a closed PolygonGeometry into a SlabExtrusion.

    The slab outline is the polygon vertices projected to XY. The slab's
    base elevation is taken from the first vertex's Z. Open polygons are
    rejected because they cannot bound a slab face.
    """
    if not polygon.closed:
        raise ValueError("polygon_to_slab_extrusion requires a closed polygon")
    outline = tuple((v.x, v.y) for v in polygon.vertices)
    base_z = polygon.vertices[0].z if polygon.vertices else 0.0
    return SlabExtrusion(outline_xy=outline, base_z=base_z, thickness_mm=thickness_mm)
