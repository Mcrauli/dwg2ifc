"""convert_dxf must keep working as a single-file shim around convert()."""

from pathlib import Path

import ezdxf
import ifcopenshell

from dwg2ifc.core.ifc_writer import convert_dxf
from dwg2ifc.profiles.loader import load_default_profile


def _write_minimal_dxf(path: Path, layer: str = "KYL-LEVYHYLLY") -> None:
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


def test_convert_dxf_single_file_emits_one_storey_named_1_krs(tmp_path):
    src = tmp_path / "in.dxf"
    out = tmp_path / "out.ifc"
    _write_minimal_dxf(src)

    convert_dxf(
        dxf_path=src,
        output_path=out,
        profile=load_default_profile(),
        preprocess_acis=False,
    )

    ifc = ifcopenshell.open(str(out))
    storeys = ifc.by_type("IfcBuildingStorey")
    assert len(storeys) == 1
    assert storeys[0].Name == "1.krs"
    assert storeys[0].Elevation == 0.0


def test_convert_dxf_with_floor_elevation_passes_through(tmp_path):
    src = tmp_path / "in.dxf"
    out = tmp_path / "out.ifc"
    _write_minimal_dxf(src)

    convert_dxf(
        dxf_path=src,
        output_path=out,
        profile=load_default_profile(),
        floor_elevation_mm=3500.0,
        preprocess_acis=False,
    )

    ifc = ifcopenshell.open(str(out))
    storey = ifc.by_type("IfcBuildingStorey")[0]
    assert storey.Elevation == 3500.0
