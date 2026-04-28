"""Plan G Task 9: ``resolve_storey(storeys, z_mm)`` returns the highest
storey whose elevation is ≤ z. Below the lowest storey it falls back to
storeys[0] (the lowest level)."""

from __future__ import annotations

from dxf2ifc.core.ifc_writer import build_ifc_project_skeleton, resolve_storey


def _three_storey_ifc():
    return build_ifc_project_skeleton(
        project_name="Resolve",
        storey_z_levels_mm=[0.0, 3500.0, 7000.0],
    )


def test_resolve_storey_lowest_z():
    ifc = _three_storey_ifc()
    storeys = ifc.by_type("IfcBuildingStorey")
    assert resolve_storey(storeys, 100.0) is storeys[0]


def test_resolve_storey_highest_z():
    ifc = _three_storey_ifc()
    storeys = ifc.by_type("IfcBuildingStorey")
    assert resolve_storey(storeys, 9999.0) is storeys[2]


def test_resolve_storey_middle_z():
    ifc = _three_storey_ifc()
    storeys = ifc.by_type("IfcBuildingStorey")
    assert resolve_storey(storeys, 4000.0) is storeys[1]


def test_resolve_storey_below_lowest_falls_back_to_first():
    ifc = _three_storey_ifc()
    storeys = ifc.by_type("IfcBuildingStorey")
    assert resolve_storey(storeys, -500.0) is storeys[0]


def test_resolve_storey_exactly_on_boundary_picks_that_storey():
    ifc = _three_storey_ifc()
    storeys = ifc.by_type("IfcBuildingStorey")
    assert resolve_storey(storeys, 3500.0) is storeys[1]
