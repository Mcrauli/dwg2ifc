"""IFC project skeleton, storey resolution, file I/O.

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
    storey_z_levels_mm: list[float] | None = None,
    floor_elevation_mm: float = 0.0,
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
    ``(0, 0, z_mm + floor_elevation_mm)`` and whose ``PlacementRelTo``
    chains to the building. Site→Building placements use the same chain
    with ``z=0``.

    ``floor_elevation_mm`` is a project-level offset added to every
    storey elevation. Use case: AutoCAD draws with the ground floor
    at Z=0; if the absolute height of 1.krs is e.g. 12000 mm, pass
    ``floor_elevation_mm=12000`` so a shelf drawn at Z=3000 in the DXF
    lands at Z=15000 in the IFC's absolute coordinate space. Default 0.0
    (no offset) preserves backward compatibility.
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
        absolute_z = float(z_mm) + float(floor_elevation_mm)
        storey = ifcopenshell.api.run(
            "root.create_entity",
            ifc,
            ifc_class="IfcBuildingStorey",
            name=f"Kerros {index}",
        )
        storey.ObjectPlacement = _make_origin_placement(
            ifc, parent=building.ObjectPlacement, z_mm=absolute_z
        )
        storey.Elevation = absolute_z
        storeys.append(storey)

    ifcopenshell.api.run("aggregate.assign_object", ifc, products=[site], relating_object=project)
    ifcopenshell.api.run("aggregate.assign_object", ifc, products=[building], relating_object=site)
    ifcopenshell.api.run("aggregate.assign_object", ifc, products=storeys, relating_object=building)

    if discipline_label:
        _attach_project_discipline(ifc, project, discipline_label)

    # Application stamping comes last so every IfcRoot created above
    # (project, site, building, storeys, classification rels, psets…)
    # picks up the same OwnerHistory in one sweep.
    _customize_application(ifc)
    _customize_file_header(ifc, output_name=project_name)

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
    """Attach a ``suunnittelualat`` classification reference AND a
    Pset_Project Authorization to the IfcProject.

    Granlund/RAVA3Pro reference IFC files (the kind Solibri's discipline
    auto-detect was tuned against) carry ``Pset_Project.Authorization =
    'Kylmäsuunnittelu'`` — without that property, Solibri cannot
    distinguish a refrigeration model from a generic file and falls back
    to the Architectural role. The ``suunnittelualat`` classification
    on top is a defence-in-depth signal that's also visible in Solibri's
    Luokittelusäännöistä tab.
    """
    import ifcopenshell.guid

    # Discipline classification reference (same source as product level).
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

    # Pset_Project Authorization — the actual mechanism Solibri reads
    # for role auto-detection. Always "Kylmäsuunnittelu" for refrigeration
    # output regardless of the per-product discipline label, because
    # Solibri's role list keys on this exact string.
    pset = ifc.create_entity(
        "IfcPropertySet",
        GlobalId=ifcopenshell.guid.new(),
        Name="Pset_Project",
        HasProperties=[
            ifc.create_entity(
                "IfcPropertySingleValue",
                Name="Authorization",
                NominalValue=ifc.create_entity("IfcText", "Kylmäsuunnittelu"),
            ),
        ],
    )
    ifc.create_entity(
        "IfcRelDefinesByProperties",
        GlobalId=ifcopenshell.guid.new(),
        RelatedObjects=[project],
        RelatingPropertyDefinition=pset,
    )


def _customize_file_header(ifc: ifcopenshell.file, *, output_name: str) -> None:
    """Stamp the STEP physical file HEADER with refrigeration metadata.

    The Granlund/RAVA3Pro reference IFC carries ``Kylmäsuunnittelu`` in
    FILE_NAME's 7th parameter (authorization) and lists
    ``ExchangeRequirement[BuildingService]`` alongside the
    ViewDefinition in FILE_DESCRIPTION. Solibri's role auto-detect
    inspects both — IfcApplication + Pset_Project alone are not
    enough. By matching the reference convention here we close that
    last gap.

    All access goes through ``ifcopenshell.wrapped_data`` because the
    standard ifcopenshell API does not expose header attributes
    directly.
    """
    from dxf2ifc import __version__

    # Attribute indices, per ISO-10303-21 STEP physical file syntax.
    # FILE_NAME(name, time_stamp, author, organization,
    #           preprocessor_version, originating_system, authorization)
    # FILE_DESCRIPTION(description[], implementation_level)

    header = ifc.wrapped_data.header()
    fn = header.file_name_py()
    fd = header.file_description_py()

    fn.setArgumentAsString(0, output_name)
    fn.setArgumentAsString(4, f"dxf2ifc {__version__}")
    fn.setArgumentAsString(5, "dxf2ifc-kylmalaite")
    fn.setArgumentAsString(6, "Kylmäsuunnittelu")

    # FILE_DESCRIPTION.description: keep the existing ViewDefinition
    # value but add the BuildingService ExchangeRequirement that
    # Solibri's discipline auto-detect treats as a strong signal.
    description: tuple[str, ...] = tuple(fd.get_attribute_value(0) or ())
    has_building_service = any(
        "buildingservice" in (s or "").lower() for s in description
    )
    if not has_building_service:
        description = (*description, "ExchangeRequirement[BuildingService]")
    fd.setArgumentAsAggregateOfString(0, list(description))


def _customize_application(ifc: ifcopenshell.file) -> None:
    """Create / re-tag the IfcApplication so Solibri identifies the
    producer as a refrigeration tool.

    Modern ``ifcopenshell.api.project.create_file`` does NOT auto-emit
    an IfcApplication or IfcOwnerHistory chain. We synthesise the full
    Person + Organization + Application + OwnerHistory chain ourselves
    and attach OwnerHistory to every IfcRoot entity, so a downstream
    consumer that branches on ApplicationIdentifier (Solibri's
    discipline auto-detect, or any other RAVA3Pro-aware tool) sees
    "dxf2ifc-kylmalaite" instead of an empty slot or a generic
    IfcOpenShell stamp.
    """
    import time

    from dxf2ifc import __version__

    existing_apps = ifc.by_type("IfcApplication")
    if existing_apps:
        for app in existing_apps:
            app.ApplicationIdentifier = "dxf2ifc-kylmalaite"
            app.ApplicationFullName = "dxf2ifc — Kylmäsuunnittelu"
            app.Version = __version__
        return

    organization = ifc.create_entity(
        "IfcOrganization",
        Name="dxf2ifc",
    )
    application = ifc.create_entity(
        "IfcApplication",
        ApplicationDeveloper=organization,
        Version=__version__,
        ApplicationFullName="dxf2ifc — Kylmäsuunnittelu",
        ApplicationIdentifier="dxf2ifc-kylmalaite",
    )
    person = ifc.create_entity(
        "IfcPerson",
        FamilyName="dxf2ifc",
    )
    person_and_org = ifc.create_entity(
        "IfcPersonAndOrganization",
        ThePerson=person,
        TheOrganization=organization,
    )
    owner_history = ifc.create_entity(
        "IfcOwnerHistory",
        OwningUser=person_and_org,
        OwningApplication=application,
        ChangeAction="ADDED",
        CreationDate=int(time.time()),
    )
    for root in ifc.by_type("IfcRoot"):
        if getattr(root, "OwnerHistory", None) is None:
            root.OwnerHistory = owner_history


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


def write_ifc(ifc: ifcopenshell.file, output_path: str | Path) -> None:
    """Write the IFC file to disk."""
    ifc.write(str(output_path))


def validate_local_extent(skeleton: object, *, max_extent_mm: float = 5_000_000.0) -> None:
    """Defensive double-transform guard. Scans every ``IfcCartesianPoint``
    in the file and raises ``RuntimeError`` if any coordinate component
    exceeds ``max_extent_mm`` (default 5 000 000 mm = 5 km).

    Geometry should stay in LOCAL coordinates within a few kilometres
    of the building origin; the storey ``Elevation`` and
    ``ObjectPlacement`` carry the floor-elevation offset. A vertex at
    e.g. 25 496 000 mm (ETRS-TM35FIN easting magnitude) signals that
    real-world projected coordinates leaked into LOCAL geometry —
    either from a double transform or a misconfigured DXF unit.
    """
    ifc = skeleton.file if hasattr(skeleton, "file") else skeleton
    for point in ifc.by_type("IfcCartesianPoint"):
        for component in point.Coordinates:
            if abs(component) > max_extent_mm:
                raise RuntimeError(
                    f"Local coordinate {component} exceeds max_extent_mm="
                    f"{max_extent_mm} on {point} — possible projected "
                    f"world coordinates leaking into LOCAL geometry."
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
