"""Solibri Anywhere CLI wrapper (Plan F Section 3 Task 8).

Builds the Solibri command line and runs it via :mod:`subprocess`, returning
the report path on success. The wrapper deliberately does *not* attempt to
locate Solibri inside the dwg2ifc test sandbox — the actual binary lives on
Lauri's Windows host. CI tests monkey-patch :func:`subprocess.run` and
:func:`shutil.which` so the wrapper can be exercised without Solibri.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

DEFAULT_SOLIBRI_EXE_NAME = "Solibri.exe"


def build_command(
    *,
    solibri_exe: str,
    ifc_path: Path | str,
    ruleset_path: Path | str,
    report_path: Path | str,
) -> list[str]:
    """Return the argv list that drives Solibri Anywhere headlessly."""
    return [
        str(solibri_exe),
        "-load",
        str(ifc_path),
        "-ruleset",
        str(ruleset_path),
        "-output",
        str(report_path),
        "-exit",
    ]


def run_solibri(
    *,
    ifc_path: Path | str,
    ruleset_path: Path | str,
    report_path: Path | str,
    solibri_exe: str | None = None,
    timeout: int | None = 600,
) -> Path:
    """Run Solibri Anywhere CLI and return the produced report path.

    Raises :class:`FileNotFoundError` when ``Solibri.exe`` cannot be located
    via ``shutil.which`` (or the explicit ``solibri_exe`` argument), and
    :class:`RuntimeError` if Solibri exits with a non-zero return code.
    """
    exe = solibri_exe or shutil.which(DEFAULT_SOLIBRI_EXE_NAME)
    if not exe:
        raise FileNotFoundError(
            f"Solibri.exe not found in PATH (looked for {DEFAULT_SOLIBRI_EXE_NAME})"
        )

    cmd = build_command(
        solibri_exe=exe,
        ifc_path=ifc_path,
        ruleset_path=ruleset_path,
        report_path=report_path,
    )

    completed = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Solibri exited with code {completed.returncode}: {completed.stderr or completed.stdout}"
        )

    return Path(report_path)
