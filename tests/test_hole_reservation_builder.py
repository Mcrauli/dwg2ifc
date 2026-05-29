import ifcopenshell.guid

from dwg2ifc.core.ifc_writer.builders import add_provision_for_void
from dwg2ifc.core.ifc_writer.skeleton import build_ifc_project_skeleton
from dwg2ifc.core.types import BlockInstance, MappedEntity, MeshGeometry, Point3D


def _hole_reservation_mapped_entity() -> MappedEntity:
    return MappedEntity(
        layer="KYL-REIKAVARAUS",
        dxf_type="INSERT",
        geometry=BlockInstance(insertion_point=Point3D(1000.0, 2000.0, 3000.0)),
        block_name="REIKAVARAUS",
        handle="ABCD",
        ifc_type="IfcBuildingElementProxy",
        predefined_type="PROVISIONFORVOID",
        talotekniikka_code="T-TATE-02-01-001",
        fi_komponentti={"yleisnimi": "Reikavaraus", "yleistunnus": "RV"},
        extra_props={
            "guid": "550e8400-e29b-41d4-a716-446655440000",
            "varaus_tyyppi": "LATTIA",
            "halkaisija_mm": 200.0,
            "pituus_mm": 300.0,
            "korko_mm": 2850.0,
            "system_name": "Refrigeration",
        },
    )


def _pset_props(product, name: str) -> dict[str, object]:
    rels = product.IsDefinedBy or []
    for rel in rels:
        if not rel.is_a("IfcRelDefinesByProperties"):
            continue
        pset = rel.RelatingPropertyDefinition
        if pset.is_a("IfcPropertySet") and pset.Name == name:
            return {
                p.Name: (p.NominalValue.wrappedValue if p.NominalValue else None)
                for p in pset.HasProperties
            }
    return {}


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
    assert product.PredefinedType == "PROVISIONFORVOID"
    assert product.Representation is not None
    pset = _pset_props(product, "Pset_ProvisionForVoid")
    assert pset["VoidShape"] == "Round"
    assert pset["Diameter"] == 200.0
    assert pset["Depth"] == 300.0
    assert pset["System"] == "Refrigeration"


def test_wall_hole_reservation_rotates_placement_axis_horizontal():
    skeleton = build_ifc_project_skeleton(project_name="Hole Test", schema="IFC4")
    mapped = _hole_reservation_mapped_entity()
    mapped.extra_props["varaus_tyyppi"] = "SEINA"
    product = add_provision_for_void(
        skeleton.file,
        mapped,
        parent_storey=skeleton.storeys[0],
    )

    body = product.Representation.Representations[0]
    solid = body.Items[0]
    assert tuple(solid.ExtrudedDirection.DirectionRatios) == (0.0, 0.0, 1.0)
    placement = product.ObjectPlacement.RelativePlacement
    axis = tuple(placement.Axis.DirectionRatios)
    assert axis == (1.0, 0.0, 0.0)


def test_hole_reservation_depth_includes_overrun_each_side():
    skeleton = build_ifc_project_skeleton(project_name="Hole Test", schema="IFC4")
    mapped = _hole_reservation_mapped_entity()
    mapped.extra_props["ylitys_mm"] = 10.0
    product = add_provision_for_void(
        skeleton.file,
        mapped,
        parent_storey=skeleton.storeys[0],
    )
    pset = _pset_props(product, "Pset_ProvisionForVoid")
    assert pset["Depth"] == 320.0
    assert pset["BaseDepth"] == 300.0
    assert pset["OverrunEachSide"] == 10.0


def test_hole_reservation_accepts_mesh_geometry_with_xdata_rotation():
    skeleton = build_ifc_project_skeleton(project_name="Hole Test", schema="IFC4")
    mapped = _hole_reservation_mapped_entity()
    mapped.geometry = MeshGeometry(
        vertices=(
            Point3D(0.0, 0.0, 0.0),
            Point3D(200.0, 0.0, 0.0),
            Point3D(200.0, 200.0, 300.0),
            Point3D(0.0, 200.0, 300.0),
        ),
        faces=((0, 1, 2, 3),),
        source="acis",
    )
    mapped.extra_props["kulma_rad"] = 1.0
    product = add_provision_for_void(
        skeleton.file,
        mapped,
        parent_storey=skeleton.storeys[0],
    )
    assert product.is_a("IfcBuildingElementProxy")
