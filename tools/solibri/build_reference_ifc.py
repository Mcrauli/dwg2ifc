"""Build tests/fixtures/solibri_reference_full.ifc — a minimal "this should
pass Solibri" baseline IFC that covers every Plan B Section 2–11 element
type. Re-runs the same DXF authoring pattern as the conftest fixture and
funnels it through ``convert_dxf`` so the file stays in lockstep with the
default Talo2000 profile.

Run from the repo root:

    python -m tools.solibri.build_reference_ifc
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import ezdxf

from dwg2ifc.core.ifc_writer import convert_dxf
from dwg2ifc.profiles.loader import load_default_profile
from dwg2ifc.profiles.schema import CRSConfig

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "solibri_reference_full.ifc"


def _author_dxf(target: Path) -> Path:
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
    for block_name in ("OVI-ULKO", "IKKUNA", "KLHYLLY-LEVY", "HOYRYSTIN"):
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
        (4000.0, 8000.0, 2700.0),
        dxfattribs={"layer": "KAAPELIHYLLY"},
    )
    msp.add_lwpolyline(
        [(5000.0, 0.0), (8000.0, 0.0), (8000.0, 3000.0), (5000.0, 3000.0)],
        close=True,
        dxfattribs={"layer": "KYL-LEVY"},
    )
    msp.add_blockref("OVI-ULKO", (1500.0, 0.0), dxfattribs={"layer": "KYL-OVET-ULKO"})
    msp.add_blockref("IKKUNA", (3000.0, 0.0), dxfattribs={"layer": "KYL-IKKUNA-MUOVI"})
    msp.add_blockref("KLHYLLY-LEVY", (4500.0, 1500.0), dxfattribs={"layer": "KYL-LEVYHYLLY"})
    msp.add_blockref("HOYRYSTIN", (4500.0, 4500.0), dxfattribs={"layer": "KYL-HOYRYSTIN-CR-30"})
    doc.saveas(str(target))
    return target


def build(output: Path = FIXTURE_PATH) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    profile = load_default_profile().model_copy(
        update={
            "crs": CRSConfig(
                eastings_mm=25_496_000.0,
                northings_mm=6_672_000.0,
                orthogonal_height_mm=0.0,
            ),
        }
    )
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        dxf_path = _author_dxf(tmp_dir / "solibri_reference_full.dxf")
        ifc_tmp = tmp_dir / "solibri_reference_full.ifc"
        convert_dxf(
            dxf_path=dxf_path,
            output_path=ifc_tmp,
            profile=profile,
            project_name="Solibri Reference (full)",
        )
        shutil.copyfile(ifc_tmp, output)
    return output


if __name__ == "__main__":
    path = build()
    print(f"Wrote {path}")
