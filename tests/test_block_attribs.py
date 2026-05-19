"""Tests for ATTRIB → FI_Tekninen merging.

AutoCAD ``ATTDEF`` lets a block carry user-typed tech-spec fields
that travel with each instance in the DWG and can be edited
post-placement via Properties palette. dwg2ifc reads
``INSERT.attribs`` into ``EntityRecord.block_attribs`` and this module
merges non-empty values into ``MappedEntity.fi_tekninen`` via the same
alias system used for Excel headers.
"""

from __future__ import annotations

from pathlib import Path

import ezdxf

from dwg2ifc.core.block_attribs import (
    apply_block_attribs,
    canonical_fi_tekninen_field,
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
