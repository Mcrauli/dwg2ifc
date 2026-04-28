"""Generate an IFC file from MappedEntity objects.

Plan A covers: IfcProject/Site/Building/Storey hierarchy, IfcUnitAssignment
(millimetres), single IfcWall creation with classification reference.
Plan B extends with slabs, doors, windows, pipes, furniture, etc.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.guid

if TYPE_CHECKING:  # pragma: no cover
    from dxf2ifc.core.quality import ValidationReport

from dxf2ifc.core.dxf_reader import read_dxf
from dxf2ifc.core.geometry import (
    FurnitureBoxExtrusion,
    block_to_furniture_box,
    door_block_to_box,
    line_to_cable_carrier,
    line_to_pipe_segment,
    line_to_wall_extrusion,
    panel_to_proxy_solid,
    polygon_to_slab_extrusion,
)
from dxf2ifc.core.mapper import apply_profile
from dxf2ifc.core.types import (
    BlockInstance,
    LineGeometry,
    MappedEntity,
    Point3D,
    PolygonGeometry,
)
from dxf2ifc.profiles.schema import Profile


def build_ifc_project_skeleton(
    *,
    project_name: str = "Untitled",
    site_name: str = "Default Site",
    building_name: str = "Default Building",
    storey_name: str = "Ground Floor",
    schema: str = "IFC4",
) -> ifcopenshell.file:
    """Create a minimal IFC project file with the requested ``schema``
    (``"IFC4"`` or ``"IFC4X3"``) and the IfcProject → Site → Building →
    Storey spatial hierarchy. Length units are millimetres via
    IfcUnitAssignment.
    """
    ifc = ifcopenshell.api.run("project.create_file", version=schema)

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
        is_si=False,
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
        raise TypeError(f"add_slab expects PolygonGeometry, got {type(mapped.geometry).__name__}")

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
        is_si=False,
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
    slab.Representation = ifc.create_entity("IfcProductDefinitionShape", Representations=[shape])

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
        raise TypeError(f"add_door expects BlockInstance, got {type(mapped.geometry).__name__}")

    width = float(mapped.extra_props.get("default_width_mm", 900.0))
    height = float(mapped.extra_props.get("default_height_mm", 2100.0))
    depth = float(mapped.extra_props.get("default_depth_mm", 50.0))
    box = door_block_to_box(mapped.geometry, width_mm=width, height_mm=height, depth_mm=depth)

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
        is_si=False,
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
    door.Representation = ifc.create_entity("IfcProductDefinitionShape", Representations=[shape])

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
        raise TypeError(f"add_window expects BlockInstance, got {type(mapped.geometry).__name__}")

    width = float(mapped.extra_props.get("default_width_mm", 1200.0))
    height = float(mapped.extra_props.get("default_height_mm", 1500.0))
    depth = float(mapped.extra_props.get("default_depth_mm", 60.0))
    box = door_block_to_box(mapped.geometry, width_mm=width, height_mm=height, depth_mm=depth)

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
        is_si=False,
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
    window.Representation = ifc.create_entity("IfcProductDefinitionShape", Representations=[shape])

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
        is_si=False,
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
    pipe.Representation = ifc.create_entity("IfcProductDefinitionShape", Representations=[shape])

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
    extrusion. For BlockInstance geometry the box is anchored at the
    insertion point and dimensions come from extra_props
    (default_width_mm / default_depth_mm / default_height_mm) with
    shelving-friendly defaults (1000 × 600 × 2000 mm). For
    PolygonGeometry (closed polyline) the bounding box of the polygon
    drives width / depth and the box is anchored at (xmin, ymin); the
    extrusion height still comes from extra_props.
    """
    if isinstance(mapped.geometry, BlockInstance):
        width = float(mapped.extra_props.get("default_width_mm", 1000.0))
        depth = float(mapped.extra_props.get("default_depth_mm", 600.0))
        height = float(mapped.extra_props.get("default_height_mm", 2000.0))
        box = block_to_furniture_box(
            mapped.geometry, width_mm=width, depth_mm=depth, height_mm=height
        )
    elif isinstance(mapped.geometry, PolygonGeometry):
        xs = [v.x for v in mapped.geometry.vertices]
        ys = [v.y for v in mapped.geometry.vertices]
        zs = [v.z for v in mapped.geometry.vertices]
        width = max(xs) - min(xs)
        depth = max(ys) - min(ys)
        if width < 50.0 or depth < 50.0:
            raise ValueError(
                "add_furniture polygon outline is degenerate "
                f"(width={width:.1f} mm, depth={depth:.1f} mm; min side 50 mm)"
            )
        height = float(mapped.extra_props.get("default_height_mm", 2000.0))
        box = FurnitureBoxExtrusion(
            anchor=Point3D(min(xs), min(ys), min(zs)),
            angle_rad=0.0,
            width_mm=width,
            depth_mm=depth,
            height_mm=height,
        )
    else:
        raise TypeError(
            "add_furniture expects BlockInstance or PolygonGeometry, "
            f"got {type(mapped.geometry).__name__}"
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
        is_si=False,
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


_IFC_CABLE_CARRIER_SEGMENT_TYPES = frozenset(
    {"CABLELADDERSEGMENT", "CABLETRAYSEGMENT", "CABLETRUNKINGSEGMENT", "CONDUITSEGMENT"}
)


def add_cable_carrier_segment(
    ifc,
    mapped: MappedEntity,
    *,
    parent_storey,
    predefined_type: str = "CABLETRUNKINGSEGMENT",
) -> object:
    """Create an IfcCableCarrierSegment from a LineGeometry-bearing MappedEntity.

    The tray is rendered as a rectangular extrusion (width × height ×
    length), anchored at the line start and rotated by the line angle.
    A single IfcCableCarrierSegmentType per requested predefined_type is
    created and reused. Tokens outside IfcCableCarrierSegmentTypeEnum are
    mapped to USERDEFINED + ObjectType / ElementType for round-tripping.
    """
    if not isinstance(mapped.geometry, LineGeometry):
        raise TypeError(
            f"add_cable_carrier_segment expects LineGeometry, got {type(mapped.geometry).__name__}"
        )

    width = float(mapped.extra_props.get("default_width_mm", 300.0))
    height = float(mapped.extra_props.get("default_height_mm", 80.0))
    ext = line_to_cable_carrier(mapped.geometry, width_mm=width, height_mm=height)

    is_userdefined = predefined_type not in _IFC_CABLE_CARRIER_SEGMENT_TYPES
    enum_value = "USERDEFINED" if is_userdefined else predefined_type

    seg = ifcopenshell.api.run(
        "root.create_entity",
        ifc,
        ifc_class="IfcCableCarrierSegment",
        name=mapped.layer,
        predefined_type=enum_value,
    )

    seg_type = _ensure_cable_carrier_segment_type(ifc, predefined_type, enum_value)
    ifcopenshell.api.run("type.assign_type", ifc, related_objects=[seg], relating_type=seg_type)

    seg.PredefinedType = enum_value
    if is_userdefined:
        seg.ObjectType = predefined_type

    matrix = _z_rotation_matrix(ext.anchor.x, ext.anchor.y, ext.anchor.z, ext.angle_rad)
    ifcopenshell.api.run(
        "geometry.edit_object_placement",
        ifc,
        product=seg,
        matrix=matrix,
        is_si=False,
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
                Coordinates=(0.0, ext.height_mm / 2.0),
            ),
        ),
        XDim=ext.width_mm,
        YDim=ext.height_mm,
    )
    extruded = ifc.create_entity(
        "IfcExtrudedAreaSolid",
        SweptArea=rect,
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
    seg.Representation = ifc.create_entity("IfcProductDefinitionShape", Representations=[shape])

    ifcopenshell.api.run(
        "spatial.assign_container",
        ifc,
        products=[seg],
        relating_structure=parent_storey,
    )
    return seg


def add_building_element_proxy(
    ifc,
    mapped: MappedEntity,
    *,
    parent_storey,
) -> object:
    """Create an IfcBuildingElementProxy from a PolygonGeometry-bearing
    MappedEntity. Used for cold-room panels (KYL-LEVY) and corner pieces
    (KYL-NURKKA): a closed polygon outline extruded upwards by
    extra_props['default_thickness_mm'] (default 120 mm).
    """
    if not isinstance(mapped.geometry, PolygonGeometry):
        raise TypeError(
            "add_building_element_proxy expects PolygonGeometry, "
            f"got {type(mapped.geometry).__name__}"
        )

    thickness = float(mapped.extra_props.get("default_thickness_mm", 120.0))
    panel = panel_to_proxy_solid(mapped.geometry, thickness_mm=thickness)

    proxy = ifcopenshell.api.run(
        "root.create_entity",
        ifc,
        ifc_class="IfcBuildingElementProxy",
        name=mapped.layer,
    )

    matrix = _z_rotation_matrix(0.0, 0.0, panel.base_z, 0.0)
    ifcopenshell.api.run(
        "geometry.edit_object_placement",
        ifc,
        product=proxy,
        matrix=matrix,
        is_si=False,
    )

    model_ctx = [
        c
        for c in ifc.by_type("IfcGeometricRepresentationSubContext")
        if c.ContextIdentifier == "Body"
    ][0]
    polyline_points = [
        ifc.create_entity("IfcCartesianPoint", Coordinates=(float(x), float(y)))
        for x, y in panel.outline_xy
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
        ExtrudedDirection=ifc.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0)),
        Depth=panel.thickness_mm,
    )
    shape = ifc.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=model_ctx,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=[extruded],
    )
    proxy.Representation = ifc.create_entity("IfcProductDefinitionShape", Representations=[shape])

    ifcopenshell.api.run(
        "spatial.assign_container",
        ifc,
        products=[proxy],
        relating_structure=parent_storey,
    )
    return proxy


_COOLING_EQUIPMENT_CLASSES = frozenset({"IfcEvaporator", "IfcCondenser", "IfcCompressor"})


def add_cooling_equipment(
    ifc,
    mapped: MappedEntity,
    *,
    parent_storey,
) -> object:
    """Create an IfcEvaporator / IfcCondenser / IfcCompressor from a
    BlockInstance-bearing MappedEntity. The selected IFC class comes from
    ``mapped.ifc_type``; the body is a width × depth × height extrusion
    using extra_props defaults that match storage furniture.
    """
    if mapped.ifc_type not in _COOLING_EQUIPMENT_CLASSES:
        raise ValueError(
            f"add_cooling_equipment requires ifc_type in {sorted(_COOLING_EQUIPMENT_CLASSES)}, "
            f"got {mapped.ifc_type!r}"
        )
    if not isinstance(mapped.geometry, BlockInstance):
        raise TypeError(
            f"add_cooling_equipment expects BlockInstance, got {type(mapped.geometry).__name__}"
        )

    width = float(mapped.extra_props.get("default_width_mm", 800.0))
    depth = float(mapped.extra_props.get("default_depth_mm", 600.0))
    height = float(mapped.extra_props.get("default_height_mm", 1200.0))
    box = block_to_furniture_box(mapped.geometry, width_mm=width, depth_mm=depth, height_mm=height)

    product = ifcopenshell.api.run(
        "root.create_entity",
        ifc,
        ifc_class=mapped.ifc_type,
        name=mapped.layer,
    )

    matrix = _z_rotation_matrix(box.anchor.x, box.anchor.y, box.anchor.z, box.angle_rad)
    ifcopenshell.api.run(
        "geometry.edit_object_placement",
        ifc,
        product=product,
        matrix=matrix,
        is_si=False,
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
    product.Representation = ifc.create_entity("IfcProductDefinitionShape", Representations=[shape])

    ifcopenshell.api.run(
        "spatial.assign_container",
        ifc,
        products=[product],
        relating_structure=parent_storey,
    )
    return product


def add_system(ifc, *, name: str) -> object:
    """Return an IfcSystem entity with the given name, creating it once per file.

    Repeated calls with the same name yield the same instance so callers can
    safely group products without bookkeeping.
    """
    for existing in ifc.by_type("IfcSystem"):
        if existing.Name == name:
            return existing
    return ifcopenshell.api.run(
        "root.create_entity",
        ifc,
        ifc_class="IfcSystem",
        name=name,
    )


def assign_to_system(ifc, *, products: list, system) -> object:
    """Attach the given products to ``system`` via IfcRelAssignsToGroup."""
    if not products:
        return None
    return ifc.create_entity(
        "IfcRelAssignsToGroup",
        GlobalId=ifcopenshell.guid.new(),
        RelatedObjects=list(products),
        RelatingGroup=system,
    )


def _ensure_cable_carrier_segment_type(ifc, requested_type: str, enum_value: str) -> object:
    """Return (creating once per file) an IfcCableCarrierSegmentType."""
    for t in ifc.by_type("IfcCableCarrierSegmentType"):
        if enum_value == "USERDEFINED":
            if t.PredefinedType == "USERDEFINED" and t.ElementType == requested_type:
                return t
        elif t.PredefinedType == enum_value:
            return t

    seg_type = ifcopenshell.api.run(
        "root.create_entity",
        ifc,
        ifc_class="IfcCableCarrierSegmentType",
        name=f"CableCarrierSegmentType_{requested_type}",
        predefined_type=enum_value,
    )
    if enum_value == "USERDEFINED":
        seg_type.ElementType = requested_type
    return seg_type


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


_CLASSIFICATION_SOURCES: dict[str, dict[str, str]] = {
    "Talo2000": {"Source": "Rakennustieto Oy", "Edition": "Talo 2000"},
    "RAVA-LVI": {"Source": "Rakennustietojärjestelmä RYTJ", "Edition": "LVI-TUOTEOSA v1.0"},
    "RAVA-TATE": {
        "Source": "Rakennustietojärjestelmä RYTJ",
        "Edition": "TALOTEKNIIKKA-TUOTEOSA v1.0",
    },
}


def _classification_name_for(domain: str, code: str) -> str:
    """Resolve the IfcClassification.Name for a (domain, code) pair."""
    if domain == "ARK":
        return "Talo2000"
    if domain == "TATE":
        if code.startswith("T-LVI"):
            return "RAVA-LVI"
        if code.startswith("T-TATE"):
            return "RAVA-TATE"
    raise ValueError(f"Cannot resolve classification source for domain={domain!r}, code={code!r}")


def add_classification(
    ifc, product, *, domain: str, code: str | None, name: str | None = None
) -> object | None:
    """Attach a discipline-aware IfcClassificationReference to ``product``.

    domain="ARK" emits IfcClassification "Talo2000".
    domain="TATE" emits "RAVA-LVI" for T-LVI-… codes and "RAVA-TATE" for
    T-TATE-… codes. Returns ``None`` and does nothing if ``code`` is empty.
    Each IfcClassification entity is created at most once per file and
    reused across products.
    """
    if not code:
        return None
    classification_name = _classification_name_for(domain, code)
    existing = [c for c in ifc.by_type("IfcClassification") if c.Name == classification_name]
    if existing:
        classification = existing[0]
    else:
        meta = _CLASSIFICATION_SOURCES[classification_name]
        classification = ifc.create_entity(
            "IfcClassification",
            Source=meta["Source"],
            Edition=meta["Edition"],
            Name=classification_name,
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


def add_talo2000_classification(
    ifc, product, *, code: str | None, name: str | None
) -> object | None:
    """Backwards-compatible wrapper around :func:`add_classification` (ARK domain).

    Returns ``None`` and does nothing for products without a Talo2000 code
    (TATE-domain rules use ``add_classification`` directly with their RAVA code).
    """
    return add_classification(ifc, product, domain="ARK", code=code, name=name)


def convert_dxf(
    *,
    dxf_path: str | Path,
    output_path: str | Path,
    profile: Profile,
    project_name: str | None = None,
    validate: bool = False,
    schema: str = "IFC4",
) -> tuple[dict[str, list], ValidationReport | None]:
    """Orchestrate DXF -> IFC conversion end-to-end.

    Returns a tuple ``(systems, report)`` where ``systems`` maps each
    ``Rule.system_name`` to the IFC products that were grouped under that
    system, and ``report`` is a :class:`ValidationReport` produced by
    :func:`dxf2ifc.core.quality.validate_ifc` when ``validate=True`` (or
    ``None`` otherwise). ``schema`` selects between ``"IFC4"`` (default)
    and ``"IFC4X3"`` (Plan H).
    """
    name = project_name or Path(dxf_path).stem
    entities = read_dxf(dxf_path)
    mapped = apply_profile(entities, profile)
    ifc = build_ifc_project_skeleton(project_name=name, schema=schema)
    storey = ifc.by_type("IfcBuildingStorey")[0]
    systems: dict[str, list] = {}

    def _record(m: object, product: object) -> None:
        sys_name = m.extra_props.get("system_name") if m.extra_props else None
        if sys_name:
            systems.setdefault(sys_name, []).append(product)

    for m in mapped:
        if m.ifc_type == "IfcWall":
            wall = add_wall(
                ifc,
                m,
                parent_storey=storey,
                predefined_type=m.predefined_type or "STANDARD",
            )
            add_talo2000_classification(ifc, wall, code=m.talo2000_code, name=m.talo2000_name)
            _record(m, wall)
        elif m.ifc_type == "IfcSlab":
            slab = add_slab(
                ifc,
                m,
                parent_storey=storey,
                predefined_type=m.predefined_type or "FLOOR",
            )
            add_talo2000_classification(ifc, slab, code=m.talo2000_code, name=m.talo2000_name)
            _record(m, slab)
        elif m.ifc_type == "IfcDoor":
            door = add_door(
                ifc,
                m,
                parent_storey=storey,
                predefined_type=m.predefined_type or "DOOR",
            )
            add_talo2000_classification(ifc, door, code=m.talo2000_code, name=m.talo2000_name)
            _record(m, door)
        elif m.ifc_type == "IfcWindow":
            window = add_window(
                ifc,
                m,
                parent_storey=storey,
                predefined_type=m.predefined_type or "WINDOW",
            )
            add_talo2000_classification(ifc, window, code=m.talo2000_code, name=m.talo2000_name)
            _record(m, window)
        elif m.ifc_type == "IfcPipeSegment":
            pipe = add_pipe_segment(
                ifc,
                m,
                parent_storey=storey,
                predefined_type=m.predefined_type or "REFRIGERATION",
            )
            add_talo2000_classification(ifc, pipe, code=m.talo2000_code, name=m.talo2000_name)
            _record(m, pipe)
        elif m.ifc_type == "IfcFurniture":
            furniture = add_furniture(ifc, m, parent_storey=storey)
            add_talo2000_classification(ifc, furniture, code=m.talo2000_code, name=m.talo2000_name)
            _record(m, furniture)
        elif m.ifc_type == "IfcCableCarrierSegment":
            seg = add_cable_carrier_segment(
                ifc,
                m,
                parent_storey=storey,
                predefined_type=m.predefined_type or "CABLETRUNKINGSEGMENT",
            )
            add_talo2000_classification(ifc, seg, code=m.talo2000_code, name=m.talo2000_name)
            _record(m, seg)
        elif m.ifc_type == "IfcBuildingElementProxy":
            proxy = add_building_element_proxy(ifc, m, parent_storey=storey)
            add_talo2000_classification(ifc, proxy, code=m.talo2000_code, name=m.talo2000_name)
            _record(m, proxy)
        elif m.ifc_type in _COOLING_EQUIPMENT_CLASSES:
            equipment = add_cooling_equipment(ifc, m, parent_storey=storey)
            add_talo2000_classification(ifc, equipment, code=m.talo2000_code, name=m.talo2000_name)
            _record(m, equipment)

    for system_name, products in systems.items():
        system = add_system(ifc, name=system_name)
        assign_to_system(ifc, products=products, system=system)

    write_ifc(ifc, output_path)

    report: ValidationReport | None = None
    if validate:
        from dxf2ifc.core.quality import validate_ifc as _validate_ifc

        report = _validate_ifc(output_path)
    return systems, report
