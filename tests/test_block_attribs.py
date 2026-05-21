"""Tests for ATTRIB → FI_Tuote / FI_Tekninen routing.

AutoCAD ``ATTDEF`` lets a block carry user-typed fields (tag, prompt,
value) that travel with each instance in the DWG. dwg2ifc reads
``INSERT.attribs`` into ``EntityRecord.block_attribs`` as a list of
:class:`~dwg2ifc.core.types.BlockAttrib` records and
:func:`apply_block_attribs` routes each one — FI_Tuote (product
identity, by tag) or FI_Tekninen (every other field, verbatim, with the
ATTDEF prompt as the Solibri label).
"""

from __future__ import annotations

from pathlib import Path

import ezdxf

from dwg2ifc.core.block_attribs import apply_block_attribs, resolve_fi_tuote_field
from dwg2ifc.core.dxf_reader import read_dxf
from dwg2ifc.core.types import (
    BlockAttrib,
    BlockInstance,
    MappedEntity,
    Point3D,
)


# --- FI_Tuote tag resolution -------------------------------------------


def test_resolve_fi_tuote_nimi_aliases():
    # "Tuotetyypin nimi" — per-instance product name / model.
    assert resolve_fi_tuote_field("MALLI") == "nimi"
    assert resolve_fi_tuote_field("LAITE") == "nimi"
    assert resolve_fi_tuote_field("NIMI") == "nimi"
    assert resolve_fi_tuote_field("MODEL") == "nimi"


def test_resolve_fi_tuote_other_fields():
    assert resolve_fi_tuote_field("VALMISTAJA") == "valmistaja"
    assert resolve_fi_tuote_field("KUVAUS") == "kuvaus"
    assert resolve_fi_tuote_field("KOMMENTTI") == "tuotteen_kommentti"
    assert resolve_fi_tuote_field("LINKKI") == "valmistajan_linkki"


def test_resolve_fi_tuote_case_insensitive():
    assert resolve_fi_tuote_field("valmistaja") == "valmistaja"
    assert resolve_fi_tuote_field("Malli") == "nimi"


def test_resolve_fi_tuote_unknown_returns_none():
    assert resolve_fi_tuote_field("RAKENNEPAINE") is None
    assert resolve_fi_tuote_field("") is None


# --- helpers -----------------------------------------------------------


def _equipment_with_attribs(attribs: list[BlockAttrib]) -> MappedEntity:
    """A bare cooling-equipment MappedEntity carrying the given ATTRIBs.

    Mirrors what dxf_reader + mapper produce for an INSERT with
    ATTDEFs: ``block_attribs`` populated, FI PSets initially None.
    """
    return MappedEntity(
        layer="KYL-LAUHDUTIN",
        dxf_type="INSERT",
        geometry=BlockInstance(insertion_point=Point3D(0, 0, 0)),
        ifc_type="IfcCondenser",
        block_attribs=attribs,
    )


# --- FI_Tekninen routing -----------------------------------------------


def test_attrib_uses_prompt_as_label():
    e = _equipment_with_attribs(
        [BlockAttrib(tag="TEHO[KW]", prompt="TEHO [KW]", value="30")]
    )
    apply_block_attribs([e])
    assert e.fi_tekninen == {"TEHO [KW]": "30"}


def test_attrib_falls_back_to_tag_when_prompt_empty():
    e = _equipment_with_attribs(
        [BlockAttrib(tag="KYLMAAINE", prompt="", value="R744")]
    )
    apply_block_attribs([e])
    assert e.fi_tekninen == {"KYLMAAINE": "R744"}


def test_attrib_no_alias_misrouting():
    # Regression: the old energy-spec alias system substring-matched
    # "RAKENNEPAINE" onto "Kylmäaine" via the "aine" alias. The verbatim
    # router must keep the field under its own prompt.
    e = _equipment_with_attribs(
        [BlockAttrib(tag="RAKENNEPAINE[BAR]", prompt="RAKENNEPAINE [BAR]", value="40")]
    )
    apply_block_attribs([e])
    assert e.fi_tekninen == {"RAKENNEPAINE [BAR]": "40"}


def test_attrib_strips_whitespace_value():
    e = _equipment_with_attribs(
        [BlockAttrib(tag="TEHO", prompt="Teho (kW)", value="  12.5  ")]
    )
    apply_block_attribs([e])
    assert e.fi_tekninen == {"Teho (kW)": "12.5"}


def test_attrib_empty_value_kept_as_placeholder():
    # A freshly placed block with unfilled fields still shows the field
    # list in Solibri — the technical tab acts as a spec sheet.
    e = _equipment_with_attribs(
        [BlockAttrib(tag="TEHO", prompt="Teho (kW)", value="")]
    )
    apply_block_attribs([e])
    assert e.fi_tekninen == {"Teho (kW)": ""}


def test_attrib_empty_value_does_not_clobber_existing():
    # An unfilled ATTRIB must not blank an energy-spec Excel value.
    e = _equipment_with_attribs(
        [BlockAttrib(tag="TEHO", prompt="Teho (kW)", value="")]
    )
    e.fi_tekninen = {"Teho (kW)": "from-excel"}
    apply_block_attribs([e])
    assert e.fi_tekninen == {"Teho (kW)": "from-excel"}


def test_attrib_nonempty_value_overrides_existing():
    e = _equipment_with_attribs(
        [BlockAttrib(tag="TEHO", prompt="Teho (kW)", value="20.0")]
    )
    e.fi_tekninen = {"Teho (kW)": "12.5"}
    apply_block_attribs([e])
    assert e.fi_tekninen["Teho (kW)"] == "20.0"


def test_attrib_preserves_order():
    e = _equipment_with_attribs(
        [
            BlockAttrib(tag="A", prompt="Eka", value="1"),
            BlockAttrib(tag="B", prompt="Toka", value="2"),
            BlockAttrib(tag="C", prompt="Kolmas", value="3"),
        ]
    )
    apply_block_attribs([e])
    assert list(e.fi_tekninen.keys()) == ["Eka", "Toka", "Kolmas"]


def test_apply_block_attribs_handles_empty_list():
    apply_block_attribs([])  # no crash


def test_apply_block_attribs_skips_entities_without_attribs():
    e = _equipment_with_attribs([])  # default empty block_attribs
    e.fi_tekninen = {"Teho (kW)": "from-excel"}
    apply_block_attribs([e])
    assert e.fi_tekninen == {"Teho (kW)": "from-excel"}


# --- FI_Tuote routing --------------------------------------------------


def test_attrib_routes_malli_into_fi_tuote_nimi():
    e = _equipment_with_attribs(
        [BlockAttrib(tag="MALLI", prompt="", value="KOJU-100")]
    )
    apply_block_attribs([e])
    assert e.fi_tuote == {"nimi": "KOJU-100"}
    assert e.fi_tekninen is None  # nothing leaked into the tech PSet


def test_attrib_routes_valmistaja_into_fi_tuote():
    e = _equipment_with_attribs(
        [BlockAttrib(tag="VALMISTAJA", prompt="", value="Polar")]
    )
    apply_block_attribs([e])
    assert e.fi_tuote == {"valmistaja": "Polar"}


def test_attrib_malli_overrides_profile_fi_tuote_nimi():
    e = _equipment_with_attribs(
        [BlockAttrib(tag="MALLI", prompt="", value="MEKA KOJU-100")]
    )
    e.fi_tuote = {"nimi": "Lauhdutin", "valmistaja": "MEKA"}
    apply_block_attribs([e])
    assert e.fi_tuote == {"nimi": "MEKA KOJU-100", "valmistaja": "MEKA"}


def test_attrib_skips_empty_fi_tuote_value():
    # An empty FI_Tuote ATTRIB must not blank an existing value.
    e = _equipment_with_attribs([BlockAttrib(tag="MALLI", prompt="", value="   ")])
    e.fi_tuote = {"nimi": "from-profile"}
    apply_block_attribs([e])
    assert e.fi_tuote == {"nimi": "from-profile"}


def test_attrib_merges_tuote_and_tekninen_together():
    e = _equipment_with_attribs(
        [
            BlockAttrib(tag="MALLI", prompt="", value="Polar XYZ-100"),
            BlockAttrib(tag="VALMISTAJA", prompt="", value="Polar"),
            BlockAttrib(tag="TEHO[KW]", prompt="TEHO [KW]", value="30"),
            BlockAttrib(tag="RAKENNEPAINE[BAR]", prompt="RAKENNEPAINE [BAR]", value="40"),
        ]
    )
    apply_block_attribs([e])
    assert e.fi_tuote == {"nimi": "Polar XYZ-100", "valmistaja": "Polar"}
    assert e.fi_tekninen == {"TEHO [KW]": "30", "RAKENNEPAINE [BAR]": "40"}


# --- end-to-end through dxf_reader -------------------------------------


def test_dxf_reader_captures_block_attribs_with_prompts(tmp_path: Path):
    """An INSERT with ATTRIB subentities must surface them in
    ``EntityRecord.block_attribs``, with the prompt copied across from
    the block definition's ATTDEFs."""
    doc = ezdxf.new("R2018")
    doc.layers.add(name="KYL-LAUHDUTIN")
    blk = doc.blocks.new(name="LAUHDUTIN")
    # ATTDEF carries tag + prompt + default; the prompt is the
    # human-readable Solibri label dwg2ifc must pick up.
    blk.add_attdef(
        "TEHO[KW]", insert=(0, 0, 0), text="0",
        dxfattribs={"prompt": "TEHO [KW]"},
    )
    blk.add_attdef(
        "RAKENNEPAINE[BAR]", insert=(0, 10, 0), text="0",
        dxfattribs={"prompt": "RAKENNEPAINE [BAR]"},
    )
    # No prompt on this one — routing must fall back to the tag.
    blk.add_attdef("KYLMAAINE", insert=(0, 20, 0), text="")
    insert = doc.modelspace().add_blockref(
        "LAUHDUTIN",
        (5000, 4000, 0),
        dxfattribs={"layer": "KYL-LAUHDUTIN"},
    )
    insert.add_auto_attribs(
        {"TEHO[KW]": "30.5", "RAKENNEPAINE[BAR]": "40", "KYLMAAINE": "R744"}
    )
    p = tmp_path / "lauhdutin.dxf"
    doc.saveas(str(p))

    records = read_dxf(p)
    inserts = [r for r in records if r.dxf_type == "INSERT"]
    assert len(inserts) == 1

    by_tag = {ba.tag: ba for ba in inserts[0].block_attribs}
    assert by_tag["TEHO[KW]"].prompt == "TEHO [KW]"
    assert by_tag["TEHO[KW]"].value == "30.5"
    assert by_tag["RAKENNEPAINE[BAR]"].prompt == "RAKENNEPAINE [BAR]"
    assert by_tag["RAKENNEPAINE[BAR]"].value == "40"
    # ATTDEF without a prompt → empty prompt, value still captured.
    assert by_tag["KYLMAAINE"].prompt == ""
    assert by_tag["KYLMAAINE"].value == "R744"
