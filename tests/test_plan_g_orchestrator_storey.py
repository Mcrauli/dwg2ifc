"""Floor-elevation Z-offset behaviour for convert_dxf (single-file shim).

The anchor-Z routing test that used to live here is gone — storey
assignment is now per-file (FileEntry.storey_index), not per-anchor-Z.
Multi-floor coverage lives in tests/test_orchestrator_multi_floor.py.
"""

from __future__ import annotations

from pathlib import Path

import ezdxf

from dxf2ifc.core.ifc_writer import convert_dxf
from dxf2ifc.profiles.loader import load_default_profile


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
    """floor_elevation_mm lifts element geometry, not just the storey
    Elevation. A pipe drawn at DXF Z=3000 with floor_elevation_mm=12000
    lands at IFC absolute Z=15000 once the placement chain is fully
    resolved (storey contributes 12000, pipe contributes 3000 relative to
    the storey)."""
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
    # The pipe's storey-relative Z equals the original DXF Z — i.e.
    # "3 m above the floor". This is what Solibri shows on storey views.
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
