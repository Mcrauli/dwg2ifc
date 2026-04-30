"""Unit tests for core.ifc_writer."""

from pathlib import Path

import ifcopenshell
import pytest

from dxf2ifc.core.ifc_writer import (
    _mesh_to_brep,
    add_building_element_proxy,
    add_cable_carrier,
    add_cable_carrier_segment,
    add_classification,
    add_cooling_equipment,
    add_door,
    add_furniture,
    add_pipe_segment,
    add_slab,
    add_system,
    add_talo2000_classification,
    add_wall,
    add_window,
    assign_to_system,
    build_ifc_project_skeleton,
    convert_dxf,
    write_ifc,
)
from dxf2ifc.core.types import (
    BlockInstance,
    LineGeometry,
    MappedEntity,
    MeshGeometry,
    Point3D,
    PolygonGeometry,
)
from dxf2ifc.profiles.loader import load_default_profile


def test_build_project_creates_ifc4_file_with_hierarchy(tmp_path: Path):
    ifc = build_ifc_project_skeleton(
        project_name="Test Project", site_name="Site", building_name="Cold Store"
    )
    assert ifc.schema == "IFC4"
    assert len(ifc.by_type("IfcProject")) == 1
    assert len(ifc.by_type("IfcSite")) == 1
    assert len(ifc.by_type("IfcBuilding")) == 1
    assert len(ifc.by_type("IfcBuildingStorey")) == 1


def test_build_project_without_crs_emits_no_projected_crs():
    ifc = build_ifc_project_skeleton(project_name="No CRS", crs=None)
    assert ifc.by_type("IfcProjectedCRS") == []
    assert ifc.by_type("IfcMapConversion") == []


def test_build_project_default_crs_kwarg_is_none():
    ifc = build_ifc_project_skeleton(project_name="Default CRS")
    assert ifc.by_type("IfcProjectedCRS") == []


def test_build_project_with_crs_emits_projected_crs_and_map_conversion():
    from dxf2ifc.profiles.schema import CRSConfig

    crs = CRSConfig(eastings_mm=25496000.0, northings_mm=6672000.0)
    ifc = build_ifc_project_skeleton(project_name="With CRS", crs=crs)

    projected = ifc.by_type("IfcProjectedCRS")
    assert len(projected) == 1
    pcrs = projected[0]
    assert pcrs.Name == "EPSG:3067"
    assert pcrs.Description == "ETRS-TM35FIN"
    assert pcrs.GeodeticDatum == "ETRS89"

    conversions = ifc.by_type("IfcMapConversion")
    assert len(conversions) == 1
    mc = conversions[0]
    assert mc.Eastings == 25496000.0
    assert mc.Northings == 6672000.0
    assert mc.OrthogonalHeight == 0.0
    assert mc.Scale == 1.0
    assert mc.XAxisAbscissa == 1.0
    assert mc.XAxisOrdinate == 0.0
    # SourceCRS = the model GeometricRepresentationContext, TargetCRS = projected
    assert mc.TargetCRS == pcrs
    assert mc.SourceCRS.is_a("IfcGeometricRepresentationContext")


def test_build_project_with_crs_validates_clean(tmp_path: Path):
    from dxf2ifc.core.quality import validate_ifc
    from dxf2ifc.profiles.schema import CRSConfig

    crs = CRSConfig(eastings_mm=25496000.0, northings_mm=6672000.0, scale=0.999)
    ifc = build_ifc_project_skeleton(project_name="Validate", crs=crs)
    out = tmp_path / "with_crs.ifc"
    write_ifc(ifc, out)
    report = validate_ifc(out)
    assert report.errors == []


def test_build_project_crs_orthogonal_height_round_trips():
    from dxf2ifc.profiles.schema import CRSConfig

    crs = CRSConfig(
        eastings_mm=25496000.0,
        northings_mm=6672000.0,
        orthogonal_height_mm=15000.0,
    )
    ifc = build_ifc_project_skeleton(project_name="High Roof", crs=crs)
    mc = ifc.by_type("IfcMapConversion")[0]
    assert mc.OrthogonalHeight == 15000.0


def test_build_project_crs_height_correction_scale_round_trips():
    from dxf2ifc.profiles.schema import CRSConfig

    crs = CRSConfig(
        eastings_mm=25496000.0,
        northings_mm=6672000.0,
        scale=0.9996,
    )
    ifc = build_ifc_project_skeleton(project_name="Scale", crs=crs)
    mc = ifc.by_type("IfcMapConversion")[0]
    assert mc.Scale == 0.9996


def test_build_project_crs_rotation_round_trips():
    """Rotated CRS (X axis points along bearing 30°) should round-trip via
    XAxisAbscissa / XAxisOrdinate."""
    import math

    from dxf2ifc.profiles.schema import CRSConfig

    angle = math.radians(30.0)
    crs = CRSConfig(
        eastings_mm=25496000.0,
        northings_mm=6672000.0,
        x_axis_abscissa=math.cos(angle),
        x_axis_ordinate=math.sin(angle),
    )
    ifc = build_ifc_project_skeleton(project_name="Rotation", crs=crs)
    mc = ifc.by_type("IfcMapConversion")[0]
    assert mc.XAxisAbscissa == pytest.approx(math.cos(angle))
    assert mc.XAxisOrdinate == pytest.approx(math.sin(angle))


def test_build_project_uses_millimetres():
    ifc = build_ifc_project_skeleton(project_name="MM Test")
    project = ifc.by_type("IfcProject")[0]
    length_units = [
        u
        for u in project.UnitsInContext.Units
        if u.is_a("IfcSIUnit") and u.UnitType == "LENGTHUNIT"
    ]
    assert len(length_units) == 1
    assert length_units[0].Prefix == "MILLI"
    assert length_units[0].Name == "METRE"


def test_write_ifc_produces_file(tmp_path: Path):
    ifc = build_ifc_project_skeleton(project_name="Write Test")
    out = tmp_path / "out.ifc"
    write_ifc(ifc, out)
    assert out.exists()
    assert out.stat().st_size > 0
    reloaded = ifcopenshell.open(str(out))
    assert len(reloaded.by_type("IfcProject")) == 1


def _wall_mapped_entity() -> MappedEntity:
    line = LineGeometry(start=Point3D(0, 0, 0), end=Point3D(5000, 0, 0))
    return MappedEntity(
        layer="KYL-ULKOSEINA",
        dxf_type="LINE",
        geometry=line,
        ifc_type="IfcWall",
        predefined_type="STANDARD",
        talo2000_code="1241",
        talo2000_name="Ulkoseinät",
        extra_props={"default_height_mm": 3000, "default_thickness_mm": 200},
    )


def test_add_wall_creates_ifcwall():
    ifc = build_ifc_project_skeleton(project_name="Wall Test")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    wall = add_wall(ifc, _wall_mapped_entity(), parent_storey=storey)
    assert wall.is_a("IfcWall")
    assert wall.PredefinedType == "STANDARD"
    assert wall.Name == "KYL-ULKOSEINA"


def test_add_wall_placed_under_storey():
    ifc = build_ifc_project_skeleton(project_name="Wall Test")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    wall = add_wall(ifc, _wall_mapped_entity(), parent_storey=storey)
    walls = ifc.by_type("IfcWall")
    assert len(walls) == 1
    rels = [
        r for r in ifc.by_type("IfcRelContainedInSpatialStructure") if r.RelatingStructure == storey
    ]
    assert any(wall in rel.RelatedElements for rel in rels)


def test_add_wall_uses_explicit_predefined_type_kwarg():
    ifc = build_ifc_project_skeleton(project_name="Partition Wall")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    mapped = MappedEntity(
        layer="KYL-VALISEINA",
        dxf_type="LINE",
        geometry=LineGeometry(start=Point3D(0, 0, 0), end=Point3D(4000, 0, 0)),
        ifc_type="IfcWall",
        predefined_type=None,
        talo2000_code="1311",
        talo2000_name="Väliseinät",
        extra_props={"default_height_mm": 3000, "default_thickness_mm": 100},
    )
    wall = add_wall(ifc, mapped, parent_storey=storey, predefined_type="PARTITIONING")
    assert wall.PredefinedType == "PARTITIONING"


def test_add_wall_defaults_predefined_type_to_standard():
    ifc = build_ifc_project_skeleton(project_name="Default Wall")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    mapped = MappedEntity(
        layer="KYL-X",
        dxf_type="LINE",
        geometry=LineGeometry(start=Point3D(0, 0, 0), end=Point3D(1000, 0, 0)),
        ifc_type="IfcWall",
        predefined_type=None,
        talo2000_code="1241",
        talo2000_name="Ulkoseinät",
        extra_props={"default_height_mm": 3000, "default_thickness_mm": 200},
    )
    wall = add_wall(ifc, mapped, parent_storey=storey)
    assert wall.PredefinedType == "STANDARD"


def _slab_mapped_entity(
    *,
    layer: str = "KYL-ALAPOHJA",
    talo_code: str = "1221",
    talo_name: str = "Alapohjalaatat",
    thickness_mm: float = 200.0,
) -> MappedEntity:
    polygon = PolygonGeometry(
        vertices=(
            Point3D(0, 0, 0),
            Point3D(4000, 0, 0),
            Point3D(4000, 3000, 0),
            Point3D(0, 3000, 0),
        ),
        closed=True,
    )
    return MappedEntity(
        layer=layer,
        dxf_type="LWPOLYLINE",
        geometry=polygon,
        ifc_type="IfcSlab",
        predefined_type="FLOOR",
        talo2000_code=talo_code,
        talo2000_name=talo_name,
        extra_props={"default_thickness_mm": thickness_mm},
    )


def test_add_slab_creates_ifcslab_with_predefined_type():
    ifc = build_ifc_project_skeleton(project_name="Slab Test")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    slab = add_slab(ifc, _slab_mapped_entity(), parent_storey=storey)
    assert slab.is_a("IfcSlab")
    assert slab.PredefinedType == "FLOOR"
    assert slab.Name == "KYL-ALAPOHJA"
    assert slab.Representation is not None


def test_add_slab_supports_roof_predefined_type():
    ifc = build_ifc_project_skeleton(project_name="Roof Test")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    mapped = _slab_mapped_entity(layer="KYL-YLAPOHJA", talo_code="1236")
    slab = add_slab(ifc, mapped, parent_storey=storey, predefined_type="ROOF")
    assert slab.PredefinedType == "ROOF"


def test_add_slab_placed_under_storey():
    ifc = build_ifc_project_skeleton(project_name="Slab Storey")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    slab = add_slab(ifc, _slab_mapped_entity(), parent_storey=storey)
    rels = [
        r for r in ifc.by_type("IfcRelContainedInSpatialStructure") if r.RelatingStructure == storey
    ]
    assert any(slab in rel.RelatedElements for rel in rels)


def _door_mapped_entity(
    *,
    layer: str = "KYL-OVET-ULKO",
    block_name: str = "OVI-ULKO",
    talo_code: str = "1243",
    talo_name: str = "Ulko-ovet",
    width_mm: float = 900.0,
    height_mm: float = 2100.0,
    depth_mm: float = 50.0,
    predefined_type: str | None = "DOOR",
) -> MappedEntity:
    block = BlockInstance(insertion_point=Point3D(1500, 2500, 0), rotation_rad=0.0)
    return MappedEntity(
        layer=layer,
        dxf_type="INSERT",
        geometry=block,
        block_name=block_name,
        ifc_type="IfcDoor",
        predefined_type=predefined_type,
        talo2000_code=talo_code,
        talo2000_name=talo_name,
        extra_props={
            "default_width_mm": width_mm,
            "default_height_mm": height_mm,
            "default_depth_mm": depth_mm,
        },
    )


def test_add_door_creates_ifcdoor():
    ifc = build_ifc_project_skeleton(project_name="Door Test")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    door = add_door(ifc, _door_mapped_entity(), parent_storey=storey)
    assert door.is_a("IfcDoor")
    assert door.PredefinedType == "DOOR"
    assert door.Name == "KYL-OVET-ULKO"


def test_add_door_sets_overall_height_and_width():
    ifc = build_ifc_project_skeleton(project_name="Door Dims")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    door = add_door(
        ifc,
        _door_mapped_entity(width_mm=1200, height_mm=2400),
        parent_storey=storey,
    )
    assert door.OverallHeight == 2400.0
    assert door.OverallWidth == 1200.0


def test_add_door_placed_under_storey():
    ifc = build_ifc_project_skeleton(project_name="Door Storey")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    door = add_door(ifc, _door_mapped_entity(), parent_storey=storey)
    rels = [
        r for r in ifc.by_type("IfcRelContainedInSpatialStructure") if r.RelatingStructure == storey
    ]
    assert any(door in rel.RelatedElements for rel in rels)


def test_add_door_supports_explicit_predefined_type_kwarg():
    ifc = build_ifc_project_skeleton(project_name="Gate Door")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    mapped = _door_mapped_entity(predefined_type=None)
    door = add_door(ifc, mapped, parent_storey=storey, predefined_type="GATE")
    assert door.PredefinedType == "GATE"


def test_add_door_defaults_predefined_type_to_door():
    ifc = build_ifc_project_skeleton(project_name="Default Door")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    mapped = _door_mapped_entity(predefined_type=None)
    door = add_door(ifc, mapped, parent_storey=storey)
    assert door.PredefinedType == "DOOR"


def _window_mapped_entity(
    *,
    layer: str = "KYL-IKKUNA-MUOVI",
    block_name: str = "IKKUNA",
    talo_code: str = "1242",
    talo_name: str = "Ikkunat",
    width_mm: float = 1200.0,
    height_mm: float = 1500.0,
    depth_mm: float = 60.0,
    predefined_type: str | None = "WINDOW",
) -> MappedEntity:
    block = BlockInstance(insertion_point=Point3D(800, 1200, 1000))
    return MappedEntity(
        layer=layer,
        dxf_type="INSERT",
        geometry=block,
        block_name=block_name,
        ifc_type="IfcWindow",
        predefined_type=predefined_type,
        talo2000_code=talo_code,
        talo2000_name=talo_name,
        extra_props={
            "default_width_mm": width_mm,
            "default_height_mm": height_mm,
            "default_depth_mm": depth_mm,
        },
    )


def test_add_window_creates_ifcwindow():
    ifc = build_ifc_project_skeleton(project_name="Window Test")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    window = add_window(ifc, _window_mapped_entity(), parent_storey=storey)
    assert window.is_a("IfcWindow")
    assert window.PredefinedType == "WINDOW"
    assert window.Name == "KYL-IKKUNA-MUOVI"


def test_add_window_sets_overall_height_and_width():
    ifc = build_ifc_project_skeleton(project_name="Window Dims")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    window = add_window(
        ifc,
        _window_mapped_entity(width_mm=1500, height_mm=1800),
        parent_storey=storey,
    )
    assert window.OverallHeight == 1800.0
    assert window.OverallWidth == 1500.0


def test_add_window_placed_under_storey():
    ifc = build_ifc_project_skeleton(project_name="Window Storey")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    window = add_window(ifc, _window_mapped_entity(), parent_storey=storey)
    rels = [
        r for r in ifc.by_type("IfcRelContainedInSpatialStructure") if r.RelatingStructure == storey
    ]
    assert any(window in rel.RelatedElements for rel in rels)


def test_add_window_defaults_predefined_type_to_window():
    ifc = build_ifc_project_skeleton(project_name="Default Window")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    mapped = _window_mapped_entity(predefined_type=None)
    window = add_window(ifc, mapped, parent_storey=storey)
    assert window.PredefinedType == "WINDOW"


def _pipe_mapped_entity(
    *,
    layer: str = "LT IMU",
    talo_code: str = "2151",
    talo_name: str = "Putkiosat — kylmäimu",
    diameter_mm: float = 22.0,
    predefined_type: str | None = "REFRIGERATION",
) -> MappedEntity:
    line = LineGeometry(start=Point3D(0, 0, 1500), end=Point3D(2000, 0, 1500))
    return MappedEntity(
        layer=layer,
        dxf_type="LINE",
        geometry=line,
        ifc_type="IfcPipeSegment",
        predefined_type=predefined_type,
        talo2000_code=talo_code,
        talo2000_name=talo_name,
        extra_props={"default_diameter_mm": diameter_mm},
    )


def test_add_pipe_segment_creates_ifcpipesegment():
    ifc = build_ifc_project_skeleton(project_name="Pipe Test")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    pipe = add_pipe_segment(ifc, _pipe_mapped_entity(), parent_storey=storey)
    assert pipe.is_a("IfcPipeSegment")
    # IFC4 IfcPipeSegmentTypeEnum has no REFRIGERATION; USERDEFINED carries it.
    assert pipe.PredefinedType == "USERDEFINED"
    assert pipe.ObjectType == "REFRIGERATION"
    assert pipe.Name == "LT IMU"
    assert pipe.Representation is not None


def test_add_pipe_segment_creates_ifcpipesegmenttype_with_predefined_type():
    ifc = build_ifc_project_skeleton(project_name="Pipe Type")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    add_pipe_segment(ifc, _pipe_mapped_entity(), parent_storey=storey)
    types = ifc.by_type("IfcPipeSegmentType")
    assert len(types) >= 1
    refrig = [t for t in types if t.ElementType == "REFRIGERATION"]
    assert len(refrig) == 1
    assert refrig[0].PredefinedType == "USERDEFINED"


def test_add_pipe_segment_placed_under_storey():
    ifc = build_ifc_project_skeleton(project_name="Pipe Storey")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    pipe = add_pipe_segment(ifc, _pipe_mapped_entity(), parent_storey=storey)
    rels = [
        r for r in ifc.by_type("IfcRelContainedInSpatialStructure") if r.RelatingStructure == storey
    ]
    assert any(pipe in rel.RelatedElements for rel in rels)


def test_add_pipe_segment_uses_native_enum_when_valid():
    ifc = build_ifc_project_skeleton(project_name="Rigid Pipe")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    pipe = add_pipe_segment(
        ifc, _pipe_mapped_entity(), parent_storey=storey, predefined_type="RIGIDSEGMENT"
    )
    assert pipe.PredefinedType == "RIGIDSEGMENT"


def test_add_pipe_segment_drainpipe_falls_back_to_userdefined():
    ifc = build_ifc_project_skeleton(project_name="Drain Pipe")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    pipe = add_pipe_segment(
        ifc, _pipe_mapped_entity(), parent_storey=storey, predefined_type="DRAINPIPE"
    )
    assert pipe.PredefinedType == "USERDEFINED"
    assert pipe.ObjectType == "DRAINPIPE"
    types = [t for t in ifc.by_type("IfcPipeSegmentType") if t.ElementType == "DRAINPIPE"]
    assert len(types) == 1
    assert types[0].PredefinedType == "USERDEFINED"


def test_add_pipe_segment_reuses_drainpipe_type_for_repeat_calls():
    ifc = build_ifc_project_skeleton(project_name="Drain Pipes")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    add_pipe_segment(ifc, _pipe_mapped_entity(), parent_storey=storey, predefined_type="DRAINPIPE")
    add_pipe_segment(ifc, _pipe_mapped_entity(), parent_storey=storey, predefined_type="DRAINPIPE")
    drain_types = [t for t in ifc.by_type("IfcPipeSegmentType") if t.ElementType == "DRAINPIPE"]
    assert len(drain_types) == 1


def _furniture_mapped_entity(
    *,
    layer: str = "KYL-LEVYHYLLY",
    block_name: str = "KLHYLLY-LEVY",
    talo_code: str = "1331",
    talo_name: str = "Vakiokiintokalusteet",
    width_mm: float = 1000.0,
    depth_mm: float = 600.0,
    height_mm: float = 2000.0,
) -> MappedEntity:
    block = BlockInstance(insertion_point=Point3D(2000, 1500, 0))
    return MappedEntity(
        layer=layer,
        dxf_type="INSERT",
        geometry=block,
        block_name=block_name,
        ifc_type="IfcFurniture",
        predefined_type=None,
        talo2000_code=talo_code,
        talo2000_name=talo_name,
        extra_props={
            "default_width_mm": width_mm,
            "default_depth_mm": depth_mm,
            "default_height_mm": height_mm,
        },
    )


def test_add_furniture_creates_ifcfurniture():
    ifc = build_ifc_project_skeleton(project_name="Furniture Test")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    furniture = add_furniture(ifc, _furniture_mapped_entity(), parent_storey=storey)
    assert furniture.is_a("IfcFurniture")
    assert furniture.Name == "KYL-LEVYHYLLY"
    assert furniture.Representation is not None


def test_add_furniture_placed_under_storey():
    ifc = build_ifc_project_skeleton(project_name="Furniture Storey")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    furniture = add_furniture(ifc, _furniture_mapped_entity(), parent_storey=storey)
    rels = [
        r for r in ifc.by_type("IfcRelContainedInSpatialStructure") if r.RelatingStructure == storey
    ]
    assert any(furniture in rel.RelatedElements for rel in rels)


def test_add_furniture_uses_extra_props_dimensions():
    ifc = build_ifc_project_skeleton(project_name="Furniture Dims")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    mapped = _furniture_mapped_entity(width_mm=1500, depth_mm=400, height_mm=1800)
    furniture = add_furniture(ifc, mapped, parent_storey=storey)
    extruded = furniture.Representation.Representations[0].Items[0]
    assert extruded.Depth == 1800.0
    assert extruded.SweptArea.XDim == 1500.0
    assert extruded.SweptArea.YDim == 400.0


def _polygon_furniture_mapped_entity(
    *,
    vertices: tuple[Point3D, ...] = (
        Point3D(1000, 500, 0),
        Point3D(2200, 500, 0),
        Point3D(2200, 1100, 0),
        Point3D(1000, 1100, 0),
    ),
    height_mm: float = 2000.0,
    layer: str = "KYL-LEVYHYLLY",
) -> MappedEntity:
    polygon = PolygonGeometry(vertices=vertices, closed=True)
    return MappedEntity(
        layer=layer,
        dxf_type="LWPOLYLINE",
        geometry=polygon,
        ifc_type="IfcFurniture",
        predefined_type=None,
        talo2000_code="1331",
        talo2000_name="Vakiokiintokalusteet",
        extra_props={"default_height_mm": height_mm},
    )


def test_add_furniture_accepts_polygon_geometry():
    ifc = build_ifc_project_skeleton(project_name="Furniture Polygon")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    furniture = add_furniture(ifc, _polygon_furniture_mapped_entity(), parent_storey=storey)
    assert furniture.is_a("IfcFurniture")
    extruded = furniture.Representation.Representations[0].Items[0]
    assert extruded.Depth == 2000.0
    assert extruded.SweptArea.XDim == 1200.0
    assert extruded.SweptArea.YDim == 600.0


def test_add_furniture_polygon_rejects_degenerate_outline():
    ifc = build_ifc_project_skeleton(project_name="Furniture Degenerate")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    tiny = _polygon_furniture_mapped_entity(
        vertices=(
            Point3D(0, 0, 0),
            Point3D(40, 0, 0),
            Point3D(40, 40, 0),
            Point3D(0, 40, 0),
        )
    )
    with pytest.raises(ValueError, match="degenerate"):
        add_furniture(ifc, tiny, parent_storey=storey)


def _cable_mapped_entity(
    *,
    layer: str = "KAAPELIHYLLY",
    talo_code: str = "2380",
    talo_name: str = "Sähköosat — kaapelihyllyt",
    width_mm: float = 300.0,
    height_mm: float = 80.0,
    predefined_type: str | None = "CABLETRUNKINGSEGMENT",
) -> MappedEntity:
    line = LineGeometry(start=Point3D(0, 0, 2700), end=Point3D(2500, 0, 2700))
    return MappedEntity(
        layer=layer,
        dxf_type="LINE",
        geometry=line,
        ifc_type="IfcCableCarrierSegment",
        predefined_type=predefined_type,
        talo2000_code=talo_code,
        talo2000_name=talo_name,
        extra_props={
            "default_width_mm": width_mm,
            "default_height_mm": height_mm,
        },
    )


def test_add_cable_carrier_segment_creates_ifccablecarriersegment():
    ifc = build_ifc_project_skeleton(project_name="Cable Test")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    seg = add_cable_carrier_segment(ifc, _cable_mapped_entity(), parent_storey=storey)
    assert seg.is_a("IfcCableCarrierSegment")
    assert seg.PredefinedType == "CABLETRUNKINGSEGMENT"
    assert seg.Name == "KAAPELIHYLLY"
    assert seg.Representation is not None


def test_add_cable_carrier_segment_creates_segment_type():
    ifc = build_ifc_project_skeleton(project_name="Cable Type")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    add_cable_carrier_segment(ifc, _cable_mapped_entity(), parent_storey=storey)
    types = ifc.by_type("IfcCableCarrierSegmentType")
    assert any(t.PredefinedType == "CABLETRUNKINGSEGMENT" for t in types)


def test_add_cable_carrier_segment_placed_under_storey():
    ifc = build_ifc_project_skeleton(project_name="Cable Storey")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    seg = add_cable_carrier_segment(ifc, _cable_mapped_entity(), parent_storey=storey)
    rels = [
        r for r in ifc.by_type("IfcRelContainedInSpatialStructure") if r.RelatingStructure == storey
    ]
    assert any(seg in rel.RelatedElements for rel in rels)


def test_add_cable_carrier_segment_reuses_type_for_repeat_calls():
    ifc = build_ifc_project_skeleton(project_name="Cable Reuse")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    add_cable_carrier_segment(ifc, _cable_mapped_entity(), parent_storey=storey)
    add_cable_carrier_segment(ifc, _cable_mapped_entity(), parent_storey=storey)
    types = ifc.by_type("IfcCableCarrierSegmentType")
    trunk = [t for t in types if t.PredefinedType == "CABLETRUNKINGSEGMENT"]
    assert len(trunk) == 1


def _proxy_mapped_entity(
    *,
    layer: str = "KYL-LEVY",
    talo_code: str = "1352",
    talo_name: str = "Kylmähuone-elementit",
    thickness_mm: float = 120.0,
) -> MappedEntity:
    polygon = PolygonGeometry(
        vertices=(
            Point3D(0, 0, 0),
            Point3D(2400, 0, 0),
            Point3D(2400, 2700, 0),
            Point3D(0, 2700, 0),
        ),
        closed=True,
    )
    return MappedEntity(
        layer=layer,
        dxf_type="POLYLINE",
        geometry=polygon,
        ifc_type="IfcBuildingElementProxy",
        predefined_type=None,
        talo2000_code=talo_code,
        talo2000_name=talo_name,
        extra_props={"default_thickness_mm": thickness_mm},
    )


def test_add_building_element_proxy_creates_ifcproxy():
    ifc = build_ifc_project_skeleton(project_name="Proxy Test")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    proxy = add_building_element_proxy(ifc, _proxy_mapped_entity(), parent_storey=storey)
    assert proxy.is_a("IfcBuildingElementProxy")
    assert proxy.Name == "KYL-LEVY"
    assert proxy.Representation is not None


def test_add_building_element_proxy_uses_thickness_from_extra_props():
    ifc = build_ifc_project_skeleton(project_name="Proxy Thick")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    proxy = add_building_element_proxy(
        ifc, _proxy_mapped_entity(thickness_mm=80), parent_storey=storey
    )
    extruded = proxy.Representation.Representations[0].Items[0]
    assert extruded.Depth == 80.0


def test_add_building_element_proxy_placed_under_storey():
    ifc = build_ifc_project_skeleton(project_name="Proxy Storey")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    proxy = add_building_element_proxy(ifc, _proxy_mapped_entity(), parent_storey=storey)
    rels = [
        r for r in ifc.by_type("IfcRelContainedInSpatialStructure") if r.RelatingStructure == storey
    ]
    assert any(proxy in rel.RelatedElements for rel in rels)


def _cooling_mapped_entity(
    *,
    layer: str,
    block_name: str,
    ifc_type: str,
    talo_code: str,
    talo_name: str,
) -> MappedEntity:
    block = BlockInstance(insertion_point=Point3D(1000, 1000, 200))
    return MappedEntity(
        layer=layer,
        dxf_type="INSERT",
        geometry=block,
        block_name=block_name,
        ifc_type=ifc_type,
        predefined_type=None,
        talo2000_code=talo_code,
        talo2000_name=talo_name,
        extra_props={
            "default_width_mm": 800.0,
            "default_depth_mm": 600.0,
            "default_height_mm": 1200.0,
        },
    )


@pytest.fixture
def _cooling_storey():
    ifc = build_ifc_project_skeleton(project_name="Cooling Test")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    return ifc, storey


def test_add_cooling_equipment_creates_ifcevaporator(_cooling_storey):
    ifc, storey = _cooling_storey
    mapped = _cooling_mapped_entity(
        layer="KYL-HOYRYSTIN-CR-30",
        block_name="HOYRYSTIN",
        ifc_type="IfcEvaporator",
        talo_code="2510",
        talo_name="Laiteosat — höyrystin",
    )
    ev = add_cooling_equipment(ifc, mapped, parent_storey=storey)
    assert ev.is_a("IfcEvaporator")
    assert ev.Name == "KYL-HOYRYSTIN-CR-30"


def test_add_cooling_equipment_creates_ifccondenser(_cooling_storey):
    ifc, storey = _cooling_storey
    mapped = _cooling_mapped_entity(
        layer="KYL-LAUHDUTIN",
        block_name="LAUHDUTIN",
        ifc_type="IfcCondenser",
        talo_code="2520",
        talo_name="Laiteosat — lauhdutin",
    )
    cond = add_cooling_equipment(ifc, mapped, parent_storey=storey)
    assert cond.is_a("IfcCondenser")


def test_add_cooling_equipment_creates_ifccompressor(_cooling_storey):
    ifc, storey = _cooling_storey
    mapped = _cooling_mapped_entity(
        layer="KYL-KOMPRESSORI",
        block_name="KOMPRESSORI",
        ifc_type="IfcCompressor",
        talo_code="2530",
        talo_name="Laiteosat — kompressori",
    )
    comp = add_cooling_equipment(ifc, mapped, parent_storey=storey)
    assert comp.is_a("IfcCompressor")


def test_add_cooling_equipment_placed_under_storey(_cooling_storey):
    ifc, storey = _cooling_storey
    mapped = _cooling_mapped_entity(
        layer="KYL-HOYRYSTIN",
        block_name="HOYRYSTIN",
        ifc_type="IfcEvaporator",
        talo_code="2510",
        talo_name="Laiteosat — höyrystin",
    )
    ev = add_cooling_equipment(ifc, mapped, parent_storey=storey)
    rels = [
        r for r in ifc.by_type("IfcRelContainedInSpatialStructure") if r.RelatingStructure == storey
    ]
    assert any(ev in rel.RelatedElements for rel in rels)


def test_add_cooling_equipment_rejects_unsupported_ifc_type(_cooling_storey):
    ifc, storey = _cooling_storey
    mapped = _cooling_mapped_entity(
        layer="KYL-X",
        block_name="X",
        ifc_type="IfcWall",
        talo_code="0",
        talo_name="x",
    )
    with pytest.raises(ValueError):
        add_cooling_equipment(ifc, mapped, parent_storey=storey)


def test_add_system_creates_ifcsystem_with_name():
    ifc = build_ifc_project_skeleton(project_name="System Test")
    system = add_system(ifc, name="Refrigeration LT")
    assert system.is_a("IfcSystem")
    assert system.Name == "Refrigeration LT"


def test_assign_to_system_links_products_via_relassignsto_group():
    ifc = build_ifc_project_skeleton(project_name="System Assign")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    pipe = add_pipe_segment(ifc, _pipe_mapped_entity(), parent_storey=storey)
    system = add_system(ifc, name="Refrigeration LT")
    assign_to_system(ifc, products=[pipe], system=system)
    rels = [r for r in ifc.by_type("IfcRelAssignsToGroup") if r.RelatingGroup == system]
    assert any(pipe in r.RelatedObjects for r in rels)


def test_add_system_caches_per_name():
    ifc = build_ifc_project_skeleton(project_name="System Reuse")
    a = add_system(ifc, name="Drainage")
    b = add_system(ifc, name="Drainage")
    assert a == b
    systems = [s for s in ifc.by_type("IfcSystem") if s.Name == "Drainage"]
    assert len(systems) == 1


def test_add_talo2000_classification_attaches_reference():
    ifc = build_ifc_project_skeleton(project_name="Class Test")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    wall = add_wall(ifc, _wall_mapped_entity(), parent_storey=storey)
    add_talo2000_classification(ifc, wall, code="1241", name="Ulkoseinät")

    refs = ifc.by_type("IfcClassificationReference")
    assert any(r.Identification == "1241" for r in refs)
    classifications = ifc.by_type("IfcClassification")
    assert any(c.Name == "Talo2000" for c in classifications)


def test_add_classification_ark_emits_talo2000():
    ifc = build_ifc_project_skeleton(project_name="ARK")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    wall = add_wall(ifc, _wall_mapped_entity(), parent_storey=storey)
    add_classification(ifc, wall, domain="ARK", code="1241", name="Ulkoseinät")

    classifications = {c.Name for c in ifc.by_type("IfcClassification")}
    assert "Talo2000" in classifications
    refs = ifc.by_type("IfcClassificationReference")
    assert any(r.Identification == "1241" for r in refs)


def test_add_classification_tate_lvi_emits_rava_lvi():
    ifc = build_ifc_project_skeleton(project_name="TATE-LVI")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    wall = add_wall(ifc, _wall_mapped_entity(), parent_storey=storey)
    add_classification(ifc, wall, domain="TATE", code="T-LVI-01-01-023", name=None)

    classifications = {c.Name for c in ifc.by_type("IfcClassification")}
    assert "RAVA-LVI" in classifications
    assert "Talo2000" not in classifications
    refs = ifc.by_type("IfcClassificationReference")
    assert any(r.Identification == "T-LVI-01-01-023" for r in refs)


def test_add_classification_tate_talotekniikka_emits_rava_tate():
    ifc = build_ifc_project_skeleton(project_name="TATE-TATE")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    wall = add_wall(ifc, _wall_mapped_entity(), parent_storey=storey)
    add_classification(ifc, wall, domain="TATE", code="T-TATE-01-01-001", name=None)

    classifications = {c.Name for c in ifc.by_type("IfcClassification")}
    assert "RAVA-TATE" in classifications
    refs = ifc.by_type("IfcClassificationReference")
    assert any(r.Identification == "T-TATE-01-01-001" for r in refs)


def test_add_classification_reuses_existing_classification():
    ifc = build_ifc_project_skeleton(project_name="Reuse")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    wall_a = add_wall(ifc, _wall_mapped_entity(), parent_storey=storey)
    wall_b = add_wall(ifc, _wall_mapped_entity(), parent_storey=storey)
    add_classification(ifc, wall_a, domain="TATE", code="T-LVI-01-01-023", name=None)
    add_classification(ifc, wall_b, domain="TATE", code="T-LVI-01-01-018", name=None)

    rava_lvi = [c for c in ifc.by_type("IfcClassification") if c.Name == "RAVA-LVI"]
    assert len(rava_lvi) == 1




def _tetrahedron_mesh(
    *, offset: tuple[float, float, float] = (0.0, 0.0, 0.0)
) -> MeshGeometry:
    """Return a tetrahedron with 4 vertices and 4 triangular faces."""
    ox, oy, oz = offset
    return MeshGeometry(
        vertices=(
            Point3D(0.0 + ox, 0.0 + oy, 0.0 + oz),
            Point3D(1000.0 + ox, 0.0 + oy, 0.0 + oz),
            Point3D(500.0 + ox, 1000.0 + oy, 0.0 + oz),
            Point3D(500.0 + ox, 500.0 + oy, 1000.0 + oz),
        ),
        faces=(
            (0, 1, 2),
            (0, 1, 3),
            (1, 2, 3),
            (2, 0, 3),
        ),
    )


def _mesh_furniture_mapped(
    *, mesh: MeshGeometry | None = None, layer: str = "KYL-LEVYHYLLY"
) -> MappedEntity:
    return MappedEntity(
        layer=layer,
        dxf_type="MESH",
        geometry=mesh or _tetrahedron_mesh(),
        ifc_type="IfcFurniture",
        predefined_type=None,
        talo2000_code="1331",
        talo2000_name="Vakiokiintokalusteet",
        extra_props={},
    )


def test_add_furniture_with_mesh_geometry_emits_brep():
    ifc = build_ifc_project_skeleton(project_name="Furniture Mesh")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    furniture = add_furniture(ifc, _mesh_furniture_mapped(), parent_storey=storey)
    assert furniture.is_a("IfcFurniture")
    assert furniture.Representation is not None
    shapes = furniture.Representation.Representations
    assert len(shapes) == 1
    assert shapes[0].RepresentationType == "Brep"
    breps = ifc.by_type("IfcFacetedBrep")
    assert len(breps) == 1
    assert len(breps[0].Outer.CfsFaces) == 4


def test_add_cable_carrier_cabletray_emits_correct_predefined_type():
    ifc = build_ifc_project_skeleton(project_name="Cable Tray")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    mapped = MappedEntity(
        layer="KAAPELIHYLLY-LEVY",
        dxf_type="MESH",
        geometry=_tetrahedron_mesh(),
        ifc_type="IfcCableCarrierSegment",
        predefined_type="CABLETRAYSEGMENT",
        domain="TATE",
        talotekniikka_code="T-TATE-01-01-001",
    )
    seg = add_cable_carrier(
        ifc, mapped, parent_storey=storey, predefined_type="CABLETRAYSEGMENT"
    )
    assert seg.is_a("IfcCableCarrierSegment")
    assert seg.PredefinedType == "CABLETRAYSEGMENT"
    types = ifc.by_type("IfcCableCarrierSegmentType")
    assert any(t.PredefinedType == "CABLETRAYSEGMENT" for t in types)


def test_add_cable_carrier_cableladder_emits_correct_predefined_type():
    ifc = build_ifc_project_skeleton(project_name="Cable Ladder")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    mapped = MappedEntity(
        layer="KAAPELIHYLLY-TIKAS",
        dxf_type="MESH",
        geometry=_tetrahedron_mesh(),
        ifc_type="IfcCableCarrierSegment",
        predefined_type="CABLELADDERSEGMENT",
        domain="TATE",
        talotekniikka_code="T-TATE-01-01-001",
    )
    seg = add_cable_carrier(
        ifc, mapped, parent_storey=storey, predefined_type="CABLELADDERSEGMENT"
    )
    assert seg.PredefinedType == "CABLELADDERSEGMENT"
    types = ifc.by_type("IfcCableCarrierSegmentType")
    assert any(t.PredefinedType == "CABLELADDERSEGMENT" for t in types)


def test_add_cable_carrier_attaches_rava_classification():
    ifc = build_ifc_project_skeleton(project_name="Cable RAVA")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    mapped = MappedEntity(
        layer="KAAPELIHYLLY-TIKAS",
        dxf_type="MESH",
        geometry=_tetrahedron_mesh(),
        ifc_type="IfcCableCarrierSegment",
        predefined_type="CABLELADDERSEGMENT",
        domain="TATE",
        talotekniikka_code="T-TATE-01-01-001",
    )
    seg = add_cable_carrier(
        ifc, mapped, parent_storey=storey, predefined_type="CABLELADDERSEGMENT"
    )
    add_classification(
        ifc,
        seg,
        domain="TATE",
        code=mapped.talotekniikka_code,
        name=None,
    )
    classifications = {c.Name for c in ifc.by_type("IfcClassification")}
    assert "RAVA-TATE" in classifications
    refs = ifc.by_type("IfcClassificationReference")
    assert any(r.Identification == "T-TATE-01-01-001" for r in refs)


def test_add_cable_carrier_assigns_to_system():
    ifc = build_ifc_project_skeleton(project_name="Cable System")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    mapped = MappedEntity(
        layer="KAAPELIHYLLY-LEVY",
        dxf_type="MESH",
        geometry=_tetrahedron_mesh(),
        ifc_type="IfcCableCarrierSegment",
        predefined_type="CABLETRAYSEGMENT",
        domain="TATE",
        talotekniikka_code="T-TATE-01-01-001",
    )
    seg = add_cable_carrier(
        ifc, mapped, parent_storey=storey, predefined_type="CABLETRAYSEGMENT"
    )
    system = add_system(ifc, name="Cable Trays")
    assign_to_system(ifc, products=[seg], system=system)
    rels = [r for r in ifc.by_type("IfcRelAssignsToGroup") if r.RelatingGroup == system]
    assert any(seg in r.RelatedObjects for r in rels)


def test_add_evaporator_with_mesh_geometry_emits_brep():
    ifc = build_ifc_project_skeleton(project_name="Evap Mesh")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    mapped = MappedEntity(
        layer="KYL-HOYRYSTIN",
        dxf_type="MESH",
        geometry=_tetrahedron_mesh(),
        ifc_type="IfcEvaporator",
        predefined_type=None,
        domain="TATE",
        lvi_code="T-LVI-01-01-023",
    )
    ev = add_cooling_equipment(ifc, mapped, parent_storey=storey)
    assert ev.is_a("IfcEvaporator")
    assert ev.Representation is not None
    assert ev.Representation.Representations[0].RepresentationType == "Brep"
    breps = ifc.by_type("IfcFacetedBrep")
    assert len(breps) == 1


def test_mesh_to_brep_handles_quad_faces():
    """N-gon faces should produce one IfcFace each, not be triangulated."""
    ifc = build_ifc_project_skeleton(project_name="Quad Mesh")
    # A simple cube: 8 vertices, 6 quad faces.
    cube = MeshGeometry(
        vertices=(
            Point3D(0, 0, 0),
            Point3D(1000, 0, 0),
            Point3D(1000, 1000, 0),
            Point3D(0, 1000, 0),
            Point3D(0, 0, 1000),
            Point3D(1000, 0, 1000),
            Point3D(1000, 1000, 1000),
            Point3D(0, 1000, 1000),
        ),
        faces=(
            (0, 3, 2, 1),  # bottom
            (4, 5, 6, 7),  # top
            (0, 1, 5, 4),  # front
            (1, 2, 6, 5),  # right
            (2, 3, 7, 6),  # back
            (3, 0, 4, 7),  # left
        ),
    )
    brep = _mesh_to_brep(ifc, cube)
    assert brep.is_a("IfcFacetedBrep")
    faces = brep.Outer.CfsFaces
    assert len(faces) == 6
    # Each face must be a quad: one IfcFaceOuterBound with 4 polyloop points.
    for face in faces:
        bounds = face.Bounds
        assert len(bounds) == 1
        assert len(bounds[0].Bound.Polygon) == 4


def test_mesh_to_brep_dedupes_vertices():
    """Repeated vertices in MeshGeometry should map to one IfcCartesianPoint."""
    ifc = build_ifc_project_skeleton(project_name="Dedup Mesh")
    # Two physically identical vertices at index 0 and index 4.
    mesh = MeshGeometry(
        vertices=(
            Point3D(0, 0, 0),
            Point3D(1000, 0, 0),
            Point3D(500, 1000, 0),
            Point3D(500, 500, 1000),
            Point3D(0, 0, 0),  # duplicate of index 0
        ),
        faces=(
            (0, 1, 2),
            (0, 1, 3),
            (1, 2, 3),
            (4, 2, 3),  # uses the duplicate vertex
        ),
    )
    points_before = len(ifc.by_type("IfcCartesianPoint"))
    brep = _mesh_to_brep(ifc, mesh)
    assert brep.is_a("IfcFacetedBrep")
    points_after = len(ifc.by_type("IfcCartesianPoint"))
    # 5 input vertices but 4 unique -> 4 new IfcCartesianPoints.
    assert points_after - points_before == 4
