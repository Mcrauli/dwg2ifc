"""Plan G Task 12: ``convert_dxf`` resolves each MappedEntity to a storey
based on its anchor-Z (LineGeometry → min(start.z, end.z), PolygonGeometry
→ min(p.z), BlockInstance → insertion_point.z) using the profile's
``storey_z_levels_mm``."""

from __future__ import annotations

from pathlib import Path

import ezdxf

from dxf2ifc.core.ifc_writer import convert_dxf
from dxf2ifc.profiles.loader import load_default_profile


def _two_storey_dxf(tmp_path: Path) -> Path:
    """Two pipe lines, one at z=0 and one at z=3500."""
    doc = ezdxf.new("R2010")
    doc.layers.add(name="LT IMU")
    msp = doc.modelspace()
    msp.add_line((0.0, 0.0, 0.0), (2000.0, 0.0, 0.0), dxfattribs={"layer": "LT IMU"})
    msp.add_line(
        (0.0, 1000.0, 3500.0),
        (2000.0, 1000.0, 3500.0),
        dxfattribs={"layer": "LT IMU"},
    )
    out = tmp_path / "two_storey.dxf"
    doc.saveas(out)
    return out


def test_orchestrator_routes_pipes_to_anchor_z_storey(tmp_path: Path):
    profile = load_default_profile()
    profile = profile.model_copy(update={"storey_z_levels_mm": [0.0, 3500.0]})

    dxf_path = _two_storey_dxf(tmp_path)
    out_path = tmp_path / "two_storey.ifc"
    convert_dxf(
        dxf_path=dxf_path,
        output_path=out_path,
        profile=profile,
        project_name="Two Storey",
    )

    import ifcopenshell

    ifc = ifcopenshell.open(str(out_path))
    storeys = sorted(ifc.by_type("IfcBuildingStorey"), key=lambda s: s.Elevation)
    assert len(storeys) == 2

    pipes = ifc.by_type("IfcPipeSegment")
    assert len(pipes) == 2

    # Inspect each pipe: low pipe → storeys[0], high pipe → storeys[1]
    by_z = {}
    for pipe in pipes:
        rel = next(
            r for r in ifc.by_type("IfcRelContainedInSpatialStructure") if pipe in r.RelatedElements
        )
        by_z[rel.RelatingStructure.Elevation] = pipe

    assert set(by_z.keys()) == {0.0, 3500.0}


def _absolute_placement_z(placement) -> float:
    """Sum the Z components of a placement chain to get world-absolute Z.

    IFC builds placements relative to a parent (here: pipe relative to
    its storey, storey relative to building, building to site). Any
    consumer that wants the world-absolute coordinate must walk
    ``PlacementRelTo`` until ``None`` and add up Location.Z at each
    step.
    """
    z = 0.0
    cursor = placement
    while cursor is not None:
        z += float(cursor.RelativePlacement.Location.Coordinates[2])
        cursor = cursor.PlacementRelTo
    return z


def test_orchestrator_floor_elevation_shifts_pipe_to_absolute_z(tmp_path: Path):
    """floor_elevation_mm must reach element placements, not just storey
    Elevation. A pipe drawn at DXF Z=3000 with floor_elevation_mm=12000
    should land at IFC absolute Z=15000 once the placement chain is
    fully resolved (storey contributes 12000, pipe contributes 3000
    relative to the storey)."""
    import ezdxf

    doc = ezdxf.new("R2010")
    doc.layers.add(name="LT IMU")
    msp = doc.modelspace()
    msp.add_line(
        (0.0, 0.0, 3000.0),
        (2000.0, 0.0, 3000.0),
        dxfattribs={"layer": "LT IMU"},
    )
    dxf_path = tmp_path / "shifted.dxf"
    doc.saveas(dxf_path)

    profile = load_default_profile()
    out_path = tmp_path / "shifted.ifc"
    convert_dxf(
        dxf_path=dxf_path,
        output_path=out_path,
        profile=profile,
        project_name="Shifted",
        floor_elevation_mm=12000.0,
    )

    import ifcopenshell

    ifc = ifcopenshell.open(str(out_path))
    pipes = ifc.by_type("IfcPipeSegment")
    assert len(pipes) == 1
    pipe = pipes[0]
    assert _absolute_placement_z(pipe.ObjectPlacement) == 15000.0
    # The pipe's storey-relative Z should equal the original DXF Z —
    # i.e. "3 m above the ground floor". This is what Solibri shows on
    # the storey-relative views.
    assert pipe.ObjectPlacement.RelativePlacement.Location.Coordinates[2] == 3000.0
    # And storey absolute Z is exactly the floor_elevation_mm.
    storey = ifc.by_type("IfcBuildingStorey")[0]
    assert storey.Elevation == 12000.0


def test_orchestrator_floor_elevation_zero_leaves_placement_unchanged(
    tmp_path: Path,
):
    import ezdxf

    doc = ezdxf.new("R2010")
    doc.layers.add(name="LT IMU")
    msp = doc.modelspace()
    msp.add_line(
        (0.0, 0.0, 3000.0),
        (2000.0, 0.0, 3000.0),
        dxfattribs={"layer": "LT IMU"},
    )
    dxf_path = tmp_path / "no_offset.dxf"
    doc.saveas(dxf_path)

    profile = load_default_profile()
    out_path = tmp_path / "no_offset.ifc"
    convert_dxf(
        dxf_path=dxf_path,
        output_path=out_path,
        profile=profile,
        project_name="No Offset",
    )

    import ifcopenshell

    ifc = ifcopenshell.open(str(out_path))
    pipe = ifc.by_type("IfcPipeSegment")[0]
    assert _absolute_placement_z(pipe.ObjectPlacement) == 3000.0
