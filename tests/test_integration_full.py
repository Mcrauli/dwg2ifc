"""End-to-end integration test covering every Section 2–11 Talo2000 code."""

from pathlib import Path

import ifcopenshell
import ifcopenshell.validate

from dxf2ifc.core.ifc_writer import convert_dxf
from dxf2ifc.profiles.loader import load_default_profile

EXPECTED_TALO2000_CODES = {
    "1241",  # KYL-ULKOSEINA → IfcWall
    "1311",  # KYL-VALISEINA → IfcWall (PARTITIONING)
    "1221",  # KYL-ALAPOHJA → IfcSlab (FLOOR)
    "1243",  # KYL-OVET-ULKO → IfcDoor
    "1242",  # KYL-IKKUNA → IfcWindow
    "2151",  # LT IMU → IfcPipeSegment (refrigeration)
    "2160",  # KYL-VIEMARI → IfcPipeSegment (drainpipe)
    "1331",  # KYL-LEVYHYLLY → IfcFurniture
    "2380",  # KAAPELIHYLLY → IfcCableCarrierSegment
    "1352",  # KYL-LEVY → IfcBuildingElementProxy
    "2510",  # KYL-HOYRYSTIN → IfcEvaporator
}


def test_full_kylmaelement_pipeline_emits_all_talo2000_codes(
    full_kylmaelement_dxf: Path, tmp_path: Path
):
    out = tmp_path / "full_kylmaelement.ifc"

    convert_dxf(
        dxf_path=full_kylmaelement_dxf,
        output_path=out,
        profile=load_default_profile(),
    )

    ifc = ifcopenshell.open(str(out))
    assert ifc.schema == "IFC4"

    codes = {r.Identification for r in ifc.by_type("IfcClassificationReference")}
    missing = EXPECTED_TALO2000_CODES - codes
    assert not missing, f"missing Talo2000 codes: {sorted(missing)}"

    classifications = ifc.by_type("IfcClassification")
    assert any(c.Name == "Talo2000" for c in classifications)


def test_full_kylmaelement_pipeline_passes_ifcopenshell_validate(
    full_kylmaelement_dxf: Path, tmp_path: Path
):
    out = tmp_path / "full_kylmaelement.ifc"
    convert_dxf(
        dxf_path=full_kylmaelement_dxf,
        output_path=out,
        profile=load_default_profile(),
    )

    ifc = ifcopenshell.open(str(out))
    logger = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(ifc, logger=logger)
    errors = [e for e in logger.statements if e.get("level") == "ERROR"]
    assert errors == [], f"IFC validation errors: {errors}"


def test_full_kylmaelement_pipeline_emits_each_ifc_class(
    full_kylmaelement_dxf: Path, tmp_path: Path
):
    out = tmp_path / "full_kylmaelement.ifc"
    convert_dxf(
        dxf_path=full_kylmaelement_dxf,
        output_path=out,
        profile=load_default_profile(),
    )

    ifc = ifcopenshell.open(str(out))
    expected_classes = [
        "IfcWall",
        "IfcSlab",
        "IfcDoor",
        "IfcWindow",
        "IfcPipeSegment",
        "IfcFurniture",
        "IfcCableCarrierSegment",
        "IfcBuildingElementProxy",
        "IfcEvaporator",
    ]
    for ifc_class in expected_classes:
        assert ifc.by_type(ifc_class), f"expected at least one {ifc_class}"
