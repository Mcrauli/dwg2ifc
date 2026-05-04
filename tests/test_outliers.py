"""Tests for geometric outlier detection (pre-conversion DXF scan)."""

from __future__ import annotations

from dxf2ifc.core.outliers import (
    DEFAULT_OUTLIER_THRESHOLD_MM,
    entity_centroid,
    find_geometric_outliers,
)
from dxf2ifc.core.types import (
    BlockInstance,
    EntityRecord,
    LineGeometry,
    MeshGeometry,
    Point3D,
    PolygonGeometry,
)


def _line_record(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    *,
    layer: str = "L",
    handle: str = "AAA",
) -> EntityRecord:
    return EntityRecord(
        layer=layer,
        dxf_type="LINE",
        geometry=LineGeometry(start=Point3D(*start), end=Point3D(*end)),
        handle=handle,
    )


def _mesh_record(
    bbox_min: tuple[float, float, float],
    bbox_max: tuple[float, float, float],
    *,
    layer: str = "M",
    handle: str = "BBB",
) -> EntityRecord:
    verts = (
        Point3D(*bbox_min),
        Point3D(bbox_max[0], bbox_min[1], bbox_min[2]),
        Point3D(bbox_max[0], bbox_max[1], bbox_min[2]),
        Point3D(*bbox_max),
    )
    return EntityRecord(
        layer=layer,
        dxf_type="3DSOLID",
        geometry=MeshGeometry(vertices=verts, faces=((0, 1, 2), (0, 2, 3))),
        handle=handle,
    )


def _block_record(
    point: tuple[float, float, float],
    *,
    layer: str = "B",
    handle: str = "CCC",
) -> EntityRecord:
    return EntityRecord(
        layer=layer,
        dxf_type="INSERT",
        geometry=BlockInstance(insertion_point=Point3D(*point)),
        block_name="X",
        handle=handle,
    )


def _polygon_record(
    points: list[tuple[float, float, float]],
    *,
    layer: str = "P",
    handle: str = "DDD",
) -> EntityRecord:
    return EntityRecord(
        layer=layer,
        dxf_type="LWPOLYLINE",
        geometry=PolygonGeometry(
            vertices=tuple(Point3D(*p) for p in points), closed=True
        ),
        handle=handle,
    )


class TestEntityCentroid:
    def test_line_midpoint(self) -> None:
        rec = _line_record((0.0, 0.0, 0.0), (10.0, 20.0, 4.0))
        assert entity_centroid(rec) == (5.0, 10.0, 2.0)

    def test_block_uses_insertion_point(self) -> None:
        rec = _block_record((100.0, 200.0, 50.0))
        assert entity_centroid(rec) == (100.0, 200.0, 50.0)

    def test_polygon_bbox_centre(self) -> None:
        rec = _polygon_record(
            [(0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (10.0, 20.0, 0.0), (0.0, 20.0, 0.0)]
        )
        assert entity_centroid(rec) == (5.0, 10.0, 0.0)

    def test_mesh_bbox_centre(self) -> None:
        rec = _mesh_record((0.0, 0.0, 0.0), (8.0, 4.0, 2.0))
        assert entity_centroid(rec) == (4.0, 2.0, 1.0)

    def test_empty_polygon_returns_none(self) -> None:
        rec = EntityRecord(
            layer="L",
            dxf_type="LWPOLYLINE",
            geometry=PolygonGeometry(vertices=(), closed=True),
        )
        assert entity_centroid(rec) is None

    def test_empty_mesh_returns_none(self) -> None:
        rec = EntityRecord(
            layer="L",
            dxf_type="3DSOLID",
            geometry=MeshGeometry(vertices=(), faces=()),
        )
        assert entity_centroid(rec) is None


class TestFindGeometricOutliers:
    def test_empty_list_yields_no_warnings(self) -> None:
        assert find_geometric_outliers([]) == []

    def test_single_entity_cannot_be_outlier(self) -> None:
        # Even a far-from-origin lone entity is fine — there's nothing to
        # be an outlier *from*.
        rec = _block_record((1_000_000.0, 0.0, 0.0))
        assert find_geometric_outliers([rec]) == []

    def test_clustered_entities_pass(self) -> None:
        records = [
            _block_record((0.0, 0.0, 0.0), handle=f"H{i}")
            for i in range(5)
        ]
        # Add a tightly clustered neighbour 1 m away
        records.append(_block_record((1000.0, 0.0, 0.0), handle="HX"))
        assert find_geometric_outliers(records) == []

    def test_single_outlier_flagged(self) -> None:
        # Cluster at origin, one stray entity 500 m away.
        records = [
            _block_record((0.0, 0.0, 0.0), layer="KYL-LEVY", handle=f"H{i}")
            for i in range(10)
        ]
        records.append(
            _block_record(
                (500_000.0, 0.0, 0.0),
                layer="KYL-TIKASHYLLY",
                handle="118A",
            )
        )
        warnings = find_geometric_outliers(records)
        assert len(warnings) == 1
        w = warnings[0]
        assert w["level"] == "WARNING"
        assert w["type"] == "geometric_outlier"
        assert w["layer"] == "KYL-TIKASHYLLY"
        assert w["handle"] == "118A"
        assert w["distance_mm"] >= 100_000
        assert "118A" in w["message"]
        assert "KYL-TIKASHYLLY" in w["message"]

    def test_model_far_from_origin_does_not_false_positive(self) -> None:
        # Whole model sits at X=730_000 mm (e.g. ETRS-TM35FIN-shifted CAD
        # data). Only the 326 m XY + 731 m Z stray should be flagged.
        cluster = [
            _mesh_record(
                (730_000.0 + i * 100, 100_000.0 + i * 100, 0.0),
                (730_500.0 + i * 100, 100_500.0 + i * 100, 3000.0),
                handle=f"H{i}",
            )
            for i in range(8)
        ]
        outlier = _mesh_record(
            (1_056_000.0, 728_000.0, 828_000.0),
            (1_057_000.0, 729_000.0, 829_000.0),
            layer="KYL-TIKASHYLLY",
            handle="118A",
        )
        warnings = find_geometric_outliers(cluster + [outlier])
        assert len(warnings) == 1
        assert warnings[0]["handle"] == "118A"

    def test_threshold_override_silences_small_offsets(self) -> None:
        records = [
            _block_record((0.0, 0.0, 0.0), handle=f"H{i}") for i in range(5)
        ]
        records.append(_block_record((150_000.0, 0.0, 0.0), handle="MID"))
        # Default 100 m → flagged
        assert any(
            w["handle"] == "MID" for w in find_geometric_outliers(records)
        )
        # Raise to 200 m → silent
        assert (
            find_geometric_outliers(records, threshold_mm=200_000.0) == []
        )

    def test_default_threshold_constant(self) -> None:
        assert DEFAULT_OUTLIER_THRESHOLD_MM == 100_000.0

    def test_unsupported_geometry_skipped_silently(self) -> None:
        # An EntityRecord with a None-ish geometry shouldn't crash the scan.
        records = [
            _block_record((0.0, 0.0, 0.0), handle=f"H{i}") for i in range(3)
        ]
        bogus = EntityRecord(
            layer="X", dxf_type="UNKNOWN", geometry=object(), handle="ZZZ"
        )
        records.append(bogus)
        # No crash; the bogus one is just ignored.
        assert find_geometric_outliers(records) == []
