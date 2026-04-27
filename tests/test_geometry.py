"""Unit tests for core.geometry."""

import pytest

from dxf2ifc.core.geometry import (
    SlabExtrusion,
    WallExtrusion,
    line_to_wall_extrusion,
    polygon_to_slab_extrusion,
)
from dxf2ifc.core.types import LineGeometry, Point3D, PolygonGeometry


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
