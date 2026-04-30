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
    """Skip integration tests when their external dependency is missing.

    * ``@pytest.mark.solibri`` — needs ``Solibri.exe`` on PATH (Plan F).
    * ``@pytest.mark.accoreconsole`` — needs AutoCAD's headless core under
      ``%ProgramFiles%\\Autodesk\\AutoCAD *``.
    """
    if not shutil.which("Solibri.exe"):
        skip_solibri = pytest.mark.skip(reason="Solibri.exe not on PATH")
        for item in items:
            if "solibri" in item.keywords:
                item.add_marker(skip_solibri)

    try:
        from dxf2ifc.core.preprocessing import find_accoreconsole
        accoreconsole_available = find_accoreconsole() is not None
    except Exception:
        accoreconsole_available = False
    if not accoreconsole_available:
        skip_acc = pytest.mark.skip(
            reason="accoreconsole.exe not found under Program Files\\Autodesk"
        )
        for item in items:
            if "accoreconsole" in item.keywords:
                item.add_marker(skip_acc)


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


@pytest.fixture
def full_kylmaelement_two_storey_dxf(tmp_path: Path) -> Path:
    """Plan G Task 17: a two-storey variant of ``full_kylmaelement_dxf``.

    Storey 1 (z=0) has the wall, partition, slab, door, window, cooling
    pipe and drain pipe. Storey 2 (z=3500) gets the cable carrier, cold-
    room panel, storage shelf and evaporator. The orchestrator picks
    each entity's storey by anchor-Z, so this fixture asserts the
    multi-storey routing end-to-end.
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

    blocks_storey1 = [
        ("OVI-ULKO", "KYL-OVET-ULKO", (1500.0, 0.0, 0.0)),
        ("IKKUNA", "KYL-IKKUNA-MUOVI", (3000.0, 0.0, 0.0)),
    ]
    blocks_storey2 = [
        ("KLHYLLY-LEVY", "KYL-LEVYHYLLY", (4500.0, 1500.0, 3500.0)),
        ("HOYRYSTIN", "KYL-HOYRYSTIN-CR-30", (4500.0, 4500.0, 3500.0)),
    ]
    for block_name, _, _ in (*blocks_storey1, *blocks_storey2):
        block = doc.blocks.new(name=block_name)
        block.add_line((0.0, 0.0), (500.0, 0.0))

    msp = doc.modelspace()
    # Storey 1 (z=0)
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
    # Storey 2 (z=3500)
    msp.add_line(
        (0.0, 8000.0, 3500.0),
        (3000.0, 8000.0, 3500.0),
        dxfattribs={"layer": "KAAPELIHYLLY"},
    )
    msp.add_lwpolyline(
        [(6000.0, 0.0), (8000.0, 0.0), (8000.0, 2700.0), (6000.0, 2700.0)],
        close=True,
        dxfattribs={"layer": "KYL-LEVY", "elevation": 3500.0},
    )
    for block_name, layer, insertion in (*blocks_storey1, *blocks_storey2):
        msp.add_blockref(block_name, insertion, dxfattribs={"layer": layer})

    path = tmp_path / "full_kylmaelement_two_storey.dxf"
    doc.saveas(str(path))
    return path
