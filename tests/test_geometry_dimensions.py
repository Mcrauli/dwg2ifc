"""Per-element-type bbox dimension tests for ifc_writer.add_* functions.

Bugfix 7: ensure that every add_*-function produces an IFC entity whose
world-space bounding box matches the input geometry/extra_props within
1 mm. The earlier tests checked only XDim/YDim/Depth on the swept area;
these tests also verify the placement origin so that we catch axis-swap
or anchor regressions per element type.
"""

from __future__ import annotations

import pytest

from dxf2ifc.core.ifc_writer import (
    add_building_element_proxy,
    add_cable_carrier_segment,
    add_cooling_equipment,
    add_door,
    add_furniture,
    add_pipe_segment,
    add_slab,
    add_wall,
    add_window,
    build_ifc_project_skeleton,
)
from dxf2ifc.core.types import (
    BlockInstance,
    LineGeometry,
    MappedEntity,
    Point3D,
    PolygonGeometry,
)


def _world_bbox_of_swept_solid(product) -> tuple[float, float, float, float, float, float]:
    """Return (xmin, ymin, zmin, xmax, ymax, zmax) for an axis-aligned
    rectangular extrusion. Assumes a single IfcExtrudedAreaSolid item with
    an IfcRectangleProfileDef profile and an upright (+Z) extrusion."""
    placement = product.ObjectPlacement
    rel = placement.RelativePlacement
    px, py, pz = rel.Location.Coordinates
    rep = product.Representation.Representations[0]
    extruded = rep.Items[0]
    profile = extruded.SweptArea
    cx, cy = profile.Position.Location.Coordinates
    half_x = profile.XDim / 2.0
    half_y = profile.YDim / 2.0
    depth = extruded.Depth
    direction = extruded.ExtrudedDirection.DirectionRatios
    dz = direction[2]
    z_low = pz + (depth * dz if dz < 0 else 0.0)
    z_high = pz + (depth * dz if dz > 0 else 0.0)
    return (
        px + cx - half_x,
        py + cy - half_y,
        z_low,
        px + cx + half_x,
        py + cy + half_y,
        z_high,
    )


def _approx(expected: tuple[float, ...], actual: tuple[float, ...], tol_mm: float = 1.0) -> None:
    for i, (e, a) in enumerate(zip(expected, actual, strict=True)):
        assert a == pytest.approx(e, abs=tol_mm), (
            f"bbox component {i}: expected {e}, got {a} (diff {a - e:.2f} mm)"
        )


def _placement_origin(product) -> tuple[float, float, float]:
    coords = product.ObjectPlacement.RelativePlacement.Location.Coordinates
    return float(coords[0]), float(coords[1]), float(coords[2])


def _swept(product):
    return product.Representation.Representations[0].Items[0]


def test_add_wall_horizontal_line_correct_bbox():
    """Wall along +X from (0,0,0) to (5000,0,0), thickness 200, height 3000.
    Expected world bbox (0, -100, 0)-(5000, 100, 3000)."""
    line = LineGeometry(start=Point3D(0, 0, 0), end=Point3D(5000, 0, 0))
    mapped = MappedEntity(
        layer="KYL-ULKOSEINA",
        dxf_type="LINE",
        geometry=line,
        ifc_type="IfcWall",
        predefined_type="STANDARD",
        extra_props={"default_height_mm": 3000.0, "default_thickness_mm": 200.0},
    )
    ifc = build_ifc_project_skeleton(project_name="Wall Bbox")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    wall = add_wall(ifc, mapped, parent_storey=storey)

    assert _placement_origin(wall) == (0.0, 0.0, 0.0)
    extruded = _swept(wall)
    assert extruded.SweptArea.XDim == pytest.approx(5000.0)
    assert extruded.SweptArea.YDim == pytest.approx(200.0)
    assert extruded.Depth == pytest.approx(3000.0)
    assert extruded.ExtrudedDirection.DirectionRatios == (0.0, 0.0, 1.0)


def test_add_slab_polygon_correct_bbox():
    """Slab outline 4000x3000 at z=0, thickness 200 → solid runs z=-200..0."""
    polygon = PolygonGeometry(
        vertices=(
            Point3D(0, 0, 0),
            Point3D(4000, 0, 0),
            Point3D(4000, 3000, 0),
            Point3D(0, 3000, 0),
        ),
        closed=True,
    )
    mapped = MappedEntity(
        layer="KYL-ALAPOHJA",
        dxf_type="LWPOLYLINE",
        geometry=polygon,
        ifc_type="IfcSlab",
        predefined_type="FLOOR",
        extra_props={"default_thickness_mm": 200.0},
    )
    ifc = build_ifc_project_skeleton(project_name="Slab Bbox")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    slab = add_slab(ifc, mapped, parent_storey=storey)

    assert _placement_origin(slab) == (0.0, 0.0, 0.0)
    extruded = _swept(slab)
    assert extruded.Depth == pytest.approx(200.0)
    assert extruded.ExtrudedDirection.DirectionRatios == (0.0, 0.0, -1.0)


def test_add_door_block_correct_bbox():
    """Door at (1500, 0, 0), 900x2100x50 → bbox (1500,-25,0)-(2400,25,2100)."""
    block = BlockInstance(insertion_point=Point3D(1500, 0, 0), rotation_rad=0.0)
    mapped = MappedEntity(
        layer="KYL-OVET-ULKO",
        dxf_type="INSERT",
        geometry=block,
        ifc_type="IfcDoor",
        predefined_type="DOOR",
        extra_props={
            "default_width_mm": 900.0,
            "default_height_mm": 2100.0,
            "default_depth_mm": 50.0,
        },
    )
    ifc = build_ifc_project_skeleton(project_name="Door Bbox")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    door = add_door(ifc, mapped, parent_storey=storey)

    assert _placement_origin(door) == (1500.0, 0.0, 0.0)
    extruded = _swept(door)
    assert extruded.SweptArea.XDim == pytest.approx(900.0)
    assert extruded.SweptArea.YDim == pytest.approx(50.0)
    assert extruded.Depth == pytest.approx(2100.0)
    assert door.OverallWidth == pytest.approx(900.0)
    assert door.OverallHeight == pytest.approx(2100.0)


def test_add_window_block_correct_bbox():
    """Window at (3000, 0, 1000), 1200x1500x60."""
    block = BlockInstance(insertion_point=Point3D(3000, 0, 1000), rotation_rad=0.0)
    mapped = MappedEntity(
        layer="KYL-IKKUNA",
        dxf_type="INSERT",
        geometry=block,
        ifc_type="IfcWindow",
        predefined_type="WINDOW",
        extra_props={
            "default_width_mm": 1200.0,
            "default_height_mm": 1500.0,
            "default_depth_mm": 60.0,
        },
    )
    ifc = build_ifc_project_skeleton(project_name="Window Bbox")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    window = add_window(ifc, mapped, parent_storey=storey)

    assert _placement_origin(window) == (3000.0, 0.0, 1000.0)
    extruded = _swept(window)
    assert extruded.SweptArea.XDim == pytest.approx(1200.0)
    assert extruded.SweptArea.YDim == pytest.approx(60.0)
    assert extruded.Depth == pytest.approx(1500.0)


def test_add_pipe_horizontal_line_correct_bbox():
    """Pipe along +X from (0,0,1000) to (2000,0,1000), diameter 22."""
    line = LineGeometry(start=Point3D(0, 0, 1000), end=Point3D(2000, 0, 1000))
    mapped = MappedEntity(
        layer="LT IMU",
        dxf_type="LINE",
        geometry=line,
        ifc_type="IfcPipeSegment",
        predefined_type="RIGIDSEGMENT",
        extra_props={"default_diameter_mm": 22.0},
    )
    ifc = build_ifc_project_skeleton(project_name="Pipe Bbox")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    pipe = add_pipe_segment(ifc, mapped, parent_storey=storey, predefined_type="RIGIDSEGMENT")

    assert _placement_origin(pipe) == (0.0, 0.0, 1000.0)
    extruded = _swept(pipe)
    assert extruded.SweptArea.is_a("IfcCircleProfileDef")
    assert extruded.SweptArea.Radius == pytest.approx(11.0)
    assert extruded.Depth == pytest.approx(2000.0)
    assert extruded.Position.Axis.DirectionRatios == (1.0, 0.0, 0.0)


def test_add_cable_carrier_horizontal_line_correct_bbox():
    """Cable tray along +X from (0,0,2700) to (3000,0,2700), 300x80."""
    line = LineGeometry(start=Point3D(0, 0, 2700), end=Point3D(3000, 0, 2700))
    mapped = MappedEntity(
        layer="KAAPELIHYLLY",
        dxf_type="LINE",
        geometry=line,
        ifc_type="IfcCableCarrierSegment",
        predefined_type="CABLETRUNKINGSEGMENT",
        extra_props={"default_width_mm": 300.0, "default_height_mm": 80.0},
    )
    ifc = build_ifc_project_skeleton(project_name="Cable Bbox")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    seg = add_cable_carrier_segment(ifc, mapped, parent_storey=storey)

    assert _placement_origin(seg) == (0.0, 0.0, 2700.0)
    extruded = _swept(seg)
    assert extruded.SweptArea.XDim == pytest.approx(300.0)
    assert extruded.SweptArea.YDim == pytest.approx(80.0)
    assert extruded.Depth == pytest.approx(3000.0)
    assert extruded.Position.Axis.DirectionRatios == (1.0, 0.0, 0.0)


def test_add_proxy_panel_correct_bbox():
    """Cold-room panel polygon 2400x2700 at z=0, thickness 120 → solid 0..120."""
    polygon = PolygonGeometry(
        vertices=(
            Point3D(0, 0, 0),
            Point3D(2400, 0, 0),
            Point3D(2400, 2700, 0),
            Point3D(0, 2700, 0),
        ),
        closed=True,
    )
    mapped = MappedEntity(
        layer="KYL-LEVY",
        dxf_type="LWPOLYLINE",
        geometry=polygon,
        ifc_type="IfcBuildingElementProxy",
        extra_props={"default_thickness_mm": 120.0},
    )
    ifc = build_ifc_project_skeleton(project_name="Proxy Bbox")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    proxy = add_building_element_proxy(ifc, mapped, parent_storey=storey)

    assert _placement_origin(proxy) == (0.0, 0.0, 0.0)
    extruded = _swept(proxy)
    assert extruded.Depth == pytest.approx(120.0)
    assert extruded.ExtrudedDirection.DirectionRatios == (0.0, 0.0, 1.0)


def test_add_cooling_equipment_block_correct_bbox():
    """Evaporator block at (4500,4500,2200), 800x600x500."""
    block = BlockInstance(insertion_point=Point3D(4500, 4500, 2200), rotation_rad=0.0)
    mapped = MappedEntity(
        layer="KYL-HOYRYSTIN-CR-30",
        dxf_type="INSERT",
        geometry=block,
        ifc_type="IfcEvaporator",
        extra_props={
            "default_width_mm": 800.0,
            "default_depth_mm": 600.0,
            "default_height_mm": 500.0,
        },
    )
    ifc = build_ifc_project_skeleton(project_name="Cooling Bbox")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    evap = add_cooling_equipment(ifc, mapped, parent_storey=storey)

    assert _placement_origin(evap) == (4500.0, 4500.0, 2200.0)
    bbox = _world_bbox_of_swept_solid(evap)
    _approx((4500.0, 4500.0, 2200.0, 5300.0, 5100.0, 2700.0), bbox)


def test_add_furniture_block_correct_bbox():
    """KYL-LEVYHYLLY block at (4500,1500,1500), explicit 800x400x60 (thin shelf)."""
    block = BlockInstance(insertion_point=Point3D(4500, 1500, 1500), rotation_rad=0.0)
    mapped = MappedEntity(
        layer="KYL-LEVYHYLLY",
        dxf_type="INSERT",
        geometry=block,
        ifc_type="IfcFurniture",
        extra_props={
            "default_width_mm": 800.0,
            "default_depth_mm": 400.0,
            "default_height_mm": 60.0,
        },
    )
    ifc = build_ifc_project_skeleton(project_name="Furniture Block Bbox")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    furn = add_furniture(ifc, mapped, parent_storey=storey)

    bbox = _world_bbox_of_swept_solid(furn)
    _approx((4500.0, 1500.0, 1500.0, 5300.0, 1900.0, 1560.0), bbox)




def test_add_furniture_polygon_correct_bbox():
    """800 × 400 polygon at world origin + 60 mm height → bbox (0,0,0)-(800,400,60)."""
    polygon = PolygonGeometry(
        vertices=(
            Point3D(0.0, 0.0, 0.0),
            Point3D(800.0, 0.0, 0.0),
            Point3D(800.0, 400.0, 0.0),
            Point3D(0.0, 400.0, 0.0),
        ),
        closed=True,
    )
    mapped = MappedEntity(
        layer="KYL-LEVYHYLLY",
        dxf_type="LWPOLYLINE",
        geometry=polygon,
        ifc_type="IfcFurniture",
        predefined_type=None,
        talo2000_code="1331",
        talo2000_name="Vakiokiintokalusteet",
        extra_props={"default_height_mm": 60.0},
    )
    ifc = build_ifc_project_skeleton(project_name="Furniture Bbox")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    furniture = add_furniture(ifc, mapped, parent_storey=storey)

    bbox = _world_bbox_of_swept_solid(furniture)
    _approx((0.0, 0.0, 0.0, 800.0, 400.0, 60.0), bbox)
