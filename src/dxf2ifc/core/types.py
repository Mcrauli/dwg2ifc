"""Core dataclasses shared across the conversion pipeline.

No business logic in this module — only plain data containers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Point3D:
    """A point in 3D space. Coordinates are in millimetres (DXF WCS)."""

    x: float
    y: float
    z: float = 0.0


@dataclass(frozen=True)
class LineGeometry:
    """A straight line between two points."""

    start: Point3D
    end: Point3D


@dataclass
class EntityRecord:
    """One DXF entity as read from the source file.

    `geometry` is one of the geometry dataclasses defined in this module
    (currently only LineGeometry; Plan B extends with polyline/solid/block).
    `attributes` carries DXF-specific extras (color, linetype, thickness).
    `block_name` and `xform` are only populated for INSERT entities.
    """

    layer: str
    dxf_type: str
    geometry: Any
    attributes: dict[str, Any] = field(default_factory=dict)
    block_name: str | None = None
    xform: Any | None = None


@dataclass
class MappedEntity(EntityRecord):
    """An EntityRecord plus the IFC type and Talo2000 classification
    resolved by the profile mapper."""

    ifc_type: str = ""
    predefined_type: str | None = None
    talo2000_code: str = ""
    talo2000_name: str = ""
    extra_props: dict[str, Any] = field(default_factory=dict)
