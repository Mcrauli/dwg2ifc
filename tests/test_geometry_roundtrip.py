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
