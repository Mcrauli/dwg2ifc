"""Tests for IfcProject skeleton storey naming + Z elevation."""

import pytest

from dxf2ifc.core.ifc_writer.skeleton import build_ifc_project_skeleton


def test_default_single_storey_named_kerros_1():
    skel = build_ifc_project_skeleton(project_name="One")
    assert [s.Name for s in skel.storeys] == ["Kerros 1"]
    assert [s.Elevation for s in skel.storeys] == [0.0]


def test_storey_names_supplied_uses_those_names():
    skel = build_ifc_project_skeleton(
        project_name="Multi",
        storey_z_levels_mm=[0.0, 3500.0, 7000.0],
        storey_names=["1.krs", "2.krs", "kellari"],
    )
    assert [s.Name for s in skel.storeys] == ["1.krs", "2.krs", "kellari"]
    assert [s.Elevation for s in skel.storeys] == [0.0, 3500.0, 7000.0]


def test_storey_names_omitted_falls_back_to_kerros_n():
    skel = build_ifc_project_skeleton(
        project_name="One",
        storey_z_levels_mm=[0.0, 3500.0],
    )
    assert [s.Name for s in skel.storeys] == ["Kerros 1", "Kerros 2"]


def test_storey_names_length_mismatch_raises():
    with pytest.raises(ValueError, match="storey_names"):
        build_ifc_project_skeleton(
            project_name="x",
            storey_z_levels_mm=[0.0, 3500.0],
            storey_names=["1.krs"],
        )
