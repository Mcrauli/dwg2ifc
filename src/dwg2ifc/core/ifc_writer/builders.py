"""All IFC element builders: walls, slabs, doors, windows, pipes,
furniture, cable carriers, building-element proxies, cooling equipment.

Plus IfcSystem grouping + cable-carrier/pipe-segment type caches and
the file-write helper.
"""

from __future__ import annotations

import math
from pathlib import Path

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.guid

from dwg2ifc.core.geometry import (
    FurnitureBoxExtrusion,
    block_to_furniture_box,
    door_block_to_box,
    line_to_cable_carrier,
    line_to_pipe_segment,
    line_to_wall_extrusion,
    panel_to_proxy_solid,
    polygon_to_slab_extrusion,
)
from dwg2ifc.core.ifc_writer.mesh import (
    _add_mesh_product,
)
from dwg2ifc.core.ifc_writer.transforms import _z_rotation_matrix
from dwg2ifc.core.types import (
    BlockInstance,
    LineGeometry,
    MappedEntity,
    MeshGeometry,
    Point3D,
    PolygonGeometry,
)


def write_ifc(ifc: ifcopenshell.file, output_path: str | Path) -> None:
    """Write the IFC file to disk.

    Final pass before write: stamp every IfcRoot created after the
    project skeleton (walls, slabs, pipes, classification rels, psets,
    systems, …) with the project's OwnerHistory so consumers like
    Solibri can read the producing IfcApplication. A first pass
    happens inside ``build_ifc_project_skeleton``; this catches
    everything added by the per-element builders in between.
    """
    owner_histories = ifc.by_type("IfcOwnerHistory")
    if owner_histories:
        oh = owner_histories[0]
        for root in ifc.by_type("IfcRoot"):
            if getattr(root, "OwnerHistory", None) is None:
                root.OwnerHistory = oh
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


def _compress_ifc_guid(uuid_value: str) -> str:
    value = str(uuid_value or "").strip()
    if not value:
        raise ValueError("hole reservation GUID missing")
    try:
        return ifcopenshell.guid.compress(value)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"invalid hole reservation GUID: {value}") from exc


def add_provision_for_void(
    ifc,
    mapped: MappedEntity,
    *,
    parent_storey,
) -> object:
    if not isinstance(mapped.geometry, BlockInstance):
        raise TypeError(
            "add_provision_for_void expects BlockInstance, "
            f"got {type(mapped.geometry).__name__}"
        )

    extras = mapped.extra_props or {}
    guid = _compress_ifc_guid(extras.get("guid"))
    diameter_mm = float(extras.get("halkaisija_mm", 200.0))
    depth_mm = float(extras.get("pituus_mm", 300.0))
    point = mapped.geometry.insertion_point

    product = ifcopenshell.api.run(
        "root.create_entity",
        ifc,
        ifc_class="IfcBuildingElementProxy",
        name=(extras.get("tunnus") or mapped.layer),
        predefined_type="PROVISIONFORVOID",
    )
    product.GlobalId = guid
    if extras.get("varaus_tyyppi"):
        product.Description = str(extras["varaus_tyyppi"])

    matrix = _z_rotation_matrix(point.x, point.y, point.z, mapped.geometry.rotation_rad)
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
    circle = ifc.create_entity(
        "IfcCircleProfileDef",
        ProfileType="AREA",
        Position=ifc.create_entity(
            "IfcAxis2Placement2D",
            Location=ifc.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0)),
        ),
        Radius=diameter_mm / 2.0,
    )
    extruded = ifc.create_entity(
        "IfcExtrudedAreaSolid",
        SweptArea=circle,
        Position=ifc.create_entity(
            "IfcAxis2Placement3D",
            Location=ifc.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0, 0.0)),
        ),
        ExtrudedDirection=ifc.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0)),
        Depth=depth_mm,
    )
    shape = ifc.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=model_ctx,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=[extruded],
    )
    product.Representation = ifc.create_entity(
        "IfcProductDefinitionShape", Representations=[shape]
    )
    pset = ifcopenshell.api.run(
        "pset.add_pset",
        ifc,
        product=product,
        name="Pset_ProvisionForVoid",
    )
    pset_props: dict[str, object] = {
        "VoidShape": "Round",
        "Diameter": diameter_mm,
        "Depth": depth_mm,
    }
    if extras.get("system_name"):
        pset_props["System"] = str(extras["system_name"])
    ifcopenshell.api.run(
        "pset.edit_pset",
        ifc,
        pset=pset,
        properties=pset_props,
    )

    ifcopenshell.api.run(
        "spatial.assign_container",
        ifc,
        products=[product],
        relating_structure=parent_storey,
    )
    return product


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

    For :class:`MeshGeometry` (DXF MESH after accoreconsole pre-processing)
    a faceted Brep representation is emitted instead of an extrusion, with
    the placement at the mesh's bounding-box minimum.
    """
    if isinstance(mapped.geometry, MeshGeometry):
        return _add_mesh_product(
            ifc,
            mapped,
            ifc_class="IfcFurniture",
            parent_storey=parent_storey,
        )
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
    elif isinstance(mapped.geometry, LineGeometry):
        # KLHYLLY-TIKAS draws TIKAS shelves as inline LINE rails rather
        # than as block INSERTs. Treat each LINE as one shelf rail: width
        # = line length, depth + height come from extra_props with
        # shelf-friendly defaults (400 mm deep × 60 mm thick).
        line = mapped.geometry
        dx = line.end.x - line.start.x
        dy = line.end.y - line.start.y
        length = math.hypot(dx, dy)
        if length < 50.0:
            raise ValueError(
                f"add_furniture line is degenerate (length={length:.1f} mm; min 50 mm)"
            )
        depth = float(mapped.extra_props.get("default_depth_mm", 400.0))
        height = float(mapped.extra_props.get("default_height_mm", 60.0))
        box = FurnitureBoxExtrusion(
            anchor=line.start,
            angle_rad=math.atan2(dy, dx),
            width_mm=length,
            depth_mm=depth,
            height_mm=height,
        )
    else:
        raise TypeError(
            "add_furniture expects BlockInstance, PolygonGeometry or LineGeometry, "
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


def add_cable_carrier(
    ifc,
    mapped: MappedEntity,
    *,
    parent_storey,
    predefined_type: str = "CABLETRAYSEGMENT",
) -> object:
    """Create an IfcCableCarrierSegment from a MeshGeometry- or
    BlockInstance-bearing MappedEntity.

    Mirrors :func:`add_cable_carrier_segment` (which handles 2D LineGeometry
    rails) but consumes 3D inputs: DXF MESH entities post accoreconsole
    pre-processing, or block placements with default-dimension
    extra_props. ``predefined_type`` follows Granlund convention:
    ``"CABLELADDERSEGMENT"`` for tikashylly, ``"CABLETRAYSEGMENT"`` for
    levyhylly. As with :func:`add_cable_carrier_segment` a single
    IfcCableCarrierSegmentType per (predefined_type) is created and
    re-used. Tokens outside IfcCableCarrierSegmentTypeEnum are mapped to
    USERDEFINED + ObjectType / ElementType for round-tripping.
    """
    if not isinstance(mapped.geometry, (MeshGeometry, BlockInstance, PolygonGeometry)):
        raise TypeError(
            "add_cable_carrier expects MeshGeometry, BlockInstance or PolygonGeometry, "
            f"got {type(mapped.geometry).__name__}"
        )

    is_userdefined = predefined_type not in _IFC_CABLE_CARRIER_SEGMENT_TYPES
    enum_value = "USERDEFINED" if is_userdefined else predefined_type

    if isinstance(mapped.geometry, MeshGeometry):
        seg = _add_mesh_product(
            ifc,
            mapped,
            ifc_class="IfcCableCarrierSegment",
            parent_storey=parent_storey,
            predefined_type=enum_value,
        )
    else:
        # BlockInstance or PolygonGeometry fallback: width × depth × height
        # extrusion box. PolygonGeometry typically comes from a closed
        # LWPOLYLINE outlining the carrier footprint; bbox-extrude into a
        # default-thickness shelf board.
        if isinstance(mapped.geometry, PolygonGeometry):
            xs = [v.x for v in mapped.geometry.vertices]
            ys = [v.y for v in mapped.geometry.vertices]
            zs = [v.z for v in mapped.geometry.vertices]
            width = max(xs) - min(xs)
            depth = max(ys) - min(ys)
            if width < 50.0 or depth < 50.0:
                raise ValueError(
                    "add_cable_carrier polygon outline is degenerate "
                    f"(width={width:.1f} mm, depth={depth:.1f} mm; min side 50 mm)"
                )
            height = float(mapped.extra_props.get("default_height_mm", 80.0))
            box = FurnitureBoxExtrusion(
                anchor=Point3D(min(xs), min(ys), min(zs)),
                angle_rad=0.0,
                width_mm=width,
                depth_mm=depth,
                height_mm=height,
            )
        else:
            width = float(mapped.extra_props.get("default_width_mm", 300.0))
            depth = float(mapped.extra_props.get("default_depth_mm", 600.0))
            height = float(mapped.extra_props.get("default_height_mm", 80.0))
            box = block_to_furniture_box(
                mapped.geometry, width_mm=width, depth_mm=depth, height_mm=height
            )

        seg = ifcopenshell.api.run(
            "root.create_entity",
            ifc,
            ifc_class="IfcCableCarrierSegment",
            name=mapped.layer,
            predefined_type=enum_value,
        )

        matrix = _z_rotation_matrix(box.anchor.x, box.anchor.y, box.anchor.z, box.angle_rad)
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
        seg.Representation = ifc.create_entity(
            "IfcProductDefinitionShape", Representations=[shape]
        )

        ifcopenshell.api.run(
            "spatial.assign_container",
            ifc,
            products=[seg],
            relating_structure=parent_storey,
        )

    seg_type = _ensure_cable_carrier_segment_type(ifc, predefined_type, enum_value)
    ifcopenshell.api.run("type.assign_type", ifc, related_objects=[seg], relating_type=seg_type)

    seg.PredefinedType = enum_value
    if is_userdefined:
        seg.ObjectType = predefined_type

    return seg


def add_building_element_proxy(
    ifc,
    mapped: MappedEntity,
    *,
    parent_storey,
) -> object:
    """Create an IfcBuildingElementProxy from a PolygonGeometry- or
    MeshGeometry-bearing MappedEntity. PolygonGeometry → 2D outline
    extruded upwards by extra_props['default_thickness_mm'] (default
    120 mm) — used for cold-room panels (KYL-LEVY) and corner pieces.
    MeshGeometry → faceted Brep — used in v0.1.19+ for MUUT_OSAT and
    other proxy_preprocessing-fed proxies whose graphics ezdxf could
    not decode (the bbox cuboid fallback path).
    """
    element_type = mapped.predefined_type or mapped.layer
    proxy_type = _ensure_proxy_type(ifc, element_type=element_type)

    if isinstance(mapped.geometry, MeshGeometry):
        product = _add_mesh_product(
            ifc,
            mapped,
            ifc_class="IfcBuildingElementProxy",
            parent_storey=parent_storey,
            predefined_type="USERDEFINED",
        )
        product.ObjectType = element_type
        ifcopenshell.api.run(
            "type.assign_type", ifc, related_objects=[product], relating_type=proxy_type
        )
        return product

    if not isinstance(mapped.geometry, PolygonGeometry):
        raise TypeError(
            "add_building_element_proxy expects PolygonGeometry or MeshGeometry, "
            f"got {type(mapped.geometry).__name__}"
        )

    thickness = float(mapped.extra_props.get("default_thickness_mm", 120.0))
    panel = panel_to_proxy_solid(mapped.geometry, thickness_mm=thickness)

    proxy = ifcopenshell.api.run(
        "root.create_entity",
        ifc,
        ifc_class="IfcBuildingElementProxy",
        name=mapped.layer,
        predefined_type="USERDEFINED",
    )
    proxy.ObjectType = element_type

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
    ifcopenshell.api.run(
        "type.assign_type", ifc, related_objects=[proxy], relating_type=proxy_type
    )
    return proxy


_COOLING_EQUIPMENT_CLASSES = frozenset({
    # Compressor stack: classic refrigeration plant components.
    "IfcEvaporator",
    "IfcCondenser",
    "IfcCompressor",
    # Whole-unit refrigeration machines added 2026-05-08:
    "IfcChiller",            # Vedenjäähdytyskone (T-LVI-01-01-003)
    "IfcUnitaryEquipment",   # Kylmävesiasema, jäähdytyskoneikko, kylmäkalusteet
    "IfcCoil",               # Välijäähdytin (T-LVI-01-01-024)
})


def add_cooling_equipment(
    ifc,
    mapped: MappedEntity,
    *,
    parent_storey,
) -> object:
    """Create an IfcEvaporator / IfcCondenser / IfcCompressor from a
    BlockInstance- or MeshGeometry-bearing MappedEntity. The selected
    IFC class comes from ``mapped.ifc_type``; for BlockInstance the body
    is a width × depth × height extrusion using extra_props defaults that
    match storage furniture, while MeshGeometry produces a faceted Brep
    representation (DXF MESH after accoreconsole pre-processing).
    """
    if mapped.ifc_type not in _COOLING_EQUIPMENT_CLASSES:
        raise ValueError(
            f"add_cooling_equipment requires ifc_type in {sorted(_COOLING_EQUIPMENT_CLASSES)}, "
            f"got {mapped.ifc_type!r}"
        )
    cooling_type = _ensure_cooling_equipment_type(ifc, mapped.ifc_type)
    if isinstance(mapped.geometry, MeshGeometry):
        product = _add_mesh_product(
            ifc,
            mapped,
            ifc_class=mapped.ifc_type,
            parent_storey=parent_storey,
        )
        ifcopenshell.api.run(
            "type.assign_type", ifc, related_objects=[product], relating_type=cooling_type
        )
        return product
    if not isinstance(mapped.geometry, BlockInstance):
        raise TypeError(
            f"add_cooling_equipment expects BlockInstance or MeshGeometry, "
            f"got {type(mapped.geometry).__name__}"
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
    ifcopenshell.api.run(
        "type.assign_type", ifc, related_objects=[product], relating_type=cooling_type
    )
    return product


def add_tank(ifc, mapped: MappedEntity, *, parent_storey) -> object:
    """Create an IfcTank from a MeshGeometry-bearing MappedEntity.

    Used in v0.1.19+ for KYL-KONDENSSIASTIAT (lauhdevesiastiat / condensate
    basins) — typically MagiCAD ACAD_PROXY_ENTITY records that
    :func:`dwg2ifc.core.proxy_preprocessing.extract_proxy_geometry` lifts
    to either a real triangulated body (Object Enabler installed) or a
    bbox cuboid fallback. Either way, a faceted Brep representation is
    enough for Solibri to display the tank in the IFC.
    """
    return _add_mesh_product(
        ifc,
        mapped,
        ifc_class="IfcTank",
        parent_storey=parent_storey,
        predefined_type=mapped.predefined_type or "BASIN",
    )


def add_flow_controller(ifc, mapped: MappedEntity, *, parent_storey) -> object:
    """Create an IfcFlowController from a MeshGeometry-bearing MappedEntity.

    Used in v0.1.19+ for KYL-JV1-LAITE (jäähdytysvesilaitteet — pumps,
    valves, accessories) — MagiCAD ACAD_PROXY_ENTITY records that need
    Object Enabler for full geometry; without enabler, a bbox cuboid is
    emitted and the user is warned in the progress log.
    """
    return _add_mesh_product(
        ifc,
        mapped,
        ifc_class="IfcFlowController",
        parent_storey=parent_storey,
        predefined_type=mapped.predefined_type or "USERDEFINED",
    )


# Generic distribution-element classes added 2026-05-08 for the broad
# kylmälaitesuunnittelu coverage. Each one is constructed from
# MeshGeometry via _add_mesh_product — the exact IFC class comes from
# the layer rule, predefined_type may also be carried on the rule.
_DISTRIBUTION_ELEMENT_CLASSES = frozenset({
    "IfcSensor",            # Termostaatit, lämpötila-/paine-/pinta-anturit, CO2-anturit
    "IfcValve",             # Magneettiventtiilit, padotusventtiilit, käsiventtiilit
    "IfcPump",              # Kierto-/lauhdepumput, sadevesipumppaamot
    "IfcWasteTerminal",     # Lattiakaivot, vesilukot, sadevesikattokaivot
    "IfcInterceptor",       # Rasvanerottimet, öljynerottimet, hiekanerottimet
    "IfcElectricDistributionBoard",  # Koneikkokeskus (KK), ryhmäkeskus (RK)
    "IfcController",        # Ohjaus-/säädinkeskukset (PROGRAMMABLE)
    "IfcAlarm",             # CO2-sireenit, palopainikkeet, hätäilmoittimet
    "IfcSwitchingDevice",   # Hätäseispainikkeet, turvakytkimet
    "IfcCommunicationsAppliance",  # Huolto-PC:t, valvomotyöasemat
    "IfcDuctSegment",       # IV-kanavat (jos KYL-piirustuksessa)
    "IfcDuctFitting",       # Kanavaosat
    "IfcAirTerminal",       # Tulo/poistoilmapäätelaitteet
})

# Every IFC type the orchestrator dispatch loop knows how to build. The
# profile editor's "IFC type" dropdown is sourced from this tuple so the
# GUI can never offer a type the writer would silently drop. Ordered for
# readability: ARK/structural base types, refrigeration plant, tanks &
# flow control, then distribution elements. Pinned to the dispatch loop
# by tests/test_supported_ifc_types.py.
SUPPORTED_IFC_TYPES: tuple[str, ...] = (
    # Structural / ARK base types
    "IfcWall",
    "IfcSlab",
    "IfcDoor",
    "IfcWindow",
    # TATE/KYL geometry primitives
    "IfcPipeSegment",
    "IfcCableCarrierSegment",
    "IfcFurniture",
    "IfcBuildingElementProxy",
    # Refrigeration plant (_COOLING_EQUIPMENT_CLASSES)
    "IfcEvaporator",
    "IfcCondenser",
    "IfcCompressor",
    "IfcChiller",
    "IfcUnitaryEquipment",
    "IfcCoil",
    # Tanks & flow control
    "IfcTank",
    "IfcFlowController",
    # Distribution elements (_DISTRIBUTION_ELEMENT_CLASSES)
    "IfcSensor",
    "IfcValve",
    "IfcPump",
    "IfcWasteTerminal",
    "IfcInterceptor",
    "IfcElectricDistributionBoard",
    "IfcController",
    "IfcAlarm",
    "IfcSwitchingDevice",
    "IfcCommunicationsAppliance",
    "IfcDuctSegment",
    "IfcDuctFitting",
    "IfcAirTerminal",
)


def add_distribution_element(
    ifc,
    mapped: MappedEntity,
    *,
    ifc_class: str,
    parent_storey,
) -> object:
    """Create any generic IfcDistributionElement subclass from a
    MeshGeometry-bearing MappedEntity.

    Added in v0.2.0-alpha11 for the broad kylmälaitesuunnittelu
    coverage. Instead of writing a dedicated ``add_*`` per IFC class
    (sensor / valve / pump / waste terminal / distribution board /
    duct), this single helper takes the class name as an argument and
    funnels through :func:`_add_mesh_product`. Predefined type comes
    from the rule (``mapped.predefined_type``) and falls back to
    ``USERDEFINED`` when the rule omits it.
    """
    if ifc_class not in _DISTRIBUTION_ELEMENT_CLASSES:
        raise ValueError(
            f"add_distribution_element supports {sorted(_DISTRIBUTION_ELEMENT_CLASSES)}, "
            f"got {ifc_class!r}"
        )
    return _add_mesh_product(
        ifc,
        mapped,
        ifc_class=ifc_class,
        parent_storey=parent_storey,
        predefined_type=mapped.predefined_type or "USERDEFINED",
    )


def add_system(ifc, *, name: str, system_code: str | None = None) -> object:
    """Return an IfcSystem entity with the given name, creating it once per file.

    Repeated calls with the same name yield the same instance so callers can
    safely group products without bookkeeping.
    """
    system = None
    for existing in ifc.by_type("IfcSystem"):
        if existing.Name == name:
            system = existing
            break
    if system is None:
        system = ifcopenshell.api.run(
            "root.create_entity",
            ifc,
            ifc_class="IfcSystem",
            name=name,
        )
    _attach_fi_jarjestelma_pset(ifc, system=system, system_name=name, system_code=system_code)
    return system


def _attach_fi_jarjestelma_pset(
    ifc, *, system, system_name: str, system_code: str | None
) -> None:
    """Attach FI_Järjestelmä on IfcSystem (RAVA3Pro style)."""
    rava_name = ""
    rava_short_name = ""
    jarjestelmalaji = ""
    jarjestelmaluokka = ""
    if system_code:
        try:
            from dwg2ifc.profiles.rava.loader import load_rava_codes

            code = load_rava_codes().get(system_code)
            if code is not None:
                rava_name = code.name or ""
                rava_short_name = code.short_name or ""
                if code.codeset == "LVI-JARJESTELMA":
                    jarjestelmalaji = "LVI-JÄRJESTELMÄT"
                elif code.codeset == "TALOTEKNIIKKA-JARJESTELMA":
                    jarjestelmalaji = "TALOTEKNIIKKA-JÄRJESTELMÄT"
        except Exception:
            pass
    if system_code:
        if system_code.startswith("J-LVI-09"):
            jarjestelmaluokka = "KYLMÄJÄRJESTELMÄT"
        elif system_code.startswith("J-LVI-04"):
            jarjestelmaluokka = "VIEMÄRIJÄRJESTELMÄT"
    system_tunnus = ""
    if rava_short_name and rava_short_name.casefold() != "ei tunnusta":
        system_tunnus = rava_short_name
    pset = None
    for rel in getattr(system, "IsDefinedBy", None) or []:
        if not rel.is_a("IfcRelDefinesByProperties"):
            continue
        pd = rel.RelatingPropertyDefinition
        if pd and pd.is_a("IfcPropertySet") and pd.Name == "FI_Järjestelmä":
            pset = pd
            break
    if pset is None:
        pset = ifcopenshell.api.run("pset.add_pset", ifc, product=system, name="FI_Järjestelmä")
    ifcopenshell.api.run(
        "pset.edit_pset",
        ifc,
        pset=pset,
        properties={
            "01 Järjestelmälaji": jarjestelmalaji,
            "02 Järjestelmäluokka": jarjestelmaluokka,
            "03 Järjestelmätyypin koodi": system_code or "",
            "04 Järjestelmätyyppi": rava_name,
            "05 Järjestelmätyypin yleistunnus": rava_short_name,
            "06 Järjestelmän nimi": system_name or "",
            "07 Järjestelmän tunnus": system_tunnus,
        },
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


def _attach_type_common_pset(ifc, type_object, pset_name: str, reference: str) -> None:
    """Attach a buildingSMART standard ``Pset_*TypeCommon`` to a type object.

    MagiCAD's "Convert to MagiCAD object" command requires the
    type-level ``Pset_*TypeCommon`` to recognise an IFC element as a
    real MEP component — without it, even a correctly-classified
    IfcCableCarrierSegmentType is treated as a generic proxy and the
    convert command silently skips it.

    We populate ``Reference`` (the only field strictly required by the
    type-detection heuristic) with the predefined-type token so the
    PSet carries a non-null payload. Other optional fields
    (``Status``, ``WorkingTemperatureRange``, ``HeightExternal``,
    ``WidthExternal``) are left unset; downstream tools fill those
    when more detail is available.
    """
    pset = ifcopenshell.api.run(
        "pset.add_pset", ifc, product=type_object, name=pset_name
    )
    ifcopenshell.api.run(
        "pset.edit_pset", ifc, pset=pset, properties={"Reference": reference}
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
    _attach_type_common_pset(
        ifc, seg_type, "Pset_CableCarrierSegmentTypeCommon", requested_type
    )
    return seg_type


def _ensure_cooling_equipment_type(
    ifc, mapped_ifc_class: str, *, predefined: str = "USERDEFINED", element_type: str | None = None
) -> object:
    """Return (creating once per file) an Ifc(Evaporator|Condenser|Compressor)Type
    with the matching ``Pset_*TypeCommon`` attached.

    MagiCAD's "Convert to MagiCAD object" command needs both the type
    object AND the type-level common PSet — without the PSet the type
    is treated as a generic proxy and the convert silently skips. We
    populate ``Reference`` with ``element_type`` (defaults to the IFC
    occurrence class name, e.g. "IfcEvaporator") so the PSet is
    non-empty.
    """
    type_class = mapped_ifc_class + "Type"
    ref = element_type or mapped_ifc_class
    for t in ifc.by_type(type_class):
        if predefined == "USERDEFINED":
            if t.PredefinedType == "USERDEFINED" and t.ElementType == ref:
                return t
        elif t.PredefinedType == predefined:
            return t

    type_obj = ifcopenshell.api.run(
        "root.create_entity",
        ifc,
        ifc_class=type_class,
        name=f"{type_class}_{ref}",
        predefined_type=predefined,
    )
    if predefined == "USERDEFINED":
        type_obj.ElementType = ref
    pset_name = f"Pset_{mapped_ifc_class[3:]}TypeCommon"  # IfcEvaporator -> Pset_EvaporatorTypeCommon
    _attach_type_common_pset(ifc, type_obj, pset_name, ref)
    return type_obj


def _ensure_proxy_type(ifc, *, element_type: str) -> object:
    """Return (creating once per element_type) an IfcBuildingElementProxyType
    with Pset_BuildingElementProxyTypeCommon attached.

    Same MagiCAD-recognition trick as for pipes / cable carriers /
    cooling equipment: a proxy without a typed Pset_*TypeCommon falls
    through MagiCAD's import filter as "unknown geometry".
    """
    for t in ifc.by_type("IfcBuildingElementProxyType"):
        if t.PredefinedType == "USERDEFINED" and t.ElementType == element_type:
            return t

    type_obj = ifcopenshell.api.run(
        "root.create_entity",
        ifc,
        ifc_class="IfcBuildingElementProxyType",
        name=f"BuildingElementProxyType_{element_type}",
        predefined_type="USERDEFINED",
    )
    type_obj.ElementType = element_type
    _attach_type_common_pset(
        ifc, type_obj, "Pset_BuildingElementProxyTypeCommon", element_type
    )
    return type_obj


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
    _attach_type_common_pset(
        ifc, pipe_type, "Pset_PipeSegmentTypeCommon", requested_type
    )
    return pipe_type
