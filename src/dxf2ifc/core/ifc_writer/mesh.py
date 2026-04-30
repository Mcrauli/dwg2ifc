"""Mesh -> IfcFacetedBrep conversion + bbox helpers."""

from __future__ import annotations

import ifcopenshell
import ifcopenshell.api

from dxf2ifc.core.ifc_writer.transforms import _z_rotation_matrix
from dxf2ifc.core.types import MeshGeometry, Point3D


def _mesh_bbox_min(mesh: MeshGeometry) -> Point3D:
    """Return the (xmin, ymin, zmin) corner of a mesh's bounding box.

    Used as the placement origin so the mesh's local coordinates stay
    centred near zero rather than carrying world-space offsets.
    """
    if not mesh.vertices:
        raise ValueError("MeshGeometry must have at least one vertex")
    xs = [v.x for v in mesh.vertices]
    ys = [v.y for v in mesh.vertices]
    zs = [v.z for v in mesh.vertices]
    return Point3D(min(xs), min(ys), min(zs))


def _mesh_to_brep(ifc, mesh: MeshGeometry) -> object:
    """Convert a :class:`MeshGeometry` into an ``IfcFacetedBrep``.

    Vertices are deduplicated (vertices with identical coordinates map to
    a single ``IfcCartesianPoint``), each face is wrapped in an
    ``IfcPolyLoop`` → ``IfcFaceOuterBound`` → ``IfcFace`` chain, and the
    full set of faces is collected into an ``IfcClosedShell`` →
    ``IfcFacetedBrep``. Coordinates are emitted relative to the mesh's
    bounding-box minimum so the geometry stays in LOCAL space; the caller
    is responsible for placing the product at that bbox-min anchor.

    N-gon faces (n>=3) are preserved as a single ``IfcFace``; the helper
    does NOT triangulate, matching the spec. Faces with fewer than 3
    distinct vertices after dedup are skipped (degenerate).
    """
    if not mesh.faces:
        raise ValueError("MeshGeometry must have at least one face")

    anchor = _mesh_bbox_min(mesh)

    # Dedupe vertices: identical coordinates map to one IfcCartesianPoint.
    point_cache: dict[tuple[float, float, float], object] = {}
    # Per-input-index → IfcCartesianPoint (keeps faces' index references valid).
    points_by_input_index: list[object] = []
    for v in mesh.vertices:
        key = (
            float(v.x) - anchor.x,
            float(v.y) - anchor.y,
            float(v.z) - anchor.z,
        )
        cached = point_cache.get(key)
        if cached is None:
            cached = ifc.create_entity("IfcCartesianPoint", Coordinates=key)
            point_cache[key] = cached
        points_by_input_index.append(cached)

    ifc_faces: list[object] = []
    for face_indices in mesh.faces:
        # Resolve indices to deduplicated points; collapse consecutive duplicates
        # but keep n-gon shape (no triangulation).
        loop_points: list[object] = []
        for idx in face_indices:
            pt = points_by_input_index[idx]
            if loop_points and loop_points[-1] is pt:
                continue
            loop_points.append(pt)
        # Trim closing duplicate (last == first).
        if len(loop_points) > 1 and loop_points[0] is loop_points[-1]:
            loop_points.pop()
        if len(loop_points) < 3:
            continue
        polyloop = ifc.create_entity("IfcPolyLoop", Polygon=loop_points)
        bound = ifc.create_entity(
            "IfcFaceOuterBound", Bound=polyloop, Orientation=True
        )
        face = ifc.create_entity("IfcFace", Bounds=[bound])
        ifc_faces.append(face)

    if not ifc_faces:
        raise ValueError("MeshGeometry produced no valid faces (all degenerate)")

    closed_shell = ifc.create_entity("IfcClosedShell", CfsFaces=ifc_faces)
    return ifc.create_entity("IfcFacetedBrep", Outer=closed_shell)


def _add_mesh_product(
    ifc,
    mapped: MappedEntity,
    *,
    ifc_class: str,
    parent_storey,
    predefined_type: str | None = None,
) -> object:
    """Create an IFC product from a MESH-bearing MappedEntity.

    Used by ``add_furniture``, ``add_cooling_equipment`` and
    ``add_cable_carrier`` to emit a faceted Brep representation when the
    DXF source is a MESH (post accoreconsole pre-processing) rather than
    a 2D extrusion proxy. Placement is at the mesh's bbox-min so the
    Brep stays in LOCAL coordinates.
    """
    if not isinstance(mapped.geometry, MeshGeometry):
        raise TypeError(
            f"_add_mesh_product expects MeshGeometry, got {type(mapped.geometry).__name__}"
        )

    create_kwargs: dict[str, object] = {"ifc_class": ifc_class, "name": mapped.layer}
    if predefined_type is not None:
        create_kwargs["predefined_type"] = predefined_type
    product = ifcopenshell.api.run("root.create_entity", ifc, **create_kwargs)

    anchor = _mesh_bbox_min(mapped.geometry)
    matrix = _z_rotation_matrix(anchor.x, anchor.y, anchor.z, 0.0)
    ifcopenshell.api.run(
        "geometry.edit_object_placement",
        ifc,
        product=product,
        matrix=matrix,
        is_si=False,
    )

    brep = _mesh_to_brep(ifc, mapped.geometry)
    _attach_brep_representation(ifc, product, brep)

    ifcopenshell.api.run(
        "spatial.assign_container",
        ifc,
        products=[product],
        relating_structure=parent_storey,
    )
    return product


def _attach_brep_representation(ifc, product, brep) -> object:
    """Wrap an IfcFacetedBrep in an IfcShapeRepresentation (RepresentationType
    = "Brep") on the model's Body sub-context and assign it to ``product``."""
    model_ctx = [
        c
        for c in ifc.by_type("IfcGeometricRepresentationSubContext")
        if c.ContextIdentifier == "Body"
    ][0]
    shape = ifc.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=model_ctx,
        RepresentationIdentifier="Body",
        RepresentationType="Brep",
        Items=[brep],
    )
    product.Representation = ifc.create_entity(
        "IfcProductDefinitionShape", Representations=[shape]
    )
    return shape
