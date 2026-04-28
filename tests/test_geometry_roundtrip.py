"""End-to-end roundtrip test: real-world-ish DXF → IFC → per-layer asserts.

Bugfix 7 step 3: a single broad-coverage test that exercises every
default-profile layer type at once and verifies (a) the expected
number of IFC entities per type are produced and (b) each entity's
placement origin matches its DXF source location within 50 mm. This
catches regressions where one element-type silently gets dropped or
gets misplaced (e.g. the 1000× world-coords bug fixed in Bugfix 4).

Tighter per-shape bbox assertions live in tests/test_geometry_dimensions.py.
"""

from __future__ import annotations

from pathlib import Path

import ifcopenshell
import pytest

from dxf2ifc.core.ifc_writer import convert_dxf
from dxf2ifc.profiles.loader import load_default_profile


def _origin(product) -> tuple[float, float, float]:
    coords = product.ObjectPlacement.RelativePlacement.Location.Coordinates
    return float(coords[0]), float(coords[1]), float(coords[2])


def _approx_xy(
    actual: tuple[float, float, float], expected_xy: tuple[float, float], tol_mm: float = 50.0
) -> None:
    assert actual[0] == pytest.approx(expected_xy[0], abs=tol_mm)
    assert actual[1] == pytest.approx(expected_xy[1], abs=tol_mm)


def test_full_kylmaelement_roundtrip_per_layer(full_kylmaelement_dxf: Path, tmp_path: Path) -> None:
    out = tmp_path / "full_kylmaelement.ifc"
    convert_dxf(dxf_path=full_kylmaelement_dxf, output_path=out, profile=load_default_profile())

    ifc = ifcopenshell.open(str(out))
    assert ifc.schema == "IFC4"

    # Expected one entity of each IFC type from the fixture's 11 layers.
    walls = ifc.by_type("IfcWall")
    slabs = ifc.by_type("IfcSlab")
    doors = ifc.by_type("IfcDoor")
    windows = ifc.by_type("IfcWindow")
    pipes = ifc.by_type("IfcPipeSegment")
    cables = ifc.by_type("IfcCableCarrierSegment")
    furniture = ifc.by_type("IfcFurniture")
    proxies = ifc.by_type("IfcBuildingElementProxy")
    evaporators = ifc.by_type("IfcEvaporator")

    assert len(walls) == 2, f"expected 2 walls (US + VS), got {len(walls)}"
    assert len(slabs) == 1, f"expected 1 slab (AP), got {len(slabs)}"
    assert len(doors) == 1, f"expected 1 door, got {len(doors)}"
    assert len(windows) == 1, f"expected 1 window, got {len(windows)}"
    assert len(pipes) == 2, f"expected 2 pipes (LT IMU + KYL-VIEMARI), got {len(pipes)}"
    assert len(cables) == 1, f"expected 1 cable carrier, got {len(cables)}"
    assert len(furniture) == 1, f"expected 1 shelving furniture, got {len(furniture)}"
    assert len(proxies) == 1, f"expected 1 cold-room panel proxy, got {len(proxies)}"
    assert len(evaporators) == 1, f"expected 1 evaporator, got {len(evaporators)}"

    # Placement origins (XY) should match the DXF source coordinates within 50 mm.
    by_layer = {
        p.Name: p
        for p in walls
        + slabs
        + doors
        + windows
        + pipes
        + cables
        + furniture
        + proxies
        + evaporators
        if p.Name
    }
    _approx_xy(_origin(by_layer["KYL-ULKOSEINA"]), (0.0, 0.0))
    _approx_xy(_origin(by_layer["KYL-VALISEINA"]), (0.0, 0.0))
    _approx_xy(_origin(by_layer["KYL-ALAPOHJA"]), (0.0, 0.0))
    _approx_xy(_origin(by_layer["KYL-OVET-ULKO"]), (1500.0, 0.0))
    _approx_xy(_origin(by_layer["KYL-IKKUNA-MUOVI"]), (3000.0, 0.0))
    _approx_xy(_origin(by_layer["LT IMU"]), (0.0, 6000.0))
    _approx_xy(_origin(by_layer["KYL-VIEMARI-LATTIA"]), (0.0, 7000.0))
    _approx_xy(_origin(by_layer["KAAPELIHYLLY"]), (0.0, 8000.0))
    _approx_xy(_origin(by_layer["KYL-LEVYHYLLY"]), (4500.0, 1500.0))
    _approx_xy(_origin(by_layer["KYL-LEVY"]), (0.0, 0.0))
    _approx_xy(_origin(by_layer["KYL-HOYRYSTIN-CR-30"]), (4500.0, 4500.0))


def test_full_kylmaelement_furniture_renders_thin_shelf(
    full_kylmaelement_dxf: Path, tmp_path: Path
) -> None:
    """The KYL-LEVYHYLLY block must render as a thin shelf (~60 mm) once
    the default-profile rule sets default_height_mm. Without the fix this
    assertion sees the 2000 mm fallback height and fails."""
    out = tmp_path / "full_kylmaelement.ifc"
    convert_dxf(dxf_path=full_kylmaelement_dxf, output_path=out, profile=load_default_profile())

    ifc = ifcopenshell.open(str(out))
    furn = ifc.by_type("IfcFurniture")[0]
    extruded = furn.Representation.Representations[0].Items[0]
    assert extruded.Depth == pytest.approx(60.0, abs=1.0), (
        f"KYL-LEVYHYLLY rendered with extrusion depth {extruded.Depth} mm — "
        "expected ~60 mm thin shelf, not a 2000 mm column."
    )
