"""Convert DXF geometry into IFC geometry parameters.

Plan A: 2D line -> WallExtrusion (length, thickness, height, rotation, anchor).
Plan B adds polyline -> slab, 3DSOLID pass-through, block placement.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from dxf2ifc.core.types import (
    BlockInstance,
    LineGeometry,
    MeshGeometry,
    Point3D,
    PolygonGeometry,
)


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


def polygon_to_slab_extrusion(polygon: PolygonGeometry, *, thickness_mm: float) -> SlabExtrusion:
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


@dataclass(frozen=True)
class DoorBoxExtrusion:
    """Parameters sufficient to create an IfcDoor as a parametric box.

    - anchor: insertion point of the door block (XY of bottom edge)
    - angle_rad: rotation around Z (door's width axis) from world +X
    - width_mm: door leaf width along the local X axis
    - height_mm: overall door height along Z
    - depth_mm: leaf thickness along the local Y axis (frame depth)
    """

    anchor: Point3D
    angle_rad: float
    width_mm: float
    height_mm: float
    depth_mm: float


def door_block_to_box(
    block: BlockInstance, *, width_mm: float, height_mm: float, depth_mm: float
) -> DoorBoxExtrusion:
    """Convert a DXF INSERT placement into an IfcDoor box-extrusion."""
    return DoorBoxExtrusion(
        anchor=block.insertion_point,
        angle_rad=block.rotation_rad,
        width_mm=width_mm,
        height_mm=height_mm,
        depth_mm=depth_mm,
    )


@dataclass(frozen=True)
class PipeSegmentExtrusion:
    """Parameters sufficient to create an IfcPipeSegment as a swept disk.

    - anchor: start point of the pipe centreline
    - angle_rad: rotation around Z so that the local +X axis follows the pipe
    - length_mm: pipe length (distance from start to end)
    - diameter_mm: nominal outside diameter (DN-equivalent) of the pipe
    """

    anchor: Point3D
    angle_rad: float
    length_mm: float
    diameter_mm: float


@dataclass(frozen=True)
class FurnitureBoxExtrusion:
    """Parameters sufficient to create an IfcFurniture as a parametric box.

    Used for storage shelving (KYL-LEVYHYLLY / KYL-TIKASHYLLY) and similar
    block-defined fixtures where the DXF block's exact geometry is not
    available; downstream code renders a width × depth × height box.
    """

    anchor: Point3D
    angle_rad: float
    width_mm: float
    depth_mm: float
    height_mm: float


def block_to_furniture_box(
    block: BlockInstance, *, width_mm: float, depth_mm: float, height_mm: float
) -> FurnitureBoxExtrusion:
    """Convert a DXF INSERT placement into an IfcFurniture box-extrusion."""
    return FurnitureBoxExtrusion(
        anchor=block.insertion_point,
        angle_rad=block.rotation_rad,
        width_mm=width_mm,
        depth_mm=depth_mm,
        height_mm=height_mm,
    )


@dataclass(frozen=True)
class PanelExtrusion:
    """Parameters sufficient to create a flat panel as IfcBuildingElementProxy.

    Used for cold-room wall/ceiling panels (KYL-LEVY) and corner pieces
    (KYL-NURKKA): a closed polygon outline projected to XY, with a
    thickness extruded upwards.
    """

    outline_xy: tuple[tuple[float, float], ...]
    base_z: float
    thickness_mm: float


def panel_to_proxy_solid(polygon: PolygonGeometry, *, thickness_mm: float) -> PanelExtrusion:
    """Convert a closed PolygonGeometry into a PanelExtrusion.

    The panel base elevation is taken from the first vertex's Z. Open
    polygons are rejected because a panel must bound a closed face.
    """
    if not polygon.closed:
        raise ValueError("panel_to_proxy_solid requires a closed polygon")
    outline = tuple((v.x, v.y) for v in polygon.vertices)
    base_z = polygon.vertices[0].z if polygon.vertices else 0.0
    return PanelExtrusion(outline_xy=outline, base_z=base_z, thickness_mm=thickness_mm)


@dataclass(frozen=True)
class CableCarrierSegmentExtrusion:
    """Parameters sufficient to create an IfcCableCarrierSegment as a tray.

    - anchor: start point of the tray centreline
    - angle_rad: rotation around Z so local +X follows the tray
    - length_mm: tray length
    - width_mm: tray internal width
    - height_mm: tray side-rail height
    """

    anchor: Point3D
    angle_rad: float
    length_mm: float
    width_mm: float
    height_mm: float


def line_to_cable_carrier(
    line: LineGeometry, *, width_mm: float, height_mm: float
) -> CableCarrierSegmentExtrusion:
    """Treat the line as a cable tray centreline at the given cross-section."""
    dx = line.end.x - line.start.x
    dy = line.end.y - line.start.y
    length = math.hypot(dx, dy)
    angle = math.atan2(dy, dx)
    return CableCarrierSegmentExtrusion(
        anchor=line.start,
        angle_rad=angle,
        length_mm=length,
        width_mm=width_mm,
        height_mm=height_mm,
    )


def line_to_pipe_segment(line: LineGeometry, *, diameter_mm: float) -> PipeSegmentExtrusion:
    """Treat the line as the pipe centreline and use ``diameter_mm`` for the section."""
    dx = line.end.x - line.start.x
    dy = line.end.y - line.start.y
    length = math.hypot(dx, dy)
    angle = math.atan2(dy, dx)
    return PipeSegmentExtrusion(
        anchor=line.start,
        angle_rad=angle,
        length_mm=length,
        diameter_mm=diameter_mm,
    )


@dataclass(frozen=True)
class GeometryExtents:
    """World-space bounding-box derivatives consumed by Finnish PSet writers.

    All values are in millimetres. ``top_z`` / ``bottom_z`` / ``install_z``
    feed the ``FI_Asennus`` elevation properties; ``korkeus`` / ``leveys``
    / ``syvyys`` feed ``FI_Geometria`` dimension properties (``None``
    means "unknown — skip the property line").
    """

    top_z: float
    bottom_z: float
    install_z: float
    korkeus: float | None = None
    leveys: float | None = None
    syvyys: float | None = None


def extents_from_geometry(
    geometry,
    *,
    height_mm: float | None = None,
    thickness_mm: float | None = None,
    width_mm: float | None = None,
    depth_mm: float | None = None,
) -> GeometryExtents:
    """Compute world-space extents for any of the supported geometry kinds.

    The caller passes the IFC builder's chosen extrusion dimensions
    (height, thickness, width, depth) so the result reflects the
    placed product, not just the raw 2D source. For mesh geometry the
    bbox is read directly from the vertex pool; profile defaults are
    used as fallbacks for the convention "the layer rule says this
    layer's products are 2.7 m tall" etc.
    """
    if isinstance(geometry, LineGeometry):
        bottom = min(geometry.start.z, geometry.end.z)
        top = bottom + (height_mm or 0.0)
        length = math.hypot(
            geometry.end.x - geometry.start.x, geometry.end.y - geometry.start.y
        )
        return GeometryExtents(
            top_z=top,
            bottom_z=bottom,
            install_z=bottom,
            korkeus=height_mm,
            leveys=thickness_mm if thickness_mm is not None else width_mm,
            syvyys=length if length > 0 else None,
        )

    if isinstance(geometry, PolygonGeometry):
        zs = [v.z for v in geometry.vertices]
        xs = [v.x for v in geometry.vertices]
        ys = [v.y for v in geometry.vertices]
        if not zs:
            return GeometryExtents(top_z=0.0, bottom_z=0.0, install_z=0.0)
        # Slabs are placed at the polygon's elevation as the TOP face,
        # extruded downward by thickness_mm.
        top = max(zs)
        bottom = top - (thickness_mm or 0.0)
        return GeometryExtents(
            top_z=top,
            bottom_z=bottom,
            install_z=top,
            korkeus=thickness_mm,
            leveys=(max(xs) - min(xs)) if xs else None,
            syvyys=(max(ys) - min(ys)) if ys else None,
        )

    if isinstance(geometry, BlockInstance):
        bottom = geometry.insertion_point.z
        top = bottom + (height_mm or 0.0)
        return GeometryExtents(
            top_z=top,
            bottom_z=bottom,
            install_z=bottom,
            korkeus=height_mm,
            leveys=(width_mm * geometry.scale_x) if width_mm is not None else None,
            syvyys=(depth_mm * geometry.scale_y) if depth_mm is not None else None,
        )

    if isinstance(geometry, MeshGeometry):
        if not geometry.vertices:
            return GeometryExtents(top_z=0.0, bottom_z=0.0, install_z=0.0)
        xs = [v.x for v in geometry.vertices]
        ys = [v.y for v in geometry.vertices]
        zs = [v.z for v in geometry.vertices]
        return GeometryExtents(
            top_z=max(zs),
            bottom_z=min(zs),
            install_z=min(zs),
            korkeus=max(zs) - min(zs),
            leveys=max(xs) - min(xs),
            syvyys=max(ys) - min(ys),
        )

    # Unknown geometry — skip elevation/dimensions, never crash.
    return GeometryExtents(top_z=0.0, bottom_z=0.0, install_z=0.0)
