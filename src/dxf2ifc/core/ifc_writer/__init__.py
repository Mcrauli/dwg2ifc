"""ifc_writer package facade -- re-exports the public API.

Splitting was a pure refactor: the implementation moved from a single
1908-line ``core/ifc_writer.py`` into focused modules. Every public
symbol stays importable as ``dxf2ifc.core.ifc_writer.X`` so neither
callers nor tests need updates.
"""

from dxf2ifc.core.ifc_writer.builders import (
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
    add_talo2000_classification,
)
from dxf2ifc.core.ifc_writer.mesh import _mesh_to_brep  # noqa: F401 — tests import this
from dxf2ifc.core.ifc_writer.orchestrator import convert_dxf
from dxf2ifc.core.ifc_writer.skeleton import (
    IfcSkeleton,
    build_ifc_project_skeleton,
    resolve_storey,
    validate_local_extent,
)

__all__ = [
    "convert_dxf",
    "build_ifc_project_skeleton",
    "IfcSkeleton",
    "resolve_storey",
    "validate_local_extent",
    "write_ifc",
    "add_wall",
    "add_slab",
    "add_door",
    "add_window",
    "add_pipe_segment",
    "add_furniture",
    "add_cable_carrier",
    "add_cable_carrier_segment",
    "add_building_element_proxy",
    "add_cooling_equipment",
    "add_tank",
    "add_flow_controller",
    "add_system",
    "assign_to_system",
    "add_classification",
    "add_discipline_classification",
    "add_talo2000_classification",
]
