"""Headless DWG -> DXF preconversion via ``accoreconsole.exe`` + DXFOUT.

The DXF-only parser pipeline (mapper, dxf_reader, ifc_writer) is unaffected:
DWG inputs are converted to a temporary DXF in the caller-supplied workdir,
and the existing :func:`dxf2ifc.core.ifc_writer.convert_dxf` path reads that
DXF.

Why accoreconsole + DXFOUT and not ODA File Converter:

* dxf2ifc already invokes ``accoreconsole.exe`` for STLOUT ACIS tessellation
  (:mod:`dxf2ifc.core.preprocessing`), so there are zero additional binary
  dependencies for AutoCAD owners.
* DXFOUT is a native AutoCAD command driven by a ``.scr`` LISP script — no
  COM, no sendkeys, no visible AutoCAD window, no profile pollution. The
  fragile keystroke pipeline retired in v0.2.0-alpha10 is NOT what this
  module reintroduces.
* The earlier ``acad.exe`` COM + sendkeys path (`dwg_preconvert.py` removed
  in alpha10) suffered from FILEDIA-toggle races and prompt-buffer overflow.
  accoreconsole's script execution has neither problem — it consumes the
  ``.scr`` line-by-line through the core engine, not through a UI prompt.

MagiCAD-DWGs are NOT a supported input here. Object Enabler renders MagiCAD
proxies as 2D fragments under DXFOUT just as it did in alpha2's POC; the
right path for MagiCAD content is still ``-MAGIIFCCD`` on the colleague's
machine, then ``--magicad-ifc`` merge in dxf2ifc.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Callable

from dxf2ifc.core.preprocessing import find_accoreconsole

_DXFOUT_SCR = (
    '(setvar "FILEDIA" 0)\r\n'
    '(setvar "CMDECHO" 1)\r\n'
    '(command "_.DXFOUT" "{out_path}" "_V" "_2018" "16")\r\n'
)


class DwgPreconvertError(RuntimeError):
    """DWG -> DXF preconversion failed (timeout, accoreconsole error, empty output)."""


def convert_dwg_to_dxf(
    dwg_path: str | Path,
    workdir: str | Path,
    *,
    accoreconsole: Path | None = None,
    timeout_s: float = 90.0,
    progress: Callable[[str], None] | None = None,
) -> Path:
    """Preconvert ``dwg_path`` to a temporary DXF inside ``workdir``.

    Returns the absolute path to the produced ``.dxf``. The caller is
    responsible for cleaning up ``workdir`` after the downstream IFC
    conversion has consumed the intermediate DXF.

    ``accoreconsole`` is auto-located via :func:`find_accoreconsole` when
    not supplied. Raises :class:`FileNotFoundError` if no AutoCAD install
    is found, :class:`DwgPreconvertError` if the subprocess fails or the
    output DXF is missing / suspiciously small.
    """
    dwg = Path(dwg_path)
    work = Path(workdir)
    work.mkdir(parents=True, exist_ok=True)

    if accoreconsole is None:
        accoreconsole = find_accoreconsole()
    if accoreconsole is None:
        raise FileNotFoundError(
            "accoreconsole.exe not found — DWG input requires an AutoCAD "
            "install. Convert the DWG to DXF manually (DXFOUT in AutoCAD) "
            "and supply the .dxf instead."
        )

    out_dxf = work / (dwg.stem + ".dxf")
    if out_dxf.exists():
        out_dxf.unlink()

    scr_path = work / "dwgout.scr"
    # accoreconsole's LISP wants forward slashes in path literals; backslashes
    # would be interpreted as escape sequences in the double-quoted string.
    out_for_lisp = str(out_dxf).replace("\\", "/")
    scr_path.write_text(
        _DXFOUT_SCR.format(out_path=out_for_lisp),
        encoding="utf-8",
    )

    if progress is not None:
        progress(f"Preconverting DWG → DXF via accoreconsole… ({dwg.name})")

    creationflags = 0
    if sys.platform == "win32":
        # DETACHED_PROCESS — see preprocessing.py:437–445 for the rationale
        # (windowed PyInstaller exe has no inherited console host).
        creationflags = 0x00000008

    log_path = work / "accoreconsole-dwgout.log"
    try:
        with log_path.open("w", encoding="utf-8") as log_fh:
            completed = subprocess.run(
                [
                    str(accoreconsole),
                    "/i",
                    str(dwg),
                    "/s",
                    str(scr_path),
                ],
                stdin=subprocess.DEVNULL,
                stdout=log_fh,
                stderr=subprocess.STDOUT,
                timeout=timeout_s,
                check=False,
                creationflags=creationflags,
            )
    except subprocess.TimeoutExpired as exc:
        raise DwgPreconvertError(
            f"accoreconsole timed out after {timeout_s:.0f}s on {dwg.name}. "
            f"Diagnostics: {log_path}"
        ) from exc
    except OSError as exc:
        raise DwgPreconvertError(
            f"accoreconsole failed to start: {exc}. Diagnostics: {log_path}"
        ) from exc

    if completed.returncode != 0 and progress is not None:
        progress(
            f"accoreconsole exited with code {completed.returncode}; "
            f"diagnostics preserved in {log_path}"
        )

    if not out_dxf.exists():
        raise DwgPreconvertError(
            f"DXFOUT did not produce an output DXF. accoreconsole exit code "
            f"{completed.returncode}. Diagnostics: {log_path}"
        )
    if out_dxf.stat().st_size < 1024:
        raise DwgPreconvertError(
            f"DXFOUT produced a suspiciously small DXF ({out_dxf.stat().st_size} "
            f"bytes). accoreconsole exit code {completed.returncode}. "
            f"Diagnostics: {log_path}"
        )

    return out_dxf
