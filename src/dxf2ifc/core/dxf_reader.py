"""Read a DXF file and produce a list of EntityRecord objects.

Plan A handles only LINE entities. Plan B extends with LWPOLYLINE, 3DSOLID, INSERT.
"""

from __future__ import annotations

from pathlib import Path

import ezdxf

from dxf2ifc.core.types import EntityRecord, LineGeometry, Point3D, PolygonGeometry


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
            vertices = tuple(
                Point3D(float(x), float(y), elevation) for x, y, *_ in entity.get_points()
            )
            records.append(
                EntityRecord(
                    layer=entity.dxf.layer,
                    dxf_type="LWPOLYLINE",
                    geometry=PolygonGeometry(vertices=vertices, closed=True),
                    attributes={},
                )
            )
    return records
