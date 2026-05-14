"""convert_dxf orchestrator -- DXF -> IFC end-to-end pipeline."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import ifcopenshell

if TYPE_CHECKING:  # pragma: no cover
    from dxf2ifc.core.quality import ValidationReport

from dxf2ifc.core.dxf_reader import read_dxf
from dxf2ifc.core.energy_specs import (
    load_energy_specs_with_headers,
    lookup_spec,
)
from dxf2ifc.core.ifc_writer.builders import (
    _COOLING_EQUIPMENT_CLASSES,
    _DISTRIBUTION_ELEMENT_CLASSES,
    add_building_element_proxy,
    add_cable_carrier,
    add_cable_carrier_segment,
    add_cooling_equipment,
    add_distribution_element,
    add_door,
    add_flow_controller,
    add_furniture,
    add_pipe_segment,
    add_slab,
    add_system,
    add_tank,
    add_wall,
    add_window,
    assign_to_system,
    write_ifc,
)
from dxf2ifc.core.ifc_writer.mesh import _add_mesh_product
from dxf2ifc.core.ifc_writer.classification import (
    add_classification,
    add_discipline_classification,
    discipline_label,
)
from dxf2ifc.core.ifc_writer.skeleton import (
    IfcSkeleton,
    build_ifc_project_skeleton,
)
from dxf2ifc.core.mapper import apply_profile
from dxf2ifc.core.types import (
    BlockInstance,
    FileEntry,
    LineGeometry,
    MappedEntity,
    MeshGeometry,
    Point3D,
    PolygonGeometry,
)
from dxf2ifc.profiles.schema import Profile


def _shift_point(p: Point3D, dz: float) -> Point3D:
    return Point3D(p.x, p.y, p.z + dz)


def _shift_geometry(geometry: object, dz: float) -> object:
    """Return a copy of ``geometry`` with every Z component offset by ``dz``.

    Geometry dataclasses are frozen, so each variant rebuilds via its
    constructor with the shifted Point3D fields. Unknown geometry types
    are returned as-is — defensive against forward-compatible additions.
    """
    if isinstance(geometry, LineGeometry):
        return LineGeometry(
            start=_shift_point(geometry.start, dz),
            end=_shift_point(geometry.end, dz),
        )
    if isinstance(geometry, PolygonGeometry):
        return PolygonGeometry(
            vertices=tuple(_shift_point(v, dz) for v in geometry.vertices),
            closed=geometry.closed,
        )
    if isinstance(geometry, BlockInstance):
        return BlockInstance(
            insertion_point=_shift_point(geometry.insertion_point, dz),
            rotation_rad=geometry.rotation_rad,
            scale_x=geometry.scale_x,
            scale_y=geometry.scale_y,
            scale_z=geometry.scale_z,
        )
    if isinstance(geometry, MeshGeometry):
        return MeshGeometry(
            vertices=tuple(_shift_point(v, dz) for v in geometry.vertices),
            faces=geometry.faces,
        )
    return geometry


def _apply_floor_elevation_offset(mapped: list[MappedEntity], dz: float) -> None:
    """Mutate every ``MappedEntity.geometry`` in place to add ``dz`` to its
    Z component(s) — the per-floor elevation offset.

    Each floor's geometry is lifted by that floor's ``elevation_mm`` so
    the objects land at ``floor_elevation + dxf_Z`` in world space.
    ``build_ifc_project_skeleton`` places the matching
    ``IfcBuildingStorey`` at the same elevation, so storey labels and
    element placements agree. ``dz == 0`` is a no-op (CAD coordinates
    pass straight through).
    """
    if dz == 0.0:
        return
    for m in mapped:
        m.geometry = _shift_geometry(m.geometry, dz)


def _emit(progress: object | None, message: str) -> None:
    """Write a status line to stderr + optional progress callback.
    Never raises; callback exceptions are swallowed so a faulty UI
    handler cannot abort the conversion."""
    print(message, file=sys.stderr)
    if callable(progress):
        try:
            progress(message)
        except Exception:  # noqa: BLE001 — UI errors must not propagate
            pass


def _run_energy_spec_lookup(
    mapped: list,
    energy_specs_path: str | Path,
    *,
    profile: Profile,
    progress: object | None,
) -> None:
    """Load the external energy-spec table and merge matching rows into
    each refrigeration MappedEntity's fi_tekninen.

    Diagnostics emitted via :func:`_emit`:
      - file load failure (with exception class + message)
      - per-sheet header summary
      - "ladattu N riviä" + "M/K kylmälaitetta sai tehotiedot"
      - per-device skip reasons (POSITIO puuttuu / ei riviä Excelissä)

    The function never raises; lookups missing from the spreadsheet
    silently leave the rule-level fi_tekninen template in place.
    """
    try:
        specs, headers_per_sheet = load_energy_specs_with_headers(energy_specs_path)
    except Exception as exc:  # noqa: BLE001 — never abort convert
        _emit(
            progress,
            f"Energiateho: tiedoston luku ei onnistunut "
            f"({type(exc).__name__}: {exc})",
        )
        return

    if not specs:
        if not headers_per_sheet:
            _emit(
                progress,
                "Energiateho: tiedostosta ei löytynyt yhtään käyttökelpoista "
                "taulukkoa (Koneikko + Laitetunnus -sarakkeet puuttuvat)",
            )
        else:
            sheets_summary = "; ".join(
                f"{name}={hdrs}" for name, hdrs in headers_per_sheet.items()
            )
            _emit(
                progress,
                f"Energiateho: 0 riviä mätsäsi. Tunnistetut headerit: "
                f"{sheets_summary}",
            )
        return

    _emit(
        progress,
        f"Energiateho: ladattu {len(specs)} riviä "
        f"({len(headers_per_sheet)} sheettiä)",
    )

    scope: set[str] = set()
    if profile.positio is not None:
        scope = set(profile.positio.apply_to)
    candidates = [m for m in mapped if m.ifc_type in scope]

    matched = 0
    skipped: list[tuple[object, str]] = []
    for m in candidates:
        ko = (m.extra_props or {}).get("koneikko") if m.extra_props else None
        la = (m.extra_props or {}).get("laitetunnus") if m.extra_props else None
        if not ko or not la:
            skipped.append((m, "POSITIO-merkki puuttuu DXF:stä"))
            continue
        spec = lookup_spec(specs, koneikko=ko, laitetunnus=la)
        if spec is None:
            skipped.append((m, f"ei riviä Excelissä avaimelle {ko}/{la}"))
            continue
        merged: dict[str, str] = {}
        if m.fi_tekninen:
            merged.update(m.fi_tekninen)
        merged.update(spec.fields)
        m.fi_tekninen = merged
        matched += 1

    _emit(
        progress,
        f"Energiateho: {matched}/{len(candidates)} kylmälaitetta "
        f"sai tehotiedot",
    )
    # Surface the first 10 skip reasons so the user can spot
    # systematic problems (whole sheet missing, one koneikko misnamed
    # etc.) without drowning the log on a 100-device project.
    for m, reason in skipped[:10]:
        layer = getattr(m, "layer", "?")
        _emit(progress, f"  ohi: {layer} → {reason}")
    if len(skipped) > 10:
        _emit(progress, f"  …ja {len(skipped) - 10} muuta ohitettua")


def _process_one_file(
    file_entry: FileEntry,
    *,
    profile: Profile,
    schema: str,
    preprocess_acis: bool,
    skip_magicad: bool,
    energy_specs_path: str | Path | None,
    progress: object | None,
) -> list[MappedEntity]:
    """Run preprocess + read + map + POSITIO + energy-spec + Z-offset for one file.

    Returns ``MappedEntity`` records ready for the IFC writer. The caller
    is responsible for assigning ``storey_index`` on each returned entry
    (default 0 — fine for single-file legacy callers).
    """
    label = file_entry.floor_label
    input_path = Path(file_entry.path)
    if input_path.suffix.lower() == ".dwg":
        from dxf2ifc.core.dwg_preconvert import convert_dwg_to_dxf
        dwg_workdir = Path(tempfile.mkdtemp(prefix="dxf2ifc_dwgin_"))
        dxf_path: str | Path = convert_dwg_to_dxf(
            input_path,
            dwg_workdir,
            progress=progress if callable(progress) else None,
        )
    else:
        dxf_path = input_path

    acis_meshes: dict[str, object] = {}
    if preprocess_acis:
        from dxf2ifc.core.preprocessing import (
            extract_acis_meshes,
            layer_filter_from_profile,
        )
        # Restrict accoreconsole STLOUT to the layers the profile actually
        # maps — otherwise every architectural / structural XREF 3DSOLID
        # gets tessellated only to be dropped by apply_profile later.
        acis_layer_filter = layer_filter_from_profile(profile)
        if progress is not None and acis_layer_filter != "*":
            progress(
                f"ACIS-tessellointi rajataan layereihin: {acis_layer_filter}"
            )
        acis_meshes = extract_acis_meshes(  # type: ignore[arg-type,assignment]
            dxf_path,
            layer_filter=acis_layer_filter,
            progress=progress,
            skip_magicad=skip_magicad,
        )

    entities = read_dxf(dxf_path, acis_meshes=acis_meshes, skip_magicad=skip_magicad)

    if progress is not None:
        polyface_count = sum(
            1 for e in entities
            if isinstance(e.geometry, MeshGeometry)
            and e.geometry.source in {"polyface", "3dface", "mesh"}
        )
        acis_count = sum(
            1 for e in entities
            if isinstance(e.geometry, MeshGeometry)
            and e.geometry.source == "acis"
        )
        layers_with_mesh: dict[str, int] = {}
        for e in entities:
            if isinstance(e.geometry, MeshGeometry):
                layers_with_mesh[e.layer] = layers_with_mesh.get(e.layer, 0) + 1
        progress(
            f"[{label}] DXF-luettu: {polyface_count} polyface/3DFACE/MESH + "
            f"{acis_count} ACIS-mesh (yhteensä {len(entities)} entiteettiä)"
        )
        if layers_with_mesh:
            top = sorted(layers_with_mesh.items(), key=lambda x: -x[1])[:5]
            progress(
                f"[{label}] Mesh-layerit (top 5): "
                + ", ".join(f"{lyr}={n}" for lyr, n in top)
            )

    mapped = apply_profile(entities, profile)

    if progress is not None:
        mapped_mesh = sum(1 for m in mapped if isinstance(m.geometry, MeshGeometry))
        mapped_types: dict[str, int] = {}
        for m in mapped:
            if isinstance(m.geometry, MeshGeometry):
                mapped_types[m.ifc_type] = mapped_types.get(m.ifc_type, 0) + 1
        progress(
            f"[{label}] Profile-mappaus: {len(mapped)} entiteettiä, joista "
            f"{mapped_mesh} mesh-pohjaisia"
        )
        if mapped_types:
            top = sorted(mapped_types.items(), key=lambda x: -x[1])[:5]
            progress(
                f"[{label}] Mesh→IFC-tyypit: "
                + ", ".join(f"{t}={n}" for t, n in top)
            )

    # POSITIO-block linkage. Index every numbering INSERT once, then per
    # refrigeration-equipment MappedEntity find the closest one (XY-2D,
    # profile-specified radius). The match goes into extra_props so
    # add_finnish_psets can read it without a separate parameter channel.
    if profile.positio is not None:
        from dxf2ifc.core.positio import (
            find_nearest_positio,
            index_positio_markers,
        )

        positio_markers = index_positio_markers(
            dxf_path, block_pattern=profile.positio.block_pattern
        )
        if positio_markers:
            scope = set(profile.positio.apply_to)
            radius = profile.positio.max_distance_mm
            import ezdxf as _ezdxf
            insert_xy_by_handle: dict[str, tuple[float, float]] = {}
            try:
                _doc = _ezdxf.readfile(str(dxf_path))
                for _ent in _doc.modelspace():
                    if _ent.dxftype() != "INSERT":
                        continue
                    try:
                        _h = str(_ent.dxf.handle).upper()
                        insert_xy_by_handle[_h] = (
                            float(_ent.dxf.insert.x),
                            float(_ent.dxf.insert.y),
                        )
                    except Exception:  # noqa: BLE001
                        continue
            except Exception:  # noqa: BLE001 — POSITIO link is best-effort
                pass

            for m in mapped:
                if m.ifc_type not in scope:
                    continue
                target_xy: tuple[float, float] | None = None
                handle = getattr(m, "handle", None)
                if handle and str(handle).upper() in insert_xy_by_handle:
                    target_xy = insert_xy_by_handle[str(handle).upper()]
                elif isinstance(m.geometry, BlockInstance):
                    target_xy = (
                        m.geometry.insertion_point.x,
                        m.geometry.insertion_point.y,
                    )
                elif isinstance(m.geometry, MeshGeometry) and m.geometry.vertices:
                    xs = [v.x for v in m.geometry.vertices]
                    ys = [v.y for v in m.geometry.vertices]
                    target_xy = (
                        (min(xs) + max(xs)) / 2.0,
                        (min(ys) + max(ys)) / 2.0,
                    )
                if target_xy is None:
                    continue
                marker = find_nearest_positio(
                    target_xy,
                    positio_markers,
                    max_distance_mm=radius,
                )
                if marker is None:
                    continue
                if m.extra_props is None:
                    m.extra_props = {}
                if marker.teksti:
                    m.extra_props["koneikko"] = marker.teksti
                if marker.numero:
                    m.extra_props["laitetunnus"] = marker.numero

    if energy_specs_path is not None:
        _run_energy_spec_lookup(
            mapped, energy_specs_path, profile=profile, progress=progress
        )

    # Bbox fallback: when accoreconsole STLOUT crashed (or didn't run),
    # cooling equipment / proxies / etc. remain BlockInstance-only and
    # the builder dispatch would skip them entirely. Compute a bbox
    # cuboid from the block definition via ezdxf and replace the
    # BlockInstance with a MeshGeometry so the equipment at least
    # appears as a placeholder box at the right XY position.
    _apply_block_bbox_fallback(mapped, dxf_path, progress=progress)

    # Per-floor elevation offset: lift this file's geometry by its
    # ``elevation_mm`` so objects land at ``elevation + dxf_Z`` in world
    # space. ``build_ifc_project_skeleton`` puts the matching
    # IfcBuildingStorey at the same elevation. ``elevation_mm == 0`` is a
    # no-op — CAD coordinates pass straight through.
    _apply_floor_elevation_offset(mapped, file_entry.elevation_mm)

    return mapped


def _sab_vertex_extents(
    acis_data: bytes,
) -> tuple[tuple[float, float, float], tuple[float, float, float]] | None:
    """Crude bbox of a 3DSOLID's ACIS SAB body by scanning for ``(0x14, x, y, z)``
    position tokens — three little-endian IEEE 754 doubles preceded by the
    SAB ``position`` opcode (0x14). Works on Autodesk SAB v4 (the binary
    format that ezdxf's structured parser does not yet handle), giving us
    a placeholder bbox even when full tessellation is unavailable.
    Returns ``None`` if no plausible coordinates can be extracted.
    """
    import struct
    if not acis_data or len(acis_data) < 25:
        return None
    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    end = len(acis_data) - 25
    for i in range(end):
        if acis_data[i] != 0x14:
            continue
        try:
            x, y, z = struct.unpack_from("<ddd", acis_data, i + 1)
        except struct.error:
            continue
        # Filter junk matches: real coordinates are finite and within a
        # generous building-scale window (kilometres). Doubles that
        # decode random byte runs typically blow past 1e30 or are NaN.
        if not (
            -1e9 < x < 1e9 and -1e9 < y < 1e9 and -1e9 < z < 1e9
        ):
            continue
        xs.append(x)
        ys.append(y)
        zs.append(z)
    if not xs:
        return None
    return (
        (min(xs), min(ys), min(zs)),
        (max(xs), max(ys), max(zs)),
    )


def _block_local_extents_with_sab(block) -> tuple[tuple[float, float, float], tuple[float, float, float]] | None:
    """Walk a block definition and return the combined bbox of every
    3DSOLID's SAB-scanned vertex cloud, in BLOCK-LOCAL coordinates.
    Fallback for INSERTs whose ezdxf bbox is empty because the block
    only contains 3DSOLIDs."""
    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    for ent in block:
        if ent.dxftype() not in ("3DSOLID", "SURFACE", "BODY", "REGION"):
            continue
        data = getattr(ent, "acis_data", None) or b""
        ext = _sab_vertex_extents(bytes(data))
        if ext is None:
            continue
        (lo, hi) = ext
        xs.extend([lo[0], hi[0]])
        ys.extend([lo[1], hi[1]])
        zs.extend([lo[2], hi[2]])
    if not xs:
        return None
    return (
        (min(xs), min(ys), min(zs)),
        (max(xs), max(ys), max(zs)),
    )


def _apply_block_bbox_fallback(
    mapped: list[MappedEntity],
    dxf_path: str | Path,
    *,
    progress: object | None,
) -> None:
    """Replace BlockInstance geometry with a bbox cuboid mesh for any
    mapped entity whose IFC type requires MeshGeometry but didn't get
    one from accoreconsole. Ensures the equipment shows up at least as
    a placeholder box even when STLOUT failed or never ran.

    The bbox is computed via ``ezdxf.bbox.extents`` on the source INSERT
    (which walks the block's content and any nested geometry). If the
    bbox can't be determined (block empty, ezdxf can't read it), the
    entity is left as BlockInstance and the dispatcher will skip it as
    before — no regression vs. the old behaviour.
    """
    candidates = [
        m for m in mapped
        if isinstance(m.geometry, BlockInstance)
        and m.ifc_type in (
            _COOLING_EQUIPMENT_CLASSES
            | _DISTRIBUTION_ELEMENT_CLASSES
            | {"IfcTank", "IfcFlowController", "IfcBuildingElementProxy", "IfcFurniture"}
        )
    ]
    if not candidates:
        return

    try:
        import ezdxf
        from ezdxf import bbox as ezbbox
    except Exception:  # noqa: BLE001 — never block convert
        return

    try:
        doc = ezdxf.readfile(str(dxf_path))
    except Exception:  # noqa: BLE001
        return

    handle_to_insert: dict[str, object] = {}
    for ent in doc.modelspace():
        if ent.dxftype() != "INSERT":
            continue
        try:
            h = str(ent.dxf.handle).upper()
            handle_to_insert[h] = ent
        except Exception:  # noqa: BLE001
            continue

    promoted = 0
    for m in candidates:
        handle = (getattr(m, "handle", "") or "").upper()
        ins = handle_to_insert.get(handle)
        if ins is None:
            continue
        xmin = ymin = zmin = xmax = ymax = zmax = None
        # First try ezdxf's structured bbox (works when block has
        # 3DFACE/MESH/POLYLINE/extruded LWPOLYLINE).
        try:
            box = ezbbox.extents([ins])
        except Exception:  # noqa: BLE001
            box = None
        if box is not None and box.has_data:
            xmin, ymin, zmin = float(box.extmin.x), float(box.extmin.y), float(box.extmin.z)
            xmax, ymax, zmax = float(box.extmax.x), float(box.extmax.y), float(box.extmax.z)
        else:
            # Block only contains 3DSOLIDs (SAB v4 binary) — ezdxf
            # returns empty. Scan the SAB binary directly for vertex
            # coordinates and compute extents from those, then apply
            # the INSERT's placement so the bbox lands in world space.
            try:
                bname = ins.dxf.name
                block_def = doc.blocks.get(bname)
            except Exception:  # noqa: BLE001
                continue
            if block_def is None:
                continue
            local = _block_local_extents_with_sab(block_def)
            if local is None:
                continue
            (lo, hi) = local
            # Apply INSERT placement: 8 corners of the local bbox →
            # transform via (scale, rotation around Z, translate). Then
            # take the axis-aligned bbox of the 8 transformed corners.
            try:
                import math
                ip = ins.dxf.insert
                sx = float(getattr(ins.dxf, "xscale", 1.0))
                sy = float(getattr(ins.dxf, "yscale", 1.0))
                sz = float(getattr(ins.dxf, "zscale", 1.0))
                rot_deg = float(getattr(ins.dxf, "rotation", 0.0))
                cos_r = math.cos(math.radians(rot_deg))
                sin_r = math.sin(math.radians(rot_deg))
                corners_local = [
                    (lo[0], lo[1], lo[2]),
                    (hi[0], lo[1], lo[2]),
                    (hi[0], hi[1], lo[2]),
                    (lo[0], hi[1], lo[2]),
                    (lo[0], lo[1], hi[2]),
                    (hi[0], lo[1], hi[2]),
                    (hi[0], hi[1], hi[2]),
                    (lo[0], hi[1], hi[2]),
                ]
                xs: list[float] = []
                ys: list[float] = []
                zs: list[float] = []
                for cx, cy, cz in corners_local:
                    px = cx * sx
                    py = cy * sy
                    pz = cz * sz
                    rx = px * cos_r - py * sin_r + float(ip.x)
                    ry = px * sin_r + py * cos_r + float(ip.y)
                    rz = pz + float(ip.z)
                    xs.append(rx)
                    ys.append(ry)
                    zs.append(rz)
                xmin, ymin, zmin = min(xs), min(ys), min(zs)
                xmax, ymax, zmax = max(xs), max(ys), max(zs)
            except Exception:  # noqa: BLE001
                continue

        if xmin is None or xmin == xmax or ymin == ymax:
            continue
        if zmin == zmax:
            zmax = zmin + 1.0
        verts = (
            Point3D(xmin, ymin, zmin), Point3D(xmax, ymin, zmin),
            Point3D(xmax, ymax, zmin), Point3D(xmin, ymax, zmin),
            Point3D(xmin, ymin, zmax), Point3D(xmax, ymin, zmax),
            Point3D(xmax, ymax, zmax), Point3D(xmin, ymax, zmax),
        )
        faces = (
            (0, 1, 2), (0, 2, 3),  # bottom
            (4, 6, 5), (4, 7, 6),  # top
            (0, 4, 5), (0, 5, 1),  # front
            (1, 5, 6), (1, 6, 2),  # right
            (2, 6, 7), (2, 7, 3),  # back
            (3, 7, 4), (3, 4, 0),  # left
        )
        m.geometry = MeshGeometry(vertices=verts, faces=faces, source="3dface")
        promoted += 1

    if progress is not None and promoted > 0:
        progress(
            f"  Bbox-fallback: {promoted} blokkia ilman ACIS-meshia "
            f"sai bbox-placeholderin (accoreconsole STLOUT puuttuva tai kaatui)"
        )


def convert_dxf(
    *,
    dxf_path: str | Path,
    output_path: str | Path,
    profile: Profile,
    project_name: str | None = None,
    validate: bool = False,
    schema: str = "IFC4",
    preprocess_acis: bool = True,
    progress: object | None = None,
    energy_specs_path: str | Path | None = None,
    floor_elevation_mm: float = 0.0,
    magicad_ifc_path: str | Path | None = None,
) -> tuple[dict[str, list], ValidationReport | None]:
    """Orchestrate DXF -> IFC conversion end-to-end.

    Returns a tuple ``(systems, report)`` where ``systems`` maps each
    ``Rule.system_name`` to the IFC products that were grouped under that
    system, and ``report`` is a :class:`ValidationReport` produced by
    :func:`dxf2ifc.core.quality.validate_ifc` when ``validate=True`` (or
    ``None`` otherwise). ``schema`` selects between ``"IFC4"`` (default)
    and ``"IFC4X3"`` (Plan H).

    When ``preprocess_acis`` is ``True`` (default) and the DXF contains
    3DSOLID/SURFACE/REGION entities, ``accoreconsole.exe`` (the headless
    AutoCAD core, no GUI) is invoked to triangulate every ACIS body into
    a per-handle binary STL file. The resulting meshes are passed to
    :func:`read_dxf` as a side-channel keyed by DXF handle. If
    accoreconsole is missing (LT-only or no AutoCAD on host), ACIS bodies
    are skipped silently and the validation report flags the gap.

    DWG inputs are accepted in v0.2.0-alpha21+: the same headless
    ``accoreconsole.exe`` runs DXFOUT on the .dwg, writes a temporary
    .dxf to ``%TEMP%/dxf2ifc_dwgin_*/``, and the existing pipeline
    consumes that. Requires an AutoCAD install (LT-only / no AutoCAD
    raises FileNotFoundError). MagiCAD-DWGs are NOT supported as input
    — for MagiCAD content the colleague's ``-MAGIIFCCD`` IFC must be
    supplied via ``magicad_ifc_path``.

    This entry point is preserved as a thin shim around the multi-file
    :func:`convert` for backward compatibility. New callers should prefer
    :func:`convert` directly with one or more ``FileEntry`` records.
    """
    file_entry = FileEntry(
        path=Path(dxf_path),
        floor_label="1.krs",
        elevation_mm=floor_elevation_mm,
    )
    return convert(
        files=[file_entry],
        output_path=output_path,
        profile=profile,
        project_name=project_name or Path(dxf_path).stem,
        validate=validate,
        schema=schema,
        preprocess_acis=preprocess_acis,
        progress=progress,
        energy_specs_path=energy_specs_path,
        magicad_ifc_path=magicad_ifc_path,
    )


def convert(
    *,
    files: list[FileEntry],
    output_path: str | Path,
    profile: Profile,
    project_name: str | None = None,
    validate: bool = False,
    schema: str = "IFC4",
    preprocess_acis: bool = True,
    progress: object | None = None,
    energy_specs_path: str | Path | None = None,
    magicad_ifc_path: str | Path | None = None,
) -> tuple[dict[str, list], ValidationReport | None]:
    """Multi-file DXF/DWG → single IFC with one ``IfcBuildingStorey`` per file.

    Each ``FileEntry`` is processed independently (preprocess, read, map,
    POSITIO, energy-spec, Z-offset). The resulting ``MappedEntity``
    records are tagged with their owning storey index and merged into a
    single IFC. ``IfcBuildingStorey.Name`` is taken from
    ``FileEntry.floor_label``; ``Elevation`` is ``FileEntry.elevation_mm``.

    World-space Z of every object becomes
    ``file_entry.elevation_mm + dxf_object.Z`` — so when every floor is
    set to elevation 0, DXF Z coordinates pass through to the IFC
    unchanged.

    The single-file legacy entry point :func:`convert_dxf` delegates here
    with a one-entry ``files`` list.
    """
    if not files:
        raise ValueError("convert() requires at least one FileEntry")
    labels_lower = [fe.floor_label.strip().lower() for fe in files]
    if "" in labels_lower:
        raise ValueError("floor_label cannot be empty")
    if len(set(labels_lower)) != len(labels_lower):
        raise ValueError(
            f"duplicate floor labels in files: {[fe.floor_label for fe in files]}"
        )

    skip_magicad = magicad_ifc_path is not None

    all_mapped: list[MappedEntity] = []
    for index, fe in enumerate(files):
        if progress is not None:
            progress(
                f"[{fe.floor_label}] käsitellään {Path(fe.path).name} "
                f"({index + 1}/{len(files)})"
            )
        mapped = _process_one_file(
            fe,
            profile=profile,
            schema=schema,
            preprocess_acis=preprocess_acis,
            skip_magicad=skip_magicad,
            energy_specs_path=energy_specs_path,
            progress=progress,
        )
        for m in mapped:
            m.storey_index = index
        all_mapped.extend(mapped)

    # Determine the dominant discipline so Solibri can auto-detect the
    # role when the file is opened. A unanimous mapped-rule domain
    # (e.g. every rule is KYL → Jäähdytys) wins; mixed-discipline files
    # leave the marker unset rather than picking a misleading role.
    domains = {m.domain for m in all_mapped if m.domain}
    project_discipline = (
        discipline_label(next(iter(domains))) if len(domains) == 1 else None
    )

    name = project_name or Path(output_path).stem

    skeleton = build_ifc_project_skeleton(
        project_name=name,
        schema=schema,
        floor_elevation_mm=0.0,
        storey_z_levels_mm=[fe.elevation_mm for fe in files],
        storey_names=[fe.floor_label for fe in files],
        discipline_label=project_discipline,
    )

    ifc = skeleton.file
    systems: dict[str, list] = {}

    def _storey_for(m) -> object:
        return skeleton.storeys[m.storey_index]

    def _record(m: object, product: object) -> None:
        sys_name = m.extra_props.get("system_name") if m.extra_props else None
        if sys_name:
            systems.setdefault(sys_name, []).append(product)
        try:
            _attach_fi_psets(product, m)
        except Exception:  # noqa: BLE001 — never block convert
            pass
        try:
            from dxf2ifc.core.ifc_writer.styling import apply_color_to_product
            apply_color_to_product(ifc, product)
        except Exception:  # noqa: BLE001 — never block convert
            pass

    def _classify(product: object, m: object) -> None:
        if m.domain == "ARK":
            add_classification(
                ifc, product, domain="ARK", code=m.talo2000_code, name=m.talo2000_name
            )
        elif m.domain in ("TATE", "KYL"):
            code = m.lvi_code or m.talotekniikka_code
            add_classification(ifc, product, domain=m.domain, code=code)
        add_discipline_classification(ifc, product, domain=m.domain)

    def _attach_fi_psets(product: object, m: object) -> None:
        from dxf2ifc.core.finnish_psets import add_finnish_psets
        from dxf2ifc.core.geometry import extents_from_geometry

        extras = m.extra_props or {}
        extents = extents_from_geometry(
            m.geometry,
            height_mm=extras.get("default_height_mm"),
            thickness_mm=extras.get("default_thickness_mm"),
            width_mm=extras.get("default_width_mm"),
            depth_mm=extras.get("default_depth_mm"),
        )
        add_finnish_psets(
            ifc,
            product=product,
            mapped=m,
            parent_storey=_storey_for(m),
            extents=extents,
        )

    try:
        for m in all_mapped:
            if m.ifc_type == "IfcWall":
                wall = add_wall(
                    ifc, m, parent_storey=_storey_for(m),
                    predefined_type=m.predefined_type or "STANDARD",
                )
                _classify(wall, m)
                _record(m, wall)
            elif m.ifc_type == "IfcSlab":
                slab = add_slab(
                    ifc, m, parent_storey=_storey_for(m),
                    predefined_type=m.predefined_type or "FLOOR",
                )
                _classify(slab, m)
                _record(m, slab)
            elif m.ifc_type == "IfcDoor":
                door = add_door(
                    ifc, m, parent_storey=_storey_for(m),
                    predefined_type=m.predefined_type or "DOOR",
                )
                _classify(door, m)
                _record(m, door)
            elif m.ifc_type == "IfcWindow":
                window = add_window(
                    ifc, m, parent_storey=_storey_for(m),
                    predefined_type=m.predefined_type or "WINDOW",
                )
                _classify(window, m)
                _record(m, window)
            elif m.ifc_type == "IfcPipeSegment":
                if isinstance(m.geometry, BlockInstance):
                    continue
                if isinstance(m.geometry, MeshGeometry):
                    pipe = _add_mesh_product(
                        ifc, m, ifc_class="IfcPipeSegment",
                        parent_storey=_storey_for(m),
                        predefined_type=m.predefined_type or "REFRIGERATION",
                    )
                else:
                    pipe = add_pipe_segment(
                        ifc, m, parent_storey=_storey_for(m),
                        predefined_type=m.predefined_type or "REFRIGERATION",
                    )
                _classify(pipe, m)
                _record(m, pipe)
            elif m.ifc_type == "IfcFurniture":
                if isinstance(m.geometry, BlockInstance):
                    continue
                furniture = add_furniture(ifc, m, parent_storey=_storey_for(m))
                _classify(furniture, m)
                _record(m, furniture)
            elif m.ifc_type == "IfcCableCarrierSegment":
                if isinstance(m.geometry, LineGeometry):
                    seg = add_cable_carrier_segment(
                        ifc, m, parent_storey=_storey_for(m),
                        predefined_type=m.predefined_type or "CABLETRUNKINGSEGMENT",
                    )
                else:
                    seg = add_cable_carrier(
                        ifc, m, parent_storey=_storey_for(m),
                        predefined_type=m.predefined_type or "CABLETRAYSEGMENT",
                    )
                _classify(seg, m)
                _record(m, seg)
            elif m.ifc_type == "IfcBuildingElementProxy":
                if isinstance(m.geometry, (LineGeometry, BlockInstance)):
                    continue
                proxy = add_building_element_proxy(ifc, m, parent_storey=_storey_for(m))
                _classify(proxy, m)
                _record(m, proxy)
            elif m.ifc_type in _COOLING_EQUIPMENT_CLASSES:
                if isinstance(m.geometry, (LineGeometry, BlockInstance)):
                    continue
                equipment = add_cooling_equipment(ifc, m, parent_storey=_storey_for(m))
                _classify(equipment, m)
                _record(m, equipment)
            elif m.ifc_type == "IfcTank":
                if isinstance(m.geometry, (LineGeometry, BlockInstance)):
                    continue
                tank = add_tank(ifc, m, parent_storey=_storey_for(m))
                _classify(tank, m)
                _record(m, tank)
            elif m.ifc_type == "IfcFlowController":
                if isinstance(m.geometry, (LineGeometry, BlockInstance)):
                    continue
                ctrl = add_flow_controller(ifc, m, parent_storey=_storey_for(m))
                _classify(ctrl, m)
                _record(m, ctrl)
            elif m.ifc_type in _DISTRIBUTION_ELEMENT_CLASSES:
                if isinstance(m.geometry, (LineGeometry, BlockInstance)):
                    continue
                element = add_distribution_element(
                    ifc, m, ifc_class=m.ifc_type, parent_storey=_storey_for(m)
                )
                _classify(element, m)
                _record(m, element)

        for system_name, products in systems.items():
            system = add_system(ifc, name=system_name)
            assign_to_system(ifc, products=products, system=system)

        write_ifc(ifc, output_path)

        if magicad_ifc_path is not None:
            from dxf2ifc.core.ifc_merger import merge_magicad_ifc

            if progress is not None:
                progress(f"Mergetään MagiCAD-IFC: {Path(magicad_ifc_path).name}")
            merge_stats = merge_magicad_ifc(
                output_path,
                magicad_ifc_path,
                progress=progress if progress is not None else None,  # type: ignore[arg-type]
            )
            if progress is not None:
                top_types = sorted(
                    merge_stats["ifc_types"].items(), key=lambda x: -x[1]
                )[:5]
                progress(
                    f"MagiCAD-merge: {merge_stats['products_appended']} tuotetta "
                    f"lisätty (epäonnistunut {merge_stats['products_skipped']})"
                )
                if top_types:
                    progress(
                        "MagiCAD-IFC-tyypit (top 5): "
                        + ", ".join(f"{t}={n}" for t, n in top_types)
                    )

        report: ValidationReport | None = None
        if validate:
            from dxf2ifc.core.quality import validate_ifc as _validate_ifc

            report = _validate_ifc(output_path)
        return systems, report
    finally:
        # accoreconsole+STLOUT cleans up its own temp dir inside
        # extract_acis_meshes; nothing to do here. The try/finally
        # remains as a stable structure for future cleanup hooks.
        pass
