"""Unit tests for profiles.loader."""

from pathlib import Path

import pytest

from dxf2ifc.profiles.loader import dump_profile, load_default_profile, load_profile
from dxf2ifc.profiles.schema import Profile


def test_default_profile_resource_uses_new_name():
    from importlib import resources

    package_files = resources.files("dxf2ifc.profiles")
    assert package_files.joinpath("default_kylmalaite.toml").is_file()
    assert not package_files.joinpath("default_kylmalaite_talo2000.toml").is_file()


def test_default_profile_marks_ark_rules_with_domain():
    profile = load_default_profile()
    ark_layers = {
        "KYL-ULKOSEINA*",
        "KYL-VALISEINA*",
        "KYL-LASIVALISEINA*",
        "KYL-ALAPOHJA*",
        "KYL-VALIPOHJA*",
        "KYL-YLAPOHJA*",
        "KYL-OVET-ULKO*",
        "KYL-OVET-VALI*",
        "KYL-OVET-ERITYIS*",
        "KYL-IKKUNA*",
        "KYL-TIKASHYLLY-V*",
        "KYL-TIKASHYLLY*",
        "KYL-LEVYHYLLY*",
        "KYL-LEVY*",
        "KYL-NURKKA*",
        "AR1241_US",
        "AR1242_IKKUNA",
        "AR1245_LASIUS",
        "AR1311_VS",
        "AR1233_PILARI",
        "AR1314_KAIDE",
        "AR1317_TILAPORTAAT",
        "AR1331_KIINTO",
        "K-OVET",
        "K-SEINÄT_VÄLISEINÄT",
        "K-KALUSTEET",
        "K-KIINTOKALUSTEET",
        "K-RST-KALUSTEET",
        "K-VALAISTUS",
    }
    by_layer = {r.layer_pattern: r for r in profile.rules}
    for layer in ark_layers:
        assert layer in by_layer, f"missing ARK rule for {layer}"
        rule = by_layer[layer]
        assert rule.domain == "ARK", f"{layer}: expected domain ARK, got {rule.domain}"
        assert rule.talo2000_code, f"{layer}: ARK rule must keep talo2000_code"


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


def test_load_default_profile_has_slab_rules():
    profile = load_default_profile()
    by_layer = {r.layer_pattern: r for r in profile.rules}
    ap = by_layer["KYL-ALAPOHJA*"]
    assert ap.entity_kind == "POLYLINE"
    assert ap.ifc_type == "IfcSlab"
    assert ap.predefined_type == "FLOOR"
    assert ap.talo2000_code == "1221"
    vp = by_layer["KYL-VALIPOHJA*"]
    assert vp.ifc_type == "IfcSlab"
    assert vp.predefined_type == "FLOOR"
    assert vp.talo2000_code == "1235"
    yp = by_layer["KYL-YLAPOHJA*"]
    assert yp.ifc_type == "IfcSlab"
    assert yp.predefined_type == "ROOF"
    assert yp.talo2000_code == "1236"


def test_load_default_profile_has_door_rules():
    profile = load_default_profile()
    by_layer = {r.layer_pattern: r for r in profile.rules}
    ulko = by_layer["KYL-OVET-ULKO*"]
    assert ulko.entity_kind == "INSERT"
    assert ulko.block_name == "OVI-ULKO"
    assert ulko.ifc_type == "IfcDoor"
    assert ulko.talo2000_code == "1243"
    vali = by_layer["KYL-OVET-VALI*"]
    assert vali.entity_kind == "INSERT"
    assert vali.block_name == "OVI-VALI"
    assert vali.talo2000_code == "1315"
    erityis = by_layer["KYL-OVET-ERITYIS*"]
    assert erityis.entity_kind == "INSERT"
    assert erityis.block_name == "OVI-ERITYIS"
    assert erityis.talo2000_code == "1316"


def test_load_default_profile_has_window_rule():
    profile = load_default_profile()
    by_layer = {r.layer_pattern: r for r in profile.rules}
    ikkuna = by_layer["KYL-IKKUNA*"]
    assert ikkuna.entity_kind == "INSERT"
    assert ikkuna.block_name == "IKKUNA"
    assert ikkuna.ifc_type == "IfcWindow"
    assert ikkuna.talo2000_code == "1242"
    assert ikkuna.talo2000_name == "Ikkunat"


def test_load_default_profile_has_pipe_segment_rules():
    profile = load_default_profile()
    by_layer = {r.layer_pattern: r for r in profile.rules}
    lt = by_layer["LT IMU"]
    assert lt.ifc_type == "IfcPipeSegment"
    assert lt.predefined_type == "REFRIGERATION"
    assert lt.domain == "TATE"
    assert lt.lvi_code == "T-LVI-02"
    assert lt.talo2000_code is None
    assert lt.system_name == "Refrigeration LT"
    assert lt.pset_overrides["Pset_PipeSegmentOccurrence"]["NominalDiameter"] == 22.0
    mt_imu = by_layer["MT IMU"]
    assert mt_imu.domain == "TATE"
    assert mt_imu.lvi_code == "T-LVI-02"
    assert mt_imu.system_name == "Refrigeration MT"
    mt_neste = by_layer["MT NESTE"]
    assert mt_neste.domain == "TATE"
    assert mt_neste.lvi_code == "T-LVI-02"
    assert mt_neste.system_name == "Refrigeration MT"
    assert mt_neste.pset_overrides["Pset_PipeSegmentOccurrence"]["NominalDiameter"] == 12.0


def test_load_default_profile_has_drainpipe_rule():
    profile = load_default_profile()
    by_layer = {r.layer_pattern: r for r in profile.rules}
    drain = by_layer["KYL-VIEMARI*"]
    assert drain.ifc_type == "IfcPipeSegment"
    assert drain.predefined_type == "DRAINPIPE"
    assert drain.domain == "TATE"
    assert drain.lvi_code == "T-LVI-04-01-001"
    assert drain.talo2000_code is None
    assert drain.system_name == "Drainage"
    assert drain.pset_overrides["Pset_PipeSegmentOccurrence"]["NominalDiameter"] == 110.0


def test_load_default_profile_has_storage_furniture_rules():
    profile = load_default_profile()
    by_layer = {r.layer_pattern: r for r in profile.rules}
    levy = by_layer["KYL-LEVYHYLLY*"]
    assert levy.entity_kind == "INSERT"
    assert levy.block_name == "KLHYLLY-LEVY"
    assert levy.ifc_type == "IfcFurniture"
    assert levy.talo2000_code == "1331"
    tikas = by_layer["KYL-TIKASHYLLY*"]
    assert tikas.block_name == "KLHYLLY-TIKAS"
    tikas_v = by_layer["KYL-TIKASHYLLY-V*"]
    assert tikas_v.block_name == "KLHYLLYV"
    # Vertical rule must precede horizontal rule for first-match resolution.
    assert profile.rules.index(tikas_v) < profile.rules.index(tikas)


def test_load_default_profile_has_cable_carrier_rule():
    profile = load_default_profile()
    by_layer = {r.layer_pattern: r for r in profile.rules}
    cable = by_layer["KAAPELIHYLLY*"]
    assert cable.ifc_type == "IfcCableCarrierSegment"
    assert cable.predefined_type == "CABLETRUNKINGSEGMENT"
    assert cable.domain == "TATE"
    assert cable.talotekniikka_code == "T-TATE-01-01-001"
    assert cable.talo2000_code is None
    assert cable.system_name == "Cable carriers"


def test_load_default_profile_has_cold_room_panel_rules():
    profile = load_default_profile()
    by_layer = {r.layer_pattern: r for r in profile.rules}
    levy = by_layer["KYL-LEVY*"]
    assert levy.entity_kind == "POLYLINE"
    assert levy.ifc_type == "IfcBuildingElementProxy"
    assert levy.talo2000_code == "1352"
    nurkka = by_layer["KYL-NURKKA*"]
    assert nurkka.entity_kind == "POLYLINE"
    assert nurkka.ifc_type == "IfcBuildingElementProxy"
    assert nurkka.talo2000_code == "1352"


def test_load_default_profile_has_cooling_equipment_rules():
    profile = load_default_profile()
    by_layer = {r.layer_pattern: r for r in profile.rules}
    hoyr = by_layer["KYL-HOYRYSTIN*"]
    assert hoyr.ifc_type == "IfcEvaporator"
    assert hoyr.block_name == "HOYRYSTIN"
    assert hoyr.domain == "TATE"
    assert hoyr.lvi_code == "T-LVI-01-01-023"
    assert hoyr.talo2000_code is None
    assert hoyr.system_name == "Refrigeration plant"
    lauh = by_layer["KYL-LAUHDUTIN*"]
    assert lauh.ifc_type == "IfcCondenser"
    assert lauh.domain == "TATE"
    assert lauh.lvi_code == "T-LVI-01-01-018"
    assert lauh.talo2000_code is None
    assert lauh.system_name == "Refrigeration plant"
    komp = by_layer["KYL-KOMPRESSORI*"]
    assert komp.ifc_type == "IfcCompressor"
    assert komp.domain == "TATE"
    assert komp.lvi_code == "T-LVI-01-01-017"
    assert komp.talo2000_code is None
    assert komp.system_name == "Refrigeration plant"


def test_load_default_profile_has_partition_wall_rules():
    profile = load_default_profile()
    by_layer = {r.layer_pattern: r for r in profile.rules}
    valiseina = by_layer["KYL-VALISEINA*"]
    assert valiseina.ifc_type == "IfcWall"
    assert valiseina.predefined_type == "PARTITIONING"
    assert valiseina.talo2000_code == "1311"
    lasi = by_layer["KYL-LASIVALISEINA*"]
    assert lasi.ifc_type == "IfcWall"
    assert lasi.predefined_type == "PARTITIONING"
    assert lasi.talo2000_code == "1312"


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
