"""Plan F Task 6: solibri_reference_full.ifc fixture loads and exposes the
same Talo2000 + IFC-class coverage as Plan B's full-fixture pipeline."""

from __future__ import annotations

from pathlib import Path

import ifcopenshell

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "solibri_reference_full.ifc"

EXPECTED_TALO2000_CODES = {
    "1241",
    "1311",
    "1221",
    "1243",
    "1242",
    "2151",
    "2160",
    "1331",
    "2380",
    "1352",
    "2510",
}


def test_reference_ifc_exists():
    assert FIXTURE_PATH.is_file(), f"missing {FIXTURE_PATH}"


def test_reference_ifc_loads_as_ifc4():
    ifc = ifcopenshell.open(str(FIXTURE_PATH))
    assert ifc.schema == "IFC4"


def test_reference_ifc_covers_every_required_talo2000_code():
    ifc = ifcopenshell.open(str(FIXTURE_PATH))
    refs = {r.Identification for r in ifc.by_type("IfcClassificationReference")}
    missing = EXPECTED_TALO2000_CODES - refs
    assert not missing, f"missing Talo2000 codes: {sorted(missing)}"


def test_reference_ifc_covers_each_required_ifc_class():
    ifc = ifcopenshell.open(str(FIXTURE_PATH))
    for ifc_class in (
        "IfcWall",
        "IfcSlab",
        "IfcDoor",
        "IfcWindow",
        "IfcPipeSegment",
        "IfcFurniture",
        "IfcCableCarrierSegment",
        "IfcBuildingElementProxy",
        "IfcEvaporator",
    ):
        assert ifc.by_type(ifc_class), f"no {ifc_class} entities in reference IFC"
