"""Pre-conversion geometric outlier detection.

Solibri's "Mallit laajasti hajallaan" rule fires when an IFC contains
products that are far from the rest of the model. The most common cause
is a stray DXF entity drafted at a coordinate hundreds of metres from
the building proper — usually leftover from an earlier xref insertion
or an accidental drag in AutoCAD. Once the IFC is open in Solibri the
warning is generic, so this module flags the offenders during DXF read
with the original handle + layer so the user can find them in AutoCAD
before re-converting.

The check is robust against the model itself being far from origin
(WCS in metres or UTM-style coordinates): the cluster centre is the
median centroid, not the origin, so only entities that are far from
their *peers* are reported.
"""

from __future__ import annotations

import math
from statistics import median
from typing import Any

from dxf2ifc.core.types import (
    BlockInstance,
    EntityRecord,
    LineGeometry,
    MeshGeometry,
    PolygonGeometry,
)

DEFAULT_OUTLIER_THRESHOLD_MM: float = 100_000.0  # 100 m


def entity_centroid(record: EntityRecord) -> tuple[float, float, float] | None:
    """Return the geometric centroid (XYZ in mm) of an EntityRecord.

    Centroid definition per geometry kind:
        LineGeometry     midpoint of start/end
        PolygonGeometry  bounding-box centre of vertices
        BlockInstance    insertion point
        MeshGeometry     bounding-box centre of vertex pool
    Anything else returns ``None`` (skipped from the cluster).
    """
    geom = record.geometry
    if isinstance(geom, LineGeometry):
        return (
            (geom.start.x + geom.end.x) / 2.0,
            (geom.start.y + geom.end.y) / 2.0,
            (geom.start.z + geom.end.z) / 2.0,
        )
    if isinstance(geom, PolygonGeometry):
        if not geom.vertices:
            return None
        xs = [v.x for v in geom.vertices]
        ys = [v.y for v in geom.vertices]
        zs = [v.z for v in geom.vertices]
        return (
            (min(xs) + max(xs)) / 2.0,
            (min(ys) + max(ys)) / 2.0,
            (min(zs) + max(zs)) / 2.0,
        )
    if isinstance(geom, BlockInstance):
        p = geom.insertion_point
        return (p.x, p.y, p.z)
    if isinstance(geom, MeshGeometry):
        if not geom.vertices:
            return None
        xs = [v.x for v in geom.vertices]
        ys = [v.y for v in geom.vertices]
        zs = [v.z for v in geom.vertices]
        return (
            (min(xs) + max(xs)) / 2.0,
            (min(ys) + max(ys)) / 2.0,
            (min(zs) + max(zs)) / 2.0,
        )
    return None


def find_geometric_outliers(
    records: list[EntityRecord],
    *,
    threshold_mm: float = DEFAULT_OUTLIER_THRESHOLD_MM,
) -> list[dict[str, Any]]:
    """Flag entities whose centroid is more than ``threshold_mm`` from the
    median centroid of the whole record list.

    The cluster centre is the per-axis median of all centroids. Median is
    robust against the very outliers we are trying to find — a single
    stray entity at X=1 km does not pull the cluster centre with it.

    Returns a list of warning dicts with the same shape as
    :class:`dxf2ifc.core.quality.ValidationReport.warnings` entries
    (level/type/message + extras for traceability).
    """
    centroids: list[tuple[EntityRecord, tuple[float, float, float]]] = []
    for record in records:
        c = entity_centroid(record)
        if c is None:
            continue
        centroids.append((record, c))

    if len(centroids) < 2:
        # Cannot define an outlier from a single point; skip cleanly.
        return []

    median_x = median(c[1][0] for c in centroids)
    median_y = median(c[1][1] for c in centroids)
    median_z = median(c[1][2] for c in centroids)

    warnings: list[dict[str, Any]] = []
    for record, (cx, cy, cz) in centroids:
        dx = cx - median_x
        dy = cy - median_y
        dz = cz - median_z
        distance = math.sqrt(dx * dx + dy * dy + dz * dz)
        if distance <= threshold_mm:
            continue
        warnings.append(
            {
                "level": "WARNING",
                "type": "geometric_outlier",
                "layer": record.layer,
                "dxf_type": record.dxf_type,
                "handle": record.handle,
                "centroid_mm": (cx, cy, cz),
                "median_mm": (median_x, median_y, median_z),
                "distance_mm": distance,
                "threshold_mm": threshold_mm,
                "message": (
                    f"{record.layer} {record.dxf_type} "
                    f"handle {record.handle or '?'} at "
                    f"({cx:.0f}, {cy:.0f}, {cz:.0f}) mm is "
                    f"{distance:.0f} mm from model centre "
                    f"({median_x:.0f}, {median_y:.0f}, {median_z:.0f}) mm — "
                    f"likely a stray entity (drafting error or leftover xref)"
                ),
            }
        )
    return warnings
