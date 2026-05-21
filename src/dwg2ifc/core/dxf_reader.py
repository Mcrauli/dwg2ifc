"""Read a DXF file and produce a list of EntityRecord objects.

Plan A handles only LINE entities. Plan B extends with LWPOLYLINE, 3DSOLID, INSERT.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Mapping

import ezdxf
from ezdxf.render import MeshBuilder

from dwg2ifc.core.types import (
    BlockAttrib,
    BlockInstance,
    EntityRecord,
    LineGeometry,
    MeshGeometry,
    Point3D,
    PolygonGeometry,
)


def _read_block_attribs(entity) -> list[BlockAttrib]:
    """Read an INSERT's ATTRIB subentities into :class:`BlockAttrib` records.

    ATTRIB entities carry only ``tag`` + ``text`` (the value); the
    human-readable ``prompt`` lives on the matching ATTDEF in the block
    definition. We look the block up via ``entity.doc.blocks`` and build
    a ``{TAG: prompt}`` map first so the FI_Tekninen property can keep
    the name the block author chose.

    Any failure (proxy-graphics synthetic INSERT, missing block,
    malformed attrib) degrades to an empty list rather than aborting
    the whole DXF read.
    """
    attribs = list(getattr(entity, "attribs", []) or [])
    if not attribs:
        return []
    # {upper-tag: prompt} from the block definition's ATTDEFs.
    prompts: dict[str, str] = {}
    try:
        doc = getattr(entity, "doc", None)
        block_name = getattr(entity.dxf, "name", None)
        block_def = doc.blocks.get(block_name) if doc and block_name else None
        if block_def is not None:
            for attdef in block_def.query("ATTDEF"):
                tag = str(getattr(attdef.dxf, "tag", "") or "").strip()
                if tag:
                    prompt = str(getattr(attdef.dxf, "prompt", "") or "").strip()
                    prompts.setdefault(tag.upper(), prompt)
    except Exception:  # noqa: BLE001 — prompt lookup is best-effort
        prompts = {}
    result: list[BlockAttrib] = []
    try:
        for attr in attribs:
            tag = str(getattr(attr.dxf, "tag", "") or "").strip()
            if not tag:
                continue
            value = str(getattr(attr.dxf, "text", "") or "").strip()
            result.append(
                BlockAttrib(
                    tag=tag,
                    prompt=prompts.get(tag.upper(), ""),
                    value=value,
                )
            )
    except Exception:  # noqa: BLE001 — malformed attrib must not crash
        return []
    return result


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


def _aggregate_3dface_from_insert(insert_entity) -> MeshGeometry | None:
    """Walk an INSERT's ``virtual_entities()`` and aggregate every
    block-level 3DFACE *plus* every closed LWPOLYLINE (extruded into
    a solid box) into a single MeshGeometry. ezdxf applies the
    INSERT's transform (insertion + rotation + scale) automatically,
    so the resulting vertices are already in world space.

    Returns ``None`` when the block has neither 3DFACEs nor closed
    LWPOLYLINEs (caller falls back to the BlockInstance path).

    **Why both 3DFACE and LWPOLYLINE extrusion**

    Lauri's rewritten KYL-LISP shelves (KLHYLLY-LEVY / KLHYLLY-TIKAS)
    encode each shelf as:

    * A closed LWPOLYLINE outlining each part footprint (rail rung,
      side rail, deck) at its bottom Z (``dxf.elevation``)
    * A 3DFACE covering that same footprint at its top Z

    Reading only the 3DFACEs gave Solibri flat top surfaces with no
    volume — visually broken. We now extrude every closed LWPOLYLINE
    from its ``elevation`` up to the Z of the smallest 3DFACE whose
    XY bounding box covers the polyline's XY bbox (the matching top
    cap). That produces real 3D boxes for each rail rung / side rail /
    deck. 3DFACEs whose footprint isn't covered by any polyline still
    render as flat faces (cosmetic detail layers).

    Vertices are deduplicated at 4-decimal precision so adjacent
    parts that share an edge produce a connected mesh.
    """
    try:
        virt = list(insert_entity.virtual_entities())
    except Exception:  # noqa: BLE001 — malformed block, ezdxf can raise
        return None

    # Recursively flatten nested INSERTs. ezdxf's INSERT.virtual_entities()
    # applies the parent transform to direct block children but does NOT
    # descend into block-level INSERTs — nested sub-blocks come back as
    # INSERT entities that we must expand ourselves. Without this loop,
    # equipment blocks built as compound assemblies (a koneikko block
    # whose definition references a compressor sub-block + condenser
    # sub-block) would surface no 3DFACE/LWPOLYLINE here and fall through
    # to the geometryless BlockInstance path. depth_cap=8 catches any
    # pathological circular nesting without crashing.
    queue = list(virt)
    flat: list = []
    depth_cap = 1000
    while queue and depth_cap > 0:
        v_ent = queue.pop()
        depth_cap -= 1
        t = v_ent.dxftype() if hasattr(v_ent, "dxftype") else ""
        if t == "INSERT":
            try:
                queue.extend(v_ent.virtual_entities())
            except Exception:  # noqa: BLE001
                continue
            continue
        flat.append(v_ent)
    virt = flat

    # Aggregation runs in a single OCS (Object Coordinate System) defined
    # by a common extrusion vector. For an axis-aligned INSERT the OCS is
    # WCS itself; for a 3D-rotated INSERT (e.g. KLHV — KLHYLLY-TIKAS stood
    # vertically by setting extrusion=(0,-1,0)) the OCS Z axis follows the
    # extrusion vector and the thickness-extrusion step below runs along
    # that axis instead of world Z. The two are equivalent when the
    # extrusion is (0,0,1) so existing axis-aligned shelves are unchanged.
    #
    # Determining the OCS:
    # * LWPOLYLINEs in a virtual block share the parent INSERT's extrusion,
    #   so the first closed polyline we see fixes it for the whole block.
    # * 3DFACEs are always emitted in WCS by DXF spec — they don't carry an
    #   extrusion vector — but they belong to the same block, so we convert
    #   their WCS vertices into the shared OCS via ``ocs.from_wcs``.
    extrusion = (0.0, 0.0, 1.0)
    block_ocs = None
    for v_ent in virt:
        if (
            v_ent.dxftype() == "LWPOLYLINE"
            and getattr(v_ent, "is_closed", False)
        ):
            try:
                ext = v_ent.dxf.extrusion
                extrusion = (float(ext[0]), float(ext[1]), float(ext[2]))
                block_ocs = v_ent.ocs()
                break
            except AttributeError:
                continue
    if block_ocs is None:
        # No LWPOLYLINE found — every 3DFACE will be treated as already
        # being in (WCS == OCS). Build a trivial OCS for that.
        from ezdxf.math import OCS as _OCS  # local import keeps top tidy

        block_ocs = _OCS(extrusion)

    # Records are now stored in OCS coordinates.
    face_records: list[tuple[
        tuple[float, float, float, float],  # (xmin, ymin, xmax, ymax) in OCS
        float,  # face top Z in OCS
        list[tuple[float, float, float]],  # vertices in OCS
    ]] = []
    polyline_records: list[tuple[
        list[tuple[float, float]],  # XY vertices in OCS (closed)
        float,  # base Z in OCS (= polyline elevation)
    ]] = []

    for v_ent in virt:
        t = v_ent.dxftype()
        if t == "3DFACE":
            try:
                v0 = v_ent.dxf.vtx0
                v1 = v_ent.dxf.vtx1
                v2 = v_ent.dxf.vtx2
                v3 = v_ent.dxf.vtx3
            except AttributeError:
                continue
            wcs_pts = [
                (float(v[0]), float(v[1]), float(v[2]) if len(v) > 2 else 0.0)
                for v in (v0, v1, v2, v3)
            ]
            # Convert WCS → OCS so the downstream bbox/pairing logic
            # runs in the same local frame as the polylines.
            try:
                pts = [
                    tuple(block_ocs.from_wcs(p))
                    for p in wcs_pts
                ]
            except Exception:  # noqa: BLE001
                continue
            pts = [(float(p[0]), float(p[1]), float(p[2])) for p in pts]
            face_pts = pts[:3] if pts[2] == pts[3] else pts
            xs = [p[0] for p in face_pts]
            ys = [p[1] for p in face_pts]
            zs = [p[2] for p in face_pts]
            face_records.append((
                (min(xs), min(ys), max(xs), max(ys)),
                max(zs),
                face_pts,
            ))
        elif t == "LWPOLYLINE":
            if not getattr(v_ent, "is_closed", False):
                continue
            try:
                ocs_pts = list(v_ent.get_points("xy"))
            except Exception:  # noqa: BLE001
                continue
            if len(ocs_pts) < 3:
                continue
            elev = float(getattr(v_ent.dxf, "elevation", 0.0) or 0.0)
            # LWPOLYLINE vertices are already in OCS. Store the raw 2D
            # coordinates plus the OCS elevation as base Z. The shared
            # block OCS converts everything back to WCS at the end —
            # this is the path that previously dropped the Z and broke
            # 3D-rotated INSERTs (every rung collapsed onto WCS-Z).
            pts2d = [(float(p[0]), float(p[1])) for p in ocs_pts]
            polyline_records.append((pts2d, elev))

    if not face_records and not polyline_records:
        return None

    vertices: list[Point3D] = []
    faces: list[tuple[int, ...]] = []
    v_to_idx: dict[tuple[float, float, float], int] = {}

    def add_vertex(x: float, y: float, z: float) -> int:
        # (x, y, z) are in the block's OCS. Convert back to WCS so the
        # downstream MeshGeometry is world-space.
        wcs = block_ocs.to_wcs((float(x), float(y), float(z)))
        wx, wy, wz = float(wcs.x), float(wcs.y), float(wcs.z)
        key = (round(wx, 4), round(wy, 4), round(wz, 4))
        idx = v_to_idx.get(key)
        if idx is None:
            idx = len(vertices)
            v_to_idx[key] = idx
            vertices.append(Point3D(wx, wy, wz))
        return idx

    # 1) Emit 3DFACEs as flat polygons
    for _, _, face_pts in face_records:
        face_idx = [add_vertex(*p) for p in face_pts]
        faces.append(tuple(face_idx))

    # 2) Extrude each closed LWPOLYLINE → solid box. Top Z is
    #    inferred from the smallest 3DFACE whose XY bbox covers the
    #    polyline's XY bbox (and is above the polyline's elevation).
    DEFAULT_TOP_OFFSET_MM = 9.0
    EPS = 1e-3
    # Threshold: polylines whose shorter side is ≤5mm are
    # "side rim" strips (e.g. levyhyllyn 1.2mm leveä etureunan kylki
    # joka kiertää koko hyllyn pohjasta yläreunaan). Their proper
    # extrusion top is NOT the matching 3DFACE Z (which gives only
    # the deck thickness) but the highest top in the block — the
    # rim wraps the entire shelf height.
    THIN_RIM_THRESHOLD_MM = 5.0
    # 3DFACEs are authoritative for the block's true top. The
    # ``max(polyline_elev) + DEFAULT_TOP_OFFSET_MM`` fallback is only
    # useful when the block has no 3DFACE info at all (legacy
    # outline-only blocks where the rim has to guess its own height) —
    # using it alongside 3DFACEs inflates ``block_max_top`` whenever a
    # polyline sits high in the block. KYL-KOTELO's top slab is a
    # polyline at elev=118.2; without this guard the thin side-wall
    # rims would extrude to 118.2 + 9 = 127.2 instead of the real
    # 3DFACE-defined top z=120, leaving the wide top slab visually
    # recessed below the protruding side walls.
    if face_records:
        block_max_top = max(fz for _, fz, _ in face_records)
    elif polyline_records:
        block_max_top = (
            max(p[1] for p in polyline_records) + DEFAULT_TOP_OFFSET_MM
        )
    else:
        block_max_top = 0.0
    for pts2d, base_z in polyline_records:
        xs = [p[0] for p in pts2d]
        ys = [p[1] for p in pts2d]
        poly_bbox = (min(xs), min(ys), max(xs), max(ys))
        poly_w = poly_bbox[2] - poly_bbox[0]
        poly_h = poly_bbox[3] - poly_bbox[1]
        # Skip degenerate polylines (single-point loops).
        if poly_w < EPS or poly_h < EPS:
            continue
        is_thin_rim = min(poly_w, poly_h) <= THIN_RIM_THRESHOLD_MM
        if is_thin_rim and block_max_top > base_z + EPS:
            # Side rim: stretch from its base up to the entire block's
            # top. This is the only way to recover the side wall of a
            # shelf when the block-level encoding only contains the
            # top-cap 3DFACE at deck height + the perimeter LWPOLYLINEs
            # at elev=0 — without this the rim would render only as a
            # 1.2mm-tall sliver coplanar with the deck.
            top_z = block_max_top
        else:
            # Find the lowest 3DFACE that is above base_z and whose
            # XY bbox covers (with small slack) the polyline's bbox.
            best_top: float | None = None
            for fbbox, fz, _ in face_records:
                if fz <= base_z + EPS:
                    continue
                if (
                    fbbox[0] <= poly_bbox[0] + EPS
                    and fbbox[1] <= poly_bbox[1] + EPS
                    and fbbox[2] >= poly_bbox[2] - EPS
                    and fbbox[3] >= poly_bbox[3] - EPS
                ):
                    if best_top is None or fz < best_top:
                        best_top = fz
            top_z = best_top if best_top is not None else base_z + DEFAULT_TOP_OFFSET_MM
        thickness = top_z - base_z
        if thickness <= EPS:
            continue
        # Drop the redundant closing vertex if present (LWPOLYLINE
        # closure is implicit; ezdxf may or may not duplicate the
        # first point at the end).
        if len(pts2d) > 1 and pts2d[0] == pts2d[-1]:
            ring = pts2d[:-1]
        else:
            ring = pts2d
        n = len(ring)
        if n < 3:
            continue
        bottom = [add_vertex(p[0], p[1], base_z) for p in ring]
        top = [add_vertex(p[0], p[1], top_z) for p in ring]
        # Side quads, CCW seen from outside (assuming polyline is CCW)
        for i in range(n):
            j = (i + 1) % n
            faces.append((bottom[i], bottom[j], top[j], top[i]))
        # Caps via fan triangulation (n-gon → n-2 triangles)
        for i in range(1, n - 1):
            faces.append((top[0], top[i], top[i + 1]))
            faces.append((bottom[0], bottom[i + 1], bottom[i]))  # reverse winding

    if not vertices or not faces:
        return None
    return MeshGeometry(
        vertices=tuple(vertices),
        faces=tuple(faces),
        source="3dface",
    )


def read_dxf(
    path: str | Path,
    *,
    acis_meshes: Mapping[str, object] | None = None,
    proxy_layers: Mapping[str, str] | None = None,
    skip_magicad: bool = False,
) -> list[EntityRecord]:
    """Parse a DXF and return every supported entity in model space.

    ``acis_meshes`` is the side-channel produced by
    :func:`dwg2ifc.core.preprocessing.extract_acis_meshes` — a mapping
    from upper-case DXF entity handle to an :class:`AcisMeshData`-like
    object exposing ``.vertices`` and ``.faces``. When a 3DSOLID entity's
    handle is in this mapping, its triangulated mesh is yielded as a
    :class:`MeshGeometry`; when not, the body is silently skipped (ezdxf
    cannot parse the SAB-encoded body itself).

    ``proxy_layers`` is the secondary side-channel produced by
    :func:`dwg2ifc.core.proxy_preprocessing.extract_proxy_geometry` —
    a ``{handle: layer}`` mapping captured from accoreconsole's LISP
    manifest. Required for MAGI* native entity classes
    (MAGIPATHWAYDEVICE, MAGIACCESSORY, …) because ezdxf cannot read
    their ``.dxf.layer`` attribute. ACAD_PROXY_ENTITY records read
    their layer directly from ezdxf and ignore this mapping.

    ``skip_magicad`` (default False): when True, every ``MAGI*`` native
    class and every ``ACAD_PROXY_ENTITY`` (the wrapper MagiCAD uses
    when its ARX isn't loaded) is dropped before mapping. The
    orchestrator sets this to True when a separate MagiCAD-IFC export
    is being merged in by :mod:`dwg2ifc.core.ifc_merger` so MagiCAD
    parts don't appear twice (once as mesh-tessellated geometry, once
    as proper IFC types from the MAGIIFCEXPORT side).
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
            if skip_magicad:
                # Caller will merge the MagiCAD products in from a
                # separate MAGIIFCEXPORT-produced IFC; drop the
                # mesh-tessellated copy here to avoid duplicates.
                continue
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
            if skip_magicad:
                # Same rationale as the MAGI* skip above. Most proxies
                # in a MagiCAD-bearing DWG ARE MagiCAD; the (rare)
                # non-MagiCAD ARX proxies will also drop, which is OK
                # because dwg2ifc only ships profiles for MagiCAD
                # patterns anyway.
                continue
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
        # ATTRIB subentities carry user-typed fields (tag, prompt,
        # value) that travel with the INSERT in the DWG. apply_block_-
        # attribs (run later by the orchestrator) routes each one into
        # FI_Tuote / FI_Tekninen.
        block_attribs = _read_block_attribs(entity)

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
                    block_attribs=block_attribs,
                )]
        # Try aggregating any 3DFACE entities the block carries —
        # Lauri's KYL-LISP shelves now emit dynamic block references
        # (anonymous *U* blocks) whose definition has 3DFACE faces in
        # block coordinates. ezdxf's INSERT.virtual_entities() applies
        # the INSERT transform (insertion, rotation, scale) so the
        # 3DFACE vertices land in world space — no accoreconsole or
        # AutoCAD COM needed.
        face_mesh = _aggregate_3dface_from_insert(entity)
        if face_mesh is not None:
            return [EntityRecord(
                layer=layer,
                dxf_type="INSERT",
                geometry=face_mesh,
                attributes={},
                block_name=entity.dxf.name,
                handle=handle,
                block_attribs=block_attribs,
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
            block_attribs=block_attribs,
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
