"""Unit tests for core.geometry."""

import pytest

from dxf2ifc.core.geometry import (
    CableCarrierSegmentExtrusion,
    DoorBoxExtrusion,
    FurnitureBoxExtrusion,
    PanelExtrusion,
    PipeSegmentExtrusion,
    SlabExtrusion,
    WallExtrusion,
    block_to_furniture_box,
    door_block_to_box,
    line_to_cable_carrier,
    line_to_pipe_segment,
    line_to_wall_extrusion,
    panel_to_proxy_solid,
    polygon_to_slab_extrusion,
)
from dxf2ifc.core.types import BlockInstance, LineGeometry, Point3D, PolygonGeometry


def test_line_to_wall_extrusion_length():
    line = LineGeometry(start=Point3D(0, 0, 0), end=Point3D(5000, 0, 0))
    w = line_to_wall_extrusion(line, thickness_mm=200, height_mm=3000)
    assert isinstance(w, WallExtrusion)
    assert w.length_mm == 5000.0


def test_line_to_wall_extrusion_dims():
    line = LineGeometry(start=Point3D(0, 0, 0), end=Point3D(5000, 0, 0))
    w = line_to_wall_extrusion(line, thickness_mm=200, height_mm=3000)
    assert w.thickness_mm == 200.0
    assert w.height_mm == 3000.0


def test_line_to_wall_extrusion_angle_zero_for_x_axis_line():
    line = LineGeometry(start=Point3D(0, 0, 0), end=Point3D(5000, 0, 0))
    w = line_to_wall_extrusion(line, thickness_mm=200, height_mm=3000)
    assert w.angle_rad == 0.0


def test_line_to_wall_extrusion_anchor_is_start_point():
    line = LineGeometry(start=Point3D(100, 200, 300), end=Point3D(5100, 200, 300))
    w = line_to_wall_extrusion(line, thickness_mm=200, height_mm=3000)
    assert w.anchor == Point3D(100, 200, 300)


def _square_polygon() -> PolygonGeometry:
    return PolygonGeometry(
        vertices=(
            Point3D(0, 0, 0),
            Point3D(4000, 0, 0),
            Point3D(4000, 3000, 0),
            Point3D(0, 3000, 0),
        ),
        closed=True,
    )


def test_polygon_to_slab_extrusion_returns_slab_extrusion():
    slab = polygon_to_slab_extrusion(_square_polygon(), thickness_mm=200)
    assert isinstance(slab, SlabExtrusion)
    assert slab.thickness_mm == 200.0


def test_polygon_to_slab_extrusion_keeps_xy_outline_in_2d():
    slab = polygon_to_slab_extrusion(_square_polygon(), thickness_mm=200)
    assert slab.outline_xy == ((0.0, 0.0), (4000.0, 0.0), (4000.0, 3000.0), (0.0, 3000.0))


def test_polygon_to_slab_extrusion_uses_first_vertex_z_as_base():
    poly = PolygonGeometry(
        vertices=(
            Point3D(0, 0, 1500),
            Point3D(2000, 0, 1500),
            Point3D(2000, 1000, 1500),
        ),
        closed=True,
    )
    slab = polygon_to_slab_extrusion(poly, thickness_mm=300)
    assert slab.base_z == 1500.0


def test_polygon_to_slab_extrusion_rejects_open_polygon():
    poly = PolygonGeometry(
        vertices=(Point3D(0, 0, 0), Point3D(1, 0, 0), Point3D(1, 1, 0)),
        closed=False,
    )
    with pytest.raises(ValueError):
        polygon_to_slab_extrusion(poly, thickness_mm=200)


def test_door_block_to_box_returns_box_extrusion_with_dims():
    block = BlockInstance(insertion_point=Point3D(0, 0, 0))
    box = door_block_to_box(block, width_mm=900, height_mm=2100, depth_mm=100)
    assert isinstance(box, DoorBoxExtrusion)
    assert box.width_mm == 900.0
    assert box.height_mm == 2100.0
    assert box.depth_mm == 100.0


def test_door_block_to_box_anchor_is_insertion_point():
    block = BlockInstance(insertion_point=Point3D(1500, 2500, 0))
    box = door_block_to_box(block, width_mm=900, height_mm=2100, depth_mm=100)
    assert box.anchor == Point3D(1500, 2500, 0)


def test_door_block_to_box_angle_matches_block_rotation():
    block = BlockInstance(insertion_point=Point3D(0, 0, 0), rotation_rad=1.5707963267948966)
    box = door_block_to_box(block, width_mm=900, height_mm=2100, depth_mm=100)
    assert box.angle_rad == pytest.approx(1.5707963267948966)


def test_door_block_to_box_default_angle_is_zero():
    block = BlockInstance(insertion_point=Point3D(0, 0, 0))
    box = door_block_to_box(block, width_mm=900, height_mm=2100, depth_mm=100)
    assert box.angle_rad == 0.0


def test_line_to_pipe_segment_returns_extrusion_with_diameter():
    line = LineGeometry(start=Point3D(0, 0, 0), end=Point3D(2000, 0, 0))
    pipe = line_to_pipe_segment(line, diameter_mm=22.0)
    assert isinstance(pipe, PipeSegmentExtrusion)
    assert pipe.diameter_mm == 22.0


def test_line_to_pipe_segment_length_matches_line_length():
    line = LineGeometry(start=Point3D(0, 0, 0), end=Point3D(3000, 4000, 0))
    pipe = line_to_pipe_segment(line, diameter_mm=18.0)
    assert pipe.length_mm == pytest.approx(5000.0)


def test_line_to_pipe_segment_anchor_is_start():
    line = LineGeometry(start=Point3D(150, 250, 350), end=Point3D(2150, 250, 350))
    pipe = line_to_pipe_segment(line, diameter_mm=12.0)
    assert pipe.anchor == Point3D(150, 250, 350)


def test_line_to_pipe_segment_angle_for_axis_aligned_line():
    line = LineGeometry(start=Point3D(0, 0, 0), end=Point3D(0, 1000, 0))
    pipe = line_to_pipe_segment(line, diameter_mm=12.0)
    assert pipe.angle_rad == pytest.approx(1.5707963267948966)


def test_block_to_furniture_box_returns_box_with_dims():
    block = BlockInstance(insertion_point=Point3D(0, 0, 0))
    box = block_to_furniture_box(block, width_mm=1000, depth_mm=600, height_mm=2000)
    assert isinstance(box, FurnitureBoxExtrusion)
    assert box.width_mm == 1000.0
    assert box.depth_mm == 600.0
    assert box.height_mm == 2000.0


def test_block_to_furniture_box_anchor_matches_insertion_point():
    block = BlockInstance(insertion_point=Point3D(3500, 1750, 0))
    box = block_to_furniture_box(block, width_mm=1000, depth_mm=600, height_mm=2000)
    assert box.anchor == Point3D(3500, 1750, 0)


def test_block_to_furniture_box_carries_block_rotation():
    block = BlockInstance(insertion_point=Point3D(0, 0, 0), rotation_rad=0.7853981633974483)
    box = block_to_furniture_box(block, width_mm=1000, depth_mm=600, height_mm=2000)
    assert box.angle_rad == pytest.approx(0.7853981633974483)


def test_block_to_furniture_box_default_angle_is_zero():
    block = BlockInstance(insertion_point=Point3D(0, 0, 0))
    box = block_to_furniture_box(block, width_mm=500, depth_mm=400, height_mm=1500)
    assert box.angle_rad == 0.0


def test_line_to_cable_carrier_returns_extrusion_with_dims():
    line = LineGeometry(start=Point3D(0, 0, 0), end=Point3D(2500, 0, 0))
    seg = line_to_cable_carrier(line, width_mm=300, height_mm=80)
    assert isinstance(seg, CableCarrierSegmentExtrusion)
    assert seg.width_mm == 300.0
    assert seg.height_mm == 80.0


def test_line_to_cable_carrier_length_matches_line():
    line = LineGeometry(start=Point3D(0, 0, 0), end=Point3D(0, 5000, 0))
    seg = line_to_cable_carrier(line, width_mm=300, height_mm=80)
    assert seg.length_mm == pytest.approx(5000.0)


def test_line_to_cable_carrier_anchor_is_start():
    line = LineGeometry(start=Point3D(100, 200, 2700), end=Point3D(2600, 200, 2700))
    seg = line_to_cable_carrier(line, width_mm=300, height_mm=80)
    assert seg.anchor == Point3D(100, 200, 2700)


def test_line_to_cable_carrier_angle_for_diagonal_line():
    line = LineGeometry(start=Point3D(0, 0, 0), end=Point3D(1000, 1000, 0))
    seg = line_to_cable_carrier(line, width_mm=300, height_mm=80)
    assert seg.angle_rad == pytest.approx(0.7853981633974483)


def _panel_polygon() -> PolygonGeometry:
    return PolygonGeometry(
        vertices=(
            Point3D(0, 0, 0),
            Point3D(2400, 0, 0),
            Point3D(2400, 2700, 0),
            Point3D(0, 2700, 0),
        ),
        closed=True,
    )


def test_panel_to_proxy_solid_returns_panel_extrusion():
    panel = panel_to_proxy_solid(_panel_polygon(), thickness_mm=120)
    assert isinstance(panel, PanelExtrusion)
    assert panel.thickness_mm == 120.0


def test_panel_to_proxy_solid_keeps_xy_outline_in_2d():
    panel = panel_to_proxy_solid(_panel_polygon(), thickness_mm=120)
    assert panel.outline_xy == ((0.0, 0.0), (2400.0, 0.0), (2400.0, 2700.0), (0.0, 2700.0))


def test_panel_to_proxy_solid_uses_first_vertex_z_as_base():
    poly = PolygonGeometry(
        vertices=(
            Point3D(0, 0, 600),
            Point3D(1200, 0, 600),
            Point3D(1200, 600, 600),
        ),
        closed=True,
    )
    panel = panel_to_proxy_solid(poly, thickness_mm=80)
    assert panel.base_z == 600.0


def test_panel_to_proxy_solid_rejects_open_polygon():
    poly = PolygonGeometry(
        vertices=(Point3D(0, 0, 0), Point3D(1, 0, 0), Point3D(1, 1, 0)),
        closed=False,
    )
    with pytest.raises(ValueError):
        panel_to_proxy_solid(poly, thickness_mm=80)
