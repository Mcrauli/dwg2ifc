"""Core dataclasses shared across the conversion pipeline.

No business logic in this module — only plain data containers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
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

    ``vertices`` is the deduplicated vertex pool. Each entry in ``faces``
    is a tuple of indices into ``vertices`` defining one (n>=3-gon) face.

    ``source`` records where the geometry came from so the IFC writer can
    pick the right representation:

    * ``"acis"`` (default): tessellated from a 3DSOLID via accoreconsole +
      STLOUT — written as ``IfcFacetedBrep``.
    * ``"polyface"``: read directly from a DXF POLYLINE polyface mesh
      (typical MAGIEXPLODE output).
    * ``"mesh"``: read from a DXF MESH entity.
    * ``"3dface"``: built from a DXF 3DFACE entity.

    All non-``"acis"`` sources are written as ``IfcTriangulatedFaceSet``
    (Body / Tessellation) so Solibri renders them as surfaces, not
    wireframe.
    """

    vertices: tuple[Point3D, ...]
    faces: tuple[tuple[int, ...], ...]
    source: str = "acis"


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
    `handle` is the upper-cased DXF entity handle (hex string), used in
    diagnostics so the user can find the offending entity in AutoCAD.
    """

    layer: str
    dxf_type: str
    geometry: Any
    attributes: dict[str, Any] = field(default_factory=dict)
    block_name: str | None = None
    xform: Any | None = None
    handle: str | None = None
    # INSERT-block ATTRIB tag → value mapping for tech-spec overrides.
    # AutoCAD's ``ATTDEF`` lets a block carry typed user fields (tag,
    # prompt, value); ``INSERT.attribs`` exposes them as Attrib
    # subentities. dwg2ifc maps the upper-case tag through the same
    # alias system as Excel headers (energy_specs._FIELD_ALIASES) into
    # FI_Tekninen keys, so users can fill per-device specs (cooling
    # capacity, voltage, refrigerant, …) directly on a lauhdutin /
    # koneikko block via Properties palette without a sidecar Excel.
    block_attribs: dict[str, str] = field(default_factory=dict)


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
    storey_index: int = 0


@dataclass(frozen=True)
class FileEntry:
    """One input file with its assigned floor label and Z elevation.

    A multi-floor conversion run takes a ``list[FileEntry]``; each entry
    becomes one ``IfcBuildingStorey``. ``elevation_mm`` is added to every
    entity's Z coordinate read from this file, so when all entries are at
    ``elevation_mm=0`` the DXF Z coordinates pass through to the IFC
    unchanged.
    """

    path: Path
    floor_label: str
    elevation_mm: float = 0.0
