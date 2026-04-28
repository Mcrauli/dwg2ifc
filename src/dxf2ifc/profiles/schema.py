"""Pydantic models validating the mapping profile TOML."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CRSConfig(BaseModel):
    """Projected coordinate reference system + IfcMapConversion parameters.

    Default values target ETRS-TM35FIN (EPSG:3067) which is the Finnish
    national projected CRS used in BIM deliverables for public-sector
    refrigeration projects.
    """

    model_config = ConfigDict(extra="forbid")

    epsg_code: str = Field(
        default="EPSG:3067",
        description="EPSG identifier written to IfcProjectedCRS.Name.",
    )
    name: str = Field(
        default="ETRS-TM35FIN",
        description="Human-readable CRS name written to IfcProjectedCRS.Description.",
    )
    geodetic_datum: str = Field(
        default="ETRS89",
        description="Geodetic datum written to IfcProjectedCRS.GeodeticDatum.",
    )
    eastings_mm: float = Field(
        ...,
        description="IfcMapConversion.Eastings (mm).",
    )
    northings_mm: float = Field(
        ...,
        description="IfcMapConversion.Northings (mm).",
    )
    orthogonal_height_mm: float = Field(
        default=0.0,
        description="IfcMapConversion.OrthogonalHeight (mm).",
    )
    x_axis_abscissa: float = Field(
        default=1.0,
        description="IfcMapConversion.XAxisAbscissa (cosine of rotation, default 1.0).",
    )
    x_axis_ordinate: float = Field(
        default=0.0,
        description="IfcMapConversion.XAxisOrdinate (sine of rotation, default 0.0).",
    )
    scale: float = Field(
        default=1.0,
        description="IfcMapConversion.Scale (default 1.0, must be > 0).",
    )

    @field_validator("scale")
    @classmethod
    def _scale_must_be_positive(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("scale must be > 0")
        return value


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
    domain: Literal["ARK", "TATE"] = Field(
        default="ARK",
        description=(
            "Discipline domain: ARK uses Talo2000 classification, TATE uses RAVA "
            "(LVI-TUOTEOSA or TALOTEKNIIKKA-TUOTEOSA)."
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
        description="RAVA LVI-TUOTEOSA code (T-LVI-…), used when domain == 'TATE'.",
    )
    talotekniikka_code: str | None = Field(
        default=None,
        description="RAVA TALOTEKNIIKKA-TUOTEOSA code (T-TATE-…), used when domain == 'TATE'.",
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
        else:  # TATE
            if self.talo2000_code:
                raise ValueError("talo2000_code must be empty when domain == 'TATE'")
            filled = [c for c in (self.lvi_code, self.talotekniikka_code) if c]
            if len(filled) != 1:
                raise ValueError(
                    "exactly one of lvi_code or talotekniikka_code must be set "
                    "when domain == 'TATE'"
                )
        return self


class Profile(BaseModel):
    """A complete mapping profile."""

    model_config = ConfigDict(extra="forbid")

    name: str
    ifc_schema: Literal["IFC4"]
    rules: list[Rule]
