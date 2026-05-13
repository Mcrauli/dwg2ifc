"""Unit tests for core.types dataclasses."""

import dataclasses
from pathlib import Path

import pytest

from dxf2ifc.core.types import EntityRecord, FileEntry, LineGeometry, MappedEntity, Point3D


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


def test_file_entry_holds_path_label_elevation():
    entry = FileEntry(path=Path("1krs.dwg"), floor_label="1.krs", elevation_mm=0.0)
    assert entry.path == Path("1krs.dwg")
    assert entry.floor_label == "1.krs"
    assert entry.elevation_mm == 0.0


def test_file_entry_is_frozen():
    entry = FileEntry(path=Path("a.dwg"), floor_label="1.krs", elevation_mm=0.0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        entry.elevation_mm = 5.0  # type: ignore[misc]


def test_mapped_entity_storey_index_defaults_to_zero():
    m = MappedEntity(layer="X", dxf_type="LINE", geometry=None)
    assert m.storey_index == 0


def test_mapped_entity_storey_index_settable():
    m = MappedEntity(layer="X", dxf_type="LINE", geometry=None, storey_index=2)
    assert m.storey_index == 2
