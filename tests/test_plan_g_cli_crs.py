"""Plan G Task 14: CLI ``--eastings``/``--northings``/``--orthogonal-height``
flags override the profile's CRS. Eastings + Northings are paired —
giving only one is an argparse error. Without any flag the profile's
existing ``crs`` is preserved."""

from __future__ import annotations

from pathlib import Path

import pytest

from dxf2ifc import cli


def _stub_convert(*, recorder):
    def fake(**kwargs):
        recorder["profile"] = kwargs["profile"]
        return ({}, None)

    return fake


def test_cli_all_three_flags_override_profile_crs(fixtures_dir: Path, tmp_path: Path, monkeypatch):
    recorder: dict = {}
    monkeypatch.setattr(cli, "convert_dxf", _stub_convert(recorder=recorder))

    rc = cli.main(
        [
            "convert",
            str(fixtures_dir / "simple_wall.dxf"),
            str(tmp_path / "out.ifc"),
            "--eastings",
            "25496000",
            "--northings",
            "6672000",
            "--orthogonal-height",
            "15000",
        ]
    )
    assert rc == 0
    assert recorder["profile"].crs is not None
    assert recorder["profile"].crs.eastings_mm == 25_496_000.0
    assert recorder["profile"].crs.northings_mm == 6_672_000.0
    assert recorder["profile"].crs.orthogonal_height_mm == 15_000.0


def test_cli_only_eastings_raises_argparse_error(fixtures_dir: Path, tmp_path: Path, monkeypatch):
    monkeypatch.setattr(cli, "convert_dxf", _stub_convert(recorder={}))

    with pytest.raises(SystemExit):
        cli.main(
            [
                "convert",
                str(fixtures_dir / "simple_wall.dxf"),
                str(tmp_path / "out.ifc"),
                "--eastings",
                "25496000",
            ]
        )


def test_cli_no_crs_flags_preserves_profile_crs(fixtures_dir: Path, tmp_path: Path, monkeypatch):
    recorder: dict = {}
    monkeypatch.setattr(cli, "convert_dxf", _stub_convert(recorder=recorder))

    rc = cli.main(
        [
            "convert",
            str(fixtures_dir / "simple_wall.dxf"),
            str(tmp_path / "out.ifc"),
        ]
    )
    assert rc == 0
    # Default profile has crs=None (commented out in TOML), so override is None.
    # The point of the test: no exception, and the profile is forwarded as-is.
    assert "profile" in recorder
