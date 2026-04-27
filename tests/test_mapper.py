"""Unit tests for core.mapper."""

import pytest

from dxf2ifc.core.mapper import apply_profile, layer_matches
from dxf2ifc.core.types import BlockInstance, EntityRecord, LineGeometry, Point3D
from dxf2ifc.profiles.loader import load_default_profile
from dxf2ifc.profiles.schema import Profile, Rule


@pytest.mark.parametrize(
    "pattern,layer,expected",
    [
        ("KYL-ULKOSEINA*", "KYL-ULKOSEINA", True),
        ("KYL-ULKOSEINA*", "KYL-ULKOSEINA-200", True),
        ("KYL-ULKOSEINA*", "KYL-VALISEINA", False),
        ("KYL-*", "KYL-LEVYHYLLY", True),
        ("KYL-*", "WALL", False),
        ("LT IMU", "LT IMU", True),
        ("LT IMU", "lt imu", True),  # case-insensitive
        # wildcard suffix matches deeper subdivisions (Plan B Task 28)
        ("KYL-VIEMARI*", "KYL-VIEMARI", True),
        ("KYL-VIEMARI*", "KYL-VIEMARI-LATTIA", True),
        ("KYL-VIEMARI*", "KYL-VIEMARI-110", True),
        ("KYL-VIEMARI*", "kyl-viemari-katto", True),  # case-insensitive suffix
        ("KYL-VIEMARI*", "KYL-PUTKI", False),
    ],
)
def test_layer_matches(pattern: str, layer: str, expected: bool):
    assert layer_matches(pattern, layer) is expected


def _simple_profile():
    return Profile(
        name="test",
        ifc_schema="IFC4",
        rules=[
            Rule(
                layer_pattern="KYL-ULKOSEINA*",
                ifc_type="IfcWall",
                predefined_type="STANDARD",
                talo2000_code="1241",
                talo2000_name="Ulkoseinät",
                default_height_mm=3000,
                default_thickness_mm=200,
            ),
        ],
    )


def _sample_line_record(layer: str = "KYL-ULKOSEINA") -> EntityRecord:
    return EntityRecord(
        layer=layer,
        dxf_type="LINE",
        geometry=LineGeometry(start=Point3D(0, 0, 0), end=Point3D(5000, 0, 0)),
    )


def test_apply_profile_returns_mapped_entity_for_matching_rule():
    entities = [_sample_line_record()]
    mapped = apply_profile(entities, _simple_profile())
    assert len(mapped) == 1
    assert mapped[0].ifc_type == "IfcWall"
    assert mapped[0].predefined_type == "STANDARD"
    assert mapped[0].talo2000_code == "1241"
    assert mapped[0].extra_props["default_height_mm"] == 3000
    assert mapped[0].extra_props["default_thickness_mm"] == 200


def test_apply_profile_skips_unmatched_layer():
    entities = [_sample_line_record(layer="RANDOM-LAYER")]
    mapped = apply_profile(entities, _simple_profile())
    assert mapped == []


def test_apply_profile_uses_first_matching_rule_by_order():
    profile = Profile(
        name="order",
        ifc_schema="IFC4",
        rules=[
            Rule(
                layer_pattern="KYL-*",
                ifc_type="IfcWall",
                predefined_type="PARTITIONING",
                talo2000_code="1311",
                talo2000_name="Väliseinät",
            ),
            Rule(
                layer_pattern="KYL-ULKOSEINA*",
                ifc_type="IfcWall",
                predefined_type="STANDARD",
                talo2000_code="1241",
                talo2000_name="Ulkoseinät",
            ),
        ],
    )
    mapped = apply_profile([_sample_line_record()], profile)
    # First match wins → PARTITIONING (because KYL-* matches first)
    assert mapped[0].predefined_type == "PARTITIONING"


def test_apply_profile_maps_partition_walls_via_default_profile():
    profile = load_default_profile()
    entities = [
        _sample_line_record(layer="KYL-VALISEINA"),
        _sample_line_record(layer="KYL-LASIVALISEINA"),
    ]
    mapped = apply_profile(entities, profile)
    by_layer = {m.layer: m for m in mapped}
    vs = by_layer["KYL-VALISEINA"]
    assert vs.ifc_type == "IfcWall"
    assert vs.predefined_type == "PARTITIONING"
    assert vs.talo2000_code == "1311"
    assert vs.talo2000_name == "Väliseinät"
    lasi = by_layer["KYL-LASIVALISEINA"]
    assert lasi.ifc_type == "IfcWall"
    assert lasi.predefined_type == "PARTITIONING"
    assert lasi.talo2000_code == "1312"
    assert lasi.talo2000_name == "Lasiväliseinät"


def test_apply_profile_maps_ikkuna_block_to_ifcwindow_via_default_profile():
    profile = load_default_profile()
    entity = EntityRecord(
        layer="KYL-IKKUNA-MUOVI",
        dxf_type="INSERT",
        geometry=BlockInstance(insertion_point=Point3D(2000, 1500, 0)),
        block_name="IKKUNA",
    )
    mapped = apply_profile([entity], profile)
    assert len(mapped) == 1
    window = mapped[0]
    assert window.ifc_type == "IfcWindow"
    assert window.talo2000_code == "1242"
    assert window.talo2000_name == "Ikkunat"
    assert window.block_name == "IKKUNA"
