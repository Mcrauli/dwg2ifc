"""Pre-conversion geometric outlier detection.

Solibri's "Mallit laajasti hajallaan" rule fires when an IFC contains
products that are far from the rest of the model. The most common cause
is a stray DXF entity drafted at a coordinate hundreds of metres from
the building proper — usually leftover from an earlier xref insertion
or an accidental drag in AutoCAD. Once the IFC is open in Solibri the
warning is generic, so this module flags the offenders during DXF read
with the original handle + layer so the user can find them in AutoCAD
before re-converting.

Detection strategy: Tukey's fences on the per-entity distance from
the median centroid. An entity whose distance exceeds
``Q3 + 3 * IQR`` is flagged. A 50 m floor on the threshold prevents
false positives in tightly modelled spaces where IQR is essentially
zero. The 3× multiplier (vs. Tukey's classic 1.5×) is intentional —
we want to catch egregious xref leftovers, not normal wide buildings.
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

OUTLIER_FLOOR_MM: float = 50_000.0  # 50 m absolute minimum threshold
OUTLIER_IQR_MULTIPLIER: float = 3.0  # how many IQRs past Q3 = outlier


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


def _percentile(sorted_values: list[float], pct: float) -> float:
    """Linear-interpolation percentile (matches NumPy's default)."""
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (len(sorted_values) - 1) * pct / 100.0
    lo = int(math.floor(rank))
    hi = int(math.ceil(rank))
    if lo == hi:
        return sorted_values[lo]
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (rank - lo)


def find_geometric_outliers(
    records: list[EntityRecord],
    *,
    threshold_mm: float | None = None,
    floor_mm: float = OUTLIER_FLOOR_MM,
    iqr_multiplier: float = OUTLIER_IQR_MULTIPLIER,
) -> list[dict[str, Any]]:
    """Flag entities whose centroid is far from the model's central cluster.

    By default the threshold is computed adaptively as
    ``max(floor_mm, Q3 + iqr_multiplier * IQR)`` of the per-entity
    distance distribution. The cluster centre is the per-axis median —
    robust against the very outliers we are trying to find.

    Pass an explicit ``threshold_mm`` to force a fixed cutoff (useful
    in tests or when the user wants a hard ceiling regardless of model
    spread).

    Returns a list of warning dicts with the same shape as
    :class:`dxf2ifc.core.quality.ValidationReport.warnings` entries.
    """
    centroids: list[tuple[EntityRecord, tuple[float, float, float]]] = []
    for record in records:
        c = entity_centroid(record)
        if c is None:
            continue
        centroids.append((record, c))

    if len(centroids) < 2:
        return []

    median_x = median(c[1][0] for c in centroids)
    median_y = median(c[1][1] for c in centroids)
    median_z = median(c[1][2] for c in centroids)

    distances: list[float] = []
    for _, (cx, cy, cz) in centroids:
        dx = cx - median_x
        dy = cy - median_y
        dz = cz - median_z
        distances.append(math.sqrt(dx * dx + dy * dy + dz * dz))

    if threshold_mm is None:
        sorted_d = sorted(distances)
        q1 = _percentile(sorted_d, 25)
        q3 = _percentile(sorted_d, 75)
        iqr = q3 - q1
        threshold_mm = max(floor_mm, q3 + iqr_multiplier * iqr)

    warnings: list[dict[str, Any]] = []
    for (record, (cx, cy, cz)), distance in zip(centroids, distances):
        if distance <= threshold_mm:
            continue
        distance_m = distance / 1000.0
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
                    f"{record.layer} handle {record.handle or '?'} "
                    f"on {distance_m:.0f} m irrallaan muusta mallista"
                ),
            }
        )
    return warnings
