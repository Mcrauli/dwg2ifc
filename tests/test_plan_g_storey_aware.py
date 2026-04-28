"""Plan G Task 11: every ``add_*`` writer routes the resulting product to
the storey passed via ``parent_storey``. Two-storey skeleton + per-add_*
placement → IfcRelContainedInSpatialStructure.RelatingStructure check."""

from __future__ import annotations

from dxf2ifc.core.ifc_writer import (
    add_building_element_proxy,
    add_cable_carrier_segment,
    add_cooling_equipment,
    add_door,
    add_furniture,
    add_pipe_segment,
    add_slab,
    add_wall,
    add_window,
    build_ifc_project_skeleton,
)
from dxf2ifc.core.types import (
    BlockInstance,
    LineGeometry,
    MappedEntity,
    Point3D,
    PolygonGeometry,
)


def _two_storey_skeleton():
    return build_ifc_project_skeleton(
        project_name="Storey Aware",
        storey_z_levels_mm=[0.0, 3500.0],
    )


def _container_for(skeleton, product) -> object:
    rels = [
        r
        for r in skeleton.by_type("IfcRelContainedInSpatialStructure")
        if product in r.RelatedElements
    ]
    assert len(rels) == 1, f"expected exactly one container for {product}, got {len(rels)}"
    return rels[0].RelatingStructure


def test_add_wall_routes_to_target_storey():
    skeleton = _two_storey_skeleton()
    target = skeleton.storeys[1]
    mapped = MappedEntity(
        layer="KYL-ULKOSEINA",
        dxf_type="LINE",
        geometry=LineGeometry(start=Point3D(0, 0, 0), end=Point3D(5000, 0, 0)),
        ifc_type="IfcWall",
        predefined_type="STANDARD",
        talo2000_code="1241",
        talo2000_name="Ulkoseinät",
        extra_props={"default_height_mm": 3000, "default_thickness_mm": 200},
    )
    wall = add_wall(skeleton.file, mapped, parent_storey=target)
    assert _container_for(skeleton, wall) == target


def test_add_slab_routes_to_target_storey():
    skeleton = _two_storey_skeleton()
    target = skeleton.storeys[0]
    mapped = MappedEntity(
        layer="KYL-ALAPOHJA",
        dxf_type="LWPOLYLINE",
        geometry=PolygonGeometry(
            vertices=(
                Point3D(0, 0, 0),
                Point3D(4000, 0, 0),
                Point3D(4000, 3000, 0),
                Point3D(0, 3000, 0),
            ),
            closed=True,
        ),
        ifc_type="IfcSlab",
        predefined_type="FLOOR",
        talo2000_code="1221",
        talo2000_name="Alapohjalaatat",
        extra_props={"default_thickness_mm": 200.0},
    )
    slab = add_slab(skeleton.file, mapped, parent_storey=target)
    assert _container_for(skeleton, slab) == target


def _block_mapped(layer: str, ifc_type: str, **extra) -> MappedEntity:
    return MappedEntity(
        layer=layer,
        dxf_type="INSERT",
        geometry=BlockInstance(insertion_point=Point3D(1000, 1000, 0)),
        ifc_type=ifc_type,
        predefined_type=None,
        talo2000_code=None,
        talo2000_name=None,
        extra_props=dict(extra),
    )


def test_add_door_routes_to_target_storey():
    skeleton = _two_storey_skeleton()
    target = skeleton.storeys[1]
    door = add_door(
        skeleton.file,
        _block_mapped("KYL-OVET-ULKO", "IfcDoor", default_width_mm=900, default_height_mm=2100),
        parent_storey=target,
    )
    assert _container_for(skeleton, door) == target


def test_add_window_routes_to_target_storey():
    skeleton = _two_storey_skeleton()
    target = skeleton.storeys[0]
    window = add_window(
        skeleton.file,
        _block_mapped("KYL-IKKUNA", "IfcWindow", default_width_mm=1200, default_height_mm=1500),
        parent_storey=target,
    )
    assert _container_for(skeleton, window) == target


def test_add_pipe_segment_routes_to_target_storey():
    skeleton = _two_storey_skeleton()
    target = skeleton.storeys[1]
    mapped = MappedEntity(
        layer="LT IMU",
        dxf_type="LINE",
        geometry=LineGeometry(start=Point3D(0, 0, 3500), end=Point3D(2000, 0, 3500)),
        ifc_type="IfcPipeSegment",
        predefined_type="REFRIGERATION",
        talo2000_code="2151",
        talo2000_name="Imuputki",
        extra_props={"default_diameter_mm": 35.0},
    )
    pipe = add_pipe_segment(skeleton.file, mapped, parent_storey=target)
    assert _container_for(skeleton, pipe) == target


def test_add_furniture_routes_to_target_storey():
    skeleton = _two_storey_skeleton()
    target = skeleton.storeys[0]
    furniture = add_furniture(
        skeleton.file,
        _block_mapped(
            "KYL-LEVYHYLLY",
            "IfcFurniture",
            default_width_mm=800,
            default_depth_mm=400,
            default_height_mm=60,
        ),
        parent_storey=target,
    )
    assert _container_for(skeleton, furniture) == target


def test_add_cable_carrier_segment_routes_to_target_storey():
    skeleton = _two_storey_skeleton()
    target = skeleton.storeys[1]
    mapped = MappedEntity(
        layer="KAAPELIHYLLY",
        dxf_type="LINE",
        geometry=LineGeometry(start=Point3D(0, 0, 3500), end=Point3D(3000, 0, 3500)),
        ifc_type="IfcCableCarrierSegment",
        predefined_type="CABLETRUNKINGSEGMENT",
        talo2000_code="2380",
        talo2000_name="Kaapelihylly",
        extra_props={"default_width_mm": 200.0, "default_height_mm": 60.0},
    )
    seg = add_cable_carrier_segment(skeleton.file, mapped, parent_storey=target)
    assert _container_for(skeleton, seg) == target


def test_add_building_element_proxy_routes_to_target_storey():
    skeleton = _two_storey_skeleton()
    target = skeleton.storeys[0]
    mapped = MappedEntity(
        layer="KYL-LEVY",
        dxf_type="LWPOLYLINE",
        geometry=PolygonGeometry(
            vertices=(
                Point3D(0, 0, 0),
                Point3D(2400, 0, 0),
                Point3D(2400, 60, 0),
                Point3D(0, 60, 0),
            ),
            closed=True,
        ),
        ifc_type="IfcBuildingElementProxy",
        predefined_type=None,
        talo2000_code="1352",
        talo2000_name="Kylmähuone-elementit",
        extra_props={"default_height_mm": 2400.0},
    )
    proxy = add_building_element_proxy(skeleton.file, mapped, parent_storey=target)
    assert _container_for(skeleton, proxy) == target


def test_add_cooling_equipment_routes_to_target_storey():
    skeleton = _two_storey_skeleton()
    target = skeleton.storeys[1]
    evap = add_cooling_equipment(
        skeleton.file,
        _block_mapped(
            "KYL-HOYRYSTIN",
            "IfcEvaporator",
            default_width_mm=800,
            default_depth_mm=600,
            default_height_mm=400,
        ),
        parent_storey=target,
    )
    assert _container_for(skeleton, evap) == target
