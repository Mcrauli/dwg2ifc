"""SUPPORTED_IFC_TYPES must stay in sync with the orchestrator dispatch.

The profile editor's IFC-type dropdown is sourced from this tuple. If a
type is offered in the GUI but the orchestrator has no branch for it, a
rule using it would silently produce nothing — so the tuple is pinned
to exactly the set the dispatch loop handles.
"""

from __future__ import annotations


def test_supported_ifc_types_matches_orchestrator_dispatch():
    from dwg2ifc.core.ifc_writer.builders import (
        SUPPORTED_IFC_TYPES,
        _COOLING_EQUIPMENT_CLASSES,
        _DISTRIBUTION_ELEMENT_CLASSES,
    )

    base = {
        "IfcWall",
        "IfcSlab",
        "IfcDoor",
        "IfcWindow",
        "IfcPipeSegment",
        "IfcCableCarrierSegment",
        "IfcFurniture",
        "IfcBuildingElementProxy",
    }
    expected = (
        base
        | set(_COOLING_EQUIPMENT_CLASSES)
        | {"IfcTank", "IfcFlowController"}
        | set(_DISTRIBUTION_ELEMENT_CLASSES)
    )
    assert set(SUPPORTED_IFC_TYPES) == expected


def test_supported_ifc_types_has_no_duplicates():
    from dwg2ifc.core.ifc_writer.builders import SUPPORTED_IFC_TYPES

    assert len(SUPPORTED_IFC_TYPES) == len(set(SUPPORTED_IFC_TYPES))
