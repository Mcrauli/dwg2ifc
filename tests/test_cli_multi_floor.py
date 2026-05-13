"""CLI multi-floor: --floor parsing + validation + dispatch."""

from pathlib import Path

import pytest

from dxf2ifc.cli import _parse_floor_arg, build_parser


def test_parse_floor_path_only():
    fe = _parse_floor_arg("1krs.dwg", default_index=0)
    assert fe.path == Path("1krs.dwg")
    assert fe.floor_label == "1.krs"
    assert fe.elevation_mm == 0.0


def test_parse_floor_path_and_label():
    fe = _parse_floor_arg("kellari.dwg:kellari", default_index=2)
    assert fe.floor_label == "kellari"
    assert fe.elevation_mm == 0.0


def test_parse_floor_full():
    fe = _parse_floor_arg("2krs.dwg:2.krs:3500", default_index=1)
    assert fe.floor_label == "2.krs"
    assert fe.elevation_mm == 3500.0


def test_parse_floor_default_label_uses_index():
    # default_index is 0-based, label is 1-based
    fe = _parse_floor_arg("any.dwg", default_index=4)
    assert fe.floor_label == "5.krs"


def test_parse_floor_rejects_non_numeric_elevation():
    with pytest.raises(ValueError):
        _parse_floor_arg("a.dwg:1.krs:huono", default_index=0)


def test_parse_floor_rejects_too_many_colons():
    with pytest.raises(ValueError):
        _parse_floor_arg("a.dwg:1.krs:0:extra", default_index=0)


def test_build_parser_accepts_repeatable_floor():
    parser = build_parser()
    args = parser.parse_args([
        "convert", "out.ifc",
        "--floor", "1krs.dwg:1.krs:0",
        "--floor", "2krs.dwg:2.krs:3500",
    ])
    assert args.floor == ["1krs.dwg:1.krs:0", "2krs.dwg:2.krs:3500"]
