"""Tests for Finnish PropertySet emission (FI_Asennus / FI_Geometria /
FI_Komponentti / FI_Tuote)."""

from __future__ import annotations

from pathlib import Path

import ezdxf
import ifcopenshell
import pytest

from dxf2ifc.core.finnish_psets import (
    add_fi_asennus,
    add_fi_geometria,
    add_fi_komponentti,
    add_fi_sijainti,
    add_fi_tekninen,
    add_fi_tuote,
)
from dxf2ifc.core.geometry import GeometryExtents, extents_from_geometry
from dxf2ifc.core.ifc_writer import convert_dxf
from dxf2ifc.core.types import (
    BlockInstance,
    LineGeometry,
    MeshGeometry,
    Point3D,
    PolygonGeometry,
)
from dxf2ifc.profiles.loader import load_default_profile


# --- Helper: build a minimal IFC4 file + product ---------------------------


def _make_ifc_with_product(ifc_class: str = "IfcWall") -> tuple[ifcopenshell.file, object]:
    ifc = ifcopenshell.file(schema="IFC4")
    from ifcopenshell.api import run

    run("root.create_entity", ifc, ifc_class="IfcProject", name="t")
    product = run("root.create_entity", ifc, ifc_class=ifc_class, name="p")
    return ifc, product


def _pset_props(product, name: str) -> dict[str, object]:
    """Return ``{prop_name: wrappedValue}`` for the named PSet on product."""
    rels = product.IsDefinedBy or []
    for rel in rels:
        if not rel.is_a("IfcRelDefinesByProperties"):
            continue
        pset = rel.RelatingPropertyDefinition
        if pset.is_a("IfcPropertySet") and pset.Name == name:
            return {
                p.Name: (p.NominalValue.wrappedValue if p.NominalValue else None)
                for p in pset.HasProperties
            }
    return {}


# --- FI_Asennus ------------------------------------------------------------


def test_add_fi_asennus_emits_seven_length_props():
    ifc, product = _make_ifc_with_product()
    add_fi_asennus(
        ifc,
        product,
        top_z_mm=2700.0,
        bottom_z_mm=0.0,
        install_z_mm=0.0,
        storey_elevation_mm=0.0,
    )
    props = _pset_props(product, "FI_Asennus")
    assert len(props) == 7  # 6 levels + Liitoskorko
    assert props["02 Komponentin yläpinnan korko, abs."] == 2700.0
    assert props["04 Komponentin alapinnan korko, abs."] == 0.0
    assert props["12 Komponentin yläpinnan korko, kerroskorosta"] == 2700.0


def test_fi_asennus_storey_relative_subtracts_storey_elevation():
    ifc, product = _make_ifc_with_product()
    add_fi_asennus(
        ifc,
        product,
        top_z_mm=8200.0,
        bottom_z_mm=5500.0,
        install_z_mm=5500.0,
        storey_elevation_mm=5500.0,
    )
    props = _pset_props(product, "FI_Asennus")
    assert props["12 Komponentin yläpinnan korko, kerroskorosta"] == 2700.0
    assert props["13 Asennuskorko, kerroskorosta"] == 0.0


def test_fi_asennus_omits_liitoskorko_when_disabled():
    ifc, product = _make_ifc_with_product()
    add_fi_asennus(
        ifc,
        product,
        top_z_mm=2700.0,
        bottom_z_mm=0.0,
        install_z_mm=0.0,
        storey_elevation_mm=0.0,
        include_liitoskorko=False,
    )
    props = _pset_props(product, "FI_Asennus")
    assert "Liitoskorko, kerroskorosta" not in props
    assert len(props) == 6


# --- FI_Geometria ----------------------------------------------------------


def test_fi_geometria_skips_psset_when_all_dims_none():
    ifc, product = _make_ifc_with_product()
    result = add_fi_geometria(ifc, product, korkeus_mm=None, leveys_mm=None, syvyys_mm=None)
    assert result is None
    assert _pset_props(product, "FI_Geometria") == {}


def test_fi_geometria_skips_zero_dim_but_keeps_others():
    ifc, product = _make_ifc_with_product()
    add_fi_geometria(ifc, product, korkeus_mm=2700.0, leveys_mm=0.0, syvyys_mm=600.0)
    props = _pset_props(product, "FI_Geometria")
    assert props == {"Korkeus": 2700.0, "Syvyys": 600.0}


# --- FI_Komponentti --------------------------------------------------------


def test_fi_komponentti_emits_static_fields_and_default_status():
    ifc, product = _make_ifc_with_product()
    add_fi_komponentti(
        ifc,
        product,
        paaryhma="LAITTEISTOT - LVI",
        alaryhma="KYLMÄLAITTEISTOT",
        koodi="T-LVI-01-01-023",
        yleisnimi="Höyrystin",
        yleistunnus="HÖY",
    )
    props = _pset_props(product, "FI_Komponentti")
    assert props["01 Komponentin pääryhmä"] == "LAITTEISTOT - LVI"
    assert props["03 Komponentin koodi"] == "T-LVI-01-01-023"
    assert props["Status"] == "New"
    assert "Laitetunnus" not in props  # skipped per skip-on-empty


def test_fi_komponentti_includes_koneikko_and_laitetunnus():
    ifc, product = _make_ifc_with_product()
    add_fi_komponentti(
        ifc,
        product,
        paaryhma="LAITTEISTOT - LVI",
        alaryhma="KYLMÄLAITTEISTOT",
        koodi="T-LVI-01-01-023",
        yleisnimi="Höyrystin",
        yleistunnus="HÖY",
        koneikko="JK1",
        laitetunnus="501",
    )
    props = _pset_props(product, "FI_Komponentti")
    assert props["Koneikko"] == "JK1"
    assert props["Laitetunnus"] == "501"


# --- FI_Tuote --------------------------------------------------------------


def test_fi_tuote_always_emit_creates_tab_with_blanks():
    ifc, product = _make_ifc_with_product()
    pset = add_fi_tuote(ifc, product)
    assert pset is not None
    props = _pset_props(product, "FI_Tuote")
    # Every text field present, all empty placeholders.
    assert set(props.keys()) == {
        "Tuotetyypin nimi",
        "Tuotetyypin kuvaus",
        "Tuotetyypin kommentti",
        "Tuotetyypin valmistaja",
        "Tuotetyypin valmistajan linkki",
        "Tuotteen kommentti",
    }
    assert all(v == "" for v in props.values())


def test_fi_tuote_emits_supplied_fields_alongside_blanks():
    ifc, product = _make_ifc_with_product()
    add_fi_tuote(ifc, product, valmistaja="FläktGroup", kuvaus="Supply air valve")
    props = _pset_props(product, "FI_Tuote")
    assert props["Tuotetyypin valmistaja"] == "FläktGroup"
    assert props["Tuotetyypin kuvaus"] == "Supply air valve"
    assert props["Tuotetyypin nimi"] == ""  # blank placeholder


def test_fi_tuote_skips_when_always_emit_false_and_no_data():
    ifc, product = _make_ifc_with_product()
    result = add_fi_tuote(ifc, product, always_emit=False)
    assert result is None
    assert _pset_props(product, "FI_Tuote") == {}


# --- FI_Tekninen + FI_Sijainti --------------------------------------------


def test_fi_tekninen_emits_dict_fields_verbatim():
    ifc, product = _make_ifc_with_product()
    add_fi_tekninen(
        ifc,
        product,
        fields={"Kuormitus": "120 kg/m", "Materiaali": "Sinkitty teräs"},
    )
    props = _pset_props(product, "FI_Tekninen")
    assert props == {"Kuormitus": "120 kg/m", "Materiaali": "Sinkitty teräs"}


def test_fi_tekninen_default_fields_per_ifc_type():
    from dxf2ifc.core.finnish_psets import fi_tekninen_default_fields

    evap = fi_tekninen_default_fields("IfcEvaporator")
    assert "Jäähdytysteho" in evap
    assert "Kylmäaine" in evap

    shelf = fi_tekninen_default_fields("IfcCableCarrierSegment")
    # Hyllyt: vain matsku + pinnoite (Lauri 2026-05-08).
    assert "Materiaali" in shelf
    assert "Pinnoite" in shelf
    # Removed fields must not be in defaults — käyttäjä voi lisätä
    # ne custom profile:n kautta jos tarvitsee.
    assert "Paloturvallisuusluokka" not in shelf
    assert "Paino" not in shelf
    assert "Kuormitus" not in shelf
    # Refrigeration fields must NOT leak onto shelves.
    assert "Jäähdytysteho" not in shelf

    pipe = fi_tekninen_default_fields("IfcPipeSegment")
    assert "Materiaali" in pipe
    assert "Eristys" in pipe


def test_fi_sijainti_emits_two_fields():
    ifc, product = _make_ifc_with_product()
    add_fi_sijainti(
        ifc, product,
        jarjestelmien_nimet="Refrigeration plant",
        jarjestelmien_tunnukset="RP",
    )
    props = _pset_props(product, "FI_Sijainti")
    assert props["Järjestelmien nimet"] == "Refrigeration plant"
    assert props["Järjestelmien tunnukset"] == "RP"


# --- extents_from_geometry -------------------------------------------------


def test_extents_from_line_geometry():
    line = LineGeometry(start=Point3D(0, 0, 1500), end=Point3D(3000, 0, 1500))
    ext = extents_from_geometry(line, height_mm=200.0, thickness_mm=22.0)
    assert ext.bottom_z == 1500.0
    assert ext.top_z == 1700.0
    assert ext.korkeus == 200.0
    assert ext.leveys == 22.0
    assert ext.syvyys == 3000.0


def test_extents_from_polygon_slab():
    poly = PolygonGeometry(
        vertices=(
            Point3D(0, 0, 100),
            Point3D(4000, 0, 100),
            Point3D(4000, 3000, 100),
            Point3D(0, 3000, 100),
        )
    )
    ext = extents_from_geometry(poly, thickness_mm=200.0)
    assert ext.top_z == 100.0
    assert ext.bottom_z == -100.0
    assert ext.korkeus == 200.0  # thickness, used as Korkeus
    assert ext.leveys == 4000.0
    assert ext.syvyys == 3000.0


def test_extents_from_block_instance():
    block = BlockInstance(insertion_point=Point3D(500, 800, 2000), rotation_rad=0.0)
    ext = extents_from_geometry(block, height_mm=2000.0, width_mm=600.0, depth_mm=400.0)
    assert ext.bottom_z == 2000.0
    assert ext.top_z == 4000.0
    assert ext.leveys == 600.0
    assert ext.syvyys == 400.0


def test_extents_from_mesh_geometry():
    mesh = MeshGeometry(
        vertices=(
            Point3D(0, 0, 0),
            Point3D(1000, 0, 0),
            Point3D(0, 500, 0),
            Point3D(0, 0, 2500),
        ),
        faces=((0, 1, 2), (0, 1, 3), (1, 2, 3), (0, 2, 3)),
    )
    ext = extents_from_geometry(mesh)
    assert ext.bottom_z == 0.0
    assert ext.top_z == 2500.0
    assert ext.korkeus == 2500.0
    assert ext.leveys == 1000.0
    assert ext.syvyys == 500.0


# --- End-to-end through convert_dxf ---------------------------------------


def test_convert_dxf_emits_fi_psets_on_pipe_segment(tmp_path: Path):
    dxf = tmp_path / "pipe.dxf"
    doc = ezdxf.new("R2018")
    doc.layers.add(name="LT IMU")
    doc.modelspace().add_line(
        (0, 0, 1500), (3000, 0, 1500), dxfattribs={"layer": "LT IMU"}
    )
    doc.saveas(str(dxf))

    out = tmp_path / "pipe.ifc"
    convert_dxf(dxf_path=dxf, output_path=out, profile=load_default_profile())

    ifc = ifcopenshell.open(str(out))
    pipes = ifc.by_type("IfcPipeSegment")
    assert len(pipes) == 1
    pset_names = {
        rel.RelatingPropertyDefinition.Name
        for rel in (pipes[0].IsDefinedBy or [])
        if rel.is_a("IfcRelDefinesByProperties")
        and rel.RelatingPropertyDefinition.is_a("IfcPropertySet")
    }
    # All six FI_* PSets emit (Tuote/Tekninen/Sijainti always-emit;
    # Geometria emits when at least one dimension is positive).
    assert "FI_Asennus" in pset_names
    assert "FI_Geometria" in pset_names
    assert "FI_Komponentti" in pset_names
    assert "FI_Tuote" in pset_names
    assert "FI_Tekninen" in pset_names
    assert "FI_Sijainti" in pset_names

    # Verify komponentti contents reflect the pipe rule's TOML.
    rels = pipes[0].IsDefinedBy or []
    komp = next(
        rel.RelatingPropertyDefinition
        for rel in rels
        if rel.is_a("IfcRelDefinesByProperties")
        and rel.RelatingPropertyDefinition.is_a("IfcPropertySet")
        and rel.RelatingPropertyDefinition.Name == "FI_Komponentti"
    )
    by_name = {p.Name: p.NominalValue.wrappedValue for p in komp.HasProperties}
    assert by_name["01 Komponentin pääryhmä"] == "PUTKISTOT - LVI"
    assert by_name["03 Komponentin koodi"] == "T-LVI-02"
    assert by_name["05 Komponentin yleistunnus"] == "KP"
    assert by_name["Status"] == "New"


# --- POSITIO linkage --------------------------------------------------------


def test_index_positio_markers_finds_blocks_by_pattern(tmp_path: Path):
    from dxf2ifc.core.positio import index_positio_markers

    dxf = tmp_path / "p.dxf"
    doc = ezdxf.new("R2018")
    doc.layers.add(name="KYL-KALUSTEET HATCH")
    block = doc.blocks.new(name="positiov2")
    block.add_line((0, 0), (1, 0))
    msp = doc.modelspace()
    insert = msp.add_blockref(
        "positiov2", (1000.0, 2000.0, 0.0), dxfattribs={"layer": "KYL-KALUSTEET HATCH"}
    )
    insert.add_attrib(tag="NUMERO", text="42", insert=(0, 0))
    insert.add_attrib(tag="TEKSTI", text="JK7", insert=(0, 0))
    doc.saveas(str(dxf))

    markers = index_positio_markers(dxf)
    assert len(markers) == 1
    assert markers[0].numero == "42"
    assert markers[0].teksti == "JK7"
    assert markers[0].insert_xy == (1000.0, 2000.0)


def test_find_nearest_positio_returns_closer_marker():
    from dxf2ifc.core.positio import PositioMarker, find_nearest_positio

    near = PositioMarker((1000.0, 1000.0), "1", "JK1", "AAA")
    far = PositioMarker((5000.0, 5000.0), "2", "JK2", "BBB")
    result = find_nearest_positio((1500.0, 1200.0), [near, far])
    assert result is near


def test_find_nearest_positio_returns_none_outside_radius():
    from dxf2ifc.core.positio import PositioMarker, find_nearest_positio

    far = PositioMarker((10_000.0, 10_000.0), "1", "JK1", "AAA")
    assert (
        find_nearest_positio((0.0, 0.0), [far], max_distance_mm=3000.0) is None
    )


def test_convert_dxf_links_positio_to_evaporator(tmp_path: Path):
    """End-to-end: a KYL-HÖYRYSTI INSERT next to a positiov2 block must
    yield FI_Komponentti.Laitetunnus filled from the marker's TEKSTI."""
    dxf = tmp_path / "evap.dxf"
    doc = ezdxf.new("R2018")
    doc.layers.add(name="KYL-HÖYRYSTI")
    doc.layers.add(name="KYL-KALUSTEET HATCH")

    # Positio block carrying NUMERO + TEKSTI attributes
    pblock = doc.blocks.new(name="positiov2")
    pblock.add_line((0, 0), (1, 0))

    # Höyrystin block (placeholder geometry)
    hblock = doc.blocks.new(name="HÖY3")
    hblock.add_line((0, 0), (300, 0))

    msp = doc.modelspace()
    msp.add_blockref(
        "HÖY3", (5000.0, 5000.0, 2200.0), dxfattribs={"layer": "KYL-HÖYRYSTI"}
    )
    pos = msp.add_blockref(
        "positiov2", (5500.0, 5200.0, 0.0),
        dxfattribs={"layer": "KYL-KALUSTEET HATCH"},
    )
    pos.add_attrib(tag="NUMERO", text="13", insert=(0, 0))
    pos.add_attrib(tag="TEKSTI", text="JK4", insert=(0, 0))
    doc.saveas(str(dxf))

    out = tmp_path / "evap.ifc"
    convert_dxf(dxf_path=dxf, output_path=out, profile=load_default_profile())
    ifc = ifcopenshell.open(str(out))
    evap = ifc.by_type("IfcEvaporator")[0]
    komp = next(
        rel.RelatingPropertyDefinition
        for rel in (evap.IsDefinedBy or [])
        if rel.is_a("IfcRelDefinesByProperties")
        and rel.RelatingPropertyDefinition.is_a("IfcPropertySet")
        and rel.RelatingPropertyDefinition.Name == "FI_Komponentti"
    )
    by_name = {p.Name: p.NominalValue.wrappedValue for p in komp.HasProperties}
    assert by_name["Koneikko"] == "JK4"  # TEKSTI from POSITIO
    assert by_name["Laitetunnus"] == "13"  # NUMERO from POSITIO


def test_convert_dxf_does_not_link_positio_to_shelf(tmp_path: Path):
    """A POSITIO right next to a KYL-LEVYHYLLY 3DSOLID-bearing layer must
    NOT leak into the shelf's FI_Komponentti — scope is refrigeration
    equipment only."""
    dxf = tmp_path / "shelf.dxf"
    doc = ezdxf.new("R2018")
    doc.layers.add(name="KYL-LEVYHYLLY")
    doc.layers.add(name="KYL-KALUSTEET HATCH")
    doc.blocks.new(name="positiov2").add_line((0, 0), (1, 0))
    msp = doc.modelspace()
    # Closed polyline ⇒ extruded cable carrier (no need for ACIS for unit test)
    msp.add_lwpolyline(
        [(0, 0), (3000, 0), (3000, 200), (0, 200)],
        close=True,
        dxfattribs={"layer": "KYL-LEVYHYLLY"},
    )
    p = msp.add_blockref(
        "positiov2", (100.0, 100.0, 0.0),
        dxfattribs={"layer": "KYL-KALUSTEET HATCH"},
    )
    p.add_attrib(tag="NUMERO", text="1", insert=(0, 0))
    p.add_attrib(tag="TEKSTI", text="JK1", insert=(0, 0))
    doc.saveas(str(dxf))

    out = tmp_path / "shelf.ifc"
    convert_dxf(dxf_path=dxf, output_path=out, profile=load_default_profile())
    ifc = ifcopenshell.open(str(out))
    shelf = ifc.by_type("IfcCableCarrierSegment")[0]
    komp = next(
        rel.RelatingPropertyDefinition
        for rel in (shelf.IsDefinedBy or [])
        if rel.is_a("IfcRelDefinesByProperties")
        and rel.RelatingPropertyDefinition.is_a("IfcPropertySet")
        and rel.RelatingPropertyDefinition.Name == "FI_Komponentti"
    )
    by_name = {p.Name: p.NominalValue.wrappedValue for p in komp.HasProperties}
    # Shelves never have Koneikko / Laitetunnus from POSITIO scope rule.
    assert "Koneikko" not in by_name
    assert "Laitetunnus" not in by_name


def test_convert_dxf_emits_fi_sijainti_with_system_name(tmp_path: Path):
    """The pipe rule for ``LT IMU`` carries ``system_name = 'Refrigeration LT'``.
    FI_Sijainti's Järjestelmien nimet/tunnukset must reflect that."""
    dxf = tmp_path / "pipe.dxf"
    doc = ezdxf.new("R2018")
    doc.layers.add(name="LT IMU")
    doc.modelspace().add_line(
        (0, 0, 0), (1000, 0, 0), dxfattribs={"layer": "LT IMU"}
    )
    doc.saveas(str(dxf))

    out = tmp_path / "out.ifc"
    convert_dxf(dxf_path=dxf, output_path=out, profile=load_default_profile())
    ifc = ifcopenshell.open(str(out))
    pipe = ifc.by_type("IfcPipeSegment")[0]
    sij = next(
        rel.RelatingPropertyDefinition
        for rel in (pipe.IsDefinedBy or [])
        if rel.is_a("IfcRelDefinesByProperties")
        and rel.RelatingPropertyDefinition.is_a("IfcPropertySet")
        and rel.RelatingPropertyDefinition.Name == "FI_Sijainti"
    )
    by_name = {p.Name: p.NominalValue.wrappedValue for p in sij.HasProperties}
    assert by_name["Järjestelmien nimet"] == "Refrigeration LT"
