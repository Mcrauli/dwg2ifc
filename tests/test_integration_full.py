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
    "1331",  # KYL-LEVYHYLLY → IfcFurniture
    "1352",  # KYL-LEVY → IfcBuildingElementProxy
}

EXPECTED_RAVA_LVI_CODES = {
    "T-LVI-01-01-023",  # KYL-HOYRYSTIN → IfcEvaporator
    "T-LVI-02",  # LT IMU → IfcPipeSegment (refrigerant)
    "T-LVI-04-01-001",  # KYL-VIEMARI → IfcPipeSegment (drainpipe)
    # NOTE: full_kylmaelement_dxf fixture omits LAUHDUTIN/KOMPRESSORI blocks;
    # T-LVI-01-01-018/-017 are still supported by the profile.
}

EXPECTED_RAVA_TATE_CODES = {
    "T-TATE-01-01-001",  # KAAPELIHYLLY → IfcCableCarrierSegment
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


def test_full_kylmaelement_pipeline_emits_rava_classifications(
    full_kylmaelement_dxf: Path, tmp_path: Path
):
    """Plan H Task 16: TATE-domain rules emit IfcClassification 'RAVA-LVI'
    (refrigerant pipes, drainpipe, cooling equipment) and 'RAVA-TATE'
    (cable carrier) alongside the existing 'Talo2000' classification."""
    out = tmp_path / "full_kylmaelement.ifc"
    convert_dxf(
        dxf_path=full_kylmaelement_dxf,
        output_path=out,
        profile=load_default_profile(),
    )

    ifc = ifcopenshell.open(str(out))
    classification_names = {c.Name for c in ifc.by_type("IfcClassification")}
    assert "Talo2000" in classification_names
    assert "RAVA-LVI" in classification_names
    assert "RAVA-TATE" in classification_names

    codes = {r.Identification for r in ifc.by_type("IfcClassificationReference")}
    missing_lvi = EXPECTED_RAVA_LVI_CODES - codes
    assert not missing_lvi, f"missing RAVA-LVI codes: {sorted(missing_lvi)}"
    missing_tate = EXPECTED_RAVA_TATE_CODES - codes
    assert not missing_tate, f"missing RAVA-TATE codes: {sorted(missing_tate)}"


def test_full_kylmaelement_pipeline_ifc4x3_emits_all_classifications(
    full_kylmaelement_dxf: Path, tmp_path: Path
):
    """Plan H Task 18: the IFC4X3 pipeline must emit the same Talo2000 +
    RAVA-LVI + RAVA-TATE classifications as the IFC4 pipeline."""
    out = tmp_path / "full_kylmaelement_ifc4x3.ifc"
    convert_dxf(
        dxf_path=full_kylmaelement_dxf,
        output_path=out,
        profile=load_default_profile(),
        schema="IFC4X3",
    )

    ifc = ifcopenshell.open(str(out))
    assert ifc.schema == "IFC4X3"

    classification_names = {c.Name for c in ifc.by_type("IfcClassification")}
    assert {"Talo2000", "RAVA-LVI", "RAVA-TATE"}.issubset(classification_names)

    codes = {r.Identification for r in ifc.by_type("IfcClassificationReference")}
    missing_ark = EXPECTED_TALO2000_CODES - codes
    missing_lvi = EXPECTED_RAVA_LVI_CODES - codes
    missing_tate = EXPECTED_RAVA_TATE_CODES - codes
    assert not missing_ark, f"missing Talo2000 codes (IFC4X3): {sorted(missing_ark)}"
    assert not missing_lvi, f"missing RAVA-LVI codes (IFC4X3): {sorted(missing_lvi)}"
    assert not missing_tate, f"missing RAVA-TATE codes (IFC4X3): {sorted(missing_tate)}"


def test_full_kylmaelement_pipeline_does_not_double_classify(
    full_kylmaelement_dxf: Path, tmp_path: Path
):
    """Plan H Task 16: every classified product carries exactly one
    IfcClassificationReference (no element belongs to both Talo2000 and
    a RAVA codeset)."""
    out = tmp_path / "full_kylmaelement.ifc"
    convert_dxf(
        dxf_path=full_kylmaelement_dxf,
        output_path=out,
        profile=load_default_profile(),
    )

    ifc = ifcopenshell.open(str(out))
    refs_per_product: dict[int, int] = {}
    for rel in ifc.by_type("IfcRelAssociatesClassification"):
        for product in rel.RelatedObjects:
            refs_per_product[product.id()] = refs_per_product.get(product.id(), 0) + 1
    over_classified = {pid: n for pid, n in refs_per_product.items() if n > 1}
    assert not over_classified, f"products with >1 classification: {over_classified}"


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
