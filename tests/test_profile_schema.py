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


def test_profile_holds_line_and_insert_rules():
    profile = Profile(
        name="line+insert",
        ifc_schema="IFC4",
        rules=[
            Rule(
                layer_pattern="KYL-ULKOSEINA*",
                ifc_type="IfcWall",
                talo2000_code="1241",
                talo2000_name="Ulkoseinät",
                entity_kind="LINE",
                extrusion_height=2700.0,
                pset_overrides={"Pset_WallCommon": {"IsExternal": True}},
            ),
            Rule(
                layer_pattern="KYL-OVET",
                ifc_type="IfcDoor",
                talo2000_code="1243",
                talo2000_name="Ulko-ovet",
                entity_kind="INSERT",
                block_name="OVI-ULKO",
            ),
        ],
    )
    line_rule, insert_rule = profile.rules
    assert line_rule.entity_kind == "LINE"
    assert line_rule.extrusion_height == 2700.0
    assert line_rule.pset_overrides["Pset_WallCommon"]["IsExternal"] is True
    assert insert_rule.entity_kind == "INSERT"
    assert insert_rule.block_name == "OVI-ULKO"


def test_rule_defaults_to_ark_domain():
    rule = Rule(
        layer_pattern="KYL-ULKOSEINA*",
        ifc_type="IfcWall",
        talo2000_code="1241",
        talo2000_name="Ulkoseinät",
    )
    assert rule.domain == "ARK"
    assert rule.lvi_code is None
    assert rule.talotekniikka_code is None


def test_rule_ark_domain_requires_talo2000_code():
    with pytest.raises(ValidationError):
        Rule(
            layer_pattern="X",
            ifc_type="IfcWall",
            domain="ARK",
        )


def test_rule_ark_domain_rejects_lvi_code():
    with pytest.raises(ValidationError):
        Rule(
            layer_pattern="X",
            ifc_type="IfcWall",
            domain="ARK",
            talo2000_code="1241",
            talo2000_name="Ulkoseinät",
            lvi_code="T-LVI-01-01-023",
        )


def test_rule_tate_domain_with_lvi_code_valid():
    rule = Rule(
        layer_pattern="KYL-HOYRYSTIN*",
        ifc_type="IfcEvaporator",
        entity_kind="INSERT",
        block_name="HOYRYSTIN",
        domain="TATE",
        lvi_code="T-LVI-01-01-023",
    )
    assert rule.domain == "TATE"
    assert rule.lvi_code == "T-LVI-01-01-023"
    assert rule.talo2000_code is None
    assert rule.talotekniikka_code is None


def test_rule_tate_domain_with_talotekniikka_code_valid():
    rule = Rule(
        layer_pattern="KAAPELIHYLLY*",
        ifc_type="IfcCableCarrierSegment",
        domain="TATE",
        talotekniikka_code="T-TATE-01-01-001",
    )
    assert rule.domain == "TATE"
    assert rule.talotekniikka_code == "T-TATE-01-01-001"
    assert rule.lvi_code is None
    assert rule.talo2000_code is None


def test_rule_tate_domain_rejects_both_codes():
    with pytest.raises(ValidationError):
        Rule(
            layer_pattern="X",
            ifc_type="IfcEvaporator",
            domain="TATE",
            lvi_code="T-LVI-01-01-023",
            talotekniikka_code="T-TATE-01-01-001",
        )


def test_rule_tate_domain_requires_one_code():
    with pytest.raises(ValidationError):
        Rule(
            layer_pattern="X",
            ifc_type="IfcEvaporator",
            domain="TATE",
        )


def test_rule_tate_domain_rejects_talo2000_code():
    with pytest.raises(ValidationError):
        Rule(
            layer_pattern="X",
            ifc_type="IfcEvaporator",
            domain="TATE",
            talo2000_code="2510",
            lvi_code="T-LVI-01-01-023",
        )


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


def _profile_no_rules(**extra) -> Profile:
    return Profile(name="t", ifc_schema="IFC4", rules=[], **extra)


def test_profile_default_storey_levels_single_zero():
    profile = _profile_no_rules()
    assert profile.storey_z_levels_mm == [0.0]


def test_profile_accepts_three_storey_z_levels():
    profile = _profile_no_rules(storey_z_levels_mm=[0.0, 3500.0, 7000.0])
    assert profile.storey_z_levels_mm == [0.0, 3500.0, 7000.0]


def test_profile_rejects_descending_storey_levels():
    with pytest.raises(ValidationError):
        _profile_no_rules(storey_z_levels_mm=[0.0, 7000.0, 3500.0])


def test_profile_rejects_empty_storey_levels():
    with pytest.raises(ValidationError):
        _profile_no_rules(storey_z_levels_mm=[])


def test_profile_rejects_storey_level_above_cap():
    with pytest.raises(ValidationError):
        _profile_no_rules(storey_z_levels_mm=[0.0, 100_001.0])


def test_profile_rejects_negative_storey_level():
    with pytest.raises(ValidationError):
        _profile_no_rules(storey_z_levels_mm=[-1.0])
