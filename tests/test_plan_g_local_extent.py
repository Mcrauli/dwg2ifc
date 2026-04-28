"""Plan G Task 13: ``validate_local_extent`` scans every
``IfcCartesianPoint`` in the file and raises ``RuntimeError`` when any
component exceeds ``max_extent_mm``. Defensive check for the double
transform bug — geometry stays in LOCAL coordinates, so a value like
25_496_000 mm (an ETRS-TM35FIN easting) leaking into the geometry is a
clear sign that the MapConversion was applied twice."""

from __future__ import annotations

import pytest

from dxf2ifc.core.ifc_writer import (
    add_wall,
    build_ifc_project_skeleton,
    validate_local_extent,
)
from dxf2ifc.core.types import LineGeometry, MappedEntity, Point3D


def _wall_skeleton():
    skeleton = build_ifc_project_skeleton(project_name="LocalExtent")
    storey = skeleton.storeys[0]
    mapped = MappedEntity(
        layer="KYL-ULKOSEINA",
        dxf_type="LINE",
        geometry=LineGeometry(start=Point3D(0, 0, 0), end=Point3D(5000, 0, 0)),
        ifc_type="IfcWall",
        predefined_type="STANDARD",
        talo2000_code="1241",
        talo2000_name="Ulkoseinät",
        extra_props={"default_height_mm": 3000, "default_thickness_mm": 200},
    )
    add_wall(skeleton.file, mapped, parent_storey=storey)
    return skeleton


def test_validate_local_extent_clean_pass():
    skeleton = _wall_skeleton()
    validate_local_extent(skeleton)  # must not raise


def test_validate_local_extent_raises_on_simulated_double_transform():
    """Inject a vertex at 25 496 000 mm (ETRS-TM35FIN easting magnitude)
    to mimic the geometry being projected into world coordinates by a
    double MapConversion."""
    skeleton = _wall_skeleton()
    skeleton.file.create_entity("IfcCartesianPoint", Coordinates=(25_496_000.0, 6_672_000.0, 0.0))
    with pytest.raises(RuntimeError, match="exceeds"):
        validate_local_extent(skeleton)


def test_validate_local_extent_uses_custom_max():
    skeleton = _wall_skeleton()
    skeleton.file.create_entity("IfcCartesianPoint", Coordinates=(6000.0, 0.0, 0.0))
    # Default 5_000_000 mm passes; 5000 mm cap fails on the new vertex.
    validate_local_extent(skeleton, max_extent_mm=10_000.0)
    with pytest.raises(RuntimeError):
        validate_local_extent(skeleton, max_extent_mm=5_000.0)
