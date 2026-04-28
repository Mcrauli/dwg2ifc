"""Bugfix 8: KYL-TIKASHYLLY entities drawn as inline LINEs by KLHYLLY-TIKAS LISP
must not silently disappear from the IFC.

Lauri's Solibri test (2026-04-28): KYL-TIKASHYLLY layer is populated in
the source DXF but produces zero IfcFurniture entities in the converted
IFC. Most likely cause: the KLHYLLY-TIKAS LISP draws each TIKAS shelf
as two rails + crossbars (inline LINEs) rather than as a single block
INSERT. The default profile rule matches the layer regardless of
entity kind, so add_furniture is invoked with a LineGeometry — and the
old implementation only accepted BlockInstance / PolygonGeometry.

This test reproduces the scenario with a synthetic DXF containing two
parallel rail-LINEs on KYL-TIKASHYLLY. Until add_furniture handles
LineGeometry, convert_dxf raises TypeError and zero furniture is
written. After the fix, each LINE becomes an IfcFurniture box (length
× default depth × default height); aggregation into one shelf per rail
pair is left for a follow-up.
"""

from __future__ import annotations

from pathlib import Path

import ezdxf
import ifcopenshell

from dxf2ifc.core.ifc_writer import convert_dxf
from dxf2ifc.profiles.loader import load_default_profile


def _write_tikashylly_dxf(path: Path) -> None:
    doc = ezdxf.new("R2010")
    doc.layers.add(name="KYL-TIKASHYLLY")
    msp = doc.modelspace()
    # Two parallel rails 400 mm apart, each 1200 mm long, at z = 1500 mm.
    msp.add_line((0.0, 0.0, 1500.0), (1200.0, 0.0, 1500.0), dxfattribs={"layer": "KYL-TIKASHYLLY"})
    msp.add_line(
        (0.0, 400.0, 1500.0), (1200.0, 400.0, 1500.0), dxfattribs={"layer": "KYL-TIKASHYLLY"}
    )
    doc.saveas(str(path))


def test_kyl_tikashylly_lines_produce_ifcfurniture(tmp_path: Path) -> None:
    dxf = tmp_path / "tikashylly_lines.dxf"
    _write_tikashylly_dxf(dxf)
    out = tmp_path / "tikashylly_lines.ifc"

    convert_dxf(dxf_path=dxf, output_path=out, profile=load_default_profile())

    ifc = ifcopenshell.open(str(out))
    furnitures = ifc.by_type("IfcFurniture")
    assert len(furnitures) >= 1, (
        "KYL-TIKASHYLLY LINE entities produced no IfcFurniture — add_furniture "
        "must accept LineGeometry so inline-drawn shelves do not vanish from the IFC"
    )
    assert all(f.Name == "KYL-TIKASHYLLY" for f in furnitures)
