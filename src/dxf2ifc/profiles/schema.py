"""Pydantic models validating the mapping profile TOML."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    talo2000_code: str = Field(..., description="Talo2000 classification code.")
    talo2000_name: str = Field(..., description="Human-readable Talo2000 category name.")

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


class Profile(BaseModel):
    """A complete mapping profile."""

    model_config = ConfigDict(extra="forbid")

    name: str
    ifc_schema: Literal["IFC4"]
    rules: list[Rule]
