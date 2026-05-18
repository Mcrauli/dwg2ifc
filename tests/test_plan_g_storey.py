"""Plan G Task 8: build_ifc_project_skeleton creates Site → Building →
list[BuildingStorey] driven by ``storey_z_levels_mm`` and wires up an
IfcLocalPlacement chain Site → Building → Storey with Storey-Z taken from
the level value."""

from __future__ import annotations

from dwg2ifc.core.ifc_writer import build_ifc_project_skeleton


def test_default_skeleton_has_one_storey_named_kerros1():
    ifc = build_ifc_project_skeleton(project_name="Default")
    storeys = ifc.by_type("IfcBuildingStorey")
    assert len(storeys) == 1
    assert storeys[0].Name == "Kerros 1"
    location = storeys[0].ObjectPlacement.RelativePlacement.Location.Coordinates
    assert location[2] == 0.0


def test_three_storey_skeleton_named_and_placed():
    ifc = build_ifc_project_skeleton(
        project_name="Three Storeys",
        storey_z_levels_mm=[0.0, 3500.0, 7000.0],
    )
    storeys = ifc.by_type("IfcBuildingStorey")
    assert len(storeys) == 3
    assert [s.Name for s in storeys] == ["Kerros 1", "Kerros 2", "Kerros 3"]
    z_levels = [s.ObjectPlacement.RelativePlacement.Location.Coordinates[2] for s in storeys]
    assert z_levels == [0.0, 3500.0, 7000.0]


def test_storey_local_placement_chain_relto_site_building():
    """Site placement has no parent. Building placement is RelTo Site.
    Each Storey placement is RelTo Building."""
    ifc = build_ifc_project_skeleton(
        project_name="Chain",
        storey_z_levels_mm=[0.0, 3500.0],
    )
    site = ifc.by_type("IfcSite")[0]
    building = ifc.by_type("IfcBuilding")[0]
    storeys = ifc.by_type("IfcBuildingStorey")

    assert site.ObjectPlacement is not None
    assert site.ObjectPlacement.PlacementRelTo is None

    assert building.ObjectPlacement is not None
    assert building.ObjectPlacement.PlacementRelTo == site.ObjectPlacement

    for storey in storeys:
        assert storey.ObjectPlacement is not None
        assert storey.ObjectPlacement.PlacementRelTo == building.ObjectPlacement


def test_storey_elevation_attribute_matches_z_level():
    """IfcBuildingStorey.Elevation should mirror the z-level in mm."""
    ifc = build_ifc_project_skeleton(
        project_name="Elevation",
        storey_z_levels_mm=[0.0, 3500.0],
    )
    storeys = ifc.by_type("IfcBuildingStorey")
    assert storeys[0].Elevation == 0.0
    assert storeys[1].Elevation == 3500.0
