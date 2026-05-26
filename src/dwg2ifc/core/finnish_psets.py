"""Finnish-localised IFC PropertySets per RAVA3Pro convention.

Solibri's "Muut ominaisuudet" tabs (FI_Asennus, FI_Geometria,
FI_Komponentti, FI_Tuote) are how Finnish LVI / refrigeration designers
inspect a model. This module attaches the four PSets to every IFC
product the converter writes.

Schema reference: ``~/Downloads/RAVA3Pro - LVI - Pilottimalli -
Kerrostalo - 2023-11-30.ifc`` (BSPro/Simplebim) and the RAVA codeset
at <https://talotekniikka-sovellus.tietomallintaja.fi/>.

Skip-on-empty rule: every helper drops property lines whose source
value is ``None`` / blank / non-positive. The whole PSet is skipped
when it would carry no usable property — Solibri then displays the
tab as empty rather than as a stub. Pakolliset perusasetelmat
(FI_Asennus, FI_Komponentti) emittoituvat aina, koska placement +
RAVA-koodi on aina tiedossa.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import ifcopenshell
from ifcopenshell.api import run as _run

from dwg2ifc.core.geometry import GeometryExtents


# ---------------------------------------------------------------------------
# Low-level helper
# ---------------------------------------------------------------------------


def _emit_pset(
    ifc: ifcopenshell.file,
    *,
    product: object,
    name: str,
    properties: Iterable[tuple[str, str, object]],
    always_emit: bool = False,
) -> object | None:
    """Create an IfcPropertySet ``name`` on ``product`` with typed entries.

    Each entry is ``(prop_name, ifc_type, value)`` — e.g.
    ``("02 Komponentin yläpinnan korko, abs.", "IfcLengthMeasure", 18734.5)``.
    Empty-value entries are filtered out by default (returning ``None`` if
    every entry is empty). Pass ``always_emit=True`` to keep the PSet
    visible even when every text field would be blank — Solibri then
    renders the tab with empty placeholders so the user knows the slot
    is supposed to be filled. Length-measure entries always skip when
    blank regardless of ``always_emit`` (writing a 0 mm elevation as a
    placeholder is misleading).
    """
    typed: dict[str, object] = {}
    for prop_name, ifc_type, value in properties:
        is_blank = value is None or (isinstance(value, str) and not value.strip())
        if ifc_type in ("IfcLengthMeasure", "IfcPositiveLengthMeasure"):
            if is_blank:
                continue
            try:
                fv = float(value)
            except (TypeError, ValueError):
                continue
            if ifc_type == "IfcPositiveLengthMeasure" and fv <= 0:
                continue
            typed[prop_name] = ifc.create_entity(ifc_type, fv)
            continue
        if is_blank:
            if not always_emit:
                continue
            # Always-emit text fields render as empty placeholders.
            typed[prop_name] = ifc.create_entity(ifc_type, "")
        else:
            typed[prop_name] = ifc.create_entity(ifc_type, str(value))
    if not typed:
        return None
    pset = _run("pset.add_pset", ifc, product=product, name=name)
    _run("pset.edit_pset", ifc, pset=pset, properties=typed)
    return pset


# ---------------------------------------------------------------------------
# FI_Asennus
# ---------------------------------------------------------------------------


def add_fi_asennus(
    ifc: ifcopenshell.file,
    product: object,
    *,
    top_z_mm: float,
    bottom_z_mm: float,
    install_z_mm: float,
    storey_elevation_mm: float,
    include_liitoskorko: bool = True,
) -> object | None:
    """Attach the FI_Asennus PSet (six elevation properties + optional liitoskorko).

    Storey-relative values are computed as ``abs - storey_elevation``.
    Solibri displays installations metric, IfcLengthMeasure in mm.
    """
    storey_top_z = top_z_mm - storey_elevation_mm
    storey_install_z = install_z_mm - storey_elevation_mm
    storey_bottom_z = bottom_z_mm - storey_elevation_mm

    properties: list[tuple[str, str, object]] = [
        ("02 Komponentin yläpinnan korko, abs.", "IfcLengthMeasure", top_z_mm),
        ("03 Asennuskorko, abs.", "IfcLengthMeasure", install_z_mm),
        ("04 Komponentin alapinnan korko, abs.", "IfcLengthMeasure", bottom_z_mm),
        (
            "12 Komponentin yläpinnan korko, kerroskorosta",
            "IfcLengthMeasure",
            storey_top_z,
        ),
        ("13 Asennuskorko, kerroskorosta", "IfcLengthMeasure", storey_install_z),
        (
            "14 Komponentin alapinnan korko, kerroskorosta",
            "IfcLengthMeasure",
            storey_bottom_z,
        ),
    ]
    if include_liitoskorko:
        # Most of Lauri's elements share install_z with the connection
        # elevation. RAVA3Pro keeps the field even when it duplicates
        # asennuskorko — Solibri rule sets check its presence.
        properties.append(
            (
                "Liitoskorko, kerroskorosta",
                "IfcLengthMeasure",
                storey_install_z,
            )
        )
    return _emit_pset(ifc, product=product, name="FI_Asennus", properties=properties)


# ---------------------------------------------------------------------------
# FI_Geometria
# ---------------------------------------------------------------------------


def add_fi_geometria(
    ifc: ifcopenshell.file,
    product: object,
    *,
    korkeus_mm: float | None,
    leveys_mm: float | None,
    syvyys_mm: float | None,
    third_label: str = "Syvyys",
) -> object | None:
    """Attach FI_Geometria with Korkeus / Leveys / Syvyys (mm).

    ``third_label`` controls the third property's label — for box-like
    products (evaporators, cabinets) "Syvyys" is the natural term; for
    elongated products (cable carriers, pipes) "Pituus" is more
    accurate. Each missing dimension is skipped. PSet is omitted
    entirely if all three are unknown / non-positive.
    """
    return _emit_pset(
        ifc,
        product=product,
        name="FI_Geometria",
        properties=[
            ("Korkeus", "IfcPositiveLengthMeasure", korkeus_mm),
            ("Leveys", "IfcPositiveLengthMeasure", leveys_mm),
            (third_label, "IfcPositiveLengthMeasure", syvyys_mm),
        ],
    )


# IFC entity types whose FI_Geometria third dimension is "Pituus"
# (length along the run) rather than "Syvyys" (cabinet depth). Cable
# carriers / pipes are inherently linear, so the longest horizontal
# extent is its length, not depth.
_LENGTH_BASED_IFC_TYPES = frozenset(
    {
        "IfcCableCarrierSegment",
        "IfcPipeSegment",
        "IfcDuctSegment",
    }
)

_SYSTEM_CODE_FALLBACKS: dict[str, str] = {
    # RAVA LVI-JARJESTELMA codes for the systems produced by default_kylmalaite.toml.
    "Refrigeration plant": "J-LVI-09-02",
    "Kylmäjärjestelmä": "J-LVI-09-02",
    "Kylmä - suorahöyrysteinen": "J-LVI-09-02",
    "Jäähdytys - vedenjäähdytyskone": "J-LVI-06-07",
}

_SYSTEM_NAME_CANONICAL: dict[str, str] = {
    "Refrigeration plant": "Kylmäjärjestelmä",
}


def resolve_system_fields(
    *,
    system_name: str | None,
    fi_sijainti: dict | None,
    fallback_code_to_name: bool = True,
) -> tuple[str | None, str | None]:
    """Resolve FI_Sijainti system name/code with RAVA-aware fallbacks."""
    if system_name:
        system_name = _SYSTEM_NAME_CANONICAL.get(system_name, system_name)
    fi_si = fi_sijainti or {}
    resolved_name = fi_si.get("jarjestelmien_nimet") or system_name
    fallback_code = _SYSTEM_CODE_FALLBACKS.get(str(system_name)) if system_name else None
    resolved_code = fi_si.get("jarjestelmien_tunnukset") or fallback_code
    if fallback_code_to_name and not resolved_code:
        resolved_code = system_name
    return resolved_name, resolved_code


# ---------------------------------------------------------------------------
# FI_Komponentti
# ---------------------------------------------------------------------------


def add_fi_komponentti(
    ifc: ifcopenshell.file,
    product: object,
    *,
    paaryhma: str | None = None,
    alaryhma: str | None = None,
    koodi: str | None = None,
    yleisnimi: str | None = None,
    yleistunnus: str | None = None,
    koneikko: str | None = None,
    laitetunnus: str | None = None,
    laitetunnus_yksilollinen: str | None = None,
    status: str | None = "New",
) -> object | None:
    """Attach FI_Komponentti with classification metadata.

    Static fields (paaryhma / alaryhma / yleisnimi / yleistunnus) come
    from the profile rule's ``fi_komponentti`` table. Per-instance
    fields skip when not supplied:

    * ``koneikko`` — group / refrigeration unit, e.g. "JK1" from a
      POSITIO TEKSTI attribute.
    * ``laitetunnus`` — device tag, e.g. a POSITIO NUMERO or a
      ``LAITETUNNUS`` ATTDEF the block author stamped on the block.
    * ``laitetunnus_yksilollinen`` — per-instance unique device tag
      from a ``LAITETUNNUS(YKSILÖLLINEN)`` ATTDEF.

    ``status`` defaults to ``"New"`` per RAVA3Pro convention.
    """
    return _emit_pset(
        ifc,
        product=product,
        name="FI_Komponentti",
        properties=[
            ("01 Komponentin pääryhmä", "IfcText", paaryhma),
            ("02 Komponentin alaryhmä", "IfcText", alaryhma),
            ("03 Komponentin koodi", "IfcText", koodi),
            ("04 Komponentin yleisnimi", "IfcText", yleisnimi),
            ("05 Komponentin yleistunnus", "IfcText", yleistunnus),
            ("Koneikko", "IfcText", koneikko),
            ("Laitetunnus", "IfcText", laitetunnus),
            ("Laitetunnus, yksilöllinen", "IfcText", laitetunnus_yksilollinen),
            ("Status", "IfcText", status),
        ],
    )


# ---------------------------------------------------------------------------
# FI_Tuote
# ---------------------------------------------------------------------------


def add_fi_tuote(
    ifc: ifcopenshell.file,
    product: object,
    *,
    nimi: str | None = None,
    kuvaus: str | None = None,
    kommentti: str | None = None,
    valmistaja: str | None = None,
    valmistajan_linkki: str | None = None,
    tuotteen_kommentti: str | None = None,
    always_emit: bool = True,
) -> object | None:
    """Attach FI_Tuote with product description / manufacturer / URLs.

    Defaults to ``always_emit=True`` so the Solibri tab is visible even
    on products without TOML-supplied data — empty fields then render as
    blanks the designer can fill in by hand.
    """
    return _emit_pset(
        ifc,
        product=product,
        name="FI_Tuote",
        always_emit=always_emit,
        properties=[
            ("Tuotetyypin nimi", "IfcText", nimi),
            ("Tuotetyypin kuvaus", "IfcText", kuvaus),
            ("Tuotetyypin kommentti", "IfcText", kommentti),
            ("Tuotetyypin valmistaja", "IfcText", valmistaja),
            ("Tuotetyypin valmistajan linkki", "IfcText", valmistajan_linkki),
            ("Tuotteen kommentti", "IfcText", tuotteen_kommentti),
        ],
    )


# ---------------------------------------------------------------------------
# FI_Tekninen
# ---------------------------------------------------------------------------


# Default FI_Tekninen field sets per IFC entity type. When the profile
# rule does not specify ``fi_tekninen`` we fall back to one of these
# templates so the tab is still meaningful and not generically full of
# refrigeration fields on a shelf. User can override the entire set via
# TOML (``fi_tekninen = { ... }``).
_FI_TEKNINEN_DEFAULTS: dict[str, dict[str, str]] = {
    # Numeerisilla teho-/sähkö-/virtauskentillä yksikkö nimen perässä
    # suluissa (Solibri näyttää sen avaimena, ja arvo jää puhtaaksi
    # numeroksi). Tekstikentät (Kylmäaine, Materiaali, Pinnoite,
    # Eristys) jätetään ilman yksikköä.
    "IfcEvaporator": {
        "Jäähdytysteho (kW)": "",
        "Sähköteho (kW)": "",
        "Vastusteho (kW)": "",
        "Jännite (V)": "",
        "Kylmäaine": "",
        "Ilmavirta (m³/h)": "",
        "Ääniteho (dB(A))": "",
        "Käyttölämpötila (°C)": "",
        "Jäähdyttävä vaikutus (kW)": "",
    },
    "IfcCondenser": {
        "Lauhdutusteho (kW)": "",
        "Sähköteho (kW)": "",
        "Vastusteho (kW)": "",
        "Jännite (V)": "",
        "Kylmäaine": "",
        "Ilmavirta (m³/h)": "",
        "Ääniteho (dB(A))": "",
        "Käyttölämpötila (°C)": "",
    },
    "IfcCompressor": {
        "Jäähdytysteho (kW)": "",
        "Sähköteho (kW)": "",
        "Kylmäaine": "",
        "Höyrystymislämpötila (°C)": "",
        "Lauhtumislämpötila (°C)": "",
        "Ääniteho (dB(A))": "",
    },
    "IfcCableCarrierSegment": {
        # Hyllyt: Lauri:n päätös 2026-05-08 — vain matsku + pinnoite
        # (esim. "Kuumasinkitty"). EI paloluokkaa, painoa, painokuormaa,
        # väriä eikä levypaksuutta — käyttäjä voi lisätä tarvittaessa
        # custom profile:n kautta.
        "Materiaali": "",
        "Pinnoite": "",
    },
    "IfcPipeSegment": {
        "Materiaali": "",
        "Eristys": "",
        "Eristyspaksuus (mm)": "",
        "Painekestävyys (bar)": "",
    },
}


# Per-IFC-type fallback for FI_Tuote "Tuotetyypin nimi" — a human-
# readable device label that appears in Solibri whenever the profile
# rule does not supply its own ``fi_tuote.nimi`` and the user has not
# added a per-instance ATTRIB override. Lets Solibri's tuoteosa view
# always answer "what device is this?" at a glance.
#
# Layer-specific names (KYL-LEVYHYLLY → "Levyhylly", KYL-KOTELO →
# "Kotelo") come from profile TOML rules and override this fallback.
_FI_TUOTE_DEFAULT_NIMI: dict[str, str] = {
    "IfcEvaporator": "Höyrystin",
    "IfcCondenser": "Lauhdutin",
    "IfcCompressor": "Kompressori",
    "IfcUnitaryEquipment": "Koneikko",
    "IfcChiller": "Vesijäähdytin",
    "IfcCoil": "Kierukka",
    "IfcCoolingTower": "Jäähdytystorni",
    "IfcTank": "Säiliö",
    "IfcFlowController": "Säädin",
    "IfcSensor": "Anturi",
    "IfcAlarm": "Hälytin",
    "IfcCommunicationsAppliance": "Tiedonsiirtolaite",
    "IfcElectricDistributionBoard": "Sähkökeskus",
    "IfcController": "Ohjain",
    "IfcSwitchingDevice": "Kytkin",
    "IfcCableCarrierSegment": "Asennushylly",
    "IfcPipeSegment": "Putki",
    "IfcWall": "Seinä",
    "IfcSlab": "Laatta",
    "IfcDoor": "Ovi",
    "IfcWindow": "Ikkuna",
    "IfcBuildingElementProxy": "Sähkölaite",
    "IfcFurniture": "Kaluste",
    "IfcDistributionElement": "Tuoteosa",
}


def fi_tuote_default_nimi(ifc_type: str) -> str | None:
    """Return the default ``Tuotetyypin nimi`` for a given IFC entity
    type, or ``None`` when no mapping exists.

    Used as the fallback when the profile rule does not specify
    ``fi_tuote.nimi`` and no per-instance ATTRIB has overridden it.
    """
    if not ifc_type:
        return None
    return _FI_TUOTE_DEFAULT_NIMI.get(ifc_type)


def fi_tekninen_default_fields(ifc_type: str) -> dict[str, str]:
    """Return the default FI_Tekninen field set for an IFC entity type.

    Returns a copy so callers can mutate without leaking into the
    template. Falls back to an empty dict for unknown types.
    """
    return dict(_FI_TEKNINEN_DEFAULTS.get(ifc_type, {}))


def add_fi_tekninen(
    ifc: ifcopenshell.file,
    product: object,
    *,
    fields: dict[str, str] | None = None,
    always_emit: bool = True,
) -> object | None:
    """Attach FI_Tekninen with free-form technical fields.

    ``fields`` is a ``{label: value}`` mapping where labels are exactly
    the Solibri-displayed property names (e.g. "Jäähdytysteho",
    "Kuormitus"). Values are free-form text. When ``fields`` is ``None``
    or empty the PSet is skipped unless ``always_emit=True`` keeps a
    placeholder visible.
    """
    fields = fields or {}
    properties = [(label, "IfcText", value) for label, value in fields.items()]
    return _emit_pset(
        ifc,
        product=product,
        name="FI_Tekninen",
        always_emit=always_emit,
        properties=properties,
    )


# ---------------------------------------------------------------------------
# FI_Sijainti
# ---------------------------------------------------------------------------


def add_fi_sijainti(
    ifc: ifcopenshell.file,
    product: object,
    *,
    jarjestelmien_nimet: str | None = None,
    jarjestelmien_tunnukset: str | None = None,
    always_emit: bool = True,
) -> object | None:
    """Attach FI_Sijainti — system membership in RAVA3Pro convention.

    Despite the name "Sijainti" (Location), this PSet carries the
    system-grouping reference (Järjestelmien nimet/tunnukset).
    """
    return _emit_pset(
        ifc,
        product=product,
        name="FI_Sijainti",
        always_emit=always_emit,
        properties=[
            ("Järjestelmien nimet", "IfcText", jarjestelmien_nimet),
            ("Järjestelmien tunnukset", "IfcText", jarjestelmien_tunnukset),
        ],
    )


# ---------------------------------------------------------------------------
# Orchestrator entry point
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _PsetInputs:
    extents: GeometryExtents
    storey_elevation_mm: float
    fi_komponentti: dict | None
    fi_tuote: dict | None
    rava_or_talo_code: str | None


def add_finnish_psets(
    ifc: ifcopenshell.file,
    *,
    product: object,
    mapped,
    parent_storey,
    extents: GeometryExtents,
) -> None:
    """Attach all four FI_* PSets to ``product`` based on a MappedEntity.

    ``mapped`` is a :class:`dwg2ifc.core.types.MappedEntity` carrying
    domain / koodi / fi_komponentti / fi_tuote. ``parent_storey`` is the
    IfcBuildingStorey assigned to the product (needed for the
    storey-relative elevations). ``extents`` is precomputed by the
    caller (``extents_from_geometry`` in :mod:`geometry`) — passing it
    in keeps this function pure-IFC and unit-testable.
    """
    storey_elev = float(parent_storey.Elevation or 0.0) if parent_storey is not None else 0.0

    # FI_Asennus — always emitted; placement is always known.
    add_fi_asennus(
        ifc,
        product,
        top_z_mm=extents.top_z,
        bottom_z_mm=extents.bottom_z,
        install_z_mm=extents.install_z,
        storey_elevation_mm=storey_elev,
    )

    # FI_Geometria — emitted if any dimension is positive. For
    # length-based products (cable carriers, pipes, ducts) the longer
    # of the two horizontal extents becomes "Pituus" and the shorter
    # stays "Leveys", so a 6 m × 200 mm × 80 mm shelf reads 6000 / 200
    # / 80 instead of the misleading 200 / 6000 / 80.
    if mapped.ifc_type in _LENGTH_BASED_IFC_TYPES:
        leveys = extents.leveys
        syvyys = extents.syvyys
        if leveys is not None and syvyys is not None:
            short, long_ = sorted([leveys, syvyys])
            leveys, syvyys = short, long_
        add_fi_geometria(
            ifc,
            product,
            korkeus_mm=extents.korkeus,
            leveys_mm=leveys,
            syvyys_mm=syvyys,
            third_label="Pituus",
        )
    else:
        add_fi_geometria(
            ifc,
            product,
            korkeus_mm=extents.korkeus,
            leveys_mm=extents.leveys,
            syvyys_mm=extents.syvyys,
        )

    # FI_Komponentti — koodi from RAVA / Talo2000, static fields from
    # the profile rule's fi_komponentti table.
    fi_k = mapped.fi_komponentti or {}
    code = (
        getattr(mapped, "lvi_code", None)
        or getattr(mapped, "talotekniikka_code", None)
        or getattr(mapped, "talo2000_code", None)
    )
    extras = mapped.extra_props or {}
    add_fi_komponentti(
        ifc,
        product,
        paaryhma=fi_k.get("paaryhma"),
        alaryhma=fi_k.get("alaryhma"),
        koodi=code,
        yleisnimi=fi_k.get("yleisnimi"),
        yleistunnus=fi_k.get("yleistunnus"),
        koneikko=extras.get("koneikko"),
        laitetunnus=extras.get("laitetunnus"),
        laitetunnus_yksilollinen=extras.get("laitetunnus_yksilollinen"),
    )

    # FI_Tuote — always emitted so the Solibri tab is visible. Profile
    # TOML can supply nimi/kuvaus/valmistaja/etc; "Tuotetyypin nimi"
    # falls back to a per-IFC-type Finnish device label
    # (``fi_tuote_default_nimi``) so the tuoteosa view always answers
    # "what device is this?" instead of an empty placeholder.
    fi_t = mapped.fi_tuote or {}
    nimi = fi_t.get("nimi") or fi_tuote_default_nimi(mapped.ifc_type)
    add_fi_tuote(
        ifc,
        product,
        nimi=nimi,
        kuvaus=fi_t.get("kuvaus"),
        kommentti=fi_t.get("kommentti"),
        valmistaja=fi_t.get("valmistaja"),
        valmistajan_linkki=fi_t.get("valmistajan_linkki"),
    )

    # FI_Tekninen — schema differs per IFC entity type. Priority:
    #   1. fields populated from the block's own ATTDEFs / energy-spec
    #      Excel (``mapped.fi_tekninen``) — used verbatim.
    #   2. when the block carried ATTDEFs (``mapped.block_attribs``) the
    #      ATTDEFs ARE the spec — never fall back to a generic template,
    #      even if every attdef value is still blank.
    #   3. otherwise a sensible per-ifc_type default template
    #      (refrigeration fields for evaporators, materiaali/pinnoite
    #      for shelves, materiaali/eristys for pipes — see
    #      ``_FI_TEKNINEN_DEFAULTS``).
    fi_te = mapped.fi_tekninen
    if not fi_te and not mapped.block_attribs:
        fi_te = fi_tekninen_default_fields(mapped.ifc_type)
    add_fi_tekninen(ifc, product, fields=fi_te)

    # FI_Sijainti — RAVA system grouping. When the profile rule supplies
    # explicit järjestelmien nimet/tunnukset (e.g. "Asennushyllyjärjes-
    # telmä - LVI" / "AHJ.LVI" for shelves), use those verbatim.
    # Otherwise use the rule's ``system_name`` as name, and resolve
    # known system-code fallbacks for ``Järjestelmien tunnukset``.
    sys_name = extras.get("system_name")
    resolved_name, resolved_code = resolve_system_fields(
        system_name=sys_name,
        fi_sijainti=mapped.fi_sijainti,
        fallback_code_to_name=True,
    )
    add_fi_sijainti(
        ifc,
        product,
        jarjestelmien_nimet=resolved_name,
        jarjestelmien_tunnukset=resolved_code,
    )
