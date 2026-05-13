"""Multi-floor: two DXF files -> one IFC with two storeys."""

from pathlib import Path

import ezdxf
import ifcopenshell
import pytest

from dxf2ifc.core.ifc_writer import FileEntry, convert
from dxf2ifc.profiles.loader import load_default_profile


def _write_minimal_dxf(path: Path, layer: str = "KYL-LEVYHYLLY") -> None:
    """Tiny DXF with one closed LWPOLYLINE on ``layer`` — maps via default
    profile to IfcCableCarrierSegment (CABLETRAYSEGMENT)."""
    doc = ezdxf.new("R2018")
    doc.layers.add(layer)
    msp = doc.modelspace()
    msp.add_lwpolyline(
        [(0, 0), (1000, 0), (1000, 1000), (0, 1000)],
        format="xy",
        close=True,
        dxfattribs={"layer": layer},
    )
    doc.saveas(str(path))


def test_multi_floor_produces_two_storeys(tmp_path):
    floor1 = tmp_path / "1krs.dxf"
    floor2 = tmp_path / "2krs.dxf"
    _write_minimal_dxf(floor1)
    _write_minimal_dxf(floor2)
    out = tmp_path / "out.ifc"

    convert(
        files=[
            FileEntry(path=floor1, floor_label="1.krs", elevation_mm=0.0),
            FileEntry(path=floor2, floor_label="2.krs", elevation_mm=3500.0),
        ],
        output_path=out,
        profile=load_default_profile(),
        preprocess_acis=False,
    )

    ifc = ifcopenshell.open(str(out))
    storeys = ifc.by_type("IfcBuildingStorey")
    assert len(storeys) == 2
    by_name = {s.Name: s for s in storeys}
    assert set(by_name) == {"1.krs", "2.krs"}
    assert by_name["1.krs"].Elevation == 0.0
    assert by_name["2.krs"].Elevation == 3500.0


def test_multi_floor_rejects_empty_list(tmp_path):
    out = tmp_path / "x.ifc"
    with pytest.raises(ValueError, match="at least one"):
        convert(
            files=[],
            output_path=out,
            profile=load_default_profile(),
            preprocess_acis=False,
        )


def test_multi_floor_rejects_duplicate_labels(tmp_path):
    floor1 = tmp_path / "1krs.dxf"
    floor2 = tmp_path / "duplicate.dxf"
    _write_minimal_dxf(floor1)
    _write_minimal_dxf(floor2)
    out = tmp_path / "x.ifc"

    with pytest.raises(ValueError, match="duplicate"):
        convert(
            files=[
                FileEntry(path=floor1, floor_label="1.krs", elevation_mm=0.0),
                FileEntry(path=floor2, floor_label="1.krs", elevation_mm=3500.0),
            ],
            output_path=out,
            profile=load_default_profile(),
            preprocess_acis=False,
        )


def test_multi_floor_rejects_empty_label(tmp_path):
    floor1 = tmp_path / "1krs.dxf"
    _write_minimal_dxf(floor1)
    out = tmp_path / "x.ifc"

    with pytest.raises(ValueError, match="floor_label"):
        convert(
            files=[FileEntry(path=floor1, floor_label="  ", elevation_mm=0.0)],
            output_path=out,
            profile=load_default_profile(),
            preprocess_acis=False,
        )


def test_multi_floor_products_attached_to_correct_storeys(tmp_path):
    """Elements from each input file land on the matching storey via
    IfcRelContainedInSpatialStructure."""
    floor1 = tmp_path / "1krs.dxf"
    floor2 = tmp_path / "2krs.dxf"
    _write_minimal_dxf(floor1)
    _write_minimal_dxf(floor2)
    out = tmp_path / "out.ifc"

    convert(
        files=[
            FileEntry(path=floor1, floor_label="1.krs", elevation_mm=0.0),
            FileEntry(path=floor2, floor_label="2.krs", elevation_mm=3500.0),
        ],
        output_path=out,
        profile=load_default_profile(),
        preprocess_acis=False,
    )

    ifc = ifcopenshell.open(str(out))
    rels = ifc.by_type("IfcRelContainedInSpatialStructure")
    storey_buckets: dict[str, int] = {}
    for rel in rels:
        storey = rel.RelatingStructure
        storey_buckets[storey.Name] = storey_buckets.get(storey.Name, 0) + len(
            rel.RelatedElements
        )
    # Each file contributes at least one product to its own storey.
    assert storey_buckets.get("1.krs", 0) >= 1
    assert storey_buckets.get("2.krs", 0) >= 1
