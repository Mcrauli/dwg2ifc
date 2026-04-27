"""Unit tests for profiles.schema pydantic models."""

import pytest
from pydantic import ValidationError

from dxf2ifc.profiles.schema import Profile, Rule


def test_rule_requires_layer_pattern_and_ifc_type():
    rule = Rule(
        layer_pattern="KYL-ULKOSEINA*",
        ifc_type="IfcWall",
        talo2000_code="1241",
        talo2000_name="Ulkoseinät",
    )
    assert rule.layer_pattern == "KYL-ULKOSEINA*"
    assert rule.ifc_type == "IfcWall"


def test_rule_allows_predefined_type_and_defaults():
    rule = Rule(
        layer_pattern="KYL-ULKOSEINA*",
        ifc_type="IfcWall",
        predefined_type="STANDARD",
        talo2000_code="1241",
        talo2000_name="Ulkoseinät",
        default_height_mm=3000,
        default_thickness_mm=200,
    )
    assert rule.predefined_type == "STANDARD"
    assert rule.default_height_mm == 3000
    assert rule.default_thickness_mm == 200


def test_rule_rejects_missing_required():
    with pytest.raises(ValidationError):
        Rule(ifc_type="IfcWall", talo2000_code="1241")  # no layer_pattern


def test_rule_defaults_entity_kind_to_line():
    rule = Rule(
        layer_pattern="KYL-ULKOSEINA*",
        ifc_type="IfcWall",
        talo2000_code="1241",
        talo2000_name="Ulkoseinät",
    )
    assert rule.entity_kind == "LINE"
    assert rule.block_name is None


def test_rule_supports_insert_with_block_name():
    rule = Rule(
        layer_pattern="KYL-OVET",
        ifc_type="IfcDoor",
        talo2000_code="1243",
        talo2000_name="Ulko-ovet",
        entity_kind="INSERT",
        block_name="OVI-ULKO",
    )
    assert rule.entity_kind == "INSERT"
    assert rule.block_name == "OVI-ULKO"


def test_rule_rejects_unknown_entity_kind():
    with pytest.raises(ValidationError):
        Rule(
            layer_pattern="X",
            ifc_type="IfcWall",
            talo2000_code="1241",
            talo2000_name="Ulkoseinät",
            entity_kind="ARC",
        )


def test_rule_insert_without_block_name_raises():
    with pytest.raises(ValidationError):
        Rule(
            layer_pattern="KYL-OVET",
            ifc_type="IfcDoor",
            talo2000_code="1243",
            talo2000_name="Ulko-ovet",
            entity_kind="INSERT",
        )


def test_rule_accepts_extrusion_height_and_pset_overrides():
    rule = Rule(
        layer_pattern="KYL-ULKOSEINA*",
        ifc_type="IfcWall",
        talo2000_code="1241",
        talo2000_name="Ulkoseinät",
        extrusion_height=2700.0,
        pset_overrides={"Pset_WallCommon": {"IsExternal": True}},
    )
    assert rule.extrusion_height == 2700.0
    assert rule.pset_overrides == {"Pset_WallCommon": {"IsExternal": True}}


def test_rule_pset_overrides_defaults_to_empty_dict():
    rule = Rule(
        layer_pattern="KYL-ULKOSEINA*",
        ifc_type="IfcWall",
        talo2000_code="1241",
        talo2000_name="Ulkoseinät",
    )
    assert rule.extrusion_height is None
    assert rule.pset_overrides == {}


def test_profile_holds_rules():
    profile = Profile(
        name="test",
        ifc_schema="IFC4",
        rules=[
            Rule(
                layer_pattern="KYL-ULKOSEINA*",
                ifc_type="IfcWall",
                talo2000_code="1241",
                talo2000_name="Ulkoseinät",
            )
        ],
    )
    assert profile.name == "test"
    assert profile.ifc_schema == "IFC4"
    assert len(profile.rules) == 1
