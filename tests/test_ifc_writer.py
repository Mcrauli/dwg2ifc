"""Unit tests for core.ifc_writer."""

from pathlib import Path

import ifcopenshell

from dxf2ifc.core.ifc_writer import (
    add_door,
    add_pipe_segment,
    add_slab,
    add_talo2000_classification,
    add_wall,
    add_window,
    build_ifc_project_skeleton,
    convert_dxf,
    write_ifc,
)
from dxf2ifc.core.types import (
    BlockInstance,
    LineGeometry,
    MappedEntity,
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
        r
        for r in ifc.by_type("IfcRelContainedInSpatialStructure")
        if r.RelatingStructure == storey
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
        r
        for r in ifc.by_type("IfcRelContainedInSpatialStructure")
        if r.RelatingStructure == storey
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
        r
        for r in ifc.by_type("IfcRelContainedInSpatialStructure")
        if r.RelatingStructure == storey
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
        r
        for r in ifc.by_type("IfcRelContainedInSpatialStructure")
        if r.RelatingStructure == storey
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
    add_pipe_segment(
        ifc, _pipe_mapped_entity(), parent_storey=storey, predefined_type="DRAINPIPE"
    )
    add_pipe_segment(
        ifc, _pipe_mapped_entity(), parent_storey=storey, predefined_type="DRAINPIPE"
    )
    drain_types = [t for t in ifc.by_type("IfcPipeSegmentType") if t.ElementType == "DRAINPIPE"]
    assert len(drain_types) == 1


def test_add_talo2000_classification_attaches_reference():
    ifc = build_ifc_project_skeleton(project_name="Class Test")
    storey = ifc.by_type("IfcBuildingStorey")[0]
    wall = add_wall(ifc, _wall_mapped_entity(), parent_storey=storey)
    add_talo2000_classification(ifc, wall, code="1241", name="Ulkoseinät")

    refs = ifc.by_type("IfcClassificationReference")
    assert any(r.Identification == "1241" for r in refs)
    classifications = ifc.by_type("IfcClassification")
    assert any(c.Name == "Talo2000" for c in classifications)


def test_convert_dxf_produces_ifc_with_wall(fixtures_dir: Path, tmp_path: Path):
    output = tmp_path / "out.ifc"
    convert_dxf(
        dxf_path=fixtures_dir / "simple_wall.dxf",
        output_path=output,
        profile=load_default_profile(),
    )
    assert output.exists()
    reloaded = ifcopenshell.open(str(output))
    walls = reloaded.by_type("IfcWall")
    assert len(walls) == 1
    refs = reloaded.by_type("IfcClassificationReference")
    assert any(r.Identification == "1241" for r in refs)
