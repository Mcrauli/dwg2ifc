"""Map AutoCAD block ATTRIB values into FI_Tekninen fields.

AutoCAD's ``ATTDEF`` lets a block carry typed user fields (tag,
prompt, value) that travel with every instance in the DWG. The user
edits them post-placement via the Properties palette or by
double-clicking the block. dwg2ifc exposes the per-instance values as
``EntityRecord.block_attribs`` (tag → value) and this module merges
them into the entity's :attr:`MappedEntity.fi_tekninen` so they land
in Solibri's tuoteosa view alongside the Excel-sourced höyrystin
specs.

Tag resolution reuses :func:`energy_specs._resolve_field_name`, the
same alias machinery that strips bracketed units from Excel column
headers — so an ATTDEF tag of ``LAUHDUTUSTEHO`` maps to the canonical
``Lauhdutusteho (kW)`` key without any extra config.

Conflict policy: ATTRIB values **override** Excel values for the same
tag — the per-instance value on a specific block is more specific
than a project-wide spreadsheet row.

Empty / whitespace-only ATTRIB values are ignored so a freshly placed
block with unset fields does not blank out an Excel-supplied value.
"""

from __future__ import annotations

from typing import Iterable

from dwg2ifc.core.energy_specs import _resolve_field_name
from dwg2ifc.core.types import MappedEntity


def canonical_fi_tekninen_field(tag_or_header: str) -> str | None:
    """Resolve an ATTRIB tag (or Excel header) to its canonical
    FI_Tekninen field name with unit suffix.

    Returns ``None`` for unknown tags so callers can ignore them
    without leaking junk keys into the PSet.
    """
    if not tag_or_header:
        return None
    return _resolve_field_name(str(tag_or_header))


def apply_block_attribs(mapped: Iterable[MappedEntity]) -> None:
    """Merge non-empty ``block_attribs`` into ``fi_tekninen`` in-place.

    ATTRIB values win over any previously-populated FI_Tekninen value
    for the same canonical key (Excel rows or profile defaults).
    Tags that do not resolve through the alias system are skipped
    silently — they leave no trace in the PSet.
    """
    for entity in mapped:
        attribs = entity.block_attribs or {}
        if not attribs:
            continue
        if entity.fi_tekninen is None:
            entity.fi_tekninen = {}
        for tag, value in attribs.items():
            text = (value or "").strip()
            if not text:
                continue
            canonical = canonical_fi_tekninen_field(tag)
            if canonical is None:
                continue
            entity.fi_tekninen[canonical] = text
