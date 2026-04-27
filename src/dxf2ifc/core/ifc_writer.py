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

from dxf2ifc.core.geometry import line_to_wall_extrusion
from dxf2ifc.core.types import LineGeometry, MappedEntity


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

    site = ifcopenshell.api.run(
        "root.create_entity", ifc, ifc_class="IfcSite", name=site_name
    )
    building = ifcopenshell.api.run(
        "root.create_entity", ifc, ifc_class="IfcBuilding", name=building_name
    )
    storey = ifcopenshell.api.run(
        "root.create_entity", ifc, ifc_class="IfcBuildingStorey", name=storey_name
    )
    ifcopenshell.api.run(
        "aggregate.assign_object", ifc, products=[site], relating_object=project
    )
    ifcopenshell.api.run(
        "aggregate.assign_object", ifc, products=[building], relating_object=site
    )
    ifcopenshell.api.run(
        "aggregate.assign_object", ifc, products=[storey], relating_object=building
    )
    return ifc


def write_ifc(ifc: ifcopenshell.file, output_path: str | Path) -> None:
    """Write the IFC file to disk."""
    ifc.write(str(output_path))


def add_wall(ifc, mapped: MappedEntity, *, parent_storey) -> object:
    """Create an IfcWall entity from a MappedEntity whose geometry is a
    LineGeometry. Adds extruded area solid representation and places it under
    parent_storey via IfcRelContainedInSpatialStructure.
    """
    if not isinstance(mapped.geometry, LineGeometry):
        raise TypeError(
            f"add_wall expects LineGeometry, got {type(mapped.geometry).__name__}"
        )

    height = float(mapped.extra_props.get("default_height_mm", 3000.0))
    thickness = float(mapped.extra_props.get("default_thickness_mm", 200.0))
    ext = line_to_wall_extrusion(
        mapped.geometry, thickness_mm=thickness, height_mm=height
    )

    wall = ifcopenshell.api.run(
        "root.create_entity",
        ifc,
        ifc_class="IfcWall",
        name=mapped.layer,
        predefined_type=mapped.predefined_type,
    )

    matrix = _z_rotation_matrix(
        ext.anchor.x, ext.anchor.y, ext.anchor.z, ext.angle_rad
    )
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
            Location=ifc.create_entity(
                "IfcCartesianPoint", Coordinates=(ext.length_mm / 2.0, 0.0)
            ),
        ),
        XDim=ext.length_mm,
        YDim=ext.thickness_mm,
    )
    extruded = ifc.create_entity(
        "IfcExtrudedAreaSolid",
        SweptArea=rect,
        Position=ifc.create_entity(
            "IfcAxis2Placement3D",
            Location=ifc.create_entity(
                "IfcCartesianPoint", Coordinates=(0.0, 0.0, 0.0)
            ),
        ),
        ExtrudedDirection=ifc.create_entity(
            "IfcDirection", DirectionRatios=(0.0, 0.0, 1.0)
        ),
        Depth=ext.height_mm,
    )
    shape = ifc.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=model_ctx,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=[extruded],
    )
    product_definition = ifc.create_entity(
        "IfcProductDefinitionShape", Representations=[shape]
    )
    wall.Representation = product_definition

    ifcopenshell.api.run(
        "spatial.assign_container",
        ifc,
        products=[wall],
        relating_structure=parent_storey,
    )
    return wall


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
