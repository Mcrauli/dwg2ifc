"""Unit tests for profiles.loader."""

from pathlib import Path

import pytest

from dxf2ifc.profiles.loader import load_default_profile, load_profile
from dxf2ifc.profiles.schema import Profile


def test_load_default_profile_returns_profile():
    profile = load_default_profile()
    assert isinstance(profile, Profile)
    assert profile.ifc_schema == "IFC4"
    assert len(profile.rules) >= 1


def test_load_default_profile_has_exterior_wall_rule():
    profile = load_default_profile()
    wall_rules = [r for r in profile.rules if r.ifc_type == "IfcWall"]
    assert len(wall_rules) >= 1
    assert wall_rules[0].talo2000_code == "1241"


def test_load_profile_from_file(tmp_path: Path):
    toml_content = """
[profile]
name = "Test"
ifc_schema = "IFC4"

[[rules]]
layer_pattern = "WALL*"
ifc_type = "IfcWall"
talo2000_code = "1241"
talo2000_name = "Ulkoseinät"
"""
    profile_file = tmp_path / "test.toml"
    profile_file.write_text(toml_content, encoding="utf-8")
    profile = load_profile(profile_file)
    assert profile.name == "Test"
    assert len(profile.rules) == 1
    assert profile.rules[0].layer_pattern == "WALL*"


def test_load_profile_roundtrips_new_fields(tmp_path: Path):
    toml_content = """
[profile]
name = "Roundtrip"
ifc_schema = "IFC4"

[[rules]]
layer_pattern = "KYL-ULKOSEINA*"
entity_kind = "LINE"
ifc_type = "IfcWall"
talo2000_code = "1241"
talo2000_name = "Ulkoseinät"
extrusion_height = 2700.0

[rules.pset_overrides.Pset_WallCommon]
IsExternal = true

[[rules]]
layer_pattern = "KYL-OVET"
entity_kind = "INSERT"
block_name = "OVI-ULKO"
ifc_type = "IfcDoor"
talo2000_code = "1243"
talo2000_name = "Ulko-ovet"
"""
    profile_file = tmp_path / "roundtrip.toml"
    profile_file.write_text(toml_content, encoding="utf-8")
    profile = load_profile(profile_file)
    line_rule, insert_rule = profile.rules
    assert line_rule.entity_kind == "LINE"
    assert line_rule.extrusion_height == 2700.0
    assert line_rule.pset_overrides == {"Pset_WallCommon": {"IsExternal": True}}
    assert insert_rule.entity_kind == "INSERT"
    assert insert_rule.block_name == "OVI-ULKO"


def test_load_profile_rejects_insert_without_block_name(tmp_path: Path):
    toml_content = """
[profile]
name = "BadInsert"
ifc_schema = "IFC4"

[[rules]]
layer_pattern = "KYL-OVET"
entity_kind = "INSERT"
ifc_type = "IfcDoor"
talo2000_code = "1243"
talo2000_name = "Ulko-ovet"
"""
    profile_file = tmp_path / "bad_insert.toml"
    profile_file.write_text(toml_content, encoding="utf-8")
    with pytest.raises(Exception):
        load_profile(profile_file)


def test_load_profile_rejects_invalid(tmp_path: Path):
    toml_content = """
[profile]
name = "Bad"
ifc_schema = "IFC4"

[[rules]]
# missing layer_pattern
ifc_type = "IfcWall"
talo2000_code = "1241"
talo2000_name = "Ulkoseinät"
"""
    profile_file = tmp_path / "bad.toml"
    profile_file.write_text(toml_content, encoding="utf-8")
    with pytest.raises(Exception):  # pydantic ValidationError
        load_profile(profile_file)
