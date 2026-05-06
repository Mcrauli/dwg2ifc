"""convert_dxf orchestrator -- DXF -> IFC end-to-end pipeline."""

from __future__ import annotations

import sys
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
    add_building_element_proxy,
    add_cable_carrier,
    add_cable_carrier_segment,
    add_cooling_equipment,
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
from dxf2ifc.core.ifc_writer.classification import (
    add_classification,
    add_discipline_classification,
    discipline_label,
)
from dxf2ifc.core.ifc_writer.skeleton import (
    IfcSkeleton,
    _entity_anchor_z,
    build_ifc_project_skeleton,
    resolve_storey,
)
from dxf2ifc.core.mapper import apply_profile
from dxf2ifc.core.types import (
    BlockInstance,
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
    """Mutate every ``MappedEntity.geometry`` in place to add ``dz`` to
    its Z component(s).

    The ``ObjectPlacement`` matrix the IFC builders feed into
    ``geometry.edit_object_placement`` is built from the entity's anchor
    Z directly — the placement chain in this writer does NOT cascade
    storey-level shifts into element coordinates, so the offset must be
    applied in the geometry itself for elements to land at the absolute
    Z the user requested. ``IfcBuildingStorey.Elevation`` is shifted
    separately in ``build_ifc_project_skeleton`` so storey labels and
    element placements match.
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


def convert_dxf(
    *,
    dxf_path: str | Path,
    output_path: str | Path,
    profile: Profile,
    project_name: str | None = None,
    validate: bool = False,
    schema: str = "IFC4",
    preprocess_acis: bool = True,
    preprocess_proxies: bool = True,
    progress: object | None = None,
    energy_specs_path: str | Path | None = None,
    floor_elevation_mm: float = 0.0,
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

    When ``preprocess_proxies`` is ``True`` (default) and the DXF
    contains ACAD_PROXY_ENTITY records (MagiCAD pipes/devices, custom
    block entities), :func:`extract_proxy_geometry` enriches the
    side-channel with per-handle meshes — either real geometry from
    ``EXPLODE`` + ``STLOUT`` when MagiCAD's free Object Enabler is
    installed, or 12-triangle bbox cuboid fallbacks for the rest.
    The 75% of MagiCAD proxies whose ``proxy_graphic`` ezdxf already
    decodes are handled by :func:`read_dxf` directly (open polylines
    accepted in v0.1.19+) and need no extra preprocessing.
    """
    name = project_name or Path(dxf_path).stem
    acis_meshes: dict[str, object] = {}
    if preprocess_acis:
        # Lazy import keeps ifc_writer importable on hosts where AutoCAD
        # is not installed — extract_acis_meshes itself returns ``{}`` in
        # that case after calling find_accoreconsole().
        from dxf2ifc.core.preprocessing import extract_acis_meshes
        acis_meshes = extract_acis_meshes(dxf_path, progress=progress)  # type: ignore[arg-type,assignment]

    if preprocess_proxies:
        # Same lazy-import pattern; ``extract_proxy_geometry`` returns
        # an empty bundle when no proxies, no accoreconsole, or no
        # Object Enabler (it never raises). Proxy meshes are merged
        # into the same ``acis_meshes`` channel under the original
        # proxy handle, so the existing 3DSOLID/INSERT branch in
        # ``read_dxf`` resolves them transparently.
        from dxf2ifc.core.proxy_preprocessing import extract_proxy_geometry
        proxy_artifacts = extract_proxy_geometry(dxf_path, progress=progress)  # type: ignore[arg-type]
        for h, mesh in proxy_artifacts.meshes.items():
            # Don't overwrite an ACIS-side mesh for the same handle —
            # that path is more authoritative (real 3DSOLID body
            # tessellation vs proxy bbox cuboid).
            acis_meshes.setdefault(h, mesh)

    entities = read_dxf(dxf_path, acis_meshes=acis_meshes)
    mapped = apply_profile(entities, profile)

    # POSITIO-block linkage. Index every numbering INSERT once, then
    # per refrigeration-equipment MappedEntity find the closest one
    # (XY-2D, profile-specified radius). The match goes into
    # extra_props so add_finnish_psets can read it without a separate
    # parameter channel.
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
            for m in mapped:
                if m.ifc_type not in scope:
                    continue
                # Resolve a target XY for the match. The geometry might
                # be a BlockInstance (raw INSERT placement) OR a
                # MeshGeometry (when accoreconsole+STLOUT replaced the
                # block content with a faceted body — höyrystimet land
                # here). Pipes / lines / polygons are intentionally not
                # matched against POSITIOs.
                target_xy: tuple[float, float] | None = None
                if isinstance(m.geometry, BlockInstance):
                    target_xy = (
                        m.geometry.insertion_point.x,
                        m.geometry.insertion_point.y,
                    )
                elif isinstance(m.geometry, MeshGeometry) and m.geometry.vertices:
                    # Bbox centroid in world XY — STLOUT writes world
                    # coordinates so the bbox is already correctly placed.
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
                # POSITIO attribute mapping:
                #   TEKSTI (e.g. "JK1") → Koneikko (refrigeration unit)
                #   NUMERO (e.g. "501") → Laitetunnus (unique device tag)
                if marker.teksti:
                    m.extra_props["koneikko"] = marker.teksti
                if marker.numero:
                    m.extra_props["laitetunnus"] = marker.numero

    # Energy-spec lookup with full diagnostics. The previous version
    # silently skipped if specs was empty or a lookup missed, so the
    # user could not tell why FI_Tekninen stayed blank in Solibri.
    # Now every code path emits a status line so the GUI preview-log
    # shows exactly what happened.
    if energy_specs_path is not None:
        _run_energy_spec_lookup(
            mapped, energy_specs_path, profile=profile, progress=progress
        )

    # Floor-elevation Z-offset: shift every entity's geometry up by
    # ``floor_elevation_mm`` BEFORE the builders consume it, since the
    # builders pass the entity's anchor Z into ``geometry.edit_object_placement``
    # as an absolute world-space matrix that does not chain through the
    # storey's IfcLocalPlacement. Without this pass, Storey.Elevation
    # shifts but the elements stay at their DXF Z. Run AFTER POSITIO
    # (XY-only matching, unaffected by Z) and energy-spec (no geometry
    # access) so neither is perturbed.
    _apply_floor_elevation_offset(mapped, floor_elevation_mm)

    # Determine the dominant discipline so Solibri can auto-detect the
    # role when the file is opened. A unanimous mapped-rule domain
    # (e.g. every rule is KYL → Jäähdytys) wins; mixed-discipline files
    # leave the marker unset rather than picking a misleading role.
    domains = {m.domain for m in mapped if m.domain}
    project_discipline = (
        discipline_label(next(iter(domains))) if len(domains) == 1 else None
    )

    skeleton = build_ifc_project_skeleton(
        project_name=name,
        schema=schema,
        floor_elevation_mm=floor_elevation_mm,
        storey_z_levels_mm=list(profile.storey_z_levels_mm),
        discipline_label=project_discipline,
    )

    def _cleanup_temp() -> None:
        """No-op retained for the trailing ``finally`` block below.

        The previous COM preprocessor wrote a temp DXF that needed
        unlinking on every exit path; the new accoreconsole+STLOUT path
        cleans up its own temp dir inside :func:`extract_acis_meshes`,
        so there is nothing to do here.
        """

    ifc = skeleton.file
    systems: dict[str, list] = {}

    def _storey_for(m) -> object:
        return resolve_storey(skeleton.storeys, _entity_anchor_z(m.geometry))

    def _record(m: object, product: object) -> None:
        sys_name = m.extra_props.get("system_name") if m.extra_props else None
        if sys_name:
            systems.setdefault(sys_name, []).append(product)
        # Finnish PSets piggy-back on _record so every builder branch
        # gets them for free (same as IfcSystem grouping). Wrapped in a
        # broad try so any PSet failure cannot block IFC export — the
        # product still lands on its storey with classification.
        try:
            _attach_fi_psets(product, m)
        except Exception:  # noqa: BLE001 — never block convert
            pass
        # Uniform AutoCAD ACI-175 surface style for every product so the
        # cooling network reads consistently in Solibri / MagiCAD. Same
        # defensive try as the PSet attach above — a styling glitch
        # never aborts the export.
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
            # KYL and TATE share the RAVA-LVI / RAVA-TATE classification
            # source — they only differ in the discipline (suunnittelualat)
            # marker emitted further down.
            code = m.lvi_code or m.talotekniikka_code
            add_classification(ifc, product, domain=m.domain, code=code)
        # Always also emit an explicit discipline classification so
        # Solibri's "suunnittelualat" view shows the right value
        # (otherwise it falls back to ARK for every IFC type heuristic).
        add_discipline_classification(ifc, product, domain=m.domain)

    def _attach_fi_psets(product: object, m: object) -> None:
        """Attach FI_Asennus / FI_Geometria / FI_Komponentti / FI_Tuote.

        Computes geometry extents from the mapped entity's geometry and
        the profile's height / thickness defaults (so e.g. a wall
        emits its real top elevation = base + 2.7 m, not 0).
        """
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
        for m in mapped:
            if m.ifc_type == "IfcWall":
                wall = add_wall(
                    ifc,
                    m,
                    parent_storey=_storey_for(m),
                    predefined_type=m.predefined_type or "STANDARD",
                )
                _classify(wall, m)
                _record(m, wall)
            elif m.ifc_type == "IfcSlab":
                slab = add_slab(
                    ifc,
                    m,
                    parent_storey=_storey_for(m),
                    predefined_type=m.predefined_type or "FLOOR",
                )
                _classify(slab, m)
                _record(m, slab)
            elif m.ifc_type == "IfcDoor":
                door = add_door(
                    ifc,
                    m,
                    parent_storey=_storey_for(m),
                    predefined_type=m.predefined_type or "DOOR",
                )
                _classify(door, m)
                _record(m, door)
            elif m.ifc_type == "IfcWindow":
                window = add_window(
                    ifc,
                    m,
                    parent_storey=_storey_for(m),
                    predefined_type=m.predefined_type or "WINDOW",
                )
                _classify(window, m)
                _record(m, window)
            elif m.ifc_type == "IfcPipeSegment":
                pipe = add_pipe_segment(
                    ifc,
                    m,
                    parent_storey=_storey_for(m),
                    predefined_type=m.predefined_type or "REFRIGERATION",
                )
                _classify(pipe, m)
                _record(m, pipe)
            elif m.ifc_type == "IfcFurniture":
                furniture = add_furniture(ifc, m, parent_storey=_storey_for(m))
                _classify(furniture, m)
                _record(m, furniture)
            elif m.ifc_type == "IfcCableCarrierSegment":
                # Dispatch by geometry: 2D LineGeometry → swept-solid extrusion,
                # MESH/BlockInstance → faceted Brep (cold-storage shelves are
                # ACIS bodies preprocessed into MESH; legacy CAD tools draw
                # cable carriers as 2D centerlines).
                if isinstance(m.geometry, LineGeometry):
                    seg = add_cable_carrier_segment(
                        ifc,
                        m,
                        parent_storey=_storey_for(m),
                        predefined_type=m.predefined_type or "CABLETRUNKINGSEGMENT",
                    )
                else:
                    seg = add_cable_carrier(
                        ifc,
                        m,
                        parent_storey=_storey_for(m),
                        predefined_type=m.predefined_type or "CABLETRAYSEGMENT",
                    )
                _classify(seg, m)
                _record(m, seg)
            elif m.ifc_type == "IfcBuildingElementProxy":
                # add_building_element_proxy expects PolygonGeometry
                # (closed outline → extruded panel) or MeshGeometry
                # (faceted Brep — used by proxy_preprocessing's bbox
                # cuboid fallback). Open-polyline LineGeometry records
                # — emitted by dxf_reader for MagiCAD proxy graphics
                # whose virtual entities are 2D detail primitives —
                # cannot be meaningfully extruded into a 3D proxy
                # body, so skip them rather than crashing or
                # synthesising a dubious shape. The MeshGeometry path
                # still covers the proxies that produced no virtual
                # entities (bbox cuboid).
                if isinstance(m.geometry, LineGeometry):
                    continue
                proxy = add_building_element_proxy(ifc, m, parent_storey=_storey_for(m))
                _classify(proxy, m)
                _record(m, proxy)
            elif m.ifc_type in _COOLING_EQUIPMENT_CLASSES:
                equipment = add_cooling_equipment(ifc, m, parent_storey=_storey_for(m))
                _classify(equipment, m)
                _record(m, equipment)
            elif m.ifc_type == "IfcTank":
                # Skip LineGeometry siblings emitted from MagiCAD proxy
                # virtual_entities — the proxy's MeshGeometry record
                # (cuboid fallback or real EXPLODE result) carries the
                # actual tank body for the same handle.
                if isinstance(m.geometry, LineGeometry):
                    continue
                tank = add_tank(ifc, m, parent_storey=_storey_for(m))
                _classify(tank, m)
                _record(m, tank)
            elif m.ifc_type == "IfcFlowController":
                if isinstance(m.geometry, LineGeometry):
                    continue
                ctrl = add_flow_controller(ifc, m, parent_storey=_storey_for(m))
                _classify(ctrl, m)
                _record(m, ctrl)

        for system_name, products in systems.items():
            system = add_system(ifc, name=system_name)
            assign_to_system(ifc, products=products, system=system)

        write_ifc(ifc, output_path)

        report: ValidationReport | None = None
        if validate:
            from dxf2ifc.core.quality import validate_ifc as _validate_ifc

            report = _validate_ifc(output_path)
        return systems, report
    finally:
        # Always clean up the preprocessing temp DXF, no matter where in
        # the IFC build any remaining exception fired. Combined with the
        # earlier read_dxf / apply_profile try/except blocks, every exit
        # path through convert_dxf removes the temp file. Honour
        # DXF2IFC_KEEP_TEMP=1 for debugging.
        _cleanup_temp()
