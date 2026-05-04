"""Tests for the suunnittelualat / discipline metadata in the IFC.

Solibri's role auto-selection reads:
  1. IfcProject.LongName (top-level project hint)
  2. ``suunnittelualat`` IfcClassification on IfcProject (file-wide)
  3. ``suunnittelualat`` IfcClassificationReference on each product
We verify all three for the default refrigeration profile so opening
the IFC in Solibri picks the Jäähdytys profile without prompting.
"""

from __future__ import annotations

from pathlib import Path

from dxf2ifc.core.ifc_writer.classification import (
    DISCIPLINE_LABELS,
    discipline_label,
)
from dxf2ifc.core.ifc_writer import convert_dxf
from dxf2ifc.core.types import (
    BlockInstance,
    EntityRecord,
    LineGeometry,
    Point3D,
)
from dxf2ifc.profiles.loader import load_default_profile


def test_discipline_label_table() -> None:
    assert DISCIPLINE_LABELS["ARK"] == "ARK"
    assert DISCIPLINE_LABELS["TATE"] == "Talotekniikka"
    assert DISCIPLINE_LABELS["KYL"] == "Jäähdytys"


def test_discipline_label_returns_none_for_unknown() -> None:
    assert discipline_label("ZZZ") is None


def _write_minimal_dxf(path: Path) -> None:
    import ezdxf

    doc = ezdxf.new(dxfversion="R2018")
    doc.layers.add(name="LT IMU")
    msp = doc.modelspace()
    # One LT IMU pipe → maps to KYL-domain IfcPipeSegment in default profile.
    msp.add_line((0, 0, 0), (1000, 0, 0), dxfattribs={"layer": "LT IMU"})
    doc.saveas(str(path))


def test_jaahdytys_classification_on_products(tmp_path: Path) -> None:
    import ifcopenshell

    dxf = tmp_path / "in.dxf"
    ifc_path = tmp_path / "out.ifc"
    _write_minimal_dxf(dxf)
    convert_dxf(
        dxf_path=dxf,
        output_path=ifc_path,
        profile=load_default_profile(),
        preprocess_acis=False,
    )
    ifc = ifcopenshell.open(str(ifc_path))
    classifications = [c for c in ifc.by_type("IfcClassification") if c.Name == "suunnittelualat"]
    assert len(classifications) == 1
    refs = [
        r for r in ifc.by_type("IfcClassificationReference")
        if r.ReferencedSource == classifications[0]
    ]
    # Every ref under the suunnittelualat classification should be Jäähdytys
    # for a refrigeration-only file.
    assert refs, "no suunnittelualat references emitted"
    for r in refs:
        assert r.Identification == "Jäähdytys", (
            f"expected Identification 'Jäähdytys', got {r.Identification!r}"
        )
        assert r.Name == "Jäähdytys"


def test_project_long_name_set_to_discipline(tmp_path: Path) -> None:
    import ifcopenshell

    dxf = tmp_path / "in.dxf"
    ifc_path = tmp_path / "out.ifc"
    _write_minimal_dxf(dxf)
    convert_dxf(
        dxf_path=dxf,
        output_path=ifc_path,
        profile=load_default_profile(),
        preprocess_acis=False,
    )
    ifc = ifcopenshell.open(str(ifc_path))
    project = ifc.by_type("IfcProject")[0]
    assert project.LongName == "Jäähdytys"


def test_project_level_classification_present(tmp_path: Path) -> None:
    import ifcopenshell

    dxf = tmp_path / "in.dxf"
    ifc_path = tmp_path / "out.ifc"
    _write_minimal_dxf(dxf)
    convert_dxf(
        dxf_path=dxf,
        output_path=ifc_path,
        profile=load_default_profile(),
        preprocess_acis=False,
    )
    ifc = ifcopenshell.open(str(ifc_path))
    project = ifc.by_type("IfcProject")[0]
    rels = [
        rel for rel in ifc.by_type("IfcRelAssociatesClassification")
        if project in (rel.RelatedObjects or [])
    ]
    assert rels, "no classification associated with IfcProject"
    discipline_refs = [
        rel for rel in rels
        if rel.RelatingClassification.ReferencedSource is not None
        and rel.RelatingClassification.ReferencedSource.Name == "suunnittelualat"
    ]
    assert len(discipline_refs) == 1
    assert discipline_refs[0].RelatingClassification.Identification == "Jäähdytys"
