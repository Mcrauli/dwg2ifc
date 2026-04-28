"""Shared pytest fixtures for dxf2ifc tests."""

import os
import shutil
from pathlib import Path

import ezdxf
import pytest

# Force the offscreen QPA platform before PySide6 / pytest-qt is imported so that
# GUI tests run headlessly in CI and sandboxed environments without a display.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def pytest_collection_modifyitems(config, items):
    """Skip any test marked @pytest.mark.solibri when Solibri.exe is not on
    PATH (Plan F Section 4 Task 13). Lauri runs these locally on Windows."""
    if shutil.which("Solibri.exe"):
        return
    skip_marker = pytest.mark.skip(reason="Solibri.exe not on PATH")
    for item in items:
        if "solibri" in item.keywords:
            item.add_marker(skip_marker)


@pytest.fixture
def fixtures_dir() -> Path:
    """Absolute path to the tests/fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def full_kylmaelement_dxf(tmp_path: Path) -> Path:
    """Generate a DXF that exercises every Section 2–11 element type.

    The result is one wall, one partition, one floor slab, one door
    block, one window block, one cooling pipe, one drain pipe, one
    storage shelf block, one cable carrier line, one cold-room panel,
    and one evaporator block — all on dxf2ifc's default-profile layers.
    """
    doc = ezdxf.new("R2010")
    layers = [
        "KYL-ULKOSEINA",
        "KYL-VALISEINA",
        "KYL-ALAPOHJA",
        "KYL-OVET-ULKO",
        "KYL-IKKUNA-MUOVI",
        "LT IMU",
        "KYL-VIEMARI-LATTIA",
        "KYL-LEVYHYLLY",
        "KAAPELIHYLLY",
        "KYL-LEVY",
        "KYL-HOYRYSTIN-CR-30",
    ]
    for name in layers:
        doc.layers.add(name=name)

    blocks = [
        ("OVI-ULKO", "KYL-OVET-ULKO", (1500.0, 0.0)),
        ("IKKUNA", "KYL-IKKUNA-MUOVI", (3000.0, 0.0)),
        ("KLHYLLY-LEVY", "KYL-LEVYHYLLY", (4500.0, 1500.0)),
        ("HOYRYSTIN", "KYL-HOYRYSTIN-CR-30", (4500.0, 4500.0)),
    ]
    for block_name, _, _ in blocks:
        block = doc.blocks.new(name=block_name)
        block.add_line((0.0, 0.0), (500.0, 0.0))

    msp = doc.modelspace()
    msp.add_line((0.0, 0.0, 0.0), (5000.0, 0.0, 0.0), dxfattribs={"layer": "KYL-ULKOSEINA"})
    msp.add_line((0.0, 0.0, 0.0), (4000.0, 0.0, 0.0), dxfattribs={"layer": "KYL-VALISEINA"})
    msp.add_lwpolyline(
        [(0.0, 0.0), (4000.0, 0.0), (4000.0, 3000.0), (0.0, 3000.0)],
        close=True,
        dxfattribs={"layer": "KYL-ALAPOHJA"},
    )
    msp.add_line((0.0, 6000.0, 0.0), (3000.0, 6000.0, 0.0), dxfattribs={"layer": "LT IMU"})
    msp.add_line(
        (0.0, 7000.0, 0.0),
        (3000.0, 7000.0, 0.0),
        dxfattribs={"layer": "KYL-VIEMARI-LATTIA"},
    )
    msp.add_line(
        (0.0, 8000.0, 2700.0),
        (3000.0, 8000.0, 2700.0),
        dxfattribs={"layer": "KAAPELIHYLLY"},
    )
    msp.add_lwpolyline(
        [(6000.0, 0.0), (8000.0, 0.0), (8000.0, 2700.0), (6000.0, 2700.0)],
        close=True,
        dxfattribs={"layer": "KYL-LEVY"},
    )
    for block_name, layer, insertion in blocks:
        msp.add_blockref(block_name, insertion, dxfattribs={"layer": layer})

    path = tmp_path / "full_kylmaelement.dxf"
    doc.saveas(str(path))
    return path
