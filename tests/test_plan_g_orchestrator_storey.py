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


def test_orchestrator_floor_elevation_does_not_shift_geometry(tmp_path: Path):
    """The storey-elevation field is the floor's BASE level — it must NOT
    shift element geometry. A pipe drawn at DXF Z=3000 with
    floor_elevation_mm=12000 keeps its raw CAD Z=3000 in absolute world
    space; the IfcBuildingStorey sits at 12000; the pipe's storey-relative
    placement is therefore 3000 − 12000 = −9000. This is the
    absolute-coordinate workflow: CAD Z is authoritative, the elevation
    field only labels where the storey datum sits."""
    import ezdxf

    doc = ezdxf.new("R2010")
    doc.layers.add(name="LT IMU")
    msp = doc.modelspace()
    msp.add_line(
        (0.0, 0.0, 3000.0),
        (2000.0, 0.0, 3000.0),
        dxfattribs={"layer": "LT IMU"},
    )
    dxf_path = tmp_path / "elevated.dxf"
    doc.saveas(dxf_path)

    profile = load_default_profile()
    out_path = tmp_path / "elevated.ifc"
    convert_dxf(
        dxf_path=dxf_path,
        output_path=out_path,
        profile=profile,
        project_name="Elevated",
        floor_elevation_mm=12000.0,
    )

    import ifcopenshell

    ifc = ifcopenshell.open(str(out_path))
    pipes = ifc.by_type("IfcPipeSegment")
    assert len(pipes) == 1
    pipe = pipes[0]
    # Object keeps its raw CAD Z — NOT shifted to 15000.
    assert _absolute_placement_z(pipe.ObjectPlacement) == 3000.0
    # Storey-relative placement = CAD Z − storey elevation = 3000 − 12000.
    assert pipe.ObjectPlacement.RelativePlacement.Location.Coordinates[2] == -9000.0
    # Storey sits at exactly the elevation the user entered.
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
