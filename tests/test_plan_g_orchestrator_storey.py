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
