"""Tests for the suunnittelualat / discipline metadata in the IFC.

Discipline-classification reference is "KYL" for refrigeration files —
sama lyhenne kuin AutoCAD-puolen layer-prefix (KYL-*). Yhden­mukaisuus
alkupäästä loppupäähän.

Solibri's role auto-selection ei automaattisesti tunnistu vaikka kaikki
yleisesti dokumentoidut signaalit (LongName, suunnittelualat,
Pset_Project.Authorization, Pset_Discipline, STEP-header) on emittoitu
— manuaalinen valinta avatessa hyväksytty.
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
    assert DISCIPLINE_LABELS["KYL"] == "KYL"


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
    # Every ref under the suunnittelualat classification should be KYL
    # for a refrigeration-only file.
    assert refs, "no suunnittelualat references emitted"
    for r in refs:
        assert r.Identification == "KYL", (
            f"expected Identification 'KYL', got {r.Identification!r}"
        )
        assert r.Name == "KYL"


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
    assert project.LongName == "KYL"


def test_project_pset_authorization_kylmasuunnittelu(tmp_path: Path) -> None:
    """Pset_Project / Authorization='Kylmäsuunnittelu' on IfcProject —
    the actual mechanism Solibri reads when deciding which role to
    auto-load. Without it the file shows up as Architectural."""
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
        rel for rel in ifc.by_type("IfcRelDefinesByProperties")
        if project in (rel.RelatedObjects or [])
    ]
    pset_project = next(
        (
            rel.RelatingPropertyDefinition for rel in rels
            if rel.RelatingPropertyDefinition is not None
            and rel.RelatingPropertyDefinition.is_a("IfcPropertySet")
            and rel.RelatingPropertyDefinition.Name == "Pset_Project"
        ),
        None,
    )
    assert pset_project is not None, "Pset_Project missing on IfcProject"
    auth = next(
        (
            p for p in (pset_project.HasProperties or ())
            if p.Name == "Authorization"
        ),
        None,
    )
    assert auth is not None
    assert auth.NominalValue.wrappedValue == "Kylmäsuunnittelu"


def test_step_header_carries_authorization_kylmasuunnittelu(tmp_path: Path) -> None:
    """STEP physical FILE_NAME's 7th param (authorization) must be
    'Kylmäsuunnittelu' — Solibri reads this header field as one of
    its discipline auto-detect signals (Granlund/RAVA3Pro convention)."""
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
    fn = ifc.wrapped_data.header().file_name_py()
    assert fn.get_attribute_value(6) == "Kylmäsuunnittelu"
    # preprocessor_version + originating_system must identify dxf2ifc
    assert "dxf2ifc" in fn.get_attribute_value(4).lower()
    assert "dxf2ifc" in fn.get_attribute_value(5).lower()


def test_step_header_lists_building_service_exchange_requirement(
    tmp_path: Path,
) -> None:
    """FILE_DESCRIPTION.description must list ExchangeRequirement[BuildingService]
    so Solibri picks up the file as a building-services exchange."""
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
    description = ifc.wrapped_data.header().file_description_py().get_attribute_value(0)
    assert any(
        "ExchangeRequirement[BuildingService]" in (s or "")
        for s in description
    ), description


def test_application_identifier_tagged_dxf2ifc(tmp_path: Path) -> None:
    """IfcApplication.ApplicationIdentifier is "dxf2ifc-kylmalaite".

    Solibri uses the producing application as one of the discipline
    auto-detect signals; a generic 'IfcOpenShell' identifier nudges it
    toward the Architectural default."""
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
    apps = ifc.by_type("IfcApplication")
    assert apps, "no IfcApplication in file"
    for app in apps:
        assert app.ApplicationIdentifier == "dxf2ifc-kylmalaite"
        assert "dxf2ifc" in (app.ApplicationFullName or "").lower()


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
    assert discipline_refs[0].RelatingClassification.Identification == "KYL"
