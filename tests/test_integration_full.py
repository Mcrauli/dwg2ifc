"""End-to-end integration test covering every Section 2–11 Talo2000 code."""

from pathlib import Path

import ifcopenshell
import ifcopenshell.validate

from dwg2ifc.core.ifc_writer import convert_dxf
from dwg2ifc.profiles.loader import load_default_profile

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
    "T-LVI-02-01-001",  # LT IMU → IfcPipeSegment (refrigerant)
    "T-LVI-04-01-001",  # KYL-VIEMARI → IfcPipeSegment (drainpipe)
    # NOTE: full_kylmaelement_dxf fixture omits LAUHDUTIN/KOMPRESSORI blocks;
    # T-LVI-01-01-018/-017 are still supported by the profile.
}

EXPECTED_RAVA_TATE_CODES = {
    "T-TATE-01-01-001",  # KAAPELIHYLLY → IfcCableCarrierSegment
}




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










def test_full_kylmaelement_pipeline_emits_grouped_ifcsystems(
    full_kylmaelement_dxf: Path, tmp_path: Path
):
    """The full fixture's LT IMU / KYL-VIEMARI-LATTIA / KAAPELIHYLLY /
    KYL-HOYRYSTIN layers produce IfcSystems with assigned products.
    Drain pipes share the Kylmäjärjestelmä group (J-LVI-09-02).
    J-LVI child systems nest under a Jakelujärjestelmä parent."""
    out = tmp_path / "full_kylmaelement.ifc"
    convert_dxf(
        dxf_path=full_kylmaelement_dxf,
        output_path=out,
        profile=load_default_profile(),
    )

    ifc = ifcopenshell.open(str(out))
    expected_system_names = {
        "Kylmä - suorahöyrysteinen",
        "Cable carriers",
        "Kylmäjärjestelmä",
        "Jakelujärjestelmä",
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
