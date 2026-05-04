"""Unit tests for profiles.loader."""

from pathlib import Path

import pytest

from dxf2ifc.profiles.loader import dump_profile, load_default_profile, load_profile
from dxf2ifc.profiles.schema import CRSConfig, Profile


def test_default_profile_resource_uses_new_name():
    from importlib import resources

    package_files = resources.files("dxf2ifc.profiles")
    assert package_files.joinpath("default_kylmalaite.toml").is_file()
    assert not package_files.joinpath("default_kylmalaite_talo2000.toml").is_file()


def test_default_profile_is_kyl_only():
    """Default profile is refrigeration-only — every rule must be
    KYL-domain (kylmälaitesuunnittelu) with a RAVA code
    (lvi_code or talotekniikka_code) and no Talo2000/ARK leakage."""
    profile = load_default_profile()
    for rule in profile.rules:
        assert rule.domain == "KYL", (
            f"{rule.layer_pattern}: default profile must be KYL-only; got {rule.domain}"
        )
        assert rule.talo2000_code is None, (
            f"{rule.layer_pattern}: default profile must not carry Talo2000 codes"
        )
        assert rule.lvi_code or rule.talotekniikka_code, (
            f"{rule.layer_pattern}: KYL rule needs an lvi_code or talotekniikka_code"
        )


def test_load_default_profile_returns_profile():
    profile = load_default_profile()
    assert isinstance(profile, Profile)
    assert profile.ifc_schema == "IFC4"
    assert len(profile.rules) >= 1


def test_load_default_profile_excludes_architectural_rules():
    """Bugfix 12 narrowed the default profile to refrigeration-only scope.
    Walls, slabs, doors, windows, and cold-room panels are out of scope —
    they belong to the architect, not the refrigeration designer."""
    profile = load_default_profile()
    ifc_types = {r.ifc_type for r in profile.rules}
    architectural_only = {
        "IfcWall", "IfcSlab", "IfcDoor", "IfcWindow",
        "IfcColumn", "IfcRailing", "IfcStair", "IfcLightFixture",
        "IfcBuildingElementProxy",
    }
    assert ifc_types.isdisjoint(architectural_only), (
        f"default profile leaked architectural types: {ifc_types & architectural_only}"
    )


def test_load_default_profile_has_pipe_segment_rules():
    profile = load_default_profile()
    by_layer = {r.layer_pattern: r for r in profile.rules}
    lt = by_layer["LT IMU"]
    assert lt.ifc_type == "IfcPipeSegment"
    assert lt.predefined_type == "REFRIGERATION"
    assert lt.domain == "KYL"
    assert lt.lvi_code == "T-LVI-02"
    assert lt.talo2000_code is None
    assert lt.system_name == "Refrigeration LT"
    assert lt.pset_overrides["Pset_PipeSegmentOccurrence"]["NominalDiameter"] == 22.0
    mt_imu = by_layer["MT IMU"]
    assert mt_imu.domain == "KYL"
    assert mt_imu.lvi_code == "T-LVI-02"
    assert mt_imu.system_name == "Refrigeration MT"
    mt_neste = by_layer["MT NESTE"]
    assert mt_neste.domain == "KYL"
    assert mt_neste.lvi_code == "T-LVI-02"
    assert mt_neste.system_name == "Refrigeration MT"
    assert mt_neste.pset_overrides["Pset_PipeSegmentOccurrence"]["NominalDiameter"] == 12.0


def test_load_default_profile_has_drainpipe_rule():
    profile = load_default_profile()
    by_layer = {r.layer_pattern: r for r in profile.rules}
    drain = by_layer["KYL-VIEMARI*"]
    assert drain.ifc_type == "IfcPipeSegment"
    assert drain.predefined_type == "DRAINPIPE"
    assert drain.domain == "KYL"
    assert drain.lvi_code == "T-LVI-04-01-001"
    assert drain.talo2000_code is None
    assert drain.system_name == "Drainage"
    assert drain.pset_overrides["Pset_PipeSegmentOccurrence"]["NominalDiameter"] == 110.0


def test_load_default_profile_has_storage_furniture_rules():
    """Per Granlund/Sweco refrigeration BIM convention (KSM_Jeppis_Pietarsaari_KYL.ifc)
    cold-storage shelves are modeled as IfcCableCarrierSegment with the
    CABLELADDERSEGMENT (tikashylly) and CABLETRAYSEGMENT (levyhylly) predefined
    types — not IfcFurniture / Talo2000 1331."""
    profile = load_default_profile()
    by_layer = {r.layer_pattern: r for r in profile.rules}
    levy = by_layer["KYL-LEVYHYLLY*"]
    assert levy.ifc_type == "IfcCableCarrierSegment"
    assert levy.predefined_type == "CABLETRAYSEGMENT"
    assert levy.domain == "KYL"
    assert levy.talotekniikka_code == "T-TATE-01-01-001"
    assert levy.talo2000_code is None
    tikas = by_layer["KYL-TIKASHYLLY*"]
    assert tikas.ifc_type == "IfcCableCarrierSegment"
    assert tikas.predefined_type == "CABLELADDERSEGMENT"
    assert tikas.domain == "KYL"
    assert tikas.talotekniikka_code == "T-TATE-01-01-001"
    tikas_v = by_layer["KYL-TIKASHYLLY-V*"]
    assert tikas_v.predefined_type == "CABLELADDERSEGMENT"
    # Vertical rule must precede horizontal rule for first-match resolution.
    assert profile.rules.index(tikas_v) < profile.rules.index(tikas)


def test_load_default_profile_has_cable_carrier_rule():
    profile = load_default_profile()
    by_layer = {r.layer_pattern: r for r in profile.rules}
    cable = by_layer["KAAPELIHYLLY*"]
    assert cable.ifc_type == "IfcCableCarrierSegment"
    assert cable.predefined_type == "CABLETRUNKINGSEGMENT"
    assert cable.domain == "KYL"
    assert cable.talotekniikka_code == "T-TATE-01-01-001"
    assert cable.talo2000_code is None
    assert cable.system_name == "Cable carriers"


def test_load_default_profile_has_cooling_equipment_rules():
    """Patterns use stems (HÖYRYSTI / LAUHDUTI / KOMPRESSO) so they match
    both singular ("HÖYRYSTIN") and plural ("HÖYRYSTIMET") layer names.
    HÖYRYSTI ships in both Ö-spelling and ASCII fallback because Python's
    str.casefold does NOT fold Ö → o."""
    profile = load_default_profile()
    by_layer = {r.layer_pattern: r for r in profile.rules}
    hoyr_o = by_layer["KYL-HOYRYSTI*"]
    assert hoyr_o.ifc_type == "IfcEvaporator"
    assert hoyr_o.domain == "KYL"
    assert hoyr_o.lvi_code == "T-LVI-01-01-023"
    assert hoyr_o.system_name == "Refrigeration plant"
    hoyr_uml = by_layer["KYL-HÖYRYSTI*"]
    assert hoyr_uml.ifc_type == "IfcEvaporator"
    assert hoyr_uml.lvi_code == "T-LVI-01-01-023"
    lauh = by_layer["KYL-LAUHDUTI*"]
    assert lauh.ifc_type == "IfcCondenser"
    assert lauh.lvi_code == "T-LVI-01-01-018"
    komp = by_layer["KYL-KOMPRESSO*"]
    assert komp.ifc_type == "IfcCompressor"
    assert komp.lvi_code == "T-LVI-01-01-017"


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


def test_dump_profile_round_trips_default(tmp_path: Path):
    original = load_default_profile()
    out = tmp_path / "roundtrip.toml"
    dump_profile(original, out)
    reloaded = load_profile(out)
    assert isinstance(reloaded, Profile)
    assert len(reloaded.rules) == len(original.rules)
    by_pattern = {r.layer_pattern: r for r in reloaded.rules}
    for original_rule in original.rules:
        re_rule = by_pattern[original_rule.layer_pattern]
        assert re_rule.ifc_type == original_rule.ifc_type
        assert re_rule.talo2000_code == original_rule.talo2000_code
        assert re_rule.system_name == original_rule.system_name


def test_load_profile_roundtrips_domain_and_rava_codes(tmp_path: Path):
    toml_content = """
[profile]
name = "Domain"
ifc_schema = "IFC4"

[[rules]]
layer_pattern = "AR1241_US*"
ifc_type = "IfcWall"
domain = "ARK"
talo2000_code = "1241"
talo2000_name = "Ulkoseinät"

[[rules]]
layer_pattern = "KYL-HOYRYSTIN*"
entity_kind = "INSERT"
block_name = "HOYRYSTIN"
ifc_type = "IfcEvaporator"
domain = "TATE"
lvi_code = "T-LVI-01-01-023"

[[rules]]
layer_pattern = "KAAPELIHYLLY*"
ifc_type = "IfcCableCarrierSegment"
domain = "TATE"
talotekniikka_code = "T-TATE-01-01-001"
"""
    profile_file = tmp_path / "domain.toml"
    profile_file.write_text(toml_content, encoding="utf-8")
    profile = load_profile(profile_file)
    ark, hoyr, kaapeli = profile.rules
    assert ark.domain == "ARK"
    assert ark.talo2000_code == "1241"
    assert hoyr.domain == "TATE"
    assert hoyr.lvi_code == "T-LVI-01-01-023"
    assert hoyr.talo2000_code is None
    assert kaapeli.domain == "TATE"
    assert kaapeli.talotekniikka_code == "T-TATE-01-01-001"

    out = tmp_path / "roundtrip.toml"
    dump_profile(profile, out)
    reloaded = load_profile(out)
    by_pattern = {r.layer_pattern: r for r in reloaded.rules}
    assert by_pattern["AR1241_US*"].domain == "ARK"
    assert by_pattern["AR1241_US*"].talo2000_code == "1241"
    assert by_pattern["KYL-HOYRYSTIN*"].domain == "TATE"
    assert by_pattern["KYL-HOYRYSTIN*"].lvi_code == "T-LVI-01-01-023"
    assert by_pattern["KYL-HOYRYSTIN*"].talo2000_code is None
    assert by_pattern["KAAPELIHYLLY*"].talotekniikka_code == "T-TATE-01-01-001"


def test_dump_profile_writes_valid_utf8_toml(tmp_path: Path):
    profile = load_default_profile()
    out = tmp_path / "roundtrip.toml"
    dump_profile(profile, out)
    text = out.read_text(encoding="utf-8")
    assert text.startswith("[profile]") or "[[rules]]" in text


def test_dump_profile_omits_crs_when_none(tmp_path: Path):
    profile = Profile(
        name="bare",
        ifc_schema="IFC4",
        rules=[],
    )
    out = tmp_path / "no_crs.toml"
    dump_profile(profile, out)
    text = out.read_text(encoding="utf-8")
    assert "[profile.crs]" not in text
    assert "crs" not in text.split("[[rules]]")[0]


def test_load_profile_round_trips_crs_and_storey_levels(tmp_path: Path):
    crs = CRSConfig(
        eastings_mm=25496000.0,
        northings_mm=6672000.0,
        orthogonal_height_mm=15000.0,
        scale=0.999,
    )
    profile = Profile(
        name="geo",
        ifc_schema="IFC4",
        rules=[],
        crs=crs,
        storey_z_levels_mm=[0.0, 3500.0, 7000.0],
    )
    out = tmp_path / "geo.toml"
    dump_profile(profile, out)
    reloaded = load_profile(out)
    assert reloaded.crs == crs
    assert reloaded.storey_z_levels_mm == [0.0, 3500.0, 7000.0]


def test_default_profile_storey_levels_default_single_zero():
    profile = load_default_profile()
    assert profile.storey_z_levels_mm == [0.0]
    assert profile.crs is None


# Removed test_load_default_tate_only_profile_drops_architecture:
# Bugfix-12 collapsed the two profiles into one (the default IS TATE-only
# now). The remaining test_default_profile_is_tate_only above covers
# the same intent on the canonical default profile.
