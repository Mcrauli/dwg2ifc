"""Pydantic models validating the mapping profile TOML."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class FiKomponenttiOverrides(BaseModel):
    """Static FI_Komponentti property values per profile rule.

    The FI_Komponentti PropertySet (Solibri "Muut ominaisuudet") needs
    pääryhmä/alaryhmä/yleisnimi/yleistunnus per IFC entity type. These
    are static at profile-level (every IfcEvaporator on KYL-HÖYRYSTI*
    shares "Höyrystin"/"HÖY"). Per-instance fields (Laitetunnus, koodi)
    are NOT here — koodi comes from rule.lvi_code/talo2000_code, the
    rest are skipped at write time when no source exists in the DXF.
    """

    model_config = ConfigDict(extra="forbid")

    paaryhma: str | None = None
    alaryhma: str | None = None
    yleisnimi: str | None = None
    yleistunnus: str | None = None


class FiTuoteOverrides(BaseModel):
    """Static FI_Tuote property values per profile rule.

    Optional product-description metadata (manufacturer, type name,
    URLs). All fields skip silently when None — IFC PSet only emits
    fields that have a value.
    """

    model_config = ConfigDict(extra="forbid")

    nimi: str | None = None
    kuvaus: str | None = None
    kommentti: str | None = None
    valmistaja: str | None = None
    valmistajan_linkki: str | None = None


# FI_Tekninen is FREE-FORM. The relevant technical properties differ
# per IFC entity type — refrigeration equipment uses Jäähdytysteho /
# Kylmäaine, cable carriers use Kuormitus / Materiaali, pipes use
# Halkaisija / Eristys, and so on. The profile TOML therefore takes
# arbitrary ``{key: value}`` pairs (key = property label as displayed
# in Solibri, value = free-form text). Pydantic's ``dict[str, str]``
# accepts both ``fi_tekninen = { "Kuormitus" = "120 kg/m" }`` (single
# field) and broader sets without a fixed schema.


class Rule(BaseModel):
    """One layer-pattern → IFC-type rule."""

    model_config = ConfigDict(extra="forbid")

    layer_pattern: str = Field(
        ...,
        description="Glob pattern matched against DXF layer name (case-insensitive).",
    )
    entity_kind: Literal["LINE", "POLYLINE", "CIRCLE", "INSERT"] = Field(
        default="LINE",
        description="DXF entity kind this rule applies to.",
    )
    block_name: str | None = Field(
        default=None,
        description="DXF block name (required when entity_kind == 'INSERT').",
    )
    ifc_type: str = Field(..., description="IFC entity name, e.g. 'IfcWall'.")
    predefined_type: str | None = Field(
        default=None, description="IFC PredefinedType enumeration value, if applicable."
    )
    domain: Literal["ARK", "TATE", "KYL"] = Field(
        default="ARK",
        description=(
            "Discipline (suunnitteluala) — written into the IFC as the "
            "'suunnittelualat' classification reference. ARK uses Talo2000 "
            "(architect), TATE uses RAVA (general talotekniikka), KYL uses "
            "RAVA but tags the discipline as kylmälaitesuunnittelu — the "
            "default for refrigeration projects so Solibri shows 'KYL' "
            "instead of 'Talotekniikka'."
        ),
    )
    talo2000_code: str | None = Field(
        default=None,
        description="Talo2000 classification code (required when domain == 'ARK').",
    )
    talo2000_name: str | None = Field(
        default=None,
        description="Human-readable Talo2000 category name (required when domain == 'ARK').",
    )
    lvi_code: str | None = Field(
        default=None,
        description="RAVA LVI-TUOTEOSA code (T-LVI-…), used when domain in ('TATE', 'KYL').",
    )
    talotekniikka_code: str | None = Field(
        default=None,
        description="RAVA TALOTEKNIIKKA-TUOTEOSA code (T-TATE-…), used when domain in ('TATE', 'KYL').",
    )

    default_height_mm: float | None = Field(
        default=None, description="Extrusion height for 2D lines."
    )
    default_thickness_mm: float | None = Field(
        default=None, description="Default element thickness (wall, slab)."
    )
    block_handling: Literal["geometry_direct", "extrude"] | None = Field(
        default=None, description="How to handle INSERT entities on this layer."
    )
    extrusion_height: float | None = Field(
        default=None,
        description="Extrusion height (mm) used when 2D geometry needs lifting to 3D.",
    )
    pset_overrides: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="IFC PropertySet overrides keyed by Pset name → {prop: value}.",
    )
    fi_komponentti: FiKomponenttiOverrides | None = Field(
        default=None,
        description=(
            "Static FI_Komponentti PropertySet values (pääryhmä, alaryhmä, "
            "yleisnimi, yleistunnus). Empty values skip the corresponding "
            "PSet line at write time."
        ),
    )
    fi_tuote: FiTuoteOverrides | None = Field(
        default=None,
        description=(
            "Static FI_Tuote PropertySet values (manufacturer, type name, "
            "URLs etc). Per-field optional; the whole PSet is skipped if "
            "every field is empty."
        ),
    )
    fi_tekninen: dict[str, str] | None = Field(
        default=None,
        description=(
            "Free-form FI_Tekninen PropertySet values. Keys are the labels "
            "Solibri displays (e.g. 'Jäähdytysteho', 'Kuormitus', "
            "'Halkaisija'); values are free text such as '5,2 kW' or "
            "'120 kg/m'. The schema differs per IFC entity type: equipment "
            "uses refrigeration fields, shelves use load/material, pipes "
            "use diameter/insulation. When a rule omits fi_tekninen the "
            "writer picks a default set based on the rule's ifc_type."
        ),
    )
    fi_sijainti: dict[str, str] | None = Field(
        default=None,
        description=(
            "FI_Sijainti override — the RAVA3Pro 'system grouping' PSet "
            "(Järjestelmien nimet / tunnukset). Use this for components "
            "whose RAVA system code (J-TATE-…/J-LVI-…) is more specific "
            "than the default ``system_name`` derivation. Keys: "
            "'jarjestelmien_nimet', 'jarjestelmien_tunnukset'."
        ),
    )
    system_name: str | None = Field(default=None, description="Optional IfcSystem grouping name.")

    @model_validator(mode="after")
    def _require_block_name_for_insert(self) -> "Rule":
        if self.entity_kind == "INSERT" and not self.block_name:
            raise ValueError("block_name is required when entity_kind == 'INSERT'")
        return self

    @model_validator(mode="after")
    def _validate_domain_codes(self) -> "Rule":
        if self.domain == "ARK":
            if not self.talo2000_code:
                raise ValueError("talo2000_code is required when domain == 'ARK'")
            if self.lvi_code or self.talotekniikka_code:
                raise ValueError(
                    "lvi_code and talotekniikka_code must be empty when domain == 'ARK'"
                )
        else:  # TATE or KYL — both share the RAVA classification rules
            if self.talo2000_code:
                raise ValueError(
                    f"talo2000_code must be empty when domain == {self.domain!r}"
                )
            filled = [c for c in (self.lvi_code, self.talotekniikka_code) if c]
            if len(filled) != 1:
                raise ValueError(
                    "exactly one of lvi_code or talotekniikka_code must be set "
                    f"when domain == {self.domain!r}"
                )
        return self


class PositioConfig(BaseModel):
    """POSITIO numbering-block linkage settings.

    Per-instance ``Laitetunnus`` / ``Laitetunnus, yksilöllinen`` values
    are sourced by matching each refrigeration-equipment INSERT against
    the nearest POSITIO block in the same DXF (XY-2D distance, ignored
    Z). When the profile sets ``positio = None`` (or omits the section
    entirely), no linkage is attempted and FI_Komponentti's Laitetunnus
    fields stay blank.
    """

    model_config = ConfigDict(extra="forbid")

    block_pattern: str = Field(
        default="positiov2*",
        description="fnmatch glob (case-insensitive) for POSITIO INSERT block names.",
    )
    max_distance_mm: float = Field(
        default=3000.0,
        description="Match radius in mm (XY only). Lähin POSITIO ulkopuolella jää tyhjäksi.",
    )
    apply_to: list[str] = Field(
        default_factory=lambda: [
            "IfcEvaporator",
            "IfcCondenser",
            "IfcCompressor",
        ],
        description="IFC entity types that receive Laitetunnus from POSITIO.",
    )


class Profile(BaseModel):
    """A complete mapping profile."""

    model_config = ConfigDict(extra="forbid")

    name: str
    ifc_schema: Literal["IFC4"]
    rules: list[Rule]
    positio: PositioConfig | None = Field(
        default=None,
        description=(
            "Optional POSITIO-block linkage. When set, scoping IFC types "
            "(default IfcEvaporator/Condenser/Compressor) get their "
            "Laitetunnus / Laitetunnus, yksilöllinen filled from the "
            "nearest matching numbering block."
        ),
    )

