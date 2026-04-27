"""Unit tests for CLI entry point."""

import os
import subprocess
import sys
from pathlib import Path

import ifcopenshell


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


def test_cli_convert_default_profile(fixtures_dir: Path, tmp_path: Path):
    out = tmp_path / "out.ifc"
    r = _run_cli("convert", str(fixtures_dir / "simple_wall.dxf"), str(out))
    assert r.returncode == 0, r.stderr
    assert out.exists()
    ifc = ifcopenshell.open(str(out))
    assert len(ifc.by_type("IfcWall")) == 1
