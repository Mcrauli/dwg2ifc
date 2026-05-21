"""Map AutoCAD block ATTRIB values into Finnish PSet fields.

AutoCAD's ``ATTDEF`` lets a block carry typed user fields (tag,
prompt, value) that travel with every instance in the DWG. The user
edits them post-placement via the Properties palette or by
double-clicking the block. dwg2ifc exposes the per-instance values as
``EntityRecord.block_attribs`` (tag → value) and this module routes
each tag to the right Finnish PSet:

- **FI_Tuote** — product identity. Tags: ``MALLI`` / ``LAITE`` /
  ``NIMI`` → ``nimi`` ("Tuotetyypin nimi"); ``VALMISTAJA``;
  ``KUVAUS``; ``KOMMENTTI``; ``LINKKI``.
- **FI_Tekninen** — technical specs (cooling capacity, voltage,
  refrigerant, …). Tag → canonical name via
  :func:`energy_specs._resolve_field_name`, the same alias system
  that handles Excel column headers, so an ATTDEF tag of
  ``LAUHDUTUSTEHO`` lands as ``Lauhdutusteho (kW)`` without extra
  config.

Conflict policy: ATTRIB values **override** any previously-set value
on the same canonical key (profile defaults, Excel rows). Per-instance
data is more specific than project-wide defaults. For FI_Tuote
"Tuotetyypin nimi" the precedence is: ``MALLI`` ATTRIB → profile-rule
``fi_tuote.nimi`` → per-IFC-type auto-label (``fi_tuote_default_nimi``).

Empty / whitespace-only ATTRIB values are ignored so a freshly placed
block with unset fields does not blank out a default or Excel value.
Tags that do not resolve through either alias system are skipped
silently — unknown tags leave no trace in the IFC.
"""

from __future__ import annotations

from typing import Iterable

from dwg2ifc.core.energy_specs import _resolve_field_name
from dwg2ifc.core.types import MappedEntity


# FI_Tuote alias map: ATTRIB field → tuple of accepted ATTDEF tags
# (uppercase). Multiple tags map to one field so users can type the
# one they remember in Finnish or English.
_FI_TUOTE_TAG_ALIASES: dict[str, tuple[str, ...]] = {
    # "Tuotetyypin nimi" — per-instance product name / model. Overrides
    # the per-IFC-type auto-label ("Koneikko", "Lauhdutin") that
    # finnish_psets.fi_tuote_default_nimi supplies when this is unset.
    "nimi": ("MALLI", "LAITE", "NIMI", "MODEL", "TUOTENIMI", "TUOTE"),
    # "Tuotetyypin valmistaja"
    "valmistaja": ("VALMISTAJA", "MANUFACTURER", "BRAND"),
    # "Tuotetyypin kuvaus"
    "kuvaus": ("KUVAUS", "DESCRIPTION", "DESC"),
    # "Tuotteen kommentti" — per-instance free note.
    "tuotteen_kommentti": ("KOMMENTTI", "COMMENT", "MUISTIINPANO"),
    # "Tuotetyypin valmistajan linkki" — datasheet / product page URL.
    "valmistajan_linkki": ("LINKKI", "LINK", "URL", "DATASHEET"),
}


# Inverse lookup: TAG (upper) → fi_tuote field name. Built once at
# import; ``resolve_fi_tuote_field`` just hits this dict.
_FI_TUOTE_TAG_TO_FIELD: dict[str, str] = {
    tag: field
    for field, tags in _FI_TUOTE_TAG_ALIASES.items()
    for tag in tags
}


def canonical_fi_tekninen_field(tag_or_header: str) -> str | None:
    """Resolve an ATTRIB tag (or Excel header) to its canonical
    FI_Tekninen field name with unit suffix.

    Returns ``None`` for unknown tags so callers can ignore them
    without leaking junk keys into the PSet.
    """
    if not tag_or_header:
        return None
    return _resolve_field_name(str(tag_or_header))


def resolve_fi_tuote_field(tag: str) -> str | None:
    """Resolve an ATTRIB tag to its FI_Tuote field name (or ``None``).

    Case-insensitive: ``MALLI`` / ``malli`` / ``Malli`` all match.
    """
    if not tag:
        return None
    return _FI_TUOTE_TAG_TO_FIELD.get(str(tag).strip().upper())


def apply_block_attribs(mapped: Iterable[MappedEntity]) -> None:
    """Route each non-empty ``block_attribs`` value into the right
    Finnish PSet on the MappedEntity, in place.

    Resolution order per tag:
      1. FI_Tuote — product-identity tags (MALLI, VALMISTAJA, …)
      2. FI_Tekninen — technical-spec tags via the energy_specs alias
         system (LAUHDUTUSTEHO, JANNITE, KYLMAAINE, …)
      3. Unrecognised — silently ignored

    ATTRIB values override anything previously set on the same
    canonical key (profile defaults, Excel rows).
    """
    for entity in mapped:
        attribs = entity.block_attribs or {}
        if not attribs:
            continue
        for tag, value in attribs.items():
            text = (value or "").strip()
            if not text:
                continue
            # 1. FI_Tuote — product identity (its tag set is checked
            #    first; the two alias systems do not share tags).
            tuote_field = resolve_fi_tuote_field(tag)
            if tuote_field is not None:
                if entity.fi_tuote is None:
                    entity.fi_tuote = {}
                entity.fi_tuote[tuote_field] = text
                continue
            # 2. FI_Tekninen — technical specs.
            tekninen_field = canonical_fi_tekninen_field(tag)
            if tekninen_field is not None:
                if entity.fi_tekninen is None:
                    entity.fi_tekninen = {}
                entity.fi_tekninen[tekninen_field] = text
                continue
            # 3. Unknown tag — silently ignored.
