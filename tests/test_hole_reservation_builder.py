import ifcopenshell.guid

from dwg2ifc.core.ifc_writer.builders import add_provision_for_void
from dwg2ifc.core.ifc_writer.skeleton import build_ifc_project_skeleton
from dwg2ifc.core.types import BlockInstance, MappedEntity, Point3D


def _hole_reservation_mapped_entity() -> MappedEntity:
    return MappedEntity(
        layer="KYL-REIKAVARAUS",
        dxf_type="INSERT",
        geometry=BlockInstance(insertion_point=Point3D(1000.0, 2000.0, 3000.0)),
        block_name="REIKAVARAUS",
        handle="ABCD",
        ifc_type="IfcProvisionForVoid",
        talotekniikka_code="T-TATE-02-01-001",
        fi_komponentti={"yleisnimi": "Reikavaraus", "yleistunnus": "RV"},
        extra_props={
            "guid": "550e8400-e29b-41d4-a716-446655440000",
            "varaus_tyyppi": "LATTIA",
            "halkaisija_mm": 200.0,
            "pituus_mm": 300.0,
            "korko_mm": 2850.0,
        },
    )


def test_hole_reservation_guid_is_derived_from_block_guid():
    skeleton = build_ifc_project_skeleton(project_name="Hole Test", schema="IFC4")
    product = add_provision_for_void(
        skeleton.file,
        _hole_reservation_mapped_entity(),
        parent_storey=skeleton.storeys[0],
    )

    assert product.GlobalId == ifcopenshell.guid.compress(
        "550e8400-e29b-41d4-a716-446655440000"
    )


def test_floor_hole_reservation_creates_hole_reservation_body():
    skeleton = build_ifc_project_skeleton(project_name="Hole Test", schema="IFC4")
    product = add_provision_for_void(
        skeleton.file,
        _hole_reservation_mapped_entity(),
        parent_storey=skeleton.storeys[0],
    )

    assert product.is_a("IfcBuildingElementProxy")
    assert product.ObjectType == "IfcProvisionForVoid"
    assert product.Representation is not None
