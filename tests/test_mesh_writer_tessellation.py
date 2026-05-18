"""Tests for the IfcTriangulatedFaceSet writer + fan-triangulation."""

from __future__ import annotations

import ifcopenshell

from dwg2ifc.core.ifc_writer.mesh import (
    _mesh_to_triangulated_face_set,
    _triangulate,
)
from dwg2ifc.core.types import MeshGeometry, Point3D


def test_triangulate_passthroughs_triangle():
    assert _triangulate((0, 1, 2)) == [(0, 1, 2)]


def test_triangulate_quad_fan():
    # [A, B, C, D] -> [(A,B,C), (A,C,D)]
    assert _triangulate((0, 1, 2, 3)) == [(0, 1, 2), (0, 2, 3)]


def test_triangulate_pentagon_fan():
    # [A, B, C, D, E] -> 3 triangles around vertex 0
    assert _triangulate((0, 1, 2, 3, 4)) == [
        (0, 1, 2),
        (0, 2, 3),
        (0, 3, 4),
    ]


def test_triangulate_degenerate_returns_empty():
    assert _triangulate(()) == []
    assert _triangulate((0,)) == []
    assert _triangulate((0, 1)) == []


def test_mesh_to_triangulated_face_set_writes_correct_indices():
    """Pyramid with 1 quad base + 4 triangle sides → 6 triangles after
    fan-trianglation (2 base + 4 sides)."""
    ifc = ifcopenshell.file(schema="IFC4")

    base_z = 0.0
    apex_z = 1000.0
    verts = (
        Point3D(0.0, 0.0, base_z),     # 0
        Point3D(1000.0, 0.0, base_z),  # 1
        Point3D(1000.0, 1000.0, base_z),  # 2
        Point3D(0.0, 1000.0, base_z),  # 3
        Point3D(500.0, 500.0, apex_z),  # 4
    )
    faces = (
        (0, 1, 2, 3),   # quad base — fan-triangulates into 2 tris
        (0, 1, 4),
        (1, 2, 4),
        (2, 3, 4),
        (3, 0, 4),
    )
    mesh = MeshGeometry(vertices=verts, faces=faces, source="polyface")

    item = _mesh_to_triangulated_face_set(ifc, mesh)
    assert item.is_a("IfcTriangulatedFaceSet")
    assert item.Closed is False

    # Coordinates: emitted relative to bbox-min, which here is (0,0,0).
    coord_list = item.Coordinates
    assert coord_list.is_a("IfcCartesianPointList3D")
    assert len(coord_list.CoordList) == 5

    # 6 triangles total: 2 from base quad + 4 sides
    assert len(item.CoordIndex) == 6
    # All indices are 1-based and reference into CoordList
    for tri in item.CoordIndex:
        assert len(tri) == 3
        for idx in tri:
            assert 1 <= idx <= 5


def test_add_mesh_product_branches_on_source():
    """Tessellation source → IfcTriangulatedFaceSet + Tessellation type;
    acis source → IfcFacetedBrep + Brep type."""
    from dwg2ifc.core.ifc_writer.mesh import _add_mesh_product
    from dwg2ifc.core.ifc_writer.skeleton import build_ifc_project_skeleton
    from dwg2ifc.core.types import MappedEntity

    # Tessellation path
    skel = build_ifc_project_skeleton(project_name="t")
    storey = skel.storeys[0]
    polyface_mesh = MeshGeometry(
        vertices=(
            Point3D(0.0, 0.0, 0.0),
            Point3D(100.0, 0.0, 0.0),
            Point3D(0.0, 100.0, 0.0),
        ),
        faces=((0, 1, 2),),
        source="polyface",
    )
    mapped_t = MappedEntity(
        layer="MAGI_OUT", dxf_type="POLYFACE",
        geometry=polyface_mesh, ifc_type="IfcBuildingElementProxy",
    )
    product_t = _add_mesh_product(
        skel.file, mapped_t, ifc_class="IfcBuildingElementProxy",
        parent_storey=storey,
    )
    items_t = product_t.Representation.Representations[0].Items
    assert items_t[0].is_a("IfcTriangulatedFaceSet")
    assert (
        product_t.Representation.Representations[0].RepresentationType
        == "Tessellation"
    )

    # ACIS path on a separate file (default source="acis")
    skel2 = build_ifc_project_skeleton(project_name="t2")
    storey2 = skel2.storeys[0]
    acis_mesh = MeshGeometry(
        vertices=(
            Point3D(0.0, 0.0, 0.0),
            Point3D(100.0, 0.0, 0.0),
            Point3D(0.0, 100.0, 0.0),
            Point3D(0.0, 0.0, 100.0),
        ),
        faces=((0, 1, 2), (0, 1, 3), (1, 2, 3), (2, 0, 3)),
        # default source="acis"
    )
    mapped_a = MappedEntity(
        layer="KYL-LEVYHYLLY", dxf_type="3DSOLID",
        geometry=acis_mesh, ifc_type="IfcCableCarrierSegment",
    )
    product_a = _add_mesh_product(
        skel2.file, mapped_a, ifc_class="IfcCableCarrierSegment",
        parent_storey=storey2,
    )
    items_a = product_a.Representation.Representations[0].Items
    assert items_a[0].is_a("IfcFacetedBrep")
    assert (
        product_a.Representation.Representations[0].RepresentationType
        == "Brep"
    )
