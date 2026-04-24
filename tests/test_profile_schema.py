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
