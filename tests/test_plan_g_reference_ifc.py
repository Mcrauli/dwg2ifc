"""Plan G Task 20: solibri_reference_full.ifc baseline now contains an
IfcProjectedCRS + IfcMapConversion (rebuild via
``python -m tools.solibri.build_reference_ifc`` with the Plan G
profile override) and validates cleanly."""

from __future__ import annotations

from pathlib import Path

import ifcopenshell

from dxf2ifc.core.quality import validate_ifc

REFERENCE_IFC = (
    Path(__file__).resolve().parent / "fixtures" / "solibri_reference_full.ifc"
)


def test_reference_ifc_has_projected_crs():
    ifc = ifcopenshell.open(str(REFERENCE_IFC))
    projected = ifc.by_type("IfcProjectedCRS")
    assert len(projected) == 1
    assert projected[0].Name == "EPSG:3067"


def test_reference_ifc_has_map_conversion():
    ifc = ifcopenshell.open(str(REFERENCE_IFC))
    conversions = ifc.by_type("IfcMapConversion")
    assert len(conversions) == 1
    assert conversions[0].Eastings == 25_496_000.0
    assert conversions[0].Northings == 6_672_000.0


def test_reference_ifc_validates_cleanly():
    report = validate_ifc(REFERENCE_IFC, expect_crs=True)
    crs_errors = [e for e in report.errors if e.get("type", "").startswith("crs_")]
    assert crs_errors == []
