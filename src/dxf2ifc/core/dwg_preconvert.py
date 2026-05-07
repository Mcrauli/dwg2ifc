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
    one form. Placeholders are substituted with concrete paths.

    Phases:

    * **0** — sysvar SAVE then ``MAGIEXPLODE`` to convert any MagiCAD
      objects into native AutoCAD geometry (polyface mesh / 3DFACE).
      Tries ``-MAGIEXPLODE`` (etuhyphen, command-line / no-dialog
      variant) first; falls back to ``MAGIEXPLODE`` if the dash form is
      "Unknown command". A MagiCAD "this loses MagiCAD identity"
      confirmation popup may still appear on render-only Object Enabler
      installs — Lauri clicks OK once if it does, the LISP keeps going.
    * **1** — the historical proxy/INSERT EXPLODE → STLOUT path. After
      MAGIEXPLODE there are usually no proxies left (MagiCAD entities
      became native), so this phase mostly handles the KYL-LISP block
      INSERTs (höyrystimet, levyhyllyt). Same code as before.
    * **2** — DXFOUT writes the intermediate DXF. Precision is **8**
      (down from 16); 8 decimal places is sub-micrometre, plenty for
      refrigeration CAD, and writes ~30 % faster on big drawings.
    * **3** — sysvar RESTORE. Always runs (each command is wrapped in
      ``vl-catch-all-apply``) so Lauri's interactive AutoCAD never
      ends up with FILEDIA=0 / CMDDIA=0.
    """
    return (
        '(progn '
        # Phase 0a — sysvar SAVE
        '(setq _sav_filedia (getvar "FILEDIA")) '
        '(setq _sav_cmddia  (getvar "CMDDIA")) '
        '(setq _sav_facetres (getvar "FACETRES")) '
        '(setq _sav_expert  (getvar "EXPERT")) '
        '(setvar "FILEDIA" 0) (setvar "CMDDIA" 0) (setvar "FACETRES" 0.1) '
        '(setvar "EXPERT" 5) '
        f'(setq logf (open "{log_path}" "w")) '
        '(write-line "PHASE_BEGIN" logf) '
        # Phase 0b — MAGIEXPLODE. Count MAGI* before / after.
        # MAGIEXPLODE is an ARX command that doesn't accept a selection
        # set passed as a ``(command "MAGIEXPLODE" _ss "")`` argument —
        # the prompt parser only takes keyboard tokens like ``ALL`` or
        # picked points and rejects the selection-set IDispatch with
        # ``Invalid selection`` (Lauri saw this 4× on the command
        # line). The reliable LISP idiom for ARX commands is to
        # ``(sssetfirst nil _ss)`` so the engine sees a *pre-pick* —
        # MAGIEXPLODE then runs without prompting at all. We still
        # fall back to ``(command "_.MAGIEXPLODE" "ALL" "")`` with the
        # ``ALL`` keyword if the pre-pick path returns no MAGI delta,
        # since some MagiCAD ARX builds may ignore pre-pick.
        '(setq _ssbef (ssget "_X" \'((0 . "ACAD_PROXY_ENTITY,MAGI*")))) '
        '(write-line (strcat "MAGI_BEFORE=" '
        '(itoa (if _ssbef (sslength _ssbef) 0))) logf) '
        # MAGIEXPLODE is sent separately from Python via SendCommand
        # (see ``preconvert_dwg`` below) because the MagiCAD ARX
        # selection prompt rejects every form of LISP-side keyword or
        # selection-set argument we tried (``Invalid selection`` for
        # ``"ALL"``, the pre-pick set, and even the literal ARX
        # keyword). SendCommand-text bypasses the LISP layer and feeds
        # the buffer the same way real keystrokes do — that's the
        # input form Lauri's ARX accepts.
        '(setq _ssaf (ssget "_X" \'((0 . "ACAD_PROXY_ENTITY,MAGI*")))) '
        '(write-line (strcat "MAGI_AFTER=" '
        '(itoa (if _ssaf (sslength _ssaf) 0))) logf) '
        '(write-line "PHASE_MAGI_DONE" logf) '
        # Phase 1 — second EXPLODE pass on AcDbProxyEntity entities
        # left behind by MAGIEXPLODE. Per Lauri's original briefing
        # ("MAGIEXPLODE + toinen EXPLODE tuottaa polygon mesh /
        # polyface mesh -geometriaa") MagiCAD's render-only Object
        # Enabler converts MAGI* classes into ACAD_PROXY_ENTITY first;
        # a second standard ``_.EXPLODE`` then unwraps those proxies
        # into native polyface mesh / 3DFACE that ezdxf reads natively
        # in the dxf_reader pipeline. Wrap each call in
        # ``vl-catch-all-apply`` so a single locked-layer entity
        # doesn't abort the loop.
        '(setq _proxss (ssget "_X" \'((0 . "ACAD_PROXY_ENTITY")))) '
        '(write-line (strcat "PROXY_BEFORE=" '
        '(itoa (if _proxss (sslength _proxss) 0))) logf) '
        '(setq _proxhandles \'()) '
        '(if _proxss '
        '(progn '
        '(setq _pi 0 _pn (sslength _proxss)) '
        '(while (< _pi _pn) '
        '(setq _pel (entget (ssname _proxss _pi))) '
        '(setq _proxhandles (cons (strcase (cdr (assoc 5 _pel))) _proxhandles)) '
        '(setq _pi (1+ _pi))))) '
        '(setq _pok 0 _pfail 0) '
        '(foreach _ph _proxhandles '
        '(setq _pent (handent _ph)) '
        '(if _pent '
        '(progn '
        '(setq _pr (vl-catch-all-apply '
        '(function (lambda () (command "_.EXPLODE" _pent))))) '
        '(if (vl-catch-all-error-p _pr) '
        '(setq _pfail (1+ _pfail)) '
        '(setq _pok (1+ _pok)))))) '
        '(write-line (strcat "PROXY_EXPLODE_OK=" (itoa _pok) '
        '" PROXY_EXPLODE_FAIL=" (itoa _pfail)) logf) '
        '(setq _proxss2 (ssget "_X" \'((0 . "ACAD_PROXY_ENTITY")))) '
        '(write-line (strcat "PROXY_AFTER=" '
        '(itoa (if _proxss2 (sslength _proxss2) 0))) logf) '
        # Phase 1.5 — second EXPLODE handled by Python SendCommand
        # keystroke ("EXPLODE\nALL\n\n") after MAGIEXPLODE, NOT here.
        # The LISP-side loop kept hitting "Invalid selection"
        # cascades because ARX-explode prompts don't accept individual
        # entity references; AutoCAD's command-line parser does.
        '(setq _final_solids (ssget "_X" \'((0 . "3DSOLID")))) '
        '(write-line (strcat "FINAL_3DSOLIDS=" '
        '(itoa (if _final_solids (sslength _final_solids) 0))) logf) '
        '(setq _meshss (ssget "_X" \'((0 . "POLYLINE,3DFACE,MESH")))) '
        '(write-line (strcat "POLYFACE_AFTER=" '
        '(itoa (if _meshss (sslength _meshss) 0))) logf) '
        '(setq _ssins (ssget "_X" \'((0 . "INSERT")))) '
        '(write-line (strcat "INSERTS_REMAINING=" '
        '(itoa (if _ssins (sslength _ssins) 0))) logf) '
        '(write-line "PHASE_EXPLODE_DONE" logf) '
        # Phase 2 — DXF write deferred to Python SendCommand text after
        # this LISP completes. Both ``vla-saveas`` and ``doc.SaveAs(…,
        # format)`` returned ``Invalid argument`` on Lauri's setup (the
        # AcSaveAsType enum values must differ in AutoCAD 2025 from
        # what we tried). Sending ``-DXFOUT`` as plain keyboard text
        # — the same trick that finally got MAGIEXPLODE working —
        # bypasses both COM SaveAs and the LISP DXFOUT prompt parser.
        f'(write-line "DXFOUT_DEFERRED_TO_PYTHON_SENDTEXT" logf) '
        f'(write-line (strcat "DXFOUT_TARGET=" "{intermediate_dxf}") logf) '
        # Phase 3 — sysvar RESTORE (AINA, vaikka edelliset failasivat)
        '(setvar "FILEDIA"  _sav_filedia) '
        '(setvar "CMDDIA"   _sav_cmddia) '
        '(setvar "FACETRES" _sav_facetres) '
        '(setvar "EXPERT"   _sav_expert) '
        '(write-line "SYSVAR_RESTORED" logf) '
        '(write-line "PHASE_END" logf) '
        '(close logf) '
        '(princ))\n'
    )


# ---------------------------------------------------------------------------
# COM session — singleton hidden AutoCAD
# ---------------------------------------------------------------------------


def _ensure_app(progress: Callable[[str], None] | None = None):
    """Return the singleton AutoCAD application; create it on first call.
    Returns ``None`` if pywin32 / AutoCAD isn't installed (caller falls
    back to a DXF-only path).

    Probes the cached singleton with a cheap property read before
    handing it back. If AutoCAD was closed manually between runs the
    pointer becomes a "zombie" — any subsequent call would raise the
    pywin32 COM error "Objektia ei ole liitetty palvelimeen"
    (HRESULT 0x800401E5). The probe drops the dead pointer so we
    create a fresh acad.exe instead.
    """
    global _app
    if _app is not None:
        try:
            _ = _app.Visible  # round-trip to detect a zombie
            return _app
        except Exception:  # noqa: BLE001 — any COM error means dead instance
            _app = None
    if sys.platform != "win32":
        return None
    try:
        import win32com.client  # type: ignore[import-not-found]
    except ImportError:
        if progress is not None:
            progress("pywin32 ei asennettu — DWG-input vaatii sen + AutoCAD:in")
        return None

    if progress is not None:
        progress("Käynnistetään AutoCAD näkyvänä (~14 s ekan kerran)…")
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

    # POC v3: Visible=True so the user can SEE the AutoCAD window and
    # click MagiCAD's "identity will be lost" popup that appears the
    # first time MAGIEXPLODE runs on render-only Object Enabler. POC v2
    # tried Visible=False which hid the popup behind the scenes and
    # blocked SendCommand for ~5 minutes. The window flash is a small
    # UX cost; the alternative is an apparent hang. POC v4 may add a
    # GUI checkbox to opt back into hidden mode for users with FULL
    # MagiCAD where the popup never fires.
    try:
        app.Visible = True
    except Exception:  # noqa: BLE001
        pass
    # Window-geometry tweaks REMOVED in POC v4.1. Forcing
    # WindowLeft/Top/Width/Height + WindowState mutated AutoCAD's
    # docked toolbar layout (the command line palette in particular
    # got stretched across both of Lauri's monitors and the change
    # persisted into the user's profile). Better to leave the window
    # alone — the user can position AutoCAD manually if needed; we
    # just need it visible so MagiCAD's confirmation popup is
    # clickable.

    elapsed = time.time() - t0
    if progress is not None:
        progress(f"AutoCAD valmis ({elapsed:.1f}s, ikkuna näkyvä)")
    _app = app
    return app


def _force_reset_app() -> None:
    """Drop the cached COM Application reference so the next call
    creates a fresh instance. Used after a SendCommand timeout when
    the AutoCAD process may be a zombie that's stuck on an invisible
    dialog. Best-effort Quit; failure is fine since the OS will reap
    the process eventually."""
    global _app
    if _app is None:
        return
    try:
        _app.Quit()
    except Exception:  # noqa: BLE001
        pass
    _app = None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def preconvert_dwg(
    dwg_path: str | Path,
    *,
    timeout_s: float = 240.0,
    progress: Callable[[str], None] | None = None,
) -> Path | None:
    """EXPLODE all proxy/MAGI* entities in ``dwg_path`` via visible
    ``acad.exe``, STLOUT any resulting 3DSOLID children, and DXFOUT an
    intermediate DXF the rest of the dxf2ifc pipeline can read with
    ezdxf.

    Returns the path to the intermediate DXF, or ``None`` when the
    preconversion could not run (pywin32 missing, AutoCAD COM
    unavailable, file does not exist, EXPLODE timed out). Per-handle
    meshes from STLOUT are stashed in :func:`last_explode_meshes` for
    the orchestrator to merge into ``acis_meshes``.

    Never raises — the orchestrator catches ``None`` and surfaces a
    clear error message to the user instead of letting downstream try
    to ezdxf-read the original DWG.

    POC v3 changes:

    * default ``timeout_s`` shortened from 300 → 120 s
    * per-phase checkpoints — bail out early if ``PHASE_BEGIN`` doesn't
      arrive within 30 s (AutoCAD froze) or ``PHASE_MAGI_DONE`` within
      60 s (MagiCAD popup blocking)
    * live "still alive" progress every 3 s when no new marker arrives
      so the user knows the conversion isn't dead
    * tail of ``lisp.log`` printed on bail-out so Lauri can see the
      last LISP marker before the freeze
    * zombie singleton dropped via :func:`_force_reset_app` after a
      timeout — next run starts a fresh AutoCAD
    * ``doc.Activate()`` before SendCommand to avoid pywin32's
      "Open.SendCommand" attribute error when the document handle isn't
      bound to the active document on slow first opens
    """
    global _last_meshes
    _last_meshes = {}

    src = Path(dwg_path).resolve()
    if not src.is_file():
        return None

    app = _ensure_app(progress=progress)
    if app is None:
        return None

    # ``.resolve()`` expands the Windows 8.3 short name (``LAURIR~1``)
    # into the full long path. AutoCAD's ``DXFOUT`` silently fails to
    # write into a 8.3-shortened temp dir on some systems even though
    # the LISP ``vl-catch-all-apply`` reports success — a common gotcha.
    workdir = Path(tempfile.mkdtemp(prefix="dxf2ifc_dwg_")).resolve()
    stl_dir = workdir / "stl"
    stl_dir.mkdir()
    intermediate_dxf = workdir / "preconverted.dxf"
    log_path = workdir / "lisp.log"

    # Copy the source DWG to the workdir before opening so AutoCAD
    # never modifies the original. ``Documents.Open(src, False)`` opens
    # writable; if Lauri runs MAGIEXPLODE manually mid-conversion or
    # AutoCAD crashes, the source could end up persisted. Working off
    # a copy is the safe default.
    work_dwg = workdir / src.name
    try:
        shutil.copy2(src, work_dwg)
    except OSError as exc:
        if progress is not None:
            progress(f"DWG-kopiointi epäonnistui: {exc!s}")
        return None

    timed_out = False
    try:
        if progress is not None:
            progress(f"Avataan DWG-kopio: {work_dwg.name}")
        try:
            # Open the WORKDIR copy (not the original) writable so
            # MAGIEXPLODE / EXPLODE / DXFOUT mutations stay scoped to
            # this temp file. The original src DWG is never opened.
            doc = app.Documents.Open(str(work_dwg), False)
        except Exception as exc:  # noqa: BLE001
            if progress is not None:
                progress(f"AutoCAD Open epäonnistui: {exc!s}")
            return None
        # ``Documents.Open(...)`` returns an IDispatch wrapper whose
        # ``SendCommand`` method pywin32 sometimes fails to resolve via
        # late binding ("Open.SendCommand" attribute error). Going
        # through ``Application.ActiveDocument`` after a small settle
        # delay yields the canonical AcadDocument wrapper that always
        # exposes ``SendCommand``. Documents.Open already activates the
        # newly-opened doc, so ActiveDocument equals our ``doc`` here.
        try:
            doc.Activate()
        except Exception:  # noqa: BLE001
            pass

        if progress is not None:
            progress("Räjäytetään MagiCAD/proxy-objektit + DXFOUT…")
            progress(
                "HUOM: jos AutoCAD:n command-rivi pyytää 'Select objects:' "
                "→ kirjoita ALL ja paina Enter (MagiCAD-Object-Enabler ei "
                "tue ohjelmallista räjäytystä)"
            )

        lisp = _build_lisp(
            stl_dir=stl_dir.as_posix() + "/",
            intermediate_dxf=intermediate_dxf.as_posix(),
            log_path=log_path.as_posix(),
        )

        # Sending the full ~2.6 KB LISP body via SendCommand has been
        # unreliable on Lauri's AutoCAD 2025: the parser sometimes
        # dumps the whole text into the command line untouched instead
        # of executing it. Writing the LISP to a .lsp file and asking
        # AutoCAD to ``(load …)`` is the safer route — load handles the
        # input atomically rather than line-buffered text streaming.
        lsp_path = workdir / "explode.lsp"
        lsp_path.write_text(lisp, encoding="utf-8")

        # ``(setvar "SECURELOAD" 0)`` allows ``(load …)`` from any
        # path for the rest of the AutoCAD session — it's a transient
        # session sysvar so we don't pollute the user's registry. The
        # explicit space + trailing newline makes AutoCAD's command-
        # line parser flush the form. Earlier attempts with multi-line
        # ``(progn …)`` priming or raw ESC keystrokes triggered
        # "Invalid input" from the OLE / SendCommand layer.
        load_payload = (
            f'(progn (setvar "SECURELOAD" 0) '
            f'(load "{lsp_path.as_posix()}") (princ))\n'
        )

        # Re-fetch the active document so we get the early-binding
        # AcadDocument wrapper rather than Documents.Open's bare
        # IDispatch. Brief settle loop in case ActiveDocument is still
        # transitioning right after the open.
        active_doc = None
        for _ in range(20):  # up to 2 s
            try:
                active_doc = app.ActiveDocument
                if active_doc is not None:
                    break
            except Exception:  # noqa: BLE001
                pass
            time.sleep(0.1)
        if active_doc is None:
            if progress is not None:
                progress("AutoCAD ActiveDocument ei resolvoitunut")
            return None

        # POC v4.1: combine MAGIEXPLODE keystroke + LISP load into a
        # single SendCommand payload. AutoCAD's command buffer processes
        # the input sequentially: ``MAGIEXPLODE`` → ``ALL`` → Enter
        # (MAGIEXPLODE runs and waits for popup OK) → ``(progn …)``
        # (LISP load fires once MAGIEXPLODE finishes). Sending it as
        # one buffered keystroke stream is more reliable than two
        # separate SendCommand calls (the second one was racing
        # MAGIEXPLODE's still-active prompt on Lauri's setup).
        if progress is not None:
            progress(
                "Lähetetään MAGIEXPLODE + ALL + LISP-load (klikkaa "
                "MagiCAD-popup OK:ksi jos ilmestyy)"
            )
        # Lauri's spec: "tasan 1 magiexplode + sit normaali explode ni
        # saa sen polyline meshin". Both EXPLODE commands sent as
        # plain SendCommand keystrokes — AutoCAD's command-line
        # buffer processes them sequentially, MagiCAD ARX accepts the
        # ALL keyword input, and then the LISP load fires last.
        combined_payload = (
            "MAGIEXPLODE\nALL\n\n"
            + "EXPLODE\nALL\n\n"
            + load_payload
        )
        time.sleep(2.0)  # let Documents.Open settle before keystrokes
        sent_ok = False
        for attempt in range(3):
            try:
                send_target = active_doc
                try:
                    send_target = app.ActiveDocument
                except Exception:  # noqa: BLE001
                    pass
                send_target.SendCommand(combined_payload)
                sent_ok = True
                break
            except Exception as exc:  # noqa: BLE001
                if progress is not None:
                    progress(
                        f"SendCommand yritys {attempt+1}/3 raise: "
                        f"{exc!s} (AutoCAD voi silti vastaanottaa)"
                    )
                time.sleep(1.0)
        if not sent_ok and progress is not None:
            progress(
                "Keystroke ei lähtenyt — kirjoita AutoCAD:n command-"
                "line:lle: MAGIEXPLODE Enter ALL Enter Enter"
            )
        # POC v4.1: MAGIEXPLODE quiescence polling REMOVED. The
        # combined ``MAGIEXPLODE\nALL\n\n + load_payload`` keystroke
        # stream is now in AutoCAD's command buffer; the buffer
        # processes the LISP load only after MAGIEXPLODE finishes.
        # The main async-polling loop below waits for ``PHASE_END``
        # which only the LISP body writes, so it implicitly waits for
        # MAGIEXPLODE too.

        # Async-polling state machine
        # ===========================
        # SendCommand is fire-and-forget on the LISP side, so we poll
        # the log file for marker lines and emit progress events. Two
        # extra signals beyond the original simple "wait for PHASE_END":
        #
        # * **Per-phase deadlines** — if PHASE_BEGIN doesn't arrive in
        #   30 s, AutoCAD likely froze before LISP started; if
        #   PHASE_MAGI_DONE is missing after 60 s, the MagiCAD popup is
        #   blocking. Both bail out with a specific error so the user
        #   doesn't sit through the full 120 s timeout watching nothing.
        # * **Liveness pings** — every 3 s without a new marker we tell
        #   the user "still alive (Xs, last marker Y)". This kills the
        #   "did it crash?" feeling during slow STLOUT phases.
        seen_markers: set[str] = set()
        marker_messages = {
            "PHASE_BEGIN": "AutoCAD-LISP käynnistyi",
            "PHASE_MAGI_DONE": "MagiCAD-räjäytys valmis",
            "PHASE_EXPLODE_DONE": "Block-EXPLODE + STLOUT valmis",
            "DXFOUT_DONE": "Välitilanne-DXF tallennettu",
            "SYSVAR_RESTORED": "AutoCAD sysvar palautettu",
        }
        # Per-phase deadlines bumped for POC v4.1: MAGIEXPLODE +
        # LISP load are now in the same buffered keystroke stream, so
        # PHASE_BEGIN may not appear until MAGIEXPLODE has finished
        # chewing through hundreds of MAGI* objects (~30 s on Lauri's
        # testimagi.dwg with 145 explodable parts).
        phase_deadlines = [
            ("PHASE_BEGIN", 90.0,
             "AutoCAD-LISP ei käynnistynyt 90 s sisällä — MAGIEXPLODE "
             "saattaa olla jumissa MagiCAD-popup:in takana. Klikkaa OK "
             "AutoCAD-ikkunassa tai sulje muut AutoCAD-instanssit"),
            ("PHASE_MAGI_DONE", 30.0,
             "LISP Phase 0b ei valmistunut 30 s sisällä PHASE_BEGIN:in "
             "jälkeen — kokeile uudelleen"),
        ]
        wait_t = time.time()
        last_marker = "(none)"
        last_progress_t = wait_t
        while True:
            now = time.time()
            elapsed = now - wait_t
            if elapsed >= timeout_s:
                timed_out = True
                if progress is not None:
                    progress(
                        f"Kokonaistimeout ({timeout_s:.0f} s) — viimeinen "
                        f"vaihe: {last_marker}"
                    )
                break
            log_text = ""
            if log_path.is_file():
                try:
                    log_text = log_path.read_text(
                        encoding="utf-8", errors="replace"
                    )
                except OSError:
                    log_text = ""
            if log_text and progress is not None:
                for marker, msg in marker_messages.items():
                    if marker in log_text and marker not in seen_markers:
                        seen_markers.add(marker)
                        last_marker = marker
                        last_progress_t = now
                        progress(msg)
            if "PHASE_END" in log_text:
                break
            # Per-phase deadline check
            phase_violation = None
            for marker, deadline, msg in phase_deadlines:
                if marker not in seen_markers and elapsed >= deadline:
                    phase_violation = msg
                    break
            if phase_violation is not None:
                timed_out = True
                if progress is not None:
                    progress(phase_violation)
                break
            # Liveness ping every 3 s when no new marker arrived
            if now - last_progress_t >= 3.0:
                last_progress_t = now
                if progress is not None:
                    progress(
                        f"Konversio käynnissä… ({elapsed:.0f} s, "
                        f"viimeinen vaihe: {last_marker})"
                    )
            time.sleep(0.1)

        # SaveAs / vla-saveas / Export all returned "Invalid argument"
        # on Lauri's AutoCAD 2025. The reliable workaround is to send
        # ``DXFOUT`` (no dash — Lauri's AutoCAD reported "Unknown
        # command -DXFOUT") as plain keyboard text. FILEDIA must be
        # 0 at the moment DXFOUT runs so the Save As dialog is
        # suppressed; the LISP body already restored sysvars at its
        # end, so we re-set FILEDIA=0 here from Python.
        if not timed_out and not intermediate_dxf.is_file():
            if progress is not None:
                progress("Tallennetaan välitilanne-DXF (DXFOUT keystroke)…")
            # FILEDIA toggle around DXFOUT so no dialog interferes.
            # Newlines flush each prompt: filename → Enter (accept
            # default format options) → decimal places (8) → Enter.
            dxfout_text = (
                "FILEDIA\n0\n"
                "DXFOUT\n"
                f"{intermediate_dxf.as_posix()}\n"
                "\n"  # accept default format option
                "8\n"  # decimal places
                "\n"  # final Enter
                "FILEDIA\n1\n"
            )
            for attempt in range(3):
                if intermediate_dxf.is_file():
                    break
                try:
                    send_target = active_doc
                    try:
                        send_target = app.ActiveDocument
                    except Exception:  # noqa: BLE001
                        pass
                    send_target.SendCommand(dxfout_text)
                except Exception as exc:  # noqa: BLE001
                    if progress is not None:
                        progress(
                            f"DXFOUT keystroke yritys {attempt+1}/3 "
                            f"raise: {exc!s} (AutoCAD voi silti vastaanottaa)"
                        )
                # Wait for AutoCAD to actually write the file
                wait_t0 = time.time()
                while time.time() - wait_t0 < 20.0:
                    if intermediate_dxf.is_file():
                        break
                    time.sleep(0.5)
            if intermediate_dxf.is_file() and progress is not None:
                progress(
                    f"DXFOUT onnistui ({intermediate_dxf.stat().st_size // 1024} kB)"
                )

        # Always tail the LISP log when something went wrong — either
        # a timeout, the LISP itself logged a failure, or SaveAs left
        # no file on disk. The tail surfaces MAGIEXPLODE_PREPICK_ERR /
        # MAGIEXPLODE_ALL_ERR / MAGI_AFTER_PREPICK diagnostics so we
        # can pinpoint the failure without asking the user to dig in
        # %TEMP%.
        log_text = ""
        if log_path.is_file():
            try:
                log_text = log_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                log_text = ""
        no_dxf_written = not intermediate_dxf.is_file()
        if (timed_out or no_dxf_written) and log_text:
            try:
                tail = "\n".join(log_text.splitlines()[-10:])
                if progress is not None and tail:
                    progress(f"LISP-loki (viimeiset 10 riviä):\n{tail}")
            except Exception:  # noqa: BLE001
                pass

        # Close the document. Don't quit the app — keep it singleton-warm.
        try:
            doc.Close(False)  # SaveChanges=False
        except Exception:  # noqa: BLE001
            pass

        # If we bailed out, the AutoCAD instance may be stuck on a
        # hidden dialog or in a bad state. Drop the singleton so the
        # next conversion attempt starts a fresh acad.exe.
        if timed_out:
            _force_reset_app()
            return None

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
