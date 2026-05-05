"""Read a DXF file and produce a list of EntityRecord objects.

Plan A handles only LINE entities. Plan B extends with LWPOLYLINE, 3DSOLID, INSERT.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Mapping

import ezdxf
from ezdxf.render import MeshBuilder

from dxf2ifc.core.types import (
    BlockInstance,
    EntityRecord,
    LineGeometry,
    MeshGeometry,
    Point3D,
    PolygonGeometry,
)


def list_layers(path: str | Path) -> list[str]:
    """Return the unique layer names referenced by model-space entities, sorted.

    Defensive against non-graphical entities (e.g. MagiCAD's MAGIFLOORORIGO
    proxy control object) which raise on ``entity.dxf.layer`` — those are
    silently skipped.
    """
    doc = ezdxf.readfile(str(path))
    layers: set[str] = set()
    for entity in doc.modelspace():
        try:
            layers.add(entity.dxf.layer)
        except Exception:  # noqa: BLE001 — non-graphical custom entity
            continue
    return sorted(layers)


def read_dxf(
    path: str | Path,
    *,
    acis_meshes: Mapping[str, object] | None = None,
) -> list[EntityRecord]:
    """Parse a DXF and return every supported entity in model space.

    ``acis_meshes`` is the side-channel produced by
    :func:`dxf2ifc.core.preprocessing.extract_acis_meshes` — a mapping
    from upper-case DXF entity handle to an :class:`AcisMeshData`-like
    object exposing ``.vertices`` and ``.faces``. When a 3DSOLID entity's
    handle is in this mapping, its triangulated mesh is yielded as a
    :class:`MeshGeometry`; when not, the body is silently skipped (ezdxf
    cannot parse the SAB-encoded body itself).
    """
    doc = ezdxf.readfile(str(path))
    msp = doc.modelspace()
    acis_meshes = acis_meshes or {}

    # Layers carrying at least one 3D mesh source — either a MESH entity
    # (manually MESHSMOOTHed by the user) or a 3DSOLID whose handle landed
    # in ``acis_meshes`` from accoreconsole+STLOUT preprocessing. KYL-* LISP
    # blocks emit BOTH a 2D LWPOLYLINE outline AND a 3DSOLID body — without
    # this filter we'd publish each shelf twice (extruded outline + faceted
    # mesh). Priority: MeshGeometry wins; LWPOLYLINE/INSERT/LINE on the same
    # layer are dropped to avoid duplicate IFC products.
    mesh_priority_layers: set[str] = set()
    for entity in msp:
        dxftype = entity.dxftype()
        if dxftype == "MESH":
            mesh_priority_layers.add(entity.dxf.layer)
        elif (
            dxftype == "3DSOLID"
            and str(entity.dxf.handle).upper() in acis_meshes
        ):
            mesh_priority_layers.add(entity.dxf.layer)

    records: list[EntityRecord] = []
    for entity in msp:
        try:
            dxftype = entity.dxftype()
        except Exception:  # noqa: BLE001 — fully unsupported entity classes
            continue
        if dxftype == "ACAD_PROXY_ENTITY":
            # MagiCAD (and some other AutoCAD add-ons) store their objects
            # as proxy entities — graphics-only stand-ins that survive
            # roundtripping when the original app is not loaded. ezdxf
            # 1.4+ can parse the embedded proxy_graphic stream and yield
            # primitive DXFGraphic entities (LINE / LWPOLYLINE / MESH /
            # CIRCLE / TEXT / ...) via __virtual_entities__(). We feed
            # each virtual entity back through the same dispatch so a
            # MagiCAD-drawn pipe centreline lands as a real LineGeometry
            # record, available to the profile mapper just like a native
            # AutoCAD LINE.
            #
            # Defensive: some MagiCAD-managed proxies (e.g. MAGIFLOORORIGO,
            # the floor-origin marker) are non-graphical control objects
            # and raise on `entity.dxf.layer` / `entity.dxf.handle`. Silent
            # skip — they have nothing to render in IFC anyway.
            try:
                proxy_layer = entity.dxf.layer
                proxy_handle = str(entity.dxf.handle).upper()
                virtual_iter = entity.__virtual_entities__()
            except Exception:  # noqa: BLE001 — non-graphical proxy / malformed
                continue
            for virtual in virtual_iter:
                v_layer = getattr(virtual.dxf, "layer", "0") or "0"
                # Virtual entities often inherit layer "0" from the
                # proxy stream. Fall back to the proxy's layer so the
                # profile mapper can still match on the AutoCAD layer
                # the user authored under (MagiCAD typically places its
                # proxies on a distinct layer like MAG_PIPE_*).
                effective_layer = proxy_layer if v_layer == "0" else v_layer
                try:
                    sub_record = _record_from_entity(
                        virtual,
                        layer_override=effective_layer,
                        handle_override=proxy_handle,
                        mesh_priority_layers=mesh_priority_layers,
                        acis_meshes=acis_meshes,
                    )
                except Exception:  # noqa: BLE001 — virtual subentity broke
                    continue
                if sub_record is not None:
                    records.append(sub_record)
            continue
        # Defensive: even native entity types may raise on missing dxf
        # attributes (custom CAD objects from third-party add-ons). One
        # bad entity must not abort the whole DXF read.
        try:
            record = _record_from_entity(
                entity,
                layer_override=None,
                handle_override=None,
                mesh_priority_layers=mesh_priority_layers,
                acis_meshes=acis_meshes,
            )
        except Exception:  # noqa: BLE001
            continue
        if record is not None:
            records.append(record)
    return records


def _record_from_entity(
    entity,
    *,
    layer_override: str | None,
    handle_override: str | None,
    mesh_priority_layers: set[str],
    acis_meshes: Mapping[str, object],
) -> EntityRecord | None:
    """Map a single ezdxf DXFGraphic entity to an EntityRecord.

    Used for both top-level model-space iteration and recursive proxy
    expansion (``ACAD_PROXY_ENTITY.__virtual_entities__()``). Returns
    ``None`` when the entity is not a supported geometry kind, when its
    body is empty, or when it is shadowed by a higher-priority mesh on
    the same layer (Plan-A double-publish guard).

    ``layer_override`` lets the caller force a layer (used for proxy
    virtual entities that inherit "0" instead of the proxy's authored
    layer). ``handle_override`` propagates the proxy's handle to its
    virtual children so the user can still trace warnings back to the
    original AutoCAD entity.
    """
    dxftype = entity.dxftype()
    layer = layer_override if layer_override is not None else getattr(entity.dxf, "layer", "0")

    def _handle() -> str:
        if handle_override is not None:
            return handle_override
        return str(getattr(entity.dxf, "handle", "")).upper()

    if (
        dxftype in ("LINE", "LWPOLYLINE", "POLYLINE")
        and layer in mesh_priority_layers
    ):
        return None

    if dxftype == "3DSOLID":
        handle = _handle()
        mesh_data = acis_meshes.get(handle)
        if mesh_data is None:
            return None
        vertices = tuple(
            Point3D(float(v[0]), float(v[1]), float(v[2]))
            for v in mesh_data.vertices
        )
        faces = tuple(tuple(int(i) for i in f) for f in mesh_data.faces)
        if not vertices or not faces:
            return None
        return EntityRecord(
            layer=layer,
            dxf_type="3DSOLID",
            geometry=MeshGeometry(vertices=vertices, faces=faces),
            attributes={},
            handle=handle,
        )

    if dxftype == "LINE":
        start = Point3D(*entity.dxf.start)
        end = Point3D(*entity.dxf.end)
        return EntityRecord(
            layer=layer,
            dxf_type="LINE",
            geometry=LineGeometry(start=start, end=end),
            attributes={},
            handle=_handle(),
        )

    if dxftype == "LWPOLYLINE" and entity.closed:
        elevation = float(entity.dxf.elevation or 0.0)
        ocs = entity.ocs()
        world_vertices: list[Point3D] = []
        for x, y, *_ in entity.get_points():
            wx, wy, wz = ocs.to_wcs((float(x), float(y), elevation))
            world_vertices.append(Point3D(float(wx), float(wy), float(wz)))
        return EntityRecord(
            layer=layer,
            dxf_type="LWPOLYLINE",
            geometry=PolygonGeometry(vertices=tuple(world_vertices), closed=True),
            attributes={},
            handle=_handle(),
        )

    if dxftype == "POLYLINE" and getattr(entity, "is_closed", False):
        # Proxy-graphics streams emit POLYLINE for closed n-gons (older
        # DXF format) instead of LWPOLYLINE. Vertices are AcDbVertex
        # subentities reachable via .points() — same WCS coordinates as
        # LWPOLYLINE but no OCS round-trip needed because the stream
        # already publishes 3D points.
        try:
            verts = list(entity.points())
        except AttributeError:
            return None
        if not verts:
            return None
        return EntityRecord(
            layer=layer,
            dxf_type="POLYLINE",
            geometry=PolygonGeometry(
                vertices=tuple(
                    Point3D(float(v[0]), float(v[1]), float(v[2]) if len(v) > 2 else 0.0)
                    for v in verts
                ),
                closed=True,
            ),
            attributes={},
            handle=_handle(),
        )

    if dxftype == "INSERT":
        handle = _handle()
        mesh_data = acis_meshes.get(handle)
        if mesh_data is not None:
            # accoreconsole EXPLODEd this INSERT and STLOUTed every
            # 3DSOLID/MESH child; the merged mesh is in world coords
            # (EXPLODE applies the block's transform). Emit as a real
            # faceted body instead of the bbox extrusion fallback.
            vertices = tuple(
                Point3D(float(v[0]), float(v[1]), float(v[2]))
                for v in mesh_data.vertices
            )
            faces = tuple(tuple(int(i) for i in f) for f in mesh_data.faces)
            if vertices and faces:
                return EntityRecord(
                    layer=layer,
                    dxf_type="INSERT",
                    geometry=MeshGeometry(vertices=vertices, faces=faces),
                    attributes={},
                    block_name=entity.dxf.name,
                    handle=handle,
                )
        insert = Point3D(
            float(entity.dxf.insert.x),
            float(entity.dxf.insert.y),
            float(entity.dxf.insert.z),
        )
        block_instance = BlockInstance(
            insertion_point=insert,
            rotation_rad=math.radians(float(entity.dxf.rotation or 0.0)),
            scale_x=float(entity.dxf.xscale or 1.0),
            scale_y=float(entity.dxf.yscale or 1.0),
            scale_z=float(entity.dxf.zscale or 1.0),
        )
        return EntityRecord(
            layer=layer,
            dxf_type="INSERT",
            geometry=block_instance,
            attributes={},
            block_name=entity.dxf.name,
            handle=handle,
        )

    if dxftype == "MESH":
        # accoreconsole.exe -MESHSMOOTH preprocesses 3DSOLIDs into MESH.
        # MeshBuilder.from_mesh extracts the deduplicated vertex pool
        # and the face index list (each face is n>=3 indices for n-gons).
        mb = MeshBuilder.from_mesh(entity)
        vertices = tuple(
            Point3D(float(v.x), float(v.y), float(v.z)) for v in mb.vertices
        )
        faces = tuple(tuple(int(i) for i in f) for f in mb.faces)
        if not vertices or not faces:
            return None
        return EntityRecord(
            layer=layer,
            dxf_type="MESH",
            geometry=MeshGeometry(vertices=vertices, faces=faces),
            attributes={},
            handle=_handle(),
        )

    return None
