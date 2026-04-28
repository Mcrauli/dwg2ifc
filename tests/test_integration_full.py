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
    # KYL-HOYRYSTIN/LAUHDUTIN/KOMPRESSORI moved to TATE domain (RAVA LVI-TUOTEOSA)
    # in Plan H Task 13. Their classification appears under IfcClassification
    # "RAVA-LVI" rather than "Talo2000" — covered by Plan H integration tests.
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


def test_full_kylmaelement_pipeline_emits_four_grouped_ifcsystems(
    full_kylmaelement_dxf: Path, tmp_path: Path
):
    """Plan C Task 11: the full fixture's LT IMU / KYL-VIEMARI-LATTIA /
    KAAPELIHYLLY / KYL-HOYRYSTIN layers each produce one IfcSystem with
    at least one assigned product via IfcRelAssignsToGroup."""
    out = tmp_path / "full_kylmaelement.ifc"
    convert_dxf(
        dxf_path=full_kylmaelement_dxf,
        output_path=out,
        profile=load_default_profile(),
    )

    ifc = ifcopenshell.open(str(out))
    expected_system_names = {
        "Refrigeration LT",
        "Drainage",
        "Cable carriers",
        "Refrigeration plant",
    }
    actual_systems = {s.Name: s for s in ifc.by_type("IfcSystem")}
    missing = expected_system_names - actual_systems.keys()
    assert not missing, f"missing IfcSystem names: {sorted(missing)}"

    members_by_system: dict[str, list] = {name: [] for name in expected_system_names}
    for rel in ifc.by_type("IfcRelAssignsToGroup"):
        group = rel.RelatingGroup
        if group.is_a("IfcSystem") and group.Name in members_by_system:
            members_by_system[group.Name].extend(rel.RelatedObjects)

    for name in expected_system_names:
        assert members_by_system[name], f"IfcSystem '{name}' has no members"
