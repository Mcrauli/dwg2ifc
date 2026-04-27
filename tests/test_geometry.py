"""Unit tests for core.geometry."""

from dxf2ifc.core.geometry import WallExtrusion, line_to_wall_extrusion
from dxf2ifc.core.types import LineGeometry, Point3D


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
