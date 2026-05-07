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
    proxy_layers: Mapping[str, str] | None = None,
) -> list[EntityRecord]:
    """Parse a DXF and return every supported entity in model space.

    ``acis_meshes`` is the side-channel produced by
    :func:`dxf2ifc.core.preprocessing.extract_acis_meshes` — a mapping
    from upper-case DXF entity handle to an :class:`AcisMeshData`-like
    object exposing ``.vertices`` and ``.faces``. When a 3DSOLID entity's
    handle is in this mapping, its triangulated mesh is yielded as a
    :class:`MeshGeometry`; when not, the body is silently skipped (ezdxf
    cannot parse the SAB-encoded body itself).

    ``proxy_layers`` is the secondary side-channel produced by
    :func:`dxf2ifc.core.proxy_preprocessing.extract_proxy_geometry` —
    a ``{handle: layer}`` mapping captured from accoreconsole's LISP
    manifest. Required for MAGI* native entity classes
    (MAGIPATHWAYDEVICE, MAGIACCESSORY, …) because ezdxf cannot read
    their ``.dxf.layer`` attribute. ACAD_PROXY_ENTITY records read
    their layer directly from ezdxf and ignore this mapping.
    """
    doc = ezdxf.readfile(str(path))
    msp = doc.modelspace()
    acis_meshes = acis_meshes or {}
    proxy_layers = proxy_layers or {}

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
        elif dxftype == "POLYLINE" and getattr(entity, "is_poly_face_mesh", False):
            # Polyface mesh from MAGIEXPLODE — same priority as MESH so
            # any leftover line/wireframe artefacts on the same layer
            # don't double-publish as IfcCableCarrierSegment etc.
            mesh_priority_layers.add(entity.dxf.layer)
        elif dxftype == "3DFACE":
            mesh_priority_layers.add(entity.dxf.layer)

    records: list[EntityRecord] = []
    for entity in msp:
        try:
            dxftype = entity.dxftype()
        except Exception:  # noqa: BLE001 — fully unsupported entity classes
            continue
        if dxftype.startswith("MAGI"):
            # Native MagiCAD entity (post-Object-Enabler-saved DXF).
            # ezdxf cannot read its ``.dxf.layer`` attribute, so the
            # only path to layer-based mapping is via the proxy_layers
            # side-channel populated from accoreconsole's manifest.
            # Geometry comes through ``acis_meshes`` (EXPLODE+STLOUT
            # of 3DSOLID children) — for non-3DSOLID-yielding entity
            # classes (MAGIDIMLINE annotations etc) the handle is
            # absent from acis_meshes and we silently skip.
            try:
                handle = str(entity.dxf.handle).upper()
            except Exception:  # noqa: BLE001
                continue
            layer = proxy_layers.get(handle)
            if layer is None:
                continue
            mesh_data = acis_meshes.get(handle)
            if mesh_data is None:
                continue
            vertices = tuple(
                Point3D(float(v[0]), float(v[1]), float(v[2]))
                for v in mesh_data.vertices
            )
            faces = tuple(tuple(int(i) for i in f) for f in mesh_data.faces)
            if vertices and faces:
                records.append(EntityRecord(
                    layer=layer,
                    dxf_type=dxftype,
                    geometry=MeshGeometry(vertices=vertices, faces=faces),
                    attributes={},
                    handle=handle,
                ))
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
            except Exception:  # noqa: BLE001 — non-graphical proxy / malformed
                continue
            # Emit BOTH virtual-entity decode AND the preprocessing
            # mesh when both are available — they share the proxy's
            # handle/layer so the orchestrator's dispatch can pick the
            # geometry that matches the rule's IFC type:
            #   - IfcPipeSegment / IfcCableCarrierSegment / etc need
            #     LineGeometry → use the virtual entities (KYL-JV1
            #     pipe centrelines split into segments).
            #   - IfcBuildingElementProxy / IfcTank / IfcFlowController
            #     etc need Mesh → use the proxy_preprocessing cuboid
            #     (MUUT_OSAT, KYL-JV1-LAITE, KYL-KONDENSSIASTIAT).
            # The dispatcher in orchestrator.py skips records whose
            # geometry the target builder doesn't accept.
            mesh_data = acis_meshes.get(proxy_handle)
            if mesh_data is not None:
                vertices = tuple(
                    Point3D(float(v[0]), float(v[1]), float(v[2]))
                    for v in mesh_data.vertices
                )
                faces = tuple(tuple(int(i) for i in f) for f in mesh_data.faces)
                if vertices and faces:
                    records.append(EntityRecord(
                        layer=proxy_layer,
                        dxf_type="ACAD_PROXY_ENTITY",
                        geometry=MeshGeometry(vertices=vertices, faces=faces),
                        attributes={},
                        handle=proxy_handle,
                    ))
            # virtual_entities decoding for ezdxf-readable proxies
            # (~75% of MagiCAD proxies in a typical pre-save DXF).
            try:
                virtual_iter = entity.__virtual_entities__()
            except Exception:  # noqa: BLE001
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
                    sub_records = _record_from_entity(
                        virtual,
                        layer_override=effective_layer,
                        handle_override=proxy_handle,
                        mesh_priority_layers=mesh_priority_layers,
                        acis_meshes=acis_meshes,
                    )
                except Exception:  # noqa: BLE001 — virtual subentity broke
                    continue
                records.extend(sub_records)
            continue
        # Defensive: even native entity types may raise on missing dxf
        # attributes (custom CAD objects from third-party add-ons). One
        # bad entity must not abort the whole DXF read.
        try:
            new_records = _record_from_entity(
                entity,
                layer_override=None,
                handle_override=None,
                mesh_priority_layers=mesh_priority_layers,
                acis_meshes=acis_meshes,
            )
        except Exception:  # noqa: BLE001
            continue
        records.extend(new_records)
    return records


def _record_from_entity(
    entity,
    *,
    layer_override: str | None,
    handle_override: str | None,
    mesh_priority_layers: set[str],
    acis_meshes: Mapping[str, object],
) -> list[EntityRecord]:
    """Map a single ezdxf DXFGraphic entity to zero or more EntityRecords.

    Used for both top-level model-space iteration and recursive proxy
    expansion (``ACAD_PROXY_ENTITY.__virtual_entities__()``). Returns an
    empty list when the entity is not a supported geometry kind, when its
    body is empty, or when it is shadowed by a higher-priority mesh on
    the same layer (Plan-A double-publish guard).

    Most dxftypes (LINE, MESH, INSERT, 3DSOLID, closed LWPOLYLINE/POLYLINE)
    yield exactly one record. **Open** LWPOLYLINE/POLYLINE — common in
    MagiCAD proxy graphics where pipe centrelines and outlines are
    emitted as N-vertex open polylines — fan out to N-1 LineGeometry
    records, one per consecutive vertex pair. This lets the profile
    mapper route them through ``add_pipe_segment`` /
    ``add_cable_carrier_segment`` (LineGeometry-only builders) instead
    of silently dropping them. Layer + handle propagate identically to
    every segment.

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
        # Polyface POLYLINEs ARE the mesh — don't drop them with the
        # wireframe sibling clean-up below.
        and not (dxftype == "POLYLINE" and getattr(entity, "is_poly_face_mesh", False))
    ):
        return []

    if dxftype == "3DSOLID":
        handle = _handle()
        mesh_data = acis_meshes.get(handle)
        if mesh_data is None:
            return []
        vertices = tuple(
            Point3D(float(v[0]), float(v[1]), float(v[2]))
            for v in mesh_data.vertices
        )
        faces = tuple(tuple(int(i) for i in f) for f in mesh_data.faces)
        if not vertices or not faces:
            return []
        return [EntityRecord(
            layer=layer,
            dxf_type="3DSOLID",
            geometry=MeshGeometry(vertices=vertices, faces=faces),
            attributes={},
            handle=handle,
        )]

    if dxftype == "LINE":
        start = Point3D(*entity.dxf.start)
        end = Point3D(*entity.dxf.end)
        return [EntityRecord(
            layer=layer,
            dxf_type="LINE",
            geometry=LineGeometry(start=start, end=end),
            attributes={},
            handle=_handle(),
        )]

    if dxftype == "LWPOLYLINE":
        elevation = float(entity.dxf.elevation or 0.0)
        ocs = entity.ocs()
        world_vertices: list[Point3D] = []
        for x, y, *_ in entity.get_points():
            wx, wy, wz = ocs.to_wcs((float(x), float(y), elevation))
            world_vertices.append(Point3D(float(wx), float(wy), float(wz)))
        if entity.closed:
            return [EntityRecord(
                layer=layer,
                dxf_type="LWPOLYLINE",
                geometry=PolygonGeometry(vertices=tuple(world_vertices), closed=True),
                attributes={},
                handle=_handle(),
            )]
        # Open polyline: emit one LineGeometry per consecutive vertex pair.
        # Common shape in MagiCAD proxy graphics (pipe centrelines, detail
        # outlines). Single-vertex degenerate polylines drop silently.
        if len(world_vertices) < 2:
            return []
        h = _handle()
        return [
            EntityRecord(
                layer=layer,
                dxf_type="LWPOLYLINE",
                geometry=LineGeometry(start=v0, end=v1),
                attributes={},
                handle=h,
            )
            for v0, v1 in zip(world_vertices, world_vertices[1:])
        ]

    if dxftype == "POLYLINE":
        # MAGIEXPLODE typically writes geometry as a POLYLINE polyface
        # mesh (DXF flag bit 64) — vertex pool + face records (1-based
        # indices, trailing zeros pad shorter faces to fixed width).
        # Convert to MeshGeometry(source="polyface") so the IFC writer
        # routes it through the IfcTriangulatedFaceSet path and Solibri
        # renders surfaces, not lines.
        if getattr(entity, "is_poly_face_mesh", False):
            # MeshBuilder.from_polyface yields a deduplicated vertex pool
            # and 0-based face index lists — same shape as the MESH
            # branch below. ezdxf's polyface decoder already handles the
            # 1-based / trailing-zero AutoCAD storage convention.
            try:
                mb = MeshBuilder.from_polyface(entity)
            except Exception:  # noqa: BLE001 — malformed polyface
                return []
            pf_vertices = tuple(
                Point3D(float(v.x), float(v.y), float(v.z)) for v in mb.vertices
            )
            pf_faces = tuple(
                tuple(int(i) for i in f) for f in mb.faces if len(f) >= 3
            )
            if not pf_vertices or not pf_faces:
                return []
            return [EntityRecord(
                layer=layer,
                dxf_type="POLYFACE",
                geometry=MeshGeometry(
                    vertices=pf_vertices,
                    faces=pf_faces,
                    source="polyface",
                ),
                attributes={},
                handle=_handle(),
            )]
        # Proxy-graphics streams emit POLYLINE for n-gons in the older
        # DXF format instead of LWPOLYLINE. Vertices are AcDbVertex
        # subentities reachable via .points() — same WCS coordinates as
        # LWPOLYLINE but no OCS round-trip needed because the stream
        # already publishes 3D points.
        try:
            verts = list(entity.points())
        except AttributeError:
            return []
        if not verts:
            return []
        world_vertices = [
            Point3D(float(v[0]), float(v[1]), float(v[2]) if len(v) > 2 else 0.0)
            for v in verts
        ]
        if getattr(entity, "is_closed", False):
            return [EntityRecord(
                layer=layer,
                dxf_type="POLYLINE",
                geometry=PolygonGeometry(
                    vertices=tuple(world_vertices),
                    closed=True,
                ),
                attributes={},
                handle=_handle(),
            )]
        if len(world_vertices) < 2:
            return []
        h = _handle()
        return [
            EntityRecord(
                layer=layer,
                dxf_type="POLYLINE",
                geometry=LineGeometry(start=v0, end=v1),
                attributes={},
                handle=h,
            )
            for v0, v1 in zip(world_vertices, world_vertices[1:])
        ]

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
                return [EntityRecord(
                    layer=layer,
                    dxf_type="INSERT",
                    geometry=MeshGeometry(vertices=vertices, faces=faces),
                    attributes={},
                    block_name=entity.dxf.name,
                    handle=handle,
                )]
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
        return [EntityRecord(
            layer=layer,
            dxf_type="INSERT",
            geometry=block_instance,
            attributes={},
            block_name=entity.dxf.name,
            handle=handle,
        )]

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
            return []
        return [EntityRecord(
            layer=layer,
            dxf_type="MESH",
            geometry=MeshGeometry(
                vertices=vertices, faces=faces, source="mesh"
            ),
            attributes={},
            handle=_handle(),
        )]

    if dxftype == "3DFACE":
        # MAGIEXPLODE occasionally emits 3DFACE quads/triangles instead
        # of polyface meshes — same flat-shaded surface, different DXF
        # encoding. Each 3DFACE becomes one MeshGeometry with a single
        # face (3 or 4 vertices). Stamping `source="3dface"` routes the
        # writer to the IfcTriangulatedFaceSet path.
        try:
            v0 = entity.dxf.vtx0
            v1 = entity.dxf.vtx1
            v2 = entity.dxf.vtx2
            v3 = entity.dxf.vtx3
        except AttributeError:
            return []
        pts = [
            Point3D(float(v0[0]), float(v0[1]), float(v0[2]) if len(v0) > 2 else 0.0),
            Point3D(float(v1[0]), float(v1[1]), float(v1[2]) if len(v1) > 2 else 0.0),
            Point3D(float(v2[0]), float(v2[1]), float(v2[2]) if len(v2) > 2 else 0.0),
            Point3D(float(v3[0]), float(v3[1]), float(v3[2]) if len(v3) > 2 else 0.0),
        ]
        # AutoCAD encodes a triangle as a quad with vtx2 == vtx3.
        if pts[2] == pts[3]:
            verts = tuple(pts[:3])
            faces = ((0, 1, 2),)
        else:
            verts = tuple(pts)
            faces = ((0, 1, 2, 3),)
        return [EntityRecord(
            layer=layer,
            dxf_type="3DFACE",
            geometry=MeshGeometry(
                vertices=verts, faces=faces, source="3dface"
            ),
            attributes={},
            handle=_handle(),
        )]

    return []
