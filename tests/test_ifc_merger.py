"""Tests for ifc_merger — appending MagiCAD-IFC products into the
master IFC under the master's first IfcBuildingStorey.

We synthesise both files programmatically (ifcopenshell.api) so the
tests are hermetic and don't depend on a real MAGIIFCEXPORT output.
"""

from __future__ import annotations

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.api.aggregate
import ifcopenshell.api.context
import ifcopenshell.api.geometry
import ifcopenshell.api.project
import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.api.unit
import pytest

from dwg2ifc.core.ifc_merger import merge_magicad_ifc


def _build_minimal_ifc(
    path,
    *,
    project_name: str,
    storey: bool = True,
    products: list[tuple[str, str]] | None = None,
):
    """Construct a minimal IFC file with units, project, optional storey
    + the requested products. Returns the path."""
    ifc = ifcopenshell.api.run("project.create_file", version="IFC4")
    project = ifcopenshell.api.run(
        "root.create_entity", ifc, ifc_class="IfcProject", name=project_name
    )
    unit = ifcopenshell.api.run(
        "unit.add_si_unit", ifc, unit_type="LENGTHUNIT", prefix="MILLI"
    )
    ifcopenshell.api.run("unit.assign_unit", ifc, units=[unit])
    ctx = ifcopenshell.api.run(
        "context.add_context", ifc, context_type="Model"
    )
    ifcopenshell.api.run(
        "context.add_context",
        ifc,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=ctx,
    )

    if storey:
        site = ifcopenshell.api.run(
            "root.create_entity", ifc, ifc_class="IfcSite", name="Site"
        )
        ifcopenshell.api.run(
            "aggregate.assign_object",
            ifc,
            products=[site],
            relating_object=project,
        )
        building = ifcopenshell.api.run(
            "root.create_entity",
            ifc,
            ifc_class="IfcBuilding",
            name="Building",
        )
        ifcopenshell.api.run(
            "aggregate.assign_object",
            ifc,
            products=[building],
            relating_object=site,
        )
        bs = ifcopenshell.api.run(
            "root.create_entity",
            ifc,
            ifc_class="IfcBuildingStorey",
            name="Kerros 1",
        )
        ifcopenshell.api.run(
            "aggregate.assign_object",
            ifc,
            products=[bs],
            relating_object=building,
        )
    else:
        bs = None

    if products:
        new_products = []
        for ifc_class, name in products:
            p = ifcopenshell.api.run(
                "root.create_entity", ifc, ifc_class=ifc_class, name=name
            )
            new_products.append(p)
        if bs is not None:
            ifcopenshell.api.run(
                "spatial.assign_container",
                ifc,
                products=new_products,
                relating_structure=bs,
            )

    ifc.write(str(path))
    return path


def test_merge_appends_magicad_products_into_master(tmp_path):
    master_path = _build_minimal_ifc(
        tmp_path / "master.ifc",
        project_name="Master",
        products=[("IfcEvaporator", "Master höyrystin")],
    )
    magicad_path = _build_minimal_ifc(
        tmp_path / "magicad.ifc",
        project_name="MagiCAD",
        products=[
            ("IfcDuctSegment", "Kanavasegment 1"),
            ("IfcDuctSegment", "Kanavasegment 2"),
            ("IfcAirTerminal", "Tuloilmapääte"),
        ],
    )

    stats = merge_magicad_ifc(master_path, magicad_path)

    assert stats["products_appended"] == 3
    assert stats["ifc_types"] == {
        "IfcDuctSegment": 2,
        "IfcAirTerminal": 1,
    }

    merged = ifcopenshell.open(str(master_path))
    duct_segments = merged.by_type("IfcDuctSegment")
    air_terminals = merged.by_type("IfcAirTerminal")
    evaporators = merged.by_type("IfcEvaporator")
    assert len(duct_segments) == 2
    assert len(air_terminals) == 1
    # Master's original product survived the merge
    assert len(evaporators) == 1


def test_merge_links_appended_products_to_master_storey(tmp_path):
    """Every appended product must end up contained in the master's
    IfcBuildingStorey via IfcRelContainedInSpatialStructure — otherwise
    Solibri shows them at IfcSite level outside the building tree."""
    master_path = _build_minimal_ifc(
        tmp_path / "master.ifc", project_name="Master"
    )
    magicad_path = _build_minimal_ifc(
        tmp_path / "magicad.ifc",
        project_name="MagiCAD",
        products=[("IfcPipeSegment", "Putkisegment 1")],
    )

    merge_magicad_ifc(master_path, magicad_path)

    merged = ifcopenshell.open(str(master_path))
    storey = merged.by_type("IfcBuildingStorey")[0]
    pipe = merged.by_type("IfcPipeSegment")[0]
    # Walk ContainedIn back from pipe → ensure storey is its container
    contained_rels = [
        r for r in merged.by_type("IfcRelContainedInSpatialStructure")
        if pipe in r.RelatedElements
    ]
    assert len(contained_rels) == 1
    assert contained_rels[0].RelatingStructure == storey


def test_merge_preserves_master_product_count(tmp_path):
    master_path = _build_minimal_ifc(
        tmp_path / "master.ifc",
        project_name="Master",
        products=[
            ("IfcEvaporator", "h1"),
            ("IfcCableCarrierSegment", "tikas"),
        ],
    )
    magicad_path = _build_minimal_ifc(
        tmp_path / "magicad.ifc",
        project_name="MagiCAD",
        products=[("IfcDuctSegment", "Kanava")],
    )

    merge_magicad_ifc(master_path, magicad_path)

    merged = ifcopenshell.open(str(master_path))
    assert len(merged.by_type("IfcEvaporator")) == 1
    assert len(merged.by_type("IfcCableCarrierSegment")) == 1
    assert len(merged.by_type("IfcDuctSegment")) == 1


def test_merge_skips_spatial_structure_from_library(tmp_path):
    """IfcSite/IfcBuilding/IfcBuildingStorey from the MagiCAD IFC must
    NOT be copied — the master keeps a single canonical hierarchy."""
    master_path = _build_minimal_ifc(
        tmp_path / "master.ifc", project_name="Master"
    )
    # MagiCAD IFC has its own full Site→Building→Storey tree
    magicad_path = _build_minimal_ifc(
        tmp_path / "magicad.ifc",
        project_name="MagiCAD",
        products=[("IfcAirTerminal", "T")],
    )

    merge_magicad_ifc(master_path, magicad_path)

    merged = ifcopenshell.open(str(master_path))
    assert len(merged.by_type("IfcSite")) == 1
    assert len(merged.by_type("IfcBuilding")) == 1
    assert len(merged.by_type("IfcBuildingStorey")) == 1


def test_merge_writes_to_output_path_when_specified(tmp_path):
    """``output_path`` lets callers keep the master untouched and write
    the merged file elsewhere."""
    master_path = _build_minimal_ifc(
        tmp_path / "master.ifc", project_name="Master"
    )
    magicad_path = _build_minimal_ifc(
        tmp_path / "magicad.ifc",
        project_name="MagiCAD",
        products=[("IfcAirTerminal", "T")],
    )
    merged_path = tmp_path / "merged.ifc"

    merge_magicad_ifc(master_path, magicad_path, output_path=merged_path)

    assert merged_path.is_file()
    # Master left untouched (no IfcAirTerminal)
    master_after = ifcopenshell.open(str(master_path))
    assert len(master_after.by_type("IfcAirTerminal")) == 0
    # Merged has the appended product
    merged = ifcopenshell.open(str(merged_path))
    assert len(merged.by_type("IfcAirTerminal")) == 1


def test_merge_raises_when_master_has_no_storey(tmp_path):
    master_path = _build_minimal_ifc(
        tmp_path / "master.ifc", project_name="Master", storey=False
    )
    magicad_path = _build_minimal_ifc(
        tmp_path / "magicad.ifc",
        project_name="MagiCAD",
        products=[("IfcAirTerminal", "T")],
    )

    with pytest.raises(ValueError, match="IfcBuildingStorey"):
        merge_magicad_ifc(master_path, magicad_path)


def test_merge_raises_on_missing_files(tmp_path):
    with pytest.raises(FileNotFoundError):
        merge_magicad_ifc(tmp_path / "missing.ifc", tmp_path / "magicad.ifc")
    master_path = _build_minimal_ifc(
        tmp_path / "master.ifc", project_name="Master"
    )
    with pytest.raises(FileNotFoundError):
        merge_magicad_ifc(master_path, tmp_path / "missing-magicad.ifc")
