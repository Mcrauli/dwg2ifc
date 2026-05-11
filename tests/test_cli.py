"""Unit tests for CLI entry point."""

import os
import subprocess
import sys
from pathlib import Path

import ifcopenshell

from dxf2ifc import cli


def _run_cli(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", "dxf2ifc", *args]
    env = os.environ.copy()
    src_path = str(Path(__file__).resolve().parent.parent / "src")
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, env=env)


def test_cli_no_args_prints_help():
    r = _run_cli()
    assert r.returncode != 0
    assert "usage" in (r.stdout + r.stderr).lower()




def test_cli_convert_validate_flag_exit_zero_on_clean_ifc(fixtures_dir: Path, tmp_path: Path):
    out = tmp_path / "out.ifc"
    r = _run_cli("convert", str(fixtures_dir / "simple_wall.dxf"), str(out), "--validate")
    assert r.returncode == 0, r.stderr
    assert out.exists()
    assert "0 errors" in r.stderr


def test_cli_convert_validate_flag_exit_one_on_errors(
    fixtures_dir: Path, tmp_path: Path, monkeypatch, capsys
):
    """When --validate is given and validate_ifc reports errors, the CLI
    must exit 1 and print the error description on stderr."""
    from dxf2ifc.core import quality

    def _fake_validate(path):
        return quality.ValidationReport(
            errors=[
                {
                    "level": "ERROR",
                    "message": "fake validation error: missing required attribute",
                }
            ],
            warnings=[],
            summary="IFC4: 1 errors, 0 warnings",
        )

    monkeypatch.setattr(cli, "validate_ifc", _fake_validate)

    out = tmp_path / "out.ifc"
    rc = cli.main(
        [
            "convert",
            str(fixtures_dir / "simple_wall.dxf"),
            str(out),
            "--validate",
        ]
    )
    captured = capsys.readouterr()
    assert rc == 1
    assert "fake validation error" in captured.err


def test_cli_convert_without_validate_does_not_call_validate(
    fixtures_dir: Path, tmp_path: Path, monkeypatch
):
    called = {"n": 0}

    def _spy(path):
        called["n"] += 1
        from dxf2ifc.core.quality import ValidationReport

        return ValidationReport(errors=[], warnings=[], summary="")

    monkeypatch.setattr(cli, "validate_ifc", _spy)

    out = tmp_path / "out.ifc"
    rc = cli.main(["convert", str(fixtures_dir / "simple_wall.dxf"), str(out)])
    assert rc == 0
    assert called["n"] == 0


def test_cli_skip_acis_flag_disables_preprocess(
    fixtures_dir: Path, tmp_path: Path, monkeypatch
):
    """--skip-acis must pass preprocess_acis=False through to convert_dxf
    so accoreconsole.exe is never launched."""
    seen: dict[str, object] = {}

    def _spy(**kwargs):
        seen.update(kwargs)
        return ({}, None)

    monkeypatch.setattr(cli, "convert_dxf", _spy)
    out = tmp_path / "out.ifc"
    rc = cli.main(
        [
            "convert",
            str(fixtures_dir / "simple_wall.dxf"),
            str(out),
            "--skip-acis",
        ]
    )
    assert rc == 0
    assert seen.get("preprocess_acis") is False


def test_cli_default_runs_preprocess_acis(
    fixtures_dir: Path, tmp_path: Path, monkeypatch
):
    seen: dict[str, object] = {}

    def _spy(**kwargs):
        seen.update(kwargs)
        return ({}, None)

    monkeypatch.setattr(cli, "convert_dxf", _spy)
    out = tmp_path / "out.ifc"
    rc = cli.main(["convert", str(fixtures_dir / "simple_wall.dxf"), str(out)])
    assert rc == 0
    assert seen.get("preprocess_acis") is True
