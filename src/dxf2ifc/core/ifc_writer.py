"""Generate an IFC file from MappedEntity objects.

Plan A covers: IfcProject/Site/Building/Storey hierarchy, IfcUnitAssignment
(millimetres), single IfcWall creation with classification reference.
Plan B extends with slabs, doors, windows, pipes, furniture, etc.
"""

from __future__ import annotations

import math
from pathlib import Path

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.guid

from dxf2ifc.core.dxf_reader import read_dxf
from dxf2ifc.core.geometry import (
    block_to_furniture_box,
    door_block_to_box,
    line_to_pipe_segment,
    line_to_wall_extrusion,
    polygon_to_slab_extrusion,
)
from dxf2ifc.core.mapper import apply_profile
from dxf2ifc.core.types import (
    BlockInstance,
    LineGeometry,
    MappedEntity,
    PolygonGeometry,
)
from dxf2ifc.profiles.schema import Profile


def build_ifc_project_skeleton(
    *,
    project_name: str = "Untitled",
    site_name: str = "Default Site",
    building_name: str = "Default Building",
    storey_name: str = "Ground Floor",
) -> ifcopenshell.file:
    """Create a minimal IFC 4 file with IfcProject -> Site -> Building -> Storey,
    with millimetre length units set via IfcUnitAssignment.
    """
    ifc = ifcopenshell.api.run("project.create_file", version="IFC4")

    project = ifcopenshell.api.run(
        "root.create_entity", ifc, ifc_class="IfcProject", name=project_name
    )

    ifcopenshell.api.run(
        "unit.assign_unit",
        ifc,
        length={"is_metric": True, "raw": "MILLIMETERS"},
    )

    context = ifcopenshell.api.run("context.add_context", ifc, context_type="Model")
    ifcopenshell.api.run(
        "context.add_context",
        ifc,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=context,
    )

    site = ifcopenshell.api.run("root.create_entity", ifc, ifc_class="IfcSite", name=site_name)
    building = ifcopenshell.api.run(
        "root.create_entity", ifc, ifc_class="IfcBuilding", name=building_name
    )
    storey = ifcopenshell.api.run(
        "root.create_entity", ifc, ifc_class="IfcBuildingStorey", name=storey_name
    )
    ifcopenshell.api.run("aggregate.assign_object", ifc, products=[site], relating_object=project)
    ifcopenshell.api.run("aggregate.assign_object", ifc, products=[building], relating_object=site)
    ifcopenshell.api.run(
        "aggregate.assign_object", ifc, products=[storey], relating_object=building
    )
    return ifc


def write_ifc(ifc: ifcopenshell.file, output_path: str | Path) -> None:
    """Write the IFC file to disk."""
    ifc.write(str(output_path))


def add_wall(
    ifc,
    mapped: MappedEntity,
    *,
    parent_storey,
    predefined_type: str = "STANDARD",
) -> object:
    """Create an IfcWall entity from a MappedEntity whose geometry is a
    LineGeometry. Adds extruded area solid representation and places it under
    parent_storey via IfcRelContainedInSpatialStructure.

    The IfcWall.PredefinedType is set from the ``predefined_type`` kwarg
    (default ``"STANDARD"``); orchestrator code should forward
    ``mapped.predefined_type`` when present.
    """
    if not isinstance(mapped.geometry, LineGeometry):
        raise TypeError(f"add_wall expects LineGeometry, got {type(mapped.geometry).__name__}")

    height = float(mapped.extra_props.get("default_height_mm", 3000.0))
    thickness = float(mapped.extra_props.get("default_thickness_mm", 200.0))
    ext = line_to_wall_extrusion(mapped.geometry, thickness_mm=thickness, height_mm=height)

    wall = ifcopenshell.api.run(
        "root.create_entity",
        ifc,
        ifc_class="IfcWall",
        name=mapped.layer,
        predefined_type=predefined_type,
    )

    matrix = _z_rotation_matrix(ext.anchor.x, ext.anchor.y, ext.anchor.z, ext.angle_rad)
    ifcopenshell.api.run(
        "geometry.edit_object_placement",
        ifc,
        product=wall,
        matrix=matrix,
    )

    model_ctx = [
        c
        for c in ifc.by_type("IfcGeometricRepresentationSubContext")
        if c.ContextIdentifier == "Body"
    ][0]
    rect = ifc.create_entity(
        "IfcRectangleProfileDef",
        ProfileType="AREA",
        ProfileName=None,
        Position=ifc.create_entity(
            "IfcAxis2Placement2D",
            Location=ifc.create_entity("IfcCartesianPoint", Coordinates=(ext.length_mm / 2.0, 0.0)),
        ),
        XDim=ext.length_mm,
        YDim=ext.thickness_mm,
    )
    extruded = ifc.create_entity(
        "IfcExtrudedAreaSolid",
        SweptArea=rect,
        Position=ifc.create_entity(
            "IfcAxis2Placement3D",
            Location=ifc.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0, 0.0)),
        ),
        ExtrudedDirection=ifc.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0)),
        Depth=ext.height_mm,
    )
    shape = ifc.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=model_ctx,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=[extruded],
    )
    product_definition = ifc.create_entity("IfcProductDefinitionShape", Representations=[shape])
    wall.Representation = product_definition

    ifcopenshell.api.run(
        "spatial.assign_container",
        ifc,
        products=[wall],
        relating_structure=parent_storey,
    )
    return wall


def add_slab(
    ifc,
    mapped: MappedEntity,
    *,
    parent_storey,
    predefined_type: str = "FLOOR",
) -> object:
    """Create an IfcSlab from a MappedEntity whose geometry is a PolygonGeometry.

    The slab outline is taken from the polygon's XY vertices; the
    extrusion runs downwards by ``default_thickness_mm`` so the polygon's
    Z elevation marks the top of the slab.
    """
    if not isinstance(mapped.geometry, PolygonGeometry):
        raise TypeError(
            f"add_slab expects PolygonGeometry, got {type(mapped.geometry).__name__}"
        )

    thickness = float(mapped.extra_props.get("default_thickness_mm", 200.0))
    ext = polygon_to_slab_extrusion(mapped.geometry, thickness_mm=thickness)

    slab = ifcopenshell.api.run(
        "root.create_entity",
        ifc,
        ifc_class="IfcSlab",
        name=mapped.layer,
        predefined_type=predefined_type,
    )

    matrix = _z_rotation_matrix(0.0, 0.0, ext.base_z, 0.0)
    ifcopenshell.api.run(
        "geometry.edit_object_placement",
        ifc,
        product=slab,
        matrix=matrix,
    )

    model_ctx = [
        c
        for c in ifc.by_type("IfcGeometricRepresentationSubContext")
        if c.ContextIdentifier == "Body"
    ][0]

    polyline_points = [
        ifc.create_entity("IfcCartesianPoint", Coordinates=(float(x), float(y)))
        for x, y in ext.outline_xy
    ]
    polyline_points.append(polyline_points[0])
    polyline = ifc.create_entity("IfcPolyline", Points=polyline_points)
    profile = ifc.create_entity(
        "IfcArbitraryClosedProfileDef",
        ProfileType="AREA",
        OuterCurve=polyline,
    )
    extruded = ifc.create_entity(
        "IfcExtrudedAreaSolid",
        SweptArea=profile,
        Position=ifc.create_entity(
            "IfcAxis2Placement3D",
            Location=ifc.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0, 0.0)),
        ),
        ExtrudedDirection=ifc.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, -1.0)),
        Depth=ext.thickness_mm,
    )
    shape = ifc.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=model_ctx,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=[extruded],
    )
    slab.Representation = ifc.create_entity(
        "IfcProductDefinitionShape", Representations=[shape]
    )

    ifcopenshell.api.run(
        "spatial.assign_container",
        ifc,
        products=[slab],
        relating_structure=parent_storey,
    )
    return slab


def add_door(
    ifc,
    mapped: MappedEntity,
    *,
    parent_storey,
    predefined_type: str = "DOOR",
) -> object:
    """Create an IfcDoor from a MappedEntity whose geometry is a BlockInstance.

    Door dimensions come from extra_props (default_width_mm, default_height_mm,
    default_depth_mm); falling back to typical Finnish door defaults
    (900 × 2100 × 50 mm). The door body is a rectangular block extruded
    upwards so the insertion point sits at the bottom-left corner.
    """
    if not isinstance(mapped.geometry, BlockInstance):
        raise TypeError(
            f"add_door expects BlockInstance, got {type(mapped.geometry).__name__}"
        )

    width = float(mapped.extra_props.get("default_width_mm", 900.0))
    height = float(mapped.extra_props.get("default_height_mm", 2100.0))
    depth = float(mapped.extra_props.get("default_depth_mm", 50.0))
    box = door_block_to_box(
        mapped.geometry, width_mm=width, height_mm=height, depth_mm=depth
    )

    door = ifcopenshell.api.run(
        "root.create_entity",
        ifc,
        ifc_class="IfcDoor",
        name=mapped.layer,
        predefined_type=predefined_type,
    )
    door.OverallHeight = box.height_mm
    door.OverallWidth = box.width_mm

    matrix = _z_rotation_matrix(box.anchor.x, box.anchor.y, box.anchor.z, box.angle_rad)
    ifcopenshell.api.run(
        "geometry.edit_object_placement",
        ifc,
        product=door,
        matrix=matrix,
    )

    model_ctx = [
        c
        for c in ifc.by_type("IfcGeometricRepresentationSubContext")
        if c.ContextIdentifier == "Body"
    ][0]
    rect = ifc.create_entity(
        "IfcRectangleProfileDef",
        ProfileType="AREA",
        ProfileName=None,
        Position=ifc.create_entity(
            "IfcAxis2Placement2D",
            Location=ifc.create_entity(
                "IfcCartesianPoint",
                Coordinates=(box.width_mm / 2.0, 0.0),
            ),
        ),
        XDim=box.width_mm,
        YDim=box.depth_mm,
    )
    extruded = ifc.create_entity(
        "IfcExtrudedAreaSolid",
        SweptArea=rect,
        Position=ifc.create_entity(
            "IfcAxis2Placement3D",
            Location=ifc.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0, 0.0)),
        ),
        ExtrudedDirection=ifc.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0)),
        Depth=box.height_mm,
    )
    shape = ifc.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=model_ctx,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=[extruded],
    )
    door.Representation = ifc.create_entity(
        "IfcProductDefinitionShape", Representations=[shape]
    )

    ifcopenshell.api.run(
        "spatial.assign_container",
        ifc,
        products=[door],
        relating_structure=parent_storey,
    )
    return door


def add_window(
    ifc,
    mapped: MappedEntity,
    *,
    parent_storey,
    predefined_type: str = "WINDOW",
) -> object:
    """Create an IfcWindow from a MappedEntity whose geometry is a BlockInstance.

    Window dimensions come from extra_props (default_width_mm,
    default_height_mm, default_depth_mm) with typical defaults
    (1200 × 1500 × 60 mm). The body is a rectangular block extruded
    upwards, anchored at the block's insertion point and rotated by
    rotation_rad.
    """
    if not isinstance(mapped.geometry, BlockInstance):
        raise TypeError(
            f"add_window expects BlockInstance, got {type(mapped.geometry).__name__}"
        )

    width = float(mapped.extra_props.get("default_width_mm", 1200.0))
    height = float(mapped.extra_props.get("default_height_mm", 1500.0))
    depth = float(mapped.extra_props.get("default_depth_mm", 60.0))
    box = door_block_to_box(
        mapped.geometry, width_mm=width, height_mm=height, depth_mm=depth
    )

    window = ifcopenshell.api.run(
        "root.create_entity",
        ifc,
        ifc_class="IfcWindow",
        name=mapped.layer,
        predefined_type=predefined_type,
    )
    window.OverallHeight = box.height_mm
    window.OverallWidth = box.width_mm

    matrix = _z_rotation_matrix(box.anchor.x, box.anchor.y, box.anchor.z, box.angle_rad)
    ifcopenshell.api.run(
        "geometry.edit_object_placement",
        ifc,
        product=window,
        matrix=matrix,
    )

    model_ctx = [
        c
        for c in ifc.by_type("IfcGeometricRepresentationSubContext")
        if c.ContextIdentifier == "Body"
    ][0]
    rect = ifc.create_entity(
        "IfcRectangleProfileDef",
        ProfileType="AREA",
        ProfileName=None,
        Position=ifc.create_entity(
            "IfcAxis2Placement2D",
            Location=ifc.create_entity(
                "IfcCartesianPoint",
                Coordinates=(box.width_mm / 2.0, 0.0),
            ),
        ),
        XDim=box.width_mm,
        YDim=box.depth_mm,
    )
    extruded = ifc.create_entity(
        "IfcExtrudedAreaSolid",
        SweptArea=rect,
        Position=ifc.create_entity(
            "IfcAxis2Placement3D",
            Location=ifc.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0, 0.0)),
        ),
        ExtrudedDirection=ifc.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0)),
        Depth=box.height_mm,
    )
    shape = ifc.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=model_ctx,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=[extruded],
    )
    window.Representation = ifc.create_entity(
        "IfcProductDefinitionShape", Representations=[shape]
    )

    ifcopenshell.api.run(
        "spatial.assign_container",
        ifc,
        products=[window],
        relating_structure=parent_storey,
    )
    return window


_IFC_PIPE_SEGMENT_TYPES = frozenset(
    {"CULVERT", "FLEXIBLESEGMENT", "RIGIDSEGMENT", "GUTTER", "SPOOL"}
)


def add_pipe_segment(
    ifc,
    mapped: MappedEntity,
    *,
    parent_storey,
    predefined_type: str = "REFRIGERATION",
) -> object:
    """Create an IfcPipeSegment from a MappedEntity whose geometry is a LineGeometry.

    The pipe is rendered as a circular extrusion (IfcCircleProfileDef along
    +X swept by length_mm) anchored at the line's start. The diameter is
    pulled from extra_props['default_diameter_mm'] (default 22 mm). An
    IfcPipeSegmentType matching the requested predefined_type is created
    once per file and re-used for subsequent pipes.

    IFC4 only allows {CULVERT, FLEXIBLESEGMENT, RIGIDSEGMENT, GUTTER,
    SPOOL} as IfcPipeSegmentTypeEnum values. Any other token (e.g. the
    medium-oriented "REFRIGERATION") is mapped to USERDEFINED and stored
    on ElementType for round-tripping in downstream tools.
    """
    if not isinstance(mapped.geometry, LineGeometry):
        raise TypeError(
            f"add_pipe_segment expects LineGeometry, got {type(mapped.geometry).__name__}"
        )

    diameter = float(mapped.extra_props.get("default_diameter_mm", 22.0))
    ext = line_to_pipe_segment(mapped.geometry, diameter_mm=diameter)

    is_userdefined = predefined_type not in _IFC_PIPE_SEGMENT_TYPES
    enum_value = "USERDEFINED" if is_userdefined else predefined_type

    pipe = ifcopenshell.api.run(
        "root.create_entity",
        ifc,
        ifc_class="IfcPipeSegment",
        name=mapped.layer,
        predefined_type=enum_value,
    )

    pipe_type = _ensure_pipe_segment_type(ifc, predefined_type, enum_value)
    ifcopenshell.api.run("type.assign_type", ifc, related_objects=[pipe], relating_type=pipe_type)

    # type.assign_type clears occurrence-level enums (IFC4 lets the type
    # carry the canonical value). Re-apply them so callers can query
    # pipe.PredefinedType directly.
    pipe.PredefinedType = enum_value
    if is_userdefined:
        pipe.ObjectType = predefined_type

    matrix = _z_rotation_matrix(ext.anchor.x, ext.anchor.y, ext.anchor.z, ext.angle_rad)
    ifcopenshell.api.run(
        "geometry.edit_object_placement",
        ifc,
        product=pipe,
        matrix=matrix,
    )

    model_ctx = [
        c
        for c in ifc.by_type("IfcGeometricRepresentationSubContext")
        if c.ContextIdentifier == "Body"
    ][0]
    circle = ifc.create_entity(
        "IfcCircleProfileDef",
        ProfileType="AREA",
        Position=ifc.create_entity(
            "IfcAxis2Placement2D",
            Location=ifc.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0)),
        ),
        Radius=ext.diameter_mm / 2.0,
    )
    extruded = ifc.create_entity(
        "IfcExtrudedAreaSolid",
        SweptArea=circle,
        Position=ifc.create_entity(
            "IfcAxis2Placement3D",
            Location=ifc.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0, 0.0)),
            Axis=ifc.create_entity("IfcDirection", DirectionRatios=(1.0, 0.0, 0.0)),
            RefDirection=ifc.create_entity("IfcDirection", DirectionRatios=(0.0, 1.0, 0.0)),
        ),
        ExtrudedDirection=ifc.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0)),
        Depth=ext.length_mm,
    )
    shape = ifc.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=model_ctx,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=[extruded],
    )
    pipe.Representation = ifc.create_entity(
        "IfcProductDefinitionShape", Representations=[shape]
    )

    ifcopenshell.api.run(
        "spatial.assign_container",
        ifc,
        products=[pipe],
        relating_structure=parent_storey,
    )
    return pipe


def add_furniture(
    ifc,
    mapped: MappedEntity,
    *,
    parent_storey,
) -> object:
    """Create an IfcFurniture from a MappedEntity whose geometry is a BlockInstance.

    The fixture is rendered as a width × depth × height rectangular
    extrusion anchored at the block's insertion point. Dimensions
    come from extra_props (default_width_mm / default_depth_mm /
    default_height_mm) with shelving-friendly defaults
    (1000 × 600 × 2000 mm).
    """
    if not isinstance(mapped.geometry, BlockInstance):
        raise TypeError(
            f"add_furniture expects BlockInstance, got {type(mapped.geometry).__name__}"
        )

    width = float(mapped.extra_props.get("default_width_mm", 1000.0))
    depth = float(mapped.extra_props.get("default_depth_mm", 600.0))
    height = float(mapped.extra_props.get("default_height_mm", 2000.0))
    box = block_to_furniture_box(
        mapped.geometry, width_mm=width, depth_mm=depth, height_mm=height
    )

    furniture = ifcopenshell.api.run(
        "root.create_entity",
        ifc,
        ifc_class="IfcFurniture",
        name=mapped.layer,
    )

    matrix = _z_rotation_matrix(box.anchor.x, box.anchor.y, box.anchor.z, box.angle_rad)
    ifcopenshell.api.run(
        "geometry.edit_object_placement",
        ifc,
        product=furniture,
        matrix=matrix,
    )

    model_ctx = [
        c
        for c in ifc.by_type("IfcGeometricRepresentationSubContext")
        if c.ContextIdentifier == "Body"
    ][0]
    rect = ifc.create_entity(
        "IfcRectangleProfileDef",
        ProfileType="AREA",
        ProfileName=None,
        Position=ifc.create_entity(
            "IfcAxis2Placement2D",
            Location=ifc.create_entity(
                "IfcCartesianPoint",
                Coordinates=(box.width_mm / 2.0, box.depth_mm / 2.0),
            ),
        ),
        XDim=box.width_mm,
        YDim=box.depth_mm,
    )
    extruded = ifc.create_entity(
        "IfcExtrudedAreaSolid",
        SweptArea=rect,
        Position=ifc.create_entity(
            "IfcAxis2Placement3D",
            Location=ifc.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0, 0.0)),
        ),
        ExtrudedDirection=ifc.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0)),
        Depth=box.height_mm,
    )
    shape = ifc.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=model_ctx,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=[extruded],
    )
    furniture.Representation = ifc.create_entity(
        "IfcProductDefinitionShape", Representations=[shape]
    )

    ifcopenshell.api.run(
        "spatial.assign_container",
        ifc,
        products=[furniture],
        relating_structure=parent_storey,
    )
    return furniture


def _ensure_pipe_segment_type(ifc, requested_type: str, enum_value: str) -> object:
    """Return (creating once per file) an IfcPipeSegmentType matching the
    requested medium. If the requested type is not part of
    IfcPipeSegmentTypeEnum, USERDEFINED is used and ElementType records
    the original token (e.g. 'REFRIGERATION').
    """
    for t in ifc.by_type("IfcPipeSegmentType"):
        if enum_value == "USERDEFINED":
            if t.PredefinedType == "USERDEFINED" and t.ElementType == requested_type:
                return t
        elif t.PredefinedType == enum_value:
            return t

    pipe_type = ifcopenshell.api.run(
        "root.create_entity",
        ifc,
        ifc_class="IfcPipeSegmentType",
        name=f"PipeSegmentType_{requested_type}",
        predefined_type=enum_value,
    )
    if enum_value == "USERDEFINED":
        pipe_type.ElementType = requested_type
    return pipe_type


def _z_rotation_matrix(x: float, y: float, z: float, angle: float) -> list[list[float]]:
    c, s = math.cos(angle), math.sin(angle)
    return [
        [c, -s, 0.0, x],
        [s, c, 0.0, y],
        [0.0, 0.0, 1.0, z],
        [0.0, 0.0, 0.0, 1.0],
    ]


def add_talo2000_classification(ifc, product, *, code: str, name: str) -> object:
    """Attach a Talo2000 IfcClassificationReference to the given product.

    Creates (once per file) an IfcClassification named 'Talo2000', then
    references it from an IfcClassificationReference tied to the product.
    """
    existing = [c for c in ifc.by_type("IfcClassification") if c.Name == "Talo2000"]
    if existing:
        classification = existing[0]
    else:
        classification = ifc.create_entity(
            "IfcClassification",
            Source="Rakennustieto Oy",
            Edition="Talo 2000",
            Name="Talo2000",
        )

    reference = ifc.create_entity(
        "IfcClassificationReference",
        Identification=code,
        Name=name,
        ReferencedSource=classification,
    )
    ifc.create_entity(
        "IfcRelAssociatesClassification",
        GlobalId=ifcopenshell.guid.new(),
        RelatedObjects=[product],
        RelatingClassification=reference,
    )
    return reference


def convert_dxf(
    *,
    dxf_path: str | Path,
    output_path: str | Path,
    profile: Profile,
    project_name: str | None = None,
) -> None:
    """Orchestrate DXF -> IFC conversion end-to-end for Plan A (walls only)."""
    name = project_name or Path(dxf_path).stem
    entities = read_dxf(dxf_path)
    mapped = apply_profile(entities, profile)
    ifc = build_ifc_project_skeleton(project_name=name)
    storey = ifc.by_type("IfcBuildingStorey")[0]
    for m in mapped:
        if m.ifc_type == "IfcWall":
            wall = add_wall(
                ifc,
                m,
                parent_storey=storey,
                predefined_type=m.predefined_type or "STANDARD",
            )
            add_talo2000_classification(ifc, wall, code=m.talo2000_code, name=m.talo2000_name)
        elif m.ifc_type == "IfcSlab":
            slab = add_slab(
                ifc,
                m,
                parent_storey=storey,
                predefined_type=m.predefined_type or "FLOOR",
            )
            add_talo2000_classification(ifc, slab, code=m.talo2000_code, name=m.talo2000_name)
        elif m.ifc_type == "IfcDoor":
            door = add_door(
                ifc,
                m,
                parent_storey=storey,
                predefined_type=m.predefined_type or "DOOR",
            )
            add_talo2000_classification(ifc, door, code=m.talo2000_code, name=m.talo2000_name)
        elif m.ifc_type == "IfcWindow":
            window = add_window(
                ifc,
                m,
                parent_storey=storey,
                predefined_type=m.predefined_type or "WINDOW",
            )
            add_talo2000_classification(ifc, window, code=m.talo2000_code, name=m.talo2000_name)
        elif m.ifc_type == "IfcPipeSegment":
            pipe = add_pipe_segment(
                ifc,
                m,
                parent_storey=storey,
                predefined_type=m.predefined_type or "REFRIGERATION",
            )
            add_talo2000_classification(ifc, pipe, code=m.talo2000_code, name=m.talo2000_name)
    write_ifc(ifc, output_path)
