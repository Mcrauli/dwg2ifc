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
    add_furniture,
    build_ifc_project_skeleton,
)
from dxf2ifc.core.types import (
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
