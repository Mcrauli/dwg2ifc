"""Plan G Task 17: end-to-end CRS + multi-storey integration test.

Drives ``convert_dxf`` against the two-storey full-element DXF with a
profile carrying ``crs`` + ``storey_z_levels_mm=[0, 3500]`` and asserts:
- IfcSite + IfcProjectedCRS + IfcMapConversion are written,
- exactly two IfcBuildingStorey entities exist,
- each element ends up in the storey matching its anchor-Z.
"""

from __future__ import annotations

from pathlib import Path

import ifcopenshell

from dxf2ifc.core.ifc_writer import convert_dxf
from dxf2ifc.profiles.loader import load_default_profile
from dxf2ifc.profiles.schema import CRSConfig


def test_full_two_storey_with_crs_writes_site_crs_and_routes_by_z(
    full_kylmaelement_two_storey_dxf: Path, tmp_path: Path
):
    profile = load_default_profile()
    profile = profile.model_copy(
        update={
            "crs": CRSConfig(eastings_mm=25_496_000.0, northings_mm=6_672_000.0),
            "storey_z_levels_mm": [0.0, 3500.0],
        }
    )
    out = tmp_path / "two_storey_full.ifc"
    convert_dxf(
        dxf_path=full_kylmaelement_two_storey_dxf,
        output_path=out,
        profile=profile,
        project_name="Plan G E2E",
    )

    ifc = ifcopenshell.open(str(out))

    assert len(ifc.by_type("IfcSite")) == 1
    assert len(ifc.by_type("IfcProjectedCRS")) == 1
    assert len(ifc.by_type("IfcMapConversion")) == 1

    storeys = sorted(ifc.by_type("IfcBuildingStorey"), key=lambda s: s.Elevation)
    assert len(storeys) == 2
    assert storeys[0].Elevation == 0.0
    assert storeys[1].Elevation == 3500.0

    storey_for: dict[int, float] = {}
    for rel in ifc.by_type("IfcRelContainedInSpatialStructure"):
        z = rel.RelatingStructure.Elevation
        for product in rel.RelatedElements or ():
            storey_for[product.id()] = z

    # Storey 1 elements (anchor-Z = 0)
    for ifc_class in ("IfcWall", "IfcSlab", "IfcDoor", "IfcWindow", "IfcPipeSegment"):
        products = ifc.by_type(ifc_class)
        assert any(storey_for.get(p.id()) == 0.0 for p in products), (
            f"expected at least one {ifc_class} in storey 1 (z=0), "
            f"got placements {[storey_for.get(p.id()) for p in products]}"
        )

    # Storey 2 elements (anchor-Z = 3500)
    for ifc_class in ("IfcCableCarrierSegment", "IfcBuildingElementProxy", "IfcEvaporator"):
        products = ifc.by_type(ifc_class)
        assert products, f"expected at least one {ifc_class} in the IFC"
        assert any(storey_for.get(p.id()) == 3500.0 for p in products), (
            f"expected at least one {ifc_class} in storey 2 (z=3500), "
            f"got placements {[storey_for.get(p.id()) for p in products]}"
        )
