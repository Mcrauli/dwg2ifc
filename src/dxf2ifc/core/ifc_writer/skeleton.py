"""IFC project skeleton, storey resolution, CRS attachment, file I/O.

Cohesion: everything related to the spatial container (IfcProject -> Site
-> Building -> Storeys) plus shared helpers for placement / extent
validation. Element builders live in :mod:`builders`; mesh / Brep
helpers in :mod:`mesh`; classification in :mod:`classification`. The
end-to-end orchestrator is :func:`orchestrator.convert_dxf`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import ifcopenshell
import ifcopenshell.api

from dxf2ifc.core.types import BlockInstance, LineGeometry, PolygonGeometry
from dxf2ifc.profiles.schema import CRSConfig


@dataclass
class IfcSkeleton:
    """Bundle of the spatial structure produced by
    :func:`build_ifc_project_skeleton`. Behaves like the underlying
    ``ifcopenshell.file`` for legacy callers via ``__getattr__`` proxy."""

    file: ifcopenshell.file
    project: object
    site: object
    building: object
    storeys: list[object] = field(default_factory=list)
    contexts: dict[str, object] = field(default_factory=dict)

    def __getattr__(self, name: str):
        return getattr(self.file, name)


def build_ifc_project_skeleton(
    *,
    project_name: str = "Untitled",
    site_name: str = "Default Site",
    building_name: str = "Default Building",
    schema: str = "IFC4",
    crs: CRSConfig | None = None,
    storey_z_levels_mm: list[float] | None = None,
    discipline_label: str | None = None,
) -> IfcSkeleton:
    """Create a minimal IFC project file with the requested ``schema``
    (``"IFC4"`` or ``"IFC4X3"``) and the IfcProject → Site → Building →
    list[Storey] spatial hierarchy. Length units are millimetres via
    IfcUnitAssignment.

    ``storey_z_levels_mm`` is a list of Z-elevations (millimetres) — one
    ``IfcBuildingStorey`` per entry, named ``"Kerros 1"``, ``"Kerros 2"``…
    Defaults to ``[0.0]`` (single ground-level storey). Each storey gets an
    ``IfcLocalPlacement`` whose ``RelativePlacement`` puts the origin at
    ``(0, 0, z_mm)`` and whose ``PlacementRelTo`` chains to the building.
    Site→Building placements use the same chain with ``z=0``.

    When ``crs`` is provided, an ``IfcProjectedCRS`` and ``IfcMapConversion``
    are written linking the model context to a real-world projected CRS
    (Plan G Section 2). When ``crs`` is ``None`` (the default), no
    georeferencing entities are emitted.
    """
    if storey_z_levels_mm is None:
        storey_z_levels_mm = [0.0]

    ifc = ifcopenshell.api.run("project.create_file", version=schema)

    project = ifcopenshell.api.run(
        "root.create_entity", ifc, ifc_class="IfcProject", name=project_name
    )

    if discipline_label:
        # Solibri reads IfcProject.LongName when auto-detecting the role
        # for an opened file — placing "Jäähdytys" here lets Solibri pick
        # the refrigeration profile without prompting the user.
        project.LongName = discipline_label

    ifcopenshell.api.run(
        "unit.assign_unit",
        ifc,
        length={"is_metric": True, "raw": "MILLIMETERS"},
    )

    model_context = ifcopenshell.api.run("context.add_context", ifc, context_type="Model")
    body_context = ifcopenshell.api.run(
        "context.add_context",
        ifc,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=model_context,
    )

    site = ifcopenshell.api.run("root.create_entity", ifc, ifc_class="IfcSite", name=site_name)
    building = ifcopenshell.api.run(
        "root.create_entity", ifc, ifc_class="IfcBuilding", name=building_name
    )

    site.ObjectPlacement = _make_origin_placement(ifc)
    building.ObjectPlacement = _make_origin_placement(ifc, parent=site.ObjectPlacement)

    storeys = []
    for index, z_mm in enumerate(storey_z_levels_mm, start=1):
        storey = ifcopenshell.api.run(
            "root.create_entity",
            ifc,
            ifc_class="IfcBuildingStorey",
            name=f"Kerros {index}",
        )
        storey.ObjectPlacement = _make_origin_placement(
            ifc, parent=building.ObjectPlacement, z_mm=float(z_mm)
        )
        storey.Elevation = float(z_mm)
        storeys.append(storey)

    ifcopenshell.api.run("aggregate.assign_object", ifc, products=[site], relating_object=project)
    ifcopenshell.api.run("aggregate.assign_object", ifc, products=[building], relating_object=site)
    ifcopenshell.api.run("aggregate.assign_object", ifc, products=storeys, relating_object=building)

    if crs is not None:
        _attach_projected_crs(ifc, crs)

    if discipline_label:
        _attach_project_discipline(ifc, project, discipline_label)

    return IfcSkeleton(
        file=ifc,
        project=project,
        site=site,
        building=building,
        storeys=storeys,
        contexts={"Model": model_context, "Body": body_context},
    )


def _attach_project_discipline(
    ifc: ifcopenshell.file, project: object, label: str
) -> None:
    """Attach a ``suunnittelualat`` classification reference to the
    IfcProject itself, in addition to the per-product references.

    Solibri's role auto-selection inspects project-level metadata when
    deciding which discipline profile to load — without this, every
    product is tagged Jäähdytys but the project as a whole reads as
    'unspecified' and Solibri prompts the user to choose. The
    classification source is the same ``suunnittelualat`` that the
    product-level helper creates, so deduplication via ``by_type``
    keeps the file clean.
    """
    import ifcopenshell.guid

    existing = [
        c for c in ifc.by_type("IfcClassification") if c.Name == "suunnittelualat"
    ]
    if existing:
        classification = existing[0]
    else:
        classification = ifc.create_entity(
            "IfcClassification",
            Source="dxf2ifc",
            Edition="1.0",
            Name="suunnittelualat",
        )
    reference = ifc.create_entity(
        "IfcClassificationReference",
        Identification=label,
        Name=label,
        ReferencedSource=classification,
    )
    ifc.create_entity(
        "IfcRelAssociatesClassification",
        GlobalId=ifcopenshell.guid.new(),
        RelatedObjects=[project],
        RelatingClassification=reference,
    )


def _make_origin_placement(
    ifc: ifcopenshell.file,
    parent: object | None = None,
    z_mm: float = 0.0,
) -> object:
    """Create an ``IfcLocalPlacement`` whose RelativePlacement is at
    ``(0, 0, z_mm)`` and whose PlacementRelTo points at ``parent`` (or
    ``None`` for the root site placement)."""
    location = ifc.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0, float(z_mm)))
    axis_placement = ifc.create_entity("IfcAxis2Placement3D", Location=location)
    return ifc.create_entity(
        "IfcLocalPlacement",
        PlacementRelTo=parent,
        RelativePlacement=axis_placement,
    )


def _attach_projected_crs(ifc: ifcopenshell.file, crs: CRSConfig) -> None:
    """Write IfcProjectedCRS + IfcMapConversion linked to the model context.

    The MapConversion's SourceCRS is the IfcGeometricRepresentationContext for
    the "Model" (created in ``build_ifc_project_skeleton``). Geometry stays in
    LOCAL coordinates; the MapConversion expresses how to project those local
    coordinates into the real-world projected CRS.
    """
    model_context = next(
        (
            ctx
            for ctx in ifc.by_type("IfcGeometricRepresentationContext", include_subtypes=False)
            if ctx.ContextType == "Model"
        ),
        None,
    )
    if model_context is None:  # pragma: no cover - skeleton always has Model context
        raise RuntimeError("IfcGeometricRepresentationContext 'Model' missing — cannot attach CRS")

    projected = ifc.create_entity(
        "IfcProjectedCRS",
        Name=crs.epsg_code,
        Description=crs.name,
        GeodeticDatum=crs.geodetic_datum,
    )
    ifc.create_entity(
        "IfcMapConversion",
        SourceCRS=model_context,
        TargetCRS=projected,
        Eastings=crs.eastings_mm,
        Northings=crs.northings_mm,
        OrthogonalHeight=crs.orthogonal_height_mm,
        XAxisAbscissa=crs.x_axis_abscissa,
        XAxisOrdinate=crs.x_axis_ordinate,
        Scale=crs.scale,
    )


def write_ifc(ifc: ifcopenshell.file, output_path: str | Path) -> None:
    """Write the IFC file to disk."""
    ifc.write(str(output_path))


def validate_local_extent(skeleton: object, *, max_extent_mm: float = 5_000_000.0) -> None:
    """Defensive double-transform guard. Scans every ``IfcCartesianPoint``
    in the file and raises ``RuntimeError`` if any coordinate component
    exceeds ``max_extent_mm`` (default 5 000 000 mm = 5 km).

    Geometry must stay in LOCAL coordinates; the MapConversion linking
    the model to a real-world projected CRS does the LOCAL→WORLD
    projection at view time. A vertex at e.g. 25 496 000 mm (ETRS-TM35FIN
    easting magnitude) is a clear signal that the MapConversion was
    applied twice — once into the geometry and once again at view time.
    """
    ifc = skeleton.file if hasattr(skeleton, "file") else skeleton
    for point in ifc.by_type("IfcCartesianPoint"):
        for component in point.Coordinates:
            if abs(component) > max_extent_mm:
                raise RuntimeError(
                    f"Local coordinate {component} exceeds max_extent_mm="
                    f"{max_extent_mm} on {point} — possible double-transform "
                    f"(CRS world coordinates leaked into LOCAL geometry)."
                )


def _entity_anchor_z(geometry: object) -> float:
    """Anchor-Z used by the orchestrator to pick a storey:
    LineGeometry → min(start.z, end.z), PolygonGeometry → min(p.z),
    BlockInstance → insertion_point.z. Other geometry types fall back to 0."""
    if isinstance(geometry, LineGeometry):
        return min(geometry.start.z, geometry.end.z)
    if isinstance(geometry, PolygonGeometry):
        return min(p.z for p in geometry.vertices)
    if isinstance(geometry, BlockInstance):
        return geometry.insertion_point.z
    return 0.0


def resolve_storey(storeys: list[object], z_mm: float) -> object:
    """Return the highest ``IfcBuildingStorey`` whose ``Elevation`` is
    ``<= z_mm``. When ``z_mm`` is below the lowest storey, falls back to
    ``storeys[0]`` so an element never ends up unparented."""
    if not storeys:
        raise ValueError("resolve_storey requires at least one storey")
    candidate = storeys[0]
    for storey in storeys:
        if storey.Elevation is not None and storey.Elevation <= z_mm:
            candidate = storey
    return candidate
