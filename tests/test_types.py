"""Unit tests for core.types dataclasses."""
from dxf2ifc.core.types import EntityRecord, LineGeometry, Point3D


def test_point3d_stores_coords():
    p = Point3D(x=1.0, y=2.0, z=3.0)
    assert p.x == 1.0
    assert p.y == 2.0
    assert p.z == 3.0


def test_point3d_equality():
    assert Point3D(1.0, 2.0, 3.0) == Point3D(1.0, 2.0, 3.0)
    assert Point3D(1.0, 2.0, 3.0) != Point3D(1.0, 2.0, 3.1)


def test_line_geometry_from_two_points():
    start = Point3D(0.0, 0.0, 0.0)
    end = Point3D(1000.0, 0.0, 0.0)
    line = LineGeometry(start=start, end=end)
    assert line.start == start
    assert line.end == end


def test_entity_record_holds_layer_type_geometry():
    line = LineGeometry(start=Point3D(0, 0, 0), end=Point3D(1, 0, 0))
    rec = EntityRecord(
        layer="KYL-ULKOSEINA",
        dxf_type="LINE",
        geometry=line,
        attributes={},
        block_name=None,
        xform=None,
    )
    assert rec.layer == "KYL-ULKOSEINA"
    assert rec.dxf_type == "LINE"
    assert rec.geometry is line


def test_mapped_entity_extends_entity_record():
    from dxf2ifc.core.types import MappedEntity

    line = LineGeometry(start=Point3D(0, 0, 0), end=Point3D(1000, 0, 0))
    mapped = MappedEntity(
        layer="KYL-ULKOSEINA",
        dxf_type="LINE",
        geometry=line,
        attributes={},
        block_name=None,
        xform=None,
        ifc_type="IfcWall",
        predefined_type="STANDARD",
        talo2000_code="1241",
        talo2000_name="Ulkoseinät",
        extra_props={"default_height_mm": 3000},
    )
    assert mapped.ifc_type == "IfcWall"
    assert mapped.talo2000_code == "1241"
    assert mapped.extra_props["default_height_mm"] == 3000
