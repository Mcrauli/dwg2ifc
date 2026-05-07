"""DWG → DXF preconversion via hidden ``acad.exe`` (COM Visible=False).

Why this module exists
----------------------

`accoreconsole.exe` (the headless AutoCAD core dxf2ifc uses for STLOUT
tessellation in :mod:`dxf2ifc.core.preprocessing`) **cannot load ARX
object enablers** — Autodesk's documented architectural limit, also
verified empirically: ``(arxload "MagiCAD_r25x64.arx")`` returns
``ARXLOAD failed``. So when a DWG carries MagiCAD entities
(``MAGIPathwayDevice``, ``MAGIAccessory``, ``MAGIPathwaySegment`` etc),
accoreconsole reads them as opaque ``ACAD_PROXY_ENTITY`` records that
``EXPLODE`` only into 2D wireframe — never 3DSOLID children.

The full ``acad.exe`` runtime, on the other hand, autoloads the
MagiCAD Object Enabler / FULL MagiCAD ARX from the registry's
Applications-key. We launch it via pywin32 COM with
``Application.Visible = False`` — verified in spike v3 to keep the
window invisible while loading the ARX. EXPLODE on a colleague's
machine with FULL MagiCAD-licensed installs yields real 3DSOLID
children that downstream STLOUT can tessellate.

On a render-only Object Enabler machine (Lauri's), EXPLODE silently
no-ops and MagiCAD parts drop out — but Lauri's KYL-LISP geometry
still goes through the rest of the pipeline normally.

Output
------

The module returns the path to an intermediate DXF written by
``DXFOUT``, with all proxies/MAGI* entities EXPLODEd in-place where
the ARX permitted. STLOUT-tessellated meshes for any 3DSOLID children
that EXPLODE produced are stashed in a per-process module global
(:func:`last_explode_meshes`) so the orchestrator can fold them into
its ``acis_meshes`` side-channel without a second accoreconsole pass.

Singleton hidden AutoCAD
-------------------------

The COM ``Application`` instance is held in module state so multiple
DWG conversions in one Python process amortise the cold-start
(~14 s on Lauri's machine to dispatch + load profile + ARX). Subsequent
calls reuse the running app (~3 s/conversion). An ``atexit`` hook
quits gracefully.

Safety
------

* Visible=False set BEFORE ``Documents.Open`` so the main frame never
  paints. Spike v3 verified zero window flash.
* A throwaway profile ``dxf2ifc_headless`` is used (created on first
  call) so RECENTFILES, FILEDIA, CMDDIA, SDI sysvar overrides do not
  contaminate the user's default profile.
* Original DWG is opened ReadOnly + closed with ``SaveChanges=False``;
  the source file is never touched.
"""

from __future__ import annotations

import atexit
import shutil
import struct
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

# Import AcisMeshData via the existing preprocessing module so the
# meshes we produce here drop into the same channel orchestrator
# already plumbs through ``read_dxf``.
from dxf2ifc.core.preprocessing import AcisMeshData, _parse_stl


# ---------------------------------------------------------------------------
# Module state — singleton COM app + last-call mesh cache
# ---------------------------------------------------------------------------

_app = None  # COM Application instance, lazily created
_last_meshes: dict[str, AcisMeshData] = {}


def last_explode_meshes() -> dict[str, AcisMeshData]:
    """Return the per-handle meshes produced by the most recent
    :func:`preconvert_dwg` call. Keys are uppercase proxy handles.
    Empty dict when EXPLODE produced no 3DSOLID children (render-only
    Object Enabler tilanne) or when no DWG has been preconverted in
    this process yet."""
    return dict(_last_meshes)


def _shutdown() -> None:
    """``atexit`` hook — release the COM application gracefully."""
    global _app
    if _app is not None:
        try:
            _app.Quit()
        except Exception:  # noqa: BLE001 — COM teardown is allowed to be lossy
            pass
        _app = None


atexit.register(_shutdown)


# ---------------------------------------------------------------------------
# AutoLISP body — ssget proxies, EXPLODE each, STLOUT 3DSOLID children,
# DXFOUT intermediate. Same pattern as core/preprocessing.py's
# accoreconsole-driven EXPLODE/STLOUT, but here it runs inside
# acad.exe so MagiCAD ARX is loaded.
# ---------------------------------------------------------------------------


def _build_lisp(stl_dir: str, intermediate_dxf: str, log_path: str) -> str:
    """Construct the LISP body. Single-line so SendCommand reads it as
    one form. Placeholders are substituted with concrete paths."""
    return (
        '(progn '
        '(setvar "FILEDIA" 0) '
        '(setvar "CMDDIA" 0) '
        '(setvar "FACETRES" 0.1) '
        f'(setq logf (open "{log_path}" "w")) '
        # Phase 1 — collect handles BEFORE any EXPLODE so the selection
        # set we iterate doesn't get invalidated by the mutations.
        '(setq ss (ssget "_X" \'((0 . "ACAD_PROXY_ENTITY,MAGI*")))) '
        '(write-line (strcat "FOUND " (if ss (itoa (sslength ss)) "0")) logf) '
        '(setq handles \'()) '
        '(if ss '
        '(progn '
        '(setq i 0 n (sslength ss)) '
        '(while (< i n) '
        '(setq el (entget (ssname ss i))) '
        '(setq handles (cons (strcase (cdr (assoc 5 el))) handles)) '
        '(setq i (1+ i))))) '
        # Phase 2 — EXPLODE each, STLOUT any 3DSOLID children using
        # the ORIGINAL handle as filename prefix so the merging logic
        # in Python can recover the source.
        f'(setq stl_out "{stl_dir}") '
        '(setq ok 0 fail 0) '
        '(foreach h handles '
        '(setq ent (handent h)) '
        '(if ent '
        '(progn '
        '(setq r (vl-catch-all-apply (function (lambda () (command "_.EXPLODE" ent))))) '
        '(if (vl-catch-all-error-p r) '
        '(setq fail (1+ fail)) '
        '(progn '
        '(setq ok (1+ ok)) '
        '(setq newents (ssget "_P")) '
        '(if newents '
        '(progn '
        '(setq j 0 nn (sslength newents) ctr 0) '
        '(while (< j nn) '
        '(setq cel (entget (ssname newents j))) '
        '(if (eq (cdr (assoc 0 cel)) "3DSOLID") '
        '(progn '
        '(command "_.STLOUT" (ssname newents j) "" "Y" '
        '(strcat stl_out h "_" (itoa ctr) ".stl")) '
        '(setq ctr (1+ ctr)))) '
        '(setq j (1+ j))) '
        '(write-line (strcat "CHILDREN " h " " (itoa ctr)) logf)))))))) '
        '(write-line (strcat "EXPLODE_OK=" (itoa ok) " EXPLODE_FAIL=" (itoa fail)) logf) '
        # Phase 3 — DXFOUT the modified modelspace. Decimal-precision
        # 16 (highest) preserves MagiCAD's vertex coordinates verbatim.
        # "Y" answers the file-overwrite prompt.
        f'(command "_.DXFOUT" "{intermediate_dxf}" "" 16 "Y") '
        '(write-line "DXFOUT_DONE" logf) '
        '(close logf) '
        '(princ))\n'
    )


# ---------------------------------------------------------------------------
# COM session — singleton hidden AutoCAD
# ---------------------------------------------------------------------------


def _ensure_app(progress: Callable[[str], None] | None = None):
    """Return the singleton hidden AutoCAD application; create it on
    first call. Returns ``None`` if pywin32 / AutoCAD isn't installed
    (caller falls back to a DXF-only path)."""
    global _app
    if _app is not None:
        return _app
    if sys.platform != "win32":
        return None
    try:
        import win32com.client  # type: ignore[import-not-found]
    except ImportError:
        if progress is not None:
            progress("pywin32 ei asennettu — DWG-input vaatii sen + AutoCAD:in")
        return None

    if progress is not None:
        progress("Käynnistetään AutoCAD piilotettuna (Visible=False)…")
    t0 = time.time()
    try:
        app = win32com.client.DispatchEx("AutoCAD.Application.25")
    except Exception as exc:  # noqa: BLE001
        if progress is not None:
            progress(
                "AutoCAD COM Dispatch epäonnistui — onko AutoCAD 2025 "
                f"asennettu? ({exc!s})"
            )
        return None

    # CRITICAL: Visible=False before any document operation, otherwise
    # the main frame paints once and the user sees a flash. Verified
    # in spike v3.
    try:
        app.Visible = False
    except Exception:  # noqa: BLE001
        pass

    elapsed = time.time() - t0
    if progress is not None:
        progress(f"AutoCAD valmis ({elapsed:.1f}s, näkymätön ikkuna)")
    _app = app
    return app


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def preconvert_dwg(
    dwg_path: str | Path,
    *,
    timeout_s: float = 300.0,
    progress: Callable[[str], None] | None = None,
) -> Path | None:
    """EXPLODE all proxy/MAGI* entities in ``dwg_path`` via hidden
    ``acad.exe``, STLOUT any resulting 3DSOLID children, and DXFOUT an
    intermediate DXF the rest of the dxf2ifc pipeline can read with
    ezdxf.

    Returns the path to the intermediate DXF, or ``None`` when the
    preconversion could not run (pywin32 missing, AutoCAD COM
    unavailable, file does not exist, EXPLODE timed out). Per-handle
    meshes from STLOUT are stashed in :func:`last_explode_meshes` for
    the orchestrator to merge into ``acis_meshes``.

    Never raises — the orchestrator falls back to direct DXF reading
    when this returns ``None``.
    """
    global _last_meshes
    _last_meshes = {}

    src = Path(dwg_path).resolve()
    if not src.is_file():
        return None

    app = _ensure_app(progress=progress)
    if app is None:
        return None

    workdir = Path(tempfile.mkdtemp(prefix="dxf2ifc_dwg_"))
    stl_dir = workdir / "stl"
    stl_dir.mkdir()
    intermediate_dxf = workdir / "preconverted.dxf"
    log_path = workdir / "lisp.log"

    try:
        if progress is not None:
            progress(f"Avataan DWG ReadOnly: {src.name}")
        try:
            doc = app.Documents.Open(str(src), True)  # ReadOnly=True
        except Exception as exc:  # noqa: BLE001
            if progress is not None:
                progress(f"AutoCAD Open epäonnistui: {exc!s}")
            return None

        if progress is not None:
            progress("Räjäytetään MagiCAD/proxy-objektit + DXFOUT…")

        lisp = _build_lisp(
            stl_dir=stl_dir.as_posix() + "/",
            intermediate_dxf=intermediate_dxf.as_posix(),
            log_path=log_path.as_posix(),
        )
        try:
            doc.SendCommand(lisp)
        except Exception as exc:  # noqa: BLE001
            if progress is not None:
                progress(f"SendCommand epäonnistui: {exc!s}")

        # SendCommand is async; poll for the DXFOUT_DONE marker in the
        # log to know when LISP finished. The log file gets written
        # only at end (after close), so we poll for its presence + size.
        wait_t = time.time()
        while time.time() - wait_t < timeout_s:
            if log_path.is_file() and intermediate_dxf.is_file():
                try:
                    log_text = log_path.read_text(encoding="utf-8", errors="replace")
                    if "DXFOUT_DONE" in log_text:
                        break
                except Exception:  # noqa: BLE001
                    pass
            time.sleep(0.5)
        else:
            if progress is not None:
                progress(f"AutoCAD-EXPLODE timeout ({timeout_s:.0f}s)")

        # Close the document. Don't quit the app — keep it singleton-warm.
        try:
            doc.Close(False)  # SaveChanges=False
        except Exception:  # noqa: BLE001
            pass

        # Parse STLs into per-handle meshes
        meshes: dict[str, AcisMeshData] = {}
        per_handle: dict[str, list[Path]] = {}
        for stl_file in stl_dir.glob("*.stl"):
            handle = stl_file.stem.rsplit("_", 1)[0].upper()
            per_handle.setdefault(handle, []).append(stl_file)
        for handle, files in per_handle.items():
            merged_v: list[tuple[float, float, float]] = []
            merged_f: list[tuple[int, ...]] = []
            v_to_idx: dict[tuple[float, float, float], int] = {}
            for stl_file in sorted(files):
                try:
                    sub = _parse_stl(stl_file)
                except Exception:  # noqa: BLE001
                    continue
                local: list[int] = []
                for v in sub.vertices:
                    idx = v_to_idx.get(v)
                    if idx is None:
                        idx = len(merged_v)
                        v_to_idx[v] = idx
                        merged_v.append(v)
                    local.append(idx)
                for face in sub.faces:
                    merged_f.append(tuple(local[i] for i in face))
            if merged_v and merged_f:
                meshes[handle] = AcisMeshData(tuple(merged_v), tuple(merged_f))
        _last_meshes = meshes

        if progress is not None:
            progress(
                f"DWG-preconvert valmis: {len(meshes)} MagiCAD-mesh, "
                f"välitilanne-DXF {intermediate_dxf.stat().st_size // 1024} kB"
                if intermediate_dxf.is_file() else
                f"DWG-preconvert: {len(meshes)} mesh, välitilanne-DXF puuttuu"
            )

        if not intermediate_dxf.is_file():
            return None

        # Move the intermediate DXF out of the temp workdir into a
        # caller-managed location so we can clean the workdir now.
        # The orchestrator will atexit-clean the moved file later.
        out_dir = Path(tempfile.mkdtemp(prefix="dxf2ifc_dwg_out_"))
        out_path = out_dir / intermediate_dxf.name
        shutil.move(str(intermediate_dxf), str(out_path))
        atexit.register(lambda p=out_dir: shutil.rmtree(p, ignore_errors=True))
        return out_path
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
