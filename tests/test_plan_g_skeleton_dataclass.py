"""Plan G Task 10: ``build_ifc_project_skeleton`` returns an
``IfcSkeleton`` dataclass with file/project/site/building/storeys/contexts
fields. Backward compatibility: legacy callers that treat the return value
as the ``ifcopenshell.file`` keep working — IfcSkeleton proxies missing
attributes to its underlying ``.file``."""

from __future__ import annotations

from dxf2ifc.core.ifc_writer import IfcSkeleton, build_ifc_project_skeleton


def test_build_returns_ifcskeleton_dataclass():
    skeleton = build_ifc_project_skeleton(project_name="Skeleton")
    assert isinstance(skeleton, IfcSkeleton)


def test_skeleton_storeys_field_matches_levels():
    skeleton = build_ifc_project_skeleton(
        project_name="Storeys",
        storey_z_levels_mm=[0.0, 3500.0, 7000.0],
    )
    assert len(skeleton.storeys) == 3
    assert skeleton.storeys[0].Name == "Kerros 1"
    assert skeleton.storeys[2].Elevation == 7000.0


def test_skeleton_exposes_project_site_building():
    skeleton = build_ifc_project_skeleton(project_name="Hierarchy")
    assert skeleton.project.is_a("IfcProject")
    assert skeleton.site.is_a("IfcSite")
    assert skeleton.building.is_a("IfcBuilding")


def test_skeleton_proxies_ifcopenshell_file_attributes():
    """Backward compat: legacy callers of ``ifc.by_type(...)`` keep working
    against the returned ``IfcSkeleton`` because ``__getattr__`` falls back
    to ``.file``."""
    skeleton = build_ifc_project_skeleton(project_name="Proxy")
    walls = skeleton.by_type("IfcWall")  # delegates to file.by_type
    assert walls == []
    assert skeleton.schema in ("IFC4", "IFC4X3")  # file.schema attr
