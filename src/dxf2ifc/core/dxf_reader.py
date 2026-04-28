"""Read a DXF file and produce a list of EntityRecord objects.

Plan A handles only LINE entities. Plan B extends with LWPOLYLINE, 3DSOLID, INSERT.
"""

from __future__ import annotations

import math
from pathlib import Path

import ezdxf

from dxf2ifc.core.types import (
    BlockInstance,
    EntityRecord,
    LineGeometry,
    Point3D,
    PolygonGeometry,
)


def list_layers(path: str | Path) -> list[str]:
    """Return the unique layer names referenced by model-space entities, sorted."""
    doc = ezdxf.readfile(str(path))
    layers = {entity.dxf.layer for entity in doc.modelspace()}
    return sorted(layers)


def read_dxf(path: str | Path) -> list[EntityRecord]:
    """Parse a DXF and return every supported entity in model space."""
    doc = ezdxf.readfile(str(path))
    msp = doc.modelspace()
    records: list[EntityRecord] = []
    for entity in msp:
        dxftype = entity.dxftype()
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
    return records
