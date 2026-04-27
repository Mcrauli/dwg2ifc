"""Read a DXF file and produce a list of EntityRecord objects.

Plan A handles only LINE entities. Plan B extends with LWPOLYLINE, 3DSOLID, INSERT.
"""

from __future__ import annotations

from pathlib import Path

import ezdxf

from dxf2ifc.core.types import EntityRecord, LineGeometry, Point3D


def read_dxf(path: str | Path) -> list[EntityRecord]:
    """Parse a DXF and return every supported entity in model space."""
    doc = ezdxf.readfile(str(path))
    msp = doc.modelspace()
    records: list[EntityRecord] = []
    for entity in msp:
        if entity.dxftype() == "LINE":
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
    return records
