"""convert_dxf orchestrator -- DXF -> IFC end-to-end pipeline."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import ifcopenshell

if TYPE_CHECKING:  # pragma: no cover
    from dxf2ifc.core.quality import ValidationReport

from dxf2ifc.core.dxf_reader import read_dxf
from dxf2ifc.core.outliers import find_geometric_outliers
from dxf2ifc.core.ifc_writer.builders import (
    _COOLING_EQUIPMENT_CLASSES,
    add_building_element_proxy,
    add_cable_carrier,
    add_cable_carrier_segment,
    add_cooling_equipment,
    add_door,
    add_furniture,
    add_pipe_segment,
    add_slab,
    add_system,
    add_wall,
    add_window,
    assign_to_system,
    write_ifc,
)
from dxf2ifc.core.ifc_writer.classification import (
    add_classification,
    add_discipline_classification,
)
from dxf2ifc.core.ifc_writer.skeleton import (
    IfcSkeleton,
    _entity_anchor_z,
    build_ifc_project_skeleton,
    resolve_storey,
)
from dxf2ifc.core.mapper import apply_profile
from dxf2ifc.core.types import BlockInstance, LineGeometry, MappedEntity, MeshGeometry
from dxf2ifc.profiles.schema import Profile


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
    detect_outliers: bool = True,
    outlier_threshold_mm: float | None = None,
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
    """
    name = project_name or Path(dxf_path).stem
    acis_meshes: dict[str, object] = {}
    if preprocess_acis:
        # Lazy import keeps ifc_writer importable on hosts where AutoCAD
        # is not installed — extract_acis_meshes itself returns ``{}`` in
        # that case after calling find_accoreconsole().
        from dxf2ifc.core.preprocessing import extract_acis_meshes
        acis_meshes = extract_acis_meshes(dxf_path, progress=progress)  # type: ignore[arg-type,assignment]

    entities = read_dxf(dxf_path, acis_meshes=acis_meshes)

    # Pre-conversion outlier scan: adaptive Tukey-fence detection over
    # the per-entity centroid distance distribution. Catches stray xref
    # leftovers BEFORE the user opens Solibri's generic "Mallit
    # hajallaan" warning. Output goes to stderr + progress callback.
    # ``detect_outliers=False`` short-circuits when the user knows the
    # model is intentionally wide.
    outlier_warnings: list[dict] = []
    if detect_outliers:
        outlier_warnings = find_geometric_outliers(
            entities, threshold_mm=outlier_threshold_mm
        )
        if outlier_warnings:
            summary = (
                f"Outlier-varoitus: {len(outlier_warnings)} entiteetti(ä) "
                "kaukana muusta mallista — tarkista AutoCADissa"
            )
            print(summary, file=sys.stderr)
            if callable(progress):
                try:
                    progress(summary)
                except Exception:  # noqa: BLE001 — never block convert on UI errors
                    pass
            for warning in outlier_warnings:
                line = f"  • {warning['message']}"
                print(line, file=sys.stderr)
                if callable(progress):
                    try:
                        progress(line)
                    except Exception:  # noqa: BLE001
                        pass

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
    skeleton = build_ifc_project_skeleton(
        project_name=name,
        schema=schema,
        crs=profile.crs,
        storey_z_levels_mm=list(profile.storey_z_levels_mm),
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
                proxy = add_building_element_proxy(ifc, m, parent_storey=_storey_for(m))
                _classify(proxy, m)
                _record(m, proxy)
            elif m.ifc_type in _COOLING_EQUIPMENT_CLASSES:
                equipment = add_cooling_equipment(ifc, m, parent_storey=_storey_for(m))
                _classify(equipment, m)
                _record(m, equipment)

        for system_name, products in systems.items():
            system = add_system(ifc, name=system_name)
            assign_to_system(ifc, products=products, system=system)

        write_ifc(ifc, output_path)

        report: ValidationReport | None = None
        if validate:
            from dxf2ifc.core.quality import validate_ifc as _validate_ifc

            report = _validate_ifc(output_path)
            # Surface the pre-conversion outlier warnings through the
            # same channel as the post-conversion IFC checks.
            if outlier_warnings:
                report.warnings.extend(outlier_warnings)
        return systems, report
    finally:
        # Always clean up the preprocessing temp DXF, no matter where in
        # the IFC build any remaining exception fired. Combined with the
        # earlier read_dxf / apply_profile try/except blocks, every exit
        # path through convert_dxf removes the temp file. Honour
        # DXF2IFC_KEEP_TEMP=1 for debugging.
        _cleanup_temp()
