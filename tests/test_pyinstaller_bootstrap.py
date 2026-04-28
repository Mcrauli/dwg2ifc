"""Smoke test: PyInstaller is importable for the .exe build pipeline."""

from __future__ import annotations

import importlib
import subprocess
import sys


def test_pyinstaller_is_importable() -> None:
    module = importlib.import_module("PyInstaller")
    assert hasattr(module, "__version__")


def test_pyinstaller_main_module_runs() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--version"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip()
