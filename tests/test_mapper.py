"""Unit tests for core.mapper."""

import pytest

from dwg2ifc.core.mapper import apply_profile, layer_matches
from dwg2ifc.core.types import (
    BlockAttrib,
    BlockInstance,
    EntityRecord,
    LineGeometry,
    Point3D,
)
from dwg2ifc.profiles.loader import load_default_profile
from dwg2ifc.profiles.schema import Profile, Rule


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


def test_apply_profile_maps_storage_shelves_via_default_profile():
    """Bugfix 12: cold-storage shelves map to IfcCableCarrierSegment per
    Granlund convention (CABLELADDERSEGMENT for tikashylly, CABLETRAYSEGMENT
    for levyhylly)."""
    profile = load_default_profile()
    entities = [
        _sample_line_record(layer="KYL-LEVYHYLLY-1500"),
        _sample_line_record(layer="KYL-TIKASHYLLY-2000"),
        _sample_line_record(layer="KYL-TIKASHYLLY-V-2200"),
    ]
    mapped = apply_profile(entities, profile)
    by_layer = {m.layer: m for m in mapped}
    levy = by_layer["KYL-LEVYHYLLY-1500"]
    assert levy.ifc_type == "IfcCableCarrierSegment"
    assert levy.predefined_type == "CABLETRAYSEGMENT"
    assert levy.talotekniikka_code == "T-TATE-01-01-001"
    tikas = by_layer["KYL-TIKASHYLLY-2000"]
    assert tikas.ifc_type == "IfcCableCarrierSegment"
    assert tikas.predefined_type == "CABLELADDERSEGMENT"
    tikas_v = by_layer["KYL-TIKASHYLLY-V-2200"]
    assert tikas_v.predefined_type == "CABLELADDERSEGMENT"


def test_apply_profile_maps_kotelo_via_default_profile():
    """Kotelo (enclosed cable trunking) maps to IfcCableCarrierSegment with
    CABLETRUNKINGSEGMENT — distinct from the open LADDER/TRAY shelves."""
    profile = load_default_profile()
    entities = [_sample_line_record(layer="KYL-KOTELO-1200")]
    mapped = apply_profile(entities, profile)
    kotelo = {m.layer: m for m in mapped}["KYL-KOTELO-1200"]
    assert kotelo.ifc_type == "IfcCableCarrierSegment"
    assert kotelo.predefined_type == "CABLETRUNKINGSEGMENT"
    assert kotelo.talotekniikka_code == "T-TATE-01-01-001"
    # Same FI_* PSet shape as KYL-LEVYHYLLY so Solibri's tuoteosa view
    # finds Materiaali + Pinnoite + nimi + valmistaja on a kotelo too.
    assert kotelo.fi_tekninen is not None
    assert kotelo.fi_tekninen.get("Materiaali") == "Teräs"
    assert kotelo.fi_tekninen.get("Pinnoite") == "Polyesterimaalattu"
    assert kotelo.fi_tuote is not None
    assert kotelo.fi_tuote.get("nimi") == "Kotelo"
    assert kotelo.fi_tuote.get("valmistaja") == "MEKA"


def test_apply_profile_propagates_block_attribs_to_mapped_entity():
    """Mapper must carry INSERT ATTRIB records across to the
    MappedEntity so the orchestrator's apply_block_attribs step has
    something to route into the FI PSets. Forgetting to copy this field
    silently dropped every per-device tech-spec value the user typed
    into BricsCAD's Properties palette (regression observed v0.3.0a5)."""
    profile = load_default_profile()
    attribs = [
        BlockAttrib(tag="TEHO", prompt="TEHO [KW]", value="30"),
        BlockAttrib(tag="JANNITE", prompt="JANNITE [V]", value="400"),
    ]
    record = EntityRecord(
        layer="KYL-LAUHDUTIN",
        dxf_type="INSERT",
        geometry=BlockInstance(insertion_point=Point3D(0, 0, 0)),
        block_attribs=attribs,
    )
    mapped = apply_profile([record], profile)
    assert len(mapped) == 1
    assert mapped[0].block_attribs == attribs


def test_hole_reservation_layer_maps_to_ifc_provision_for_void():
    profile = load_default_profile()
    entity = EntityRecord(
        layer="KYL-REIKAVARAUS",
        dxf_type="INSERT",
        geometry=BlockInstance(insertion_point=Point3D(1000.0, 2000.0, 3000.0)),
        block_name="REIKAVARAUS",
        handle="ABCD",
    )

    mapped = apply_profile([entity], profile)

    assert len(mapped) == 1
    assert mapped[0].ifc_type == "IfcProvisionForVoid"
    assert mapped[0].talotekniikka_code == "T-TATE-02-01-001"
    assert mapped[0].fi_komponentti["yleisnimi"] == "Reikävaraus"
    assert mapped[0].fi_komponentti["yleistunnus"] == "RV"


def test_apply_profile_propagates_system_name_to_extra_props():
    profile = Profile(
        name="system",
        ifc_schema="IFC4",
        rules=[
            Rule(
                layer_pattern="LT IMU",
                ifc_type="IfcPipeSegment",
                predefined_type="REFRIGERATION",
                talo2000_code="2151",
                talo2000_name="Putkiosat — kylmäimu",
                system_name="Refrigeration LT",
            ),
        ],
    )
    record = EntityRecord(
        layer="LT IMU",
        dxf_type="LINE",
        geometry=LineGeometry(start=Point3D(0, 0, 0), end=Point3D(1000, 0, 0)),
    )
    mapped = apply_profile([record], profile)
    assert len(mapped) == 1
    assert mapped[0].extra_props["system_name"] == "Refrigeration LT"


def test_apply_profile_maps_cooling_equipment_blocks_via_default_profile():
    profile = load_default_profile()
    entities = [
        EntityRecord(
            layer="KYL-HOYRYSTIN-CR-30",
            dxf_type="INSERT",
            geometry=BlockInstance(insertion_point=Point3D(0, 0, 0)),
            block_name="HOYRYSTIN",
        ),
        EntityRecord(
            layer="KYL-LAUHDUTIN-EXT",
            dxf_type="INSERT",
            geometry=BlockInstance(insertion_point=Point3D(5000, 0, 0)),
            block_name="LAUHDUTIN",
        ),
        EntityRecord(
            layer="KYL-KOMPRESSORI-1",
            dxf_type="INSERT",
            geometry=BlockInstance(insertion_point=Point3D(0, 5000, 0)),
            block_name="KOMPRESSORI",
        ),
    ]
    mapped = apply_profile(entities, profile)
    by_ifc = {m.ifc_type: m for m in mapped}
    # Cooling equipment is KYL-domain (kylmälaitesuunnittelu) with RAVA lvi_code.
    assert by_ifc["IfcEvaporator"].domain == "KYL"
    assert by_ifc["IfcEvaporator"].lvi_code == "T-LVI-01-01-023"
    assert by_ifc["IfcEvaporator"].talo2000_code is None
    assert by_ifc["IfcCondenser"].lvi_code == "T-LVI-01-01-018"
    assert by_ifc["IfcCompressor"].lvi_code == "T-LVI-01-01-017"


def test_apply_profile_default_profile_emits_four_distinct_system_names():
    profile = load_default_profile()
    entities = [
        EntityRecord(
            layer="LT IMU",
            dxf_type="LINE",
            geometry=LineGeometry(start=Point3D(0, 0, 0), end=Point3D(1000, 0, 0)),
        ),
        EntityRecord(
            layer="MT IMU",
            dxf_type="LINE",
            geometry=LineGeometry(start=Point3D(0, 0, 0), end=Point3D(1000, 0, 0)),
        ),
        EntityRecord(
            layer="KYL-VIEMARI-LATTIA",
            dxf_type="LINE",
            geometry=LineGeometry(start=Point3D(0, 0, 0), end=Point3D(1000, 0, 0)),
        ),
        EntityRecord(
            layer="KAAPELIHYLLY",
            dxf_type="LINE",
            geometry=LineGeometry(start=Point3D(0, 0, 0), end=Point3D(1000, 0, 0)),
        ),
        EntityRecord(
            layer="KYL-HOYRYSTIN",
            dxf_type="INSERT",
            geometry=BlockInstance(insertion_point=Point3D(0, 0, 0)),
            block_name="HOYRYSTIN",
        ),
    ]
    mapped = apply_profile(entities, profile)
    systems = {m.layer: m.extra_props.get("system_name") for m in mapped}
    assert systems["LT IMU"] == "Refrigeration LT"
    assert systems["MT IMU"] == "Refrigeration MT"
    assert systems["KYL-VIEMARI-LATTIA"] == "Drainage"
    assert systems["KAAPELIHYLLY"] == "Cable carriers"
    assert systems["KYL-HOYRYSTIN"] == "Refrigeration plant"


def test_apply_profile_propagates_domain_and_rava_codes():
    profile = Profile(
        name="domain",
        ifc_schema="IFC4",
        rules=[
            Rule(
                layer_pattern="AR1241_US*",
                ifc_type="IfcWall",
                domain="ARK",
                talo2000_code="1241",
                talo2000_name="Ulkoseinät",
            ),
            Rule(
                layer_pattern="KYL-HOYRYSTIN*",
                ifc_type="IfcEvaporator",
                entity_kind="INSERT",
                block_name="HOYRYSTIN",
                domain="TATE",
                lvi_code="T-LVI-01-01-023",
            ),
            Rule(
                layer_pattern="KAAPELIHYLLY*",
                ifc_type="IfcCableCarrierSegment",
                domain="TATE",
                talotekniikka_code="T-TATE-01-01-001",
            ),
        ],
    )
    entities = [
        _sample_line_record(layer="AR1241_US"),
        EntityRecord(
            layer="KYL-HOYRYSTIN",
            dxf_type="INSERT",
            geometry=BlockInstance(insertion_point=Point3D(0, 0, 0)),
            block_name="HOYRYSTIN",
        ),
        _sample_line_record(layer="KAAPELIHYLLY"),
    ]
    mapped = apply_profile(entities, profile)
    by_layer = {m.layer: m for m in mapped}
    ark = by_layer["AR1241_US"]
    assert ark.domain == "ARK"
    assert ark.talo2000_code == "1241"
    assert ark.lvi_code is None
    assert ark.talotekniikka_code is None
    hoyr = by_layer["KYL-HOYRYSTIN"]
    assert hoyr.domain == "TATE"
    assert hoyr.lvi_code == "T-LVI-01-01-023"
    assert hoyr.talo2000_code is None
    assert hoyr.talotekniikka_code is None
    kaapeli = by_layer["KAAPELIHYLLY"]
    assert kaapeli.domain == "TATE"
    assert kaapeli.talotekniikka_code == "T-TATE-01-01-001"
    assert kaapeli.lvi_code is None
    assert kaapeli.talo2000_code is None
