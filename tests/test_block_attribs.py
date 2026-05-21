"""Tests for ATTRIB → FI_Tuote / FI_Tekninen merging.

AutoCAD ``ATTDEF`` lets a block carry user-typed fields that travel
with each instance in the DWG and can be edited post-placement via
the Properties palette. dwg2ifc reads ``INSERT.attribs`` into
``EntityRecord.block_attribs`` and this module routes each tag to the
right Finnish PSet — FI_Tuote (product identity) or FI_Tekninen
(technical specs).
"""

from __future__ import annotations

from pathlib import Path

import ezdxf

from dwg2ifc.core.block_attribs import (
    apply_block_attribs,
    canonical_fi_tekninen_field,
    resolve_fi_tuote_field,
)
from dwg2ifc.core.dxf_reader import read_dxf
from dwg2ifc.core.types import (
    BlockInstance,
    MappedEntity,
    Point3D,
)


# --- canonical name resolution -----------------------------------------


def test_canonical_resolves_finnish_uppercase_tag():
    assert canonical_fi_tekninen_field("LAUHDUTUSTEHO") == "Lauhdutusteho (kW)"
    assert canonical_fi_tekninen_field("JANNITE") == "Jännite (V)"
    assert canonical_fi_tekninen_field("ILMAVIRTA") == "Ilmavirta (m³/h)"


def test_canonical_resolves_english_alias():
    assert canonical_fi_tekninen_field("VOLTAGE") == "Jännite (V)"
    assert canonical_fi_tekninen_field("REFRIGERANT") == "Kylmäaine"


def test_canonical_unknown_tag_returns_none():
    assert canonical_fi_tekninen_field("RANDOMSTUFF") is None
    assert canonical_fi_tekninen_field("") is None


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
    assert resolve_fi_tuote_field("RANDOMTAG") is None
    assert resolve_fi_tuote_field("") is None


# --- merge behaviour ---------------------------------------------------


def _evaporator_with_attribs(attribs: dict[str, str]) -> MappedEntity:
    """A bare cooling-equipment MappedEntity with the given ATTRIB map.

    Mirrors what dxf_reader produces for an INSERT carrying ATTDEFs:
    ``block_attribs`` populated, ``fi_tekninen`` initially None (the
    mapper has not yet populated profile defaults at the point this
    merge runs in the orchestrator pipeline).
    """
    return MappedEntity(
        layer="KYL-HOYRYSTIN",
        dxf_type="INSERT",
        geometry=BlockInstance(insertion_point=Point3D(0, 0, 0)),
        ifc_type="IfcEvaporator",
        block_attribs=attribs,
    )


def test_apply_block_attribs_merges_into_empty_fi_tekninen():
    e = _evaporator_with_attribs({"JAAHDYTYSTEHO": "12.5", "JANNITE": "400"})
    apply_block_attribs([e])
    assert e.fi_tekninen == {
        "Jäähdytysteho (kW)": "12.5",
        "Jännite (V)": "400",
    }


def test_apply_block_attribs_strips_whitespace_values():
    e = _evaporator_with_attribs({"JAAHDYTYSTEHO": "  12.5  "})
    apply_block_attribs([e])
    assert e.fi_tekninen == {"Jäähdytysteho (kW)": "12.5"}


def test_apply_block_attribs_skips_empty_values():
    # Freshly-placed block: ATTDEFs created but user has not filled in
    # values yet. Must NOT blank out existing Excel-supplied data.
    e = _evaporator_with_attribs({"JAAHDYTYSTEHO": "", "JANNITE": "   "})
    e.fi_tekninen = {"Jäähdytysteho (kW)": "from-excel"}
    apply_block_attribs([e])
    assert e.fi_tekninen == {"Jäähdytysteho (kW)": "from-excel"}


def test_apply_block_attribs_overrides_excel_for_known_tag():
    # Per-block specifity wins over project-wide spreadsheet rows.
    e = _evaporator_with_attribs({"JAAHDYTYSTEHO": "20.0"})
    e.fi_tekninen = {"Jäähdytysteho (kW)": "12.5"}
    apply_block_attribs([e])
    assert e.fi_tekninen["Jäähdytysteho (kW)"] == "20.0"


def test_apply_block_attribs_skips_unknown_tags():
    # An unrecognised tag is ignored — does not leak into the PSet.
    e = _evaporator_with_attribs({"NOTAFIELD": "junk", "JANNITE": "400"})
    e.fi_tekninen = {}
    apply_block_attribs([e])
    assert e.fi_tekninen == {"Jännite (V)": "400"}


def test_apply_block_attribs_handles_empty_list():
    apply_block_attribs([])  # no crash


def test_apply_block_attribs_skips_entities_without_attribs():
    e = _evaporator_with_attribs({})  # default empty block_attribs
    e.fi_tekninen = {"Jäähdytysteho (kW)": "from-excel"}
    apply_block_attribs([e])
    assert e.fi_tekninen == {"Jäähdytysteho (kW)": "from-excel"}


# --- FI_Tuote merging --------------------------------------------------


def test_apply_block_attribs_routes_malli_into_fi_tuote_nimi():
    e = _evaporator_with_attribs({"MALLI": "KOJU-100"})
    apply_block_attribs([e])
    assert e.fi_tuote == {"nimi": "KOJU-100"}
    assert e.fi_tekninen is None  # nothing leaked into the tech PSet


def test_apply_block_attribs_routes_valmistaja_into_fi_tuote():
    e = _evaporator_with_attribs({"VALMISTAJA": "Polar"})
    apply_block_attribs([e])
    assert e.fi_tuote == {"valmistaja": "Polar"}


def test_apply_block_attribs_malli_overrides_profile_fi_tuote_nimi():
    # Per-instance MALLI wins over the profile-rule / auto-label name.
    e = _evaporator_with_attribs({"MALLI": "MEKA KOJU-100"})
    e.fi_tuote = {"nimi": "Höyrystin", "valmistaja": "MEKA"}
    apply_block_attribs([e])
    assert e.fi_tuote == {"nimi": "MEKA KOJU-100", "valmistaja": "MEKA"}


def test_apply_block_attribs_skips_empty_fi_tuote_value():
    # Empty FI_Tuote ATTRIB must not blank out an existing value.
    e = _evaporator_with_attribs({"MALLI": "   "})
    e.fi_tuote = {"nimi": "from-profile"}
    apply_block_attribs([e])
    assert e.fi_tuote == {"nimi": "from-profile"}


def test_apply_block_attribs_merges_tuote_and_tekninen_together():
    e = _evaporator_with_attribs({
        "MALLI": "Polar XYZ-100",
        "VALMISTAJA": "Polar",
        "LAUHDUTUSTEHO": "30",
        "JANNITE": "400",
    })
    apply_block_attribs([e])
    assert e.fi_tuote == {"nimi": "Polar XYZ-100", "valmistaja": "Polar"}
    assert e.fi_tekninen == {
        "Lauhdutusteho (kW)": "30",
        "Jännite (V)": "400",
    }


# --- end-to-end through dxf_reader -------------------------------------


def test_dxf_reader_captures_block_attribs(tmp_path: Path):
    """An INSERT with ATTRIB subentities must surface them in
    ``EntityRecord.block_attribs``."""
    doc = ezdxf.new("R2018")
    doc.layers.add(name="KYL-LAUHDUTIN")
    blk = doc.blocks.new(name="LAUHDUTIN")
    # ATTDEF defines the typed field carried by the block. The Attrib
    # subentity copies the tag onto the INSERT instance.
    blk.add_attdef("LAUHDUTUSTEHO", insert=(0, 0, 0), text="0")
    blk.add_attdef("JANNITE", insert=(0, 10, 0), text="0")
    blk.add_attdef("KYLMAAINE", insert=(0, 20, 0), text="")
    insert = doc.modelspace().add_blockref(
        "LAUHDUTIN",
        (5000, 4000, 0),
        dxfattribs={"layer": "KYL-LAUHDUTIN"},
    )
    insert.add_auto_attribs(
        {"LAUHDUTUSTEHO": "30.5", "JANNITE": "400", "KYLMAAINE": "R744"}
    )
    p = tmp_path / "lauhdutin.dxf"
    doc.saveas(str(p))

    records = read_dxf(p)
    inserts = [r for r in records if r.dxf_type == "INSERT"]
    assert len(inserts) == 1
    assert inserts[0].block_attribs == {
        "LAUHDUTUSTEHO": "30.5",
        "JANNITE": "400",
        "KYLMAAINE": "R744",
    }
