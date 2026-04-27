"""Generate an IFC file from MappedEntity objects.

Plan A covers: IfcProject/Site/Building/Storey hierarchy, IfcUnitAssignment
(millimetres), single IfcWall creation with classification reference.
Plan B extends with slabs, doors, windows, pipes, furniture, etc.
"""
from __future__ import annotations

from pathlib import Path

import ifcopenshell
import ifcopenshell.api


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
