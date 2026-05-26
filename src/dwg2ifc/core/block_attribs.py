"""Route AutoCAD block ATTRIB fields into the Finnish PSets.

AutoCAD's ``ATTDEF`` lets a block carry typed user fields (tag,
prompt, default value) that travel with every instance in the DWG.
The user edits the values post-placement via the Properties palette
or by double-clicking the block. dwg2ifc exposes the per-instance
fields as ``EntityRecord.block_attribs`` — a list of
:class:`dwg2ifc.core.types.BlockAttrib` records (tag, prompt, value) —
and this module routes each one to the right Finnish PSet:

- **FI_Tuote** — product identity. Tags ``MALLI`` / ``LAITE`` /
  ``NIMI`` / ``MODEL`` → ``nimi`` ("Tuotetyypin nimi"); ``VALMISTAJA``;
  ``KUVAUS``; ``KOMMENTTI``; ``LINKKI``. These are resolved by tag
  because they map onto fixed, schema-defined FI_Tuote slots.

- **FI_Komponentti** — device-tag ATTDEFs. Tags ``LAITETUNNUS`` and
  ``LAITETUNNUS(YKSILÖLLINEN)`` (matched on a punctuation-insensitive
  normalised form) carry the device identifier; they land on the
  FI_Komponentti tab — device classification — next to the
  POSITIO-derived ``Koneikko`` field, **not** on the FI_Tekninen
  per-device tech-spec tab. They route through ``extra_props`` (the
  same channel the POSITIO-marker pairing uses), so a non-blank block
  value overrides a POSITIO-derived one and a blank value never wipes
  it.

- **FI_Tekninen** — every other ATTDEF, taken **verbatim**. The Solibri
  property name is the ATTDEF's *prompt* — the human-readable label the
  block author typed — falling back to the raw tag when the prompt was
  left empty. There is deliberately no alias / canonical-name lookup
  here: the block IS the spec, so "what the block carries" is exactly
  "what Solibri shows". (The energy-spec Excel importer keeps its own
  alias system for spreadsheet column headers — that is a separate
  input path and unaffected.)

- **Hole reservations** — only `KYL-REIKAVARAUS` `INSERT` blocks get a
  narrow extra promotion pass for reservation metadata tags
  (``GUID``, ``VARAUS_TYYPPI``, ``HALKAISIJA``, ``PITUUS``, ``KORKO``,
  ``VARAAJA``, ``TUNNUS``). These route into ``extra_props`` so the
  reservation pipeline can consume typed values, while every non-hole
  block still sends the same tags to FI_Tekninen verbatim.

  One cosmetic touch: a label written entirely in CAPS (a tag, or a
  prompt typed with caps lock on) is converted to sentence case so
  Solibri does not shout — ``TEHO [KW]`` → ``Teho [kw]``. A label that
  already contains a lowercase letter is kept verbatim, so the block
  author can still pin exact casing (``Kylmäteho -8C [kW]``) by typing
  the prompt with any lowercase character.

Empty-value policy:

- FI_Tuote — a blank ATTRIB value is skipped so an unfilled field does
  not wipe a profile-supplied / auto-label name.
- FI_Tekninen — a blank value is kept as an empty placeholder row (so
  the technical tab shows the full field list to fill in), but it
  never overwrites a value already present from an earlier source
  (e.g. an energy-spec Excel merge).
"""

from __future__ import annotations

import re
from typing import Callable, Iterable

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

_HOLE_RESERVATION_EXTRA_PROPS: dict[str, tuple[str, Callable[[str], object] | None]] = {
    "GUID": ("guid", str),
    "VARAUS_TYYPPI": ("varaus_tyyppi", str),
    "HALKAISIJA": ("halkaisija_mm", float),
    "PITUUS": ("pituus_mm", float),
    "YLITYS_MM": ("ylitys_mm", float),
    "KULMA_RAD": ("kulma_rad", float),
    "KORKO": ("korko_mm", float),
    "VARAAJA": ("varaaja", str),
    "TUNNUS": ("tunnus", str),
}


def resolve_fi_tuote_field(tag: str) -> str | None:
    """Resolve an ATTRIB tag to its FI_Tuote field name (or ``None``).

    Case-insensitive: ``MALLI`` / ``malli`` / ``Malli`` all match.
    ``None`` means the tag is not a product-identity field — the caller
    then routes it to FI_Tekninen instead.
    """
    if not tag:
        return None
    return _FI_TUOTE_TAG_TO_FIELD.get(str(tag).strip().upper())


def resolve_hole_reservation_field(
    tag: str,
) -> tuple[str, Callable[[str], object] | None] | None:
    if not tag:
        return None
    return _HOLE_RESERVATION_EXTRA_PROPS.get(str(tag).strip().upper())


def _is_hole_reservation_entity(entity: MappedEntity) -> bool:
    return (
        str(entity.layer or "").strip().upper() == "KYL-REIKAVARAUS"
    )


# FI_Komponentti device-tag ATTDEFs. The block author can stamp the
# device identifier straight onto a koneikko / lauhdutin block; it
# belongs on the FI_Komponentti tab. Both values route through
# ``extra_props`` — the same channel ``positio.py`` uses — under these
# keys, which ``finnish_psets.add_finnish_psets`` feeds into
# ``add_fi_komponentti``.
_FI_KOMPONENTTI_LAITETUNNUS = "laitetunnus"
_FI_KOMPONENTTI_LAITETUNNUS_YKSILOLLINEN = "laitetunnus_yksilollinen"


def _normalise_komponentti_tag(tag: str) -> str:
    """Lower-case ``tag`` and drop every non-alphanumeric character.

    Punctuation- and spacing-insensitive so the block author can write
    ``LAITETUNNUS(YKSILÖLLINEN)``, ``Laitetunnus, yksilöllinen`` or
    ``LAITETUNNUS_YKSILOLLINEN`` and still hit the same slot.
    """
    return re.sub(r"[^0-9a-zåäö]", "", str(tag).casefold())


def resolve_fi_komponentti_field(tag: str) -> str | None:
    """Resolve an ATTRIB tag to its FI_Komponentti ``extra_props`` key.

    Returns ``"laitetunnus"`` for a plain device-tag ATTDEF and
    ``"laitetunnus_yksilollinen"`` for the per-instance unique variant
    — any ``laitetunnus…`` tag that also mentions "yksil". ``None``
    means the tag is not a device-tag field; the caller then routes it
    to FI_Tuote / FI_Tekninen instead.
    """
    if not tag:
        return None
    n = _normalise_komponentti_tag(tag)
    if not n.startswith("laitetunnus"):
        return None
    if "yksil" in n:
        return _FI_KOMPONENTTI_LAITETUNNUS_YKSILOLLINEN
    if n == "laitetunnus":
        return _FI_KOMPONENTTI_LAITETUNNUS
    return None


def apply_block_attribs(mapped: Iterable[MappedEntity]) -> None:
    """Route each INSERT's ATTRIB fields into the right Finnish PSet.

    Per :class:`~dwg2ifc.core.types.BlockAttrib`:

      1. **FI_Tuote** — product-identity tags (MALLI, VALMISTAJA, …)
         resolved by :func:`resolve_fi_tuote_field`. Blank values are
         skipped so an unfilled ATTRIB never wipes an existing name.
      2. **Hole reservations** — only `KYL-REIKAVARAUS` `INSERT`
         entities promote the reservation metadata tags handled by
         :func:`resolve_hole_reservation_field` into ``extra_props``.
         This runs after FI_Tuote, so shared FI_Tuote tags such as
         ``KOMMENTTI`` still keep their normal destination.
      3. **FI_Komponentti** — device-tag fields (LAITETUNNUS,
         LAITETUNNUS(YKSILÖLLINEN)) resolved by
         :func:`resolve_fi_komponentti_field`. Written into
         ``extra_props`` so a non-blank block value overrides a
         POSITIO-derived one; a blank value is skipped.
      4. **FI_Tekninen** — every other field, verbatim. The property
         name is the ATTDEF prompt, or the raw tag when the prompt is
         empty. A blank value is kept as a placeholder row but never
         overwrites a value already set on the same label.

    Mutates each MappedEntity's ``fi_tuote`` / ``extra_props`` /
    ``fi_tekninen`` in place.
    """
    for entity in mapped:
        if _is_hole_reservation_entity(entity):
            xdata = (entity.attributes or {}).get("radika_reikavaraus_xdata")
            if isinstance(xdata, dict):
                for raw_tag, raw_value in xdata.items():
                    hole_field = resolve_hole_reservation_field(str(raw_tag))
                    if hole_field is None:
                        continue
                    key, caster = hole_field
                    value = str(raw_value or "").strip()
                    if not value:
                        continue
                    try:
                        entity.extra_props[key] = (
                            caster(value) if caster is not None else value
                        )
                    except (TypeError, ValueError):
                        pass
        for attrib in entity.block_attribs or []:
            tag = (attrib.tag or "").strip()
            if not tag:
                continue
            value = (attrib.value or "").strip()

            # 1. FI_Tuote — product identity.
            tuote_field = resolve_fi_tuote_field(tag)
            if tuote_field is not None:
                if not value:
                    # Blank ATTRIB must not blank a profile / auto value.
                    continue
                if entity.fi_tuote is None:
                    entity.fi_tuote = {}
                entity.fi_tuote[tuote_field] = value
                continue

            if _is_hole_reservation_entity(entity):
                hole_field = resolve_hole_reservation_field(tag)
                if hole_field is not None:
                    key, caster = hole_field
                    if value:
                        try:
                            entity.extra_props[key] = caster(value) if caster is not None else value
                        except (TypeError, ValueError):
                            pass
                    continue

            # 3. FI_Komponentti — device-tag ATTDEFs (Laitetunnus /
            #    Laitetunnus, yksilöllinen). Routed via extra_props, the
            #    same channel the POSITIO-marker pairing uses; because
            #    apply_block_attribs runs after the POSITIO pass a
            #    non-blank block value wins over a POSITIO-derived one.
            #    A blank value is skipped — it must not wipe a POSITIO
            #    value, and these fields never belong on FI_Tekninen.
            komponentti_key = resolve_fi_komponentti_field(tag)
            if komponentti_key is not None:
                if value:
                    entity.extra_props[komponentti_key] = value
                continue

            # 4. FI_Tekninen — prompt as the Solibri label (raw tag when
            #    the prompt is empty). A label written entirely in CAPS
            #    is sentence-cased so Solibri does not shout; a label
            #    that already has a lowercase letter is kept verbatim
            #    (the author pinned that casing on purpose).
            label = (attrib.prompt or "").strip() or tag
            if label.isupper():
                label = label.capitalize()
            if entity.fi_tekninen is None:
                entity.fi_tekninen = {}
            # Non-empty value always wins; an empty value only creates a
            # placeholder row and never clobbers an existing value.
            if value or label not in entity.fi_tekninen:
                entity.fi_tekninen[label] = value
