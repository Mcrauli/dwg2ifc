"""Smoke checks for the local PyInstaller build scripts."""

from __future__ import annotations

import stat
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PS1_PATH = REPO_ROOT / "scripts" / "build_exe.ps1"
SH_PATH = REPO_ROOT / "scripts" / "build_exe.sh"


def test_powershell_build_script_drives_uv_and_pyinstaller() -> None:
    assert PS1_PATH.exists(), f"missing {PS1_PATH}"
    text = PS1_PATH.read_text(encoding="utf-8")
    assert "uv sync" in text
    assert "pyinstaller" in text.lower()
    assert "build/dxf2ifc.spec" in text or "build\\dxf2ifc.spec" in text
    assert "Get-FileHash" in text
    assert "DXF2IFC_VERSION" in text


def test_shell_build_script_drives_uv_and_pyinstaller() -> None:
    assert SH_PATH.exists(), f"missing {SH_PATH}"
    text = SH_PATH.read_text(encoding="utf-8")
    assert text.startswith("#!"), "shell script missing shebang"
    assert "uv sync" in text
    assert "pyinstaller" in text
    assert "build/dxf2ifc.spec" in text
    assert "sha256sum" in text or "shasum" in text


def test_shell_build_script_is_executable() -> None:
    mode = SH_PATH.stat().st_mode
    assert mode & stat.S_IXUSR, f"{SH_PATH} is not user-executable"
