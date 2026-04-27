"""Convert DXF geometry into IFC geometry parameters.

Plan A: 2D line -> WallExtrusion (length, thickness, height, rotation, anchor).
Plan B adds polyline -> slab, 3DSOLID pass-through, block placement.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from dxf2ifc.core.types import LineGeometry, Point3D


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
