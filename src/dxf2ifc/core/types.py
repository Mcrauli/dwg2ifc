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


@dataclass(frozen=True)
class PolygonGeometry:
    """A planar polygon defined by an ordered list of vertices.

    `closed=True` means the polygon's last vertex is implicitly connected
    back to the first; only closed polygons are usable as slab outlines.
    """

    vertices: tuple[Point3D, ...]
    closed: bool = True


@dataclass(frozen=True)
class MeshGeometry:
    """A faceted polyhedral mesh.

    Used for DXF MESH entities. ``accoreconsole.exe -MESHSMOOTH`` converts
    3DSOLIDs into MESH so we can read them without an ACIS parser.

    ``vertices`` is the deduplicated vertex pool. Each entry in ``faces``
    is a tuple of indices into ``vertices`` defining one (n>=3-gon) face.
    """

    vertices: tuple[Point3D, ...]
    faces: tuple[tuple[int, ...], ...]


@dataclass(frozen=True)
class BlockInstance:
    """A DXF INSERT placement.

    The block's local geometry stays in its BLOCK definition; instances
    only carry the placement (insertion point, rotation around Z, scale).
    """

    insertion_point: Point3D
    rotation_rad: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0
    scale_z: float = 1.0


@dataclass
class EntityRecord:
    """One DXF entity as read from the source file.

    `geometry` is one of the geometry dataclasses defined in this module
    (LineGeometry, PolygonGeometry, BlockInstance, MeshGeometry).
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
    domain: str = "ARK"
    talo2000_code: str | None = ""
    talo2000_name: str | None = ""
    lvi_code: str | None = None
    talotekniikka_code: str | None = None
    fi_komponentti: dict[str, Any] | None = None
    fi_tuote: dict[str, Any] | None = None
    fi_tekninen: dict[str, Any] | None = None
    fi_sijainti: dict[str, Any] | None = None
    extra_props: dict[str, Any] = field(default_factory=dict)
