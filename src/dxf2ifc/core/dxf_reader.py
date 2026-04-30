"""Read a DXF file and produce a list of EntityRecord objects.

Plan A handles only LINE entities. Plan B extends with LWPOLYLINE, 3DSOLID, INSERT.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Mapping

import ezdxf
from ezdxf.render import MeshBuilder

from dxf2ifc.core.types import (
    BlockInstance,
    EntityRecord,
    LineGeometry,
    MeshGeometry,
    Point3D,
    PolygonGeometry,
)


def list_layers(path: str | Path) -> list[str]:
    """Return the unique layer names referenced by model-space entities, sorted."""
    doc = ezdxf.readfile(str(path))
    layers = {entity.dxf.layer for entity in doc.modelspace()}
    return sorted(layers)


def read_dxf(
    path: str | Path,
    *,
    acis_meshes: Mapping[str, object] | None = None,
) -> list[EntityRecord]:
    """Parse a DXF and return every supported entity in model space.

    ``acis_meshes`` is the side-channel produced by
    :func:`dxf2ifc.core.preprocessing.extract_acis_meshes` — a mapping
    from upper-case DXF entity handle to an :class:`AcisMeshData`-like
    object exposing ``.vertices`` and ``.faces``. When a 3DSOLID entity's
    handle is in this mapping, its triangulated mesh is yielded as a
    :class:`MeshGeometry`; when not, the body is silently skipped (ezdxf
    cannot parse the SAB-encoded body itself).
    """
    doc = ezdxf.readfile(str(path))
    msp = doc.modelspace()
    acis_meshes = acis_meshes or {}

    # Layers carrying at least one 3D mesh source — either a MESH entity
    # (manually MESHSMOOTHed by the user) or a 3DSOLID whose handle landed
    # in ``acis_meshes`` from accoreconsole+STLOUT preprocessing. KYL-* LISP
    # blocks emit BOTH a 2D LWPOLYLINE outline AND a 3DSOLID body — without
    # this filter we'd publish each shelf twice (extruded outline + faceted
    # mesh). Priority: MeshGeometry wins; LWPOLYLINE/INSERT/LINE on the same
    # layer are dropped to avoid duplicate IFC products.
    mesh_priority_layers: set[str] = set()
    for entity in msp:
        dxftype = entity.dxftype()
        if dxftype == "MESH":
            mesh_priority_layers.add(entity.dxf.layer)
        elif (
            dxftype == "3DSOLID"
            and str(entity.dxf.handle).upper() in acis_meshes
        ):
            mesh_priority_layers.add(entity.dxf.layer)

    records: list[EntityRecord] = []
    for entity in msp:
        dxftype = entity.dxftype()
        # Drop 2D fallback shapes when a faithful 3D mesh exists for the
        # same layer (e.g. KYL-LEVYHYLLY draws both an LWPOLYLINE outline
        # AND a 3DSOLID body — the mesh wins). INSERTs are NOT filtered
        # here: each INSERT may carry its own mesh in ``acis_meshes`` and
        # represents a distinct physical thing on the layer.
        if (
            dxftype in ("LINE", "LWPOLYLINE")
            and entity.dxf.layer in mesh_priority_layers
        ):
            continue
        if dxftype == "3DSOLID":
            handle = str(entity.dxf.handle).upper()
            mesh_data = acis_meshes.get(handle)
            if mesh_data is None:
                # ezdxf cannot parse SAB ACIS bodies and accoreconsole did
                # not produce a mesh for this handle — drop silently.
                continue
            vertices = tuple(
                Point3D(float(v[0]), float(v[1]), float(v[2]))
                for v in mesh_data.vertices
            )
            faces = tuple(tuple(int(i) for i in f) for f in mesh_data.faces)
            if not vertices or not faces:
                continue
            records.append(
                EntityRecord(
                    layer=entity.dxf.layer,
                    dxf_type="3DSOLID",
                    geometry=MeshGeometry(vertices=vertices, faces=faces),
                    attributes={},
                )
            )
            continue
        if dxftype == "LINE":
            start = Point3D(*entity.dxf.start)
            end = Point3D(*entity.dxf.end)
            records.append(
                EntityRecord(
                    layer=entity.dxf.layer,
                    dxf_type="LINE",
                    geometry=LineGeometry(start=start, end=end),
                    attributes={},
                )
            )
        elif dxftype == "LWPOLYLINE" and entity.closed:
            elevation = float(entity.dxf.elevation or 0.0)
            ocs = entity.ocs()
            world_vertices: list[Point3D] = []
            for x, y, *_ in entity.get_points():
                wx, wy, wz = ocs.to_wcs((float(x), float(y), elevation))
                world_vertices.append(Point3D(float(wx), float(wy), float(wz)))
            records.append(
                EntityRecord(
                    layer=entity.dxf.layer,
                    dxf_type="LWPOLYLINE",
                    geometry=PolygonGeometry(vertices=tuple(world_vertices), closed=True),
                    attributes={},
                )
            )
        elif dxftype == "INSERT":
            handle = str(entity.dxf.handle).upper()
            mesh_data = acis_meshes.get(handle)
            if mesh_data is not None:
                # accoreconsole EXPLODEd this INSERT and STLOUTed every
                # 3DSOLID/MESH child; the merged mesh is in world coords
                # (EXPLODE applies the block's transform). Emit as a real
                # faceted body instead of the bbox extrusion fallback.
                vertices = tuple(
                    Point3D(float(v[0]), float(v[1]), float(v[2]))
                    for v in mesh_data.vertices
                )
                faces = tuple(tuple(int(i) for i in f) for f in mesh_data.faces)
                if vertices and faces:
                    records.append(
                        EntityRecord(
                            layer=entity.dxf.layer,
                            dxf_type="INSERT",
                            geometry=MeshGeometry(vertices=vertices, faces=faces),
                            attributes={},
                            block_name=entity.dxf.name,
                        )
                    )
                    continue
            insert = Point3D(
                float(entity.dxf.insert.x),
                float(entity.dxf.insert.y),
                float(entity.dxf.insert.z),
            )
            block_instance = BlockInstance(
                insertion_point=insert,
                rotation_rad=math.radians(float(entity.dxf.rotation or 0.0)),
                scale_x=float(entity.dxf.xscale or 1.0),
                scale_y=float(entity.dxf.yscale or 1.0),
                scale_z=float(entity.dxf.zscale or 1.0),
            )
            records.append(
                EntityRecord(
                    layer=entity.dxf.layer,
                    dxf_type="INSERT",
                    geometry=block_instance,
                    attributes={},
                    block_name=entity.dxf.name,
                )
            )
        elif dxftype == "MESH":
            # accoreconsole.exe -MESHSMOOTH preprocesses 3DSOLIDs into MESH.
            # MeshBuilder.from_mesh extracts the deduplicated vertex pool
            # and the face index list (each face is n>=3 indices for n-gons).
            mb = MeshBuilder.from_mesh(entity)
            vertices = tuple(
                Point3D(float(v.x), float(v.y), float(v.z)) for v in mb.vertices
            )
            faces = tuple(tuple(int(i) for i in f) for f in mb.faces)
            if not vertices or not faces:
                continue  # skip degenerate / empty mesh
            records.append(
                EntityRecord(
                    layer=entity.dxf.layer,
                    dxf_type="MESH",
                    geometry=MeshGeometry(vertices=vertices, faces=faces),
                    attributes={},
                )
            )
    return records
