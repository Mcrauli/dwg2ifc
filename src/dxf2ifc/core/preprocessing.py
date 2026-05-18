"""Headless ACIS body extraction via ``accoreconsole.exe`` + STLOUT.

ezdxf cannot parse the SAB ACIS records emitted by AutoCAD 2025 (token 0x14
unsupported as of ezdxf 1.4.3), so 3DSOLID entities silently disappear from
the IFC unless we triangulate them externally. The previous implementation
launched the full AutoCAD GUI via ``win32com.client.DispatchEx`` and ran
``MESHSMOOTH``; that path was removed because:

* opening a temp DXF in full AutoCAD added it to the user's Recent Files
  list (visible in interactive AutoCAD's Start Tab),
* the AutoCAD window popped on screen for ~14 s per conversion,
* MESHSMOOTH silently no-oped for non-primitive bodies because of the
  "Smooth Mesh — Non-primitive Objects Selected" dialog,
* it pulled in ~30 MB of pywin32 binaries.

This module replaces all of that with a single-shot subprocess call to
``accoreconsole.exe`` — the headless AutoCAD core that ships with every
full AutoCAD install. accoreconsole has no UI, no Start Tab and no recent
files registration; it loads the user's profile read-only and runs the
script we feed it. STLOUT triangulates each 3DSOLID into a per-handle
binary STL file which we parse here in pure Python.
"""

from __future__ import annotations

import os
import shutil
import struct
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

import ezdxf

ACIS_DXF_TYPES: frozenset[str] = frozenset(
    {
        "3DSOLID",
        "SURFACE",
        "PLANESURFACE",
        "EXTRUDEDSURFACE",
        "REVOLVEDSURFACE",
        "SWEPTSURFACE",
        "LOFTEDSURFACE",
        "NURBSURFACE",
        "REGION",
        "BODY",
    }
)


@dataclass(frozen=True)
class AcisMeshData:
    """Triangulated mesh extracted from one ACIS body, indexed by DXF handle."""

    vertices: tuple[tuple[float, float, float], ...]
    faces: tuple[tuple[int, ...], ...]


def dxf_contains_acis_bodies(path: str | Path) -> bool:
    """Return ``True`` if the DXF carries any ACIS-backed entity, anywhere.

    Walks every block definition (including modelspace, which is itself
    a block) so equipment blocks whose 3DSOLID contents live inside the
    block definition — KYL-KONEIKKO assemblies created in MEKA / Solibri
    /  manufacturer libraries are typically built this way — trigger the
    accoreconsole pipeline. The previous modelspace-only scan caused the
    early-exit path to skip every drawing whose only ACIS content was
    sealed inside a block.
    """
    doc = ezdxf.readfile(str(path))
    for block in doc.blocks:
        for entity in block:
            try:
                if entity.dxftype() in ACIS_DXF_TYPES:
                    return True
            except Exception:  # noqa: BLE001 — non-graphical custom entity
                continue
    return False


def _acis_bearing_block_names(doc: object) -> set[str]:
    """Upper-cased names of every block that contains ACIS bodies — either
    directly, or transitively through nested INSERTs.

    Phase 2 of the accoreconsole script EXPLODEs INSERTs to reach the
    3DSOLIDs sealed inside their block definitions. Exploding an INSERT
    whose block has no ACIS content anywhere in its tree is pure waste
    (a command round-trip + an ``ssget "_P"`` that finds nothing) — and
    in explode-heavy drawings the majority of INSERTs are exactly that
    (dynamic-block shelves, 2D symbols). This returns the set of block
    names worth exploding so Phase 2 can skip the rest.

    The transitive walk is essential: equipment is frequently nested
    inside a container block (e.g. on layer "0") that has no direct
    3DSOLIDs of its own — that container must still be exploded to reach
    the equipment. A plain "does this block directly contain ACIS"
    check would drop it.
    """
    # direct[name] = True if the block body has an ACIS entity directly.
    # children[name] = set of block names this block INSERTs.
    direct: dict[str, bool] = {}
    children: dict[str, set[str]] = {}
    for block in doc.blocks:  # type: ignore[attr-defined]
        name = block.name.upper()
        has_acis = False
        kids: set[str] = set()
        for entity in block:
            try:
                etype = entity.dxftype()
            except Exception:  # noqa: BLE001 — non-graphical custom entity
                continue
            if etype in ACIS_DXF_TYPES:
                has_acis = True
            elif etype == "INSERT":
                try:
                    kids.add(entity.dxf.name.upper())
                except Exception:  # noqa: BLE001
                    continue
        direct[name] = has_acis
        children[name] = kids

    # Fixpoint: a block is "worth it" if it has direct ACIS or INSERTs a
    # block that is worth it. Iterate until the set stops growing.
    worth: set[str] = {n for n, d in direct.items() if d}
    changed = True
    while changed:
        changed = False
        for name, kids in children.items():
            if name not in worth and kids & worth:
                worth.add(name)
                changed = True
    return worth


def _worthlist_literal(worth_names: Iterable[str]) -> str:
    """Build the AutoLISP ``worthlist`` literal for the accoreconsole
    SETUP form, or ``"nil"`` when no usable literal can be produced.

    Only ASCII block names go into the literal. Non-ASCII names (the
    Finnish ``Höyrystin`` / ``Säädin`` equipment blocks etc.) are
    deliberately left out — and that exclusion is correct, not merely
    safe:

    * the .scr file is written UTF-8 but accoreconsole reads it in the
      system ANSI codepage, so a non-ASCII name would arrive mangled, and
    * AutoLISP ``strcase`` does not case-fold non-ASCII letters the way
      Python ``str.upper()`` does, so ``(member (strcase bname) worthlist)``
      would never match even if the bytes survived.

    Phase 2 always EXPLODEs non-ASCII-named blocks via its
    ``(not (asciip bname))`` escape, so omitting them here does not skip
    them — it routes them to the unconditional path. ``nil`` (no literal
    at all) means "explode everything": returned when nothing ASCII-safe
    is left, or the literal would exceed the .scr line-buffer budget.
    """
    safe = sorted(
        n
        for n in worth_names
        if n.isascii() and '"' not in n and "\\" not in n
    )
    if not safe:
        return "nil"
    literal = "'(" + " ".join(f'"{n}"' for n in safe) + ")"
    # Keep the SETUP form well under accoreconsole's 2048-char .scr line
    # cap — fall back to "explode all" if the literal is too long.
    if len(literal) > 1200:
        return "nil"
    return literal


# ---------------------------------------------------------------------------
# STLOUT positive-Z-shift correction
#
# AutoCAD's STLOUT command refuses to write geometry below Z=0: whenever a
# solid dips under the datum, STLOUT translates the *whole* body up in +Z so
# the exported STL has min Z == 0 exactly (X and Y are left untouched). A
# koneikko drawn at Z=-5000 therefore comes back tessellated at Z=0, and every
# piece of equipment below the storey datum collapses onto the storey
# elevation. To undo it we need each body's *true* world-space min Z, which we
# read straight from the DXF via ezdxf's ACIS decoder before accoreconsole
# runs.
# ---------------------------------------------------------------------------


def _scan_sab_positions(data: bytes) -> list[tuple[float, float, float]]:
    """Crude vertex cloud from a SAB body: every ``0x14`` position opcode
    followed by three little-endian doubles, filtered to a building-scale
    window so random byte runs that decode as 1e30 / NaN are dropped.

    Fallback for the rare body ezdxf's structured ACIS parser cannot crack.
    """
    out: list[tuple[float, float, float]] = []
    if len(data) < 25:
        return out
    end = len(data) - 25
    for i in range(end):
        if data[i] != 0x14:
            continue
        try:
            x, y, z = struct.unpack_from("<ddd", data, i + 1)
        except struct.error:
            continue
        if -1e9 < x < 1e9 and -1e9 < y < 1e9 and -1e9 < z < 1e9:
            out.append((x, y, z))
    return out


def _acis_body_vertices(acis_data: object) -> list[tuple[float, float, float]]:
    """Decode an ACIS body's vertices (SAT text or SAB binary).

    Uses ezdxf's structured ACIS parser (exact tessellated vertices); if
    that fails or yields nothing, falls back to the raw SAB position-token
    byte scan. Returns an empty list when neither path produces coordinates.
    """
    if not acis_data:
        return []
    try:
        from ezdxf.acis import api as _acis_api

        verts: list[tuple[float, float, float]] = []
        for body in _acis_api.load(acis_data):
            for mesh in _acis_api.mesh_from_body(body):
                verts.extend(
                    (float(v[0]), float(v[1]), float(v[2])) for v in mesh.vertices
                )
        if verts:
            return verts
    except Exception:  # noqa: BLE001 — ezdxf ACIS parser is best-effort
        pass
    if isinstance(acis_data, (bytes, bytearray)):
        return _scan_sab_positions(bytes(acis_data))
    return []


def _insert_acis_world_vertices(
    insert: object, _depth: int = 0
) -> list[tuple[float, float, float]]:
    """Every ACIS-body vertex reachable from an INSERT, transformed into
    world space. Recurses into nested INSERTs (depth-capped) so compound
    equipment assemblies — a koneikko block whose definition references a
    compressor + condenser sub-block — are covered in full."""
    if _depth > 16:
        return []
    try:
        matrix = insert.matrix44()  # type: ignore[attr-defined]
        block = insert.doc.blocks.get(insert.dxf.name)  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        return []
    if block is None:
        return []
    local: list[tuple[float, float, float]] = []
    for ent in block:
        try:
            etype = ent.dxftype()
        except Exception:  # noqa: BLE001 — non-graphical custom entity
            continue
        if etype in ACIS_DXF_TYPES:
            local.extend(_acis_body_vertices(getattr(ent, "acis_data", None)))
        elif etype == "INSERT":
            local.extend(_insert_acis_world_vertices(ent, _depth + 1))
    if not local:
        return []
    return [(v.x, v.y, v.z) for v in matrix.transform_vertices(local)]


def _world_min_z_by_handle(doc: object) -> dict[str, float]:
    """Map every modelspace 3DSOLID and INSERT handle to the minimum
    world-space Z of its ACIS geometry — the datum STLOUT's positive-Z
    shift must be undone against. Best-effort: handles whose geometry
    cannot be decoded are simply absent (no correction applied)."""
    result: dict[str, float] = {}
    try:
        msp = doc.modelspace()  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        return result
    for ent in msp:
        try:
            etype = ent.dxftype()
            handle = str(ent.dxf.handle).upper()
        except Exception:  # noqa: BLE001
            continue
        if etype in ACIS_DXF_TYPES:
            verts = _acis_body_vertices(getattr(ent, "acis_data", None))
        elif etype == "INSERT":
            verts = _insert_acis_world_vertices(ent)
        else:
            continue
        if verts:
            result[handle] = min(v[2] for v in verts)
    return result


def _undo_stlout_z_shift(
    handle: str, mesh: AcisMeshData, world_min_z: dict[str, float]
) -> AcisMeshData:
    """Translate a parsed STL mesh back onto its true world Z.

    STLOUT's signature is unmistakable: an STL whose min Z sits at ~0 while
    the source body's true world min Z is genuinely negative. Only that
    exact case is corrected — solids STLOUT left alone (already at/above the
    datum) keep their STL coordinates untouched, so positive-Z geometry
    carries zero regression risk.
    """
    true_min = world_min_z.get(handle)
    if true_min is None or not mesh.vertices:
        return mesh
    stl_min = min(v[2] for v in mesh.vertices)
    if abs(stl_min) >= 1.0 or true_min >= -1.0:
        return mesh
    dz = true_min - stl_min
    return AcisMeshData(
        tuple((x, y, z + dz) for (x, y, z) in mesh.vertices),
        mesh.faces,
    )


def find_accoreconsole() -> Path | None:
    """Locate ``accoreconsole.exe`` under ``%ProgramFiles%\\Autodesk``.

    Returns the highest-version install (sorted by directory name) or
    ``None`` if no AutoCAD install carries the headless core. The shim
    used to fall back to full AutoCAD via COM has been retired — when
    accoreconsole is missing, ACIS bodies are simply skipped.
    """
    if sys.platform != "win32":
        return None
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    base = Path(program_files) / "Autodesk"
    if not base.is_dir():
        return None
    candidates = sorted(base.glob("AutoCAD */accoreconsole.exe"), reverse=True)
    return candidates[0] if candidates else None


# ---------------------------------------------------------------------------
# STL parser (pure Python, supports binary + ASCII)
# ---------------------------------------------------------------------------


def _parse_stl(path: Path) -> AcisMeshData:
    raw = path.read_bytes()
    # ASCII STL files start with "solid " in plain text. Binary headers may
    # incidentally start the same way too (the spec reserves the first 80
    # bytes as a free-form header), so look for the "facet" keyword in the
    # first 300 bytes to disambiguate. AutoCAD STLOUT writes binary by
    # default when the script answers "Y" to the binary prompt.
    head = raw[:300]
    if head.startswith(b"solid ") and b"facet" in head:
        return _parse_stl_ascii(raw.decode("ascii", errors="ignore"))
    return _parse_stl_binary(raw)


def _parse_stl_binary(raw: bytes) -> AcisMeshData:
    if len(raw) < 84:
        return AcisMeshData((), ())
    n_triangles = struct.unpack_from("<I", raw, 80)[0]
    expected = 84 + 50 * n_triangles
    if len(raw) < expected:
        return AcisMeshData((), ())
    vertex_to_idx: dict[tuple[float, float, float], int] = {}
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    offset = 84
    for _ in range(n_triangles):
        # Skip the 12-byte normal — we recompute from face winding in the
        # IFC writer if needed. Each triangle: normal[3] + v0[3] + v1[3] +
        # v2[3] + uint16 attribute count = 50 bytes.
        offset += 12
        face: list[int] = []
        for _ in range(3):
            v = struct.unpack_from("<3f", raw, offset)
            offset += 12
            key = (float(v[0]), float(v[1]), float(v[2]))
            idx = vertex_to_idx.get(key)
            if idx is None:
                idx = len(vertices)
                vertex_to_idx[key] = idx
                vertices.append(key)
            face.append(idx)
        offset += 2  # attribute byte count
        if face[0] != face[1] and face[1] != face[2] and face[0] != face[2]:
            faces.append(tuple(face))
    return AcisMeshData(tuple(vertices), tuple(faces))


def _parse_stl_ascii(text: str) -> AcisMeshData:
    vertex_to_idx: dict[tuple[float, float, float], int] = {}
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    current: list[int] = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("vertex "):
            parts = s.split()
            if len(parts) >= 4:
                key = (float(parts[1]), float(parts[2]), float(parts[3]))
                idx = vertex_to_idx.get(key)
                if idx is None:
                    idx = len(vertices)
                    vertex_to_idx[key] = idx
                    vertices.append(key)
                current.append(idx)
        elif s.startswith("endloop"):
            if (
                len(current) >= 3
                and len(set(current)) == len(current)
            ):
                faces.append(tuple(current))
            current = []
    return AcisMeshData(tuple(vertices), tuple(faces))


# ---------------------------------------------------------------------------
# accoreconsole driver
# ---------------------------------------------------------------------------


# The LISP body executed inside accoreconsole, split into four
# top-level forms so each .scr line stays under accoreconsole's hard
# 2048-char line buffer (verified by bisection: 2048 → OK, 2092 →
# parser hangs in "((_>" multi-paren prompt forever). When the body
# was a single (progn ...) form it formatted to ~2065 chars after
# tempdir paths substituted in, silently truncating mid-Phase-1 and
# leaving zero STLs written. Each form below is independently
# balanced; setq globals (logf, solid_out, insert_out) persist across
# forms because they share one accoreconsole LISP environment.
#
# Two extraction phases:
#   Phase 1 — raw ACIS bodies on the matching layer get STLOUTed directly,
#     filename = ``{handle}.stl``.
#   Phase 2 — INSERT block references on the matching layer are EXPLODEd,
#     each resulting 3DSOLID child gets STLOUTed under the SOURCE INSERT's
#     handle, filename = ``{insert_handle}_{counter}.stl``. KLHYLLY-LEVY/
#     KLHYLLY-TIKAS blocks store geometry as LWPOLYLINE+thickness, which
#     CONVTOSOLID promotes to 3DSOLID before STLOUT. Python aggregates
#     ``*_0.stl, *_1.stl, …`` per handle into one :class:`AcisMeshData`.
#     Children inherit the INSERT's world placement (EXPLODE applies the
#     block transform), so the meshes are already in world coordinates.
#
# Termination strategy: the .scr file ends right after the cleanup form
# (no explicit ``_QUIT``). When accoreconsole hits EOF on the script it
# exits cleanly without prompting for save — STLOUT writes external
# files only, the in-memory drawing is never persisted, and the EXPLODEs
# we run only mutate the throwaway in-memory copy.
#
# FACETRES 0.1 — the lowest non-trivial value. Curved surfaces
# (evaporator fans, hoses) tessellate coarsely; planar faces (cable
# carrier panels, ladder rails) are unaffected. Higher values explode
# triangle count: FACETRES 0.5 → 50k tri/evaporator; FACETRES 10 →
# 800k tri/body (~12 GB IFC). 0.1 is the sweet spot.
_LISP_SETUP = (
    '(progn '
    '(setvar "FILEDIA" 0) '
    '(setvar "CMDDIA" 0) '
    '(setvar "FACETRES" 0.1) '
    # TILEMODE 1 forces the Model tab active. accoreconsole opens a DWG
    # on whatever tab was active when it was saved — if that is a
    # paper-space layout, every ``ssget "_X"`` hit on a modelspace
    # 3DSOLID comes back "1 was not in current space" and STLOUT
    # rejects it. Switching to modelspace up front makes the bodies
    # selectable.
    '(setvar "TILEMODE" 1) '
    # REPORTERROR=0 + SENDREPORTINFO=0 silence AutoCAD's Customer Error
    # Report popup that otherwise appears on every accoreconsole-side
    # crash (e.g. STLOUT failing on a malformed 3DSOLID body). Our caller
    # already handles a non-zero exit code from the subprocess; the popup
    # only adds noise.
    '(setvar "REPORTERROR" 0) '
    '(if (= (type (getvar "SENDREPORTINFO")) \'INT) (setvar "SENDREPORTINFO" 0)) '
    '(setq solid_out "{solid_out}") '
    '(setq insert_out "{insert_out}") '
    # worthlist — upper-cased names of blocks that contain ACIS bodies,
    # directly or via nested INSERTs. PHASE2 only EXPLODEs INSERTs whose
    # block is on this list; everything else (dynamic-block shelves, 2D
    # symbols) is skipped — ezdxf reads those directly, no accoreconsole
    # round-trip needed. ``nil`` means "explode everything" (fallback
    # when the Python-side block scan was empty or hit unsafe names).
    "(setq worthlist {worthlist}) "
    '(setq logf (open (strcat "{log_out}" "extract.log") "w")) '
    '(defun tryx (tag fn / err) (setq err (vl-catch-all-apply fn)) (if (vl-catch-all-error-p err) (write-line (strcat tag ":" (vl-catch-all-error-message err)) logf))) '
    # flushcmd cancels any half-open command (e.g. STLOUT stuck at its
    # "Select solids or watertight meshes" prompt after rejecting a
    # non-watertight 3DSOLID). Without this the next loop iteration's
    # "_.STLOUT" token is consumed as a selection for the still-pending
    # command, the command stack corrupts, and accoreconsole dies with
    # STATUS_STACK_BUFFER_OVERRUN (0xC0000409). (command) with no args
    # is the AutoLISP equivalent of pressing ESC.
    '(defun fc () (repeat 8 (if (> (getvar "CMDACTIVE") 0) (command)))) '
    # acis? — is this exploded entity an ACIS-backed body STLOUT can
    # triangulate? Defined here so PHASE2 can call (acis? etype) instead
    # of inlining the 10-way (or (eq etype ...)) — keeps PHASE2 under the
    # 2048-char .scr line cap.
    '(defun acis? (et) (member et \'("3DSOLID" "SURFACE" "REGION" "BODY" "PLANESURFACE" "EXTRUDEDSURFACE" "REVOLVEDSURFACE" "SWEPTSURFACE" "LOFTEDSURFACE" "NURBSURFACE"))) '
    # asciip — T when every character of S is plain 7-bit ASCII. PHASE2
    # always EXPLODEs blocks whose name is NOT ascii (Finnish Höyrystin /
    # Säädin equipment blocks): such names cannot be carried in the UTF-8
    # .scr ``worthlist`` literal accoreconsole reads as ANSI, and AutoLISP
    # ``strcase`` would not case-fold them to match anyway — so they are
    # excluded from the literal on the Python side and caught here
    # instead. Any non-ASCII byte is >= 128 in every codepage.
    '(defun asciip (s / i n) (setq i 1 n (strlen s)) (while (and (<= i n) (< (ascii (substr s i 1)) 128)) (setq i (1+ i))) (> i n)))'
)

# Phase 1: every raw ACIS body in modelspace.
_LISP_PHASE1 = (
    '(progn '
    '(setq ss (ssget "_X" \'((0 . "3DSOLID,SURFACE,REGION,BODY,PLANESURFACE,EXTRUDEDSURFACE,REVOLVEDSURFACE,SWEPTSURFACE,LOFTEDSURFACE,NURBSURFACE")))) '
    '(write-line (strcat "phase1_solids=" (if ss (itoa (sslength ss)) "0")) logf) '
    '(if ss '
    '(progn '
    '(setq i 0 n (sslength ss)) '
    '(while (< i n) '
    '(setq obj (ssname ss i)) '
    '(setq h (cdr (assoc 5 (entget obj)))) '
    '(write-line (strcat "phase1_handle=" h) logf) '
    '(tryx (strcat "p1_stl_err=" h) (function (lambda () (command "_.STLOUT" obj "" "Y" (strcat solid_out h ".stl"))))) '
    '(fc) '
    '(setq i (1+ i))))))'
)

# Phase 2: explode INSERT block references on the layer filter, walk
# every nested INSERT recursively (depth-cap 1000 iterations), and STLOUT
# every ACIS body the explosion uncovers. The previous version filtered
# by hard-coded block name (*yrystin*,*ahdutin*,*pressori*,KLHYLLY-*,
# VPUTKI-*) which silently dropped any new equipment block — KONEIKKO,
# CHILLER, KOMPLAUH, KAASUNJAA, NESTEJAAHD, VARAAJA, PAKASTEKAAPPI etc.
# Using the layer filter (same one Phase 1 uses) means every KYL-*
# equipment block — including ones we have no knowledge of — gets
# exploded and triangulated.
#
# POSITIO annotation bubbles share KYL-* layers in some drawings (the
# autocad-lisp-ohjeet/files/positio.lsp tool puts them on each
# device's own layer). Exploding those would triple conversion time
# and bloat the IFC with letter-shaped meshes, so we skip blocks whose
# name matches *POSITIO* before calling EXPLODE.
#
# Recursion handles compound blocks where the equipment is drawn as
# nested sub-blocks (e.g. a koneikko block whose definition has child
# INSERTs for compressor + condenser sub-assemblies). Without the
# recursion the first EXPLODE would surface only the sub-INSERT
# wrappers, never reaching the 3DSOLID children inside.
#
# ACIS types caught: 3DSOLID + SURFACE + REGION + BODY + *SURFACE
# (PLANESURFACE / EXTRUDEDSURFACE / REVOLVEDSURFACE / SWEPTSURFACE /
# LOFTEDSURFACE / NURBSURFACE). KLHYLLY-LEVY / VPUTKI-* still rely on
# CONVTOSOLID promoting LWPOLYLINE+thickness to 3DSOLID first.
#
# PERF: every ACIS body uncovered by the explode walk is collected into
# ONE selection set ``bodies`` and STLOUT'd in a SINGLE call per INSERT —
# ``insert_out/<ih>.stl``. The previous version issued one STLOUT (plus a
# command round-trip + file write + flushcmd) per nested 3DSOLID; a
# koneikko block with 65 solids meant 65 calls. STLOUT happily accepts a
# multi-solid selection and concatenates their triangles into one STL,
# which is exactly the per-INSERT merged mesh the Python side wants
# anyway — so one call replaces dozens.
_LISP_PHASE2 = (
    '(progn '
    '(setq inserts (ssget "_X" \'((0 . "INSERT")))) '
    '(write-line (strcat "phase2_inserts=" (if inserts (itoa (sslength inserts)) "0")) logf) '
    '(if inserts '
    '(progn '
    '(setq k 0 m (sslength inserts)) '
    '(while (< k m) '
    '(setq ins (ssname inserts k)) '
    '(setq insel (entget ins)) '
    '(setq bname (cdr (assoc 2 insel))) '
    '(if (and bname (not (wcmatch (strcase bname) "{skip_blocks}")) (or (null worthlist) (member (strcase bname) worthlist) (not (asciip bname)))) '
    '(progn '
    '(setq ih (cdr (assoc 5 insel))) '
    '(write-line (strcat "phase2_handle=" ih "/block=" bname) logf) '
    '(setq bodies (ssadd) toconv (ssadd) iter_cap 1000) '
    '(command "_.EXPLODE" ins) '
    '(fc) '
    '(setq queue (list (ssget "_P"))) '
    '(while (and queue (> iter_cap 0)) '
    '(setq curss (car queue)) '
    '(setq queue (cdr queue)) '
    '(setq iter_cap (1- iter_cap)) '
    '(if curss '
    '(progn '
    '(setq j 0 nn (sslength curss)) '
    '(while (< j nn) '
    '(setq ent (ssname curss j)) '
    '(setq el (entget ent)) '
    '(setq etype (cdr (assoc 0 el))) '
    '(setq ethick (cdr (assoc 39 el))) '
    '(cond '
    '((acis? etype) '
    '(setq bodies (ssadd ent bodies))) '
    '((eq etype "INSERT") '
    '(setq sbname (cdr (assoc 2 el))) '
    '(if (and sbname (not (wcmatch (strcase sbname) "{skip_blocks}")) (or (null worthlist) (member (strcase sbname) worthlist) (not (asciip sbname)))) '
    '(progn '
    '(command "_.EXPLODE" ent) '
    '(fc) '
    '(setq subss (ssget "_P")) '
    '(if subss (setq queue (cons subss queue)))))) '
    '((and (eq etype "LWPOLYLINE") ethick (> ethick 0.0)) '
    '(setq toconv (ssadd ent toconv)))) '
    '(setq j (1+ j)))))) '
    '(if (> (sslength toconv) 0) '
    '(progn '
    '(command "_.CONVTOSOLID" toconv "") '
    '(fc) '
    '(setq postents (ssget "_P")) '
    '(if postents '
    '(progn '
    '(setq j 0 nn2 (sslength postents)) '
    '(while (< j nn2) '
    '(setq ent (ssname postents j)) '
    '(setq el (entget ent)) '
    '(if (eq (cdr (assoc 0 el)) "3DSOLID") (setq bodies (ssadd ent bodies))) '
    '(setq j (1+ j))))))) '
    '(if (> (sslength bodies) 0) '
    '(tryx (strcat "p2_stl_err=" ih) (function (lambda () (command "_.STLOUT" bodies "" "Y" (strcat insert_out ih ".stl")))))) '
    '(fc))) '
    '(setq k (1+ k))))))'
)

_LISP_CLEANUP = (
    '(progn '
    '(write-line "done" logf) '
    '(close logf) '
    '(princ))'
)


def extract_acis_meshes(
    dxf_path: str | Path,
    *,
    timeout_s: float = 180.0,
    progress: Callable[[str], None] | None = None,
    skip_magicad: bool = False,
) -> dict[str, AcisMeshData]:
    """Triangulate every ACIS body in ``dxf_path`` via accoreconsole.

    Returns a ``{handle.upper(): AcisMeshData}`` mapping. Returns an empty
    dict if accoreconsole is not installed, the subprocess times out or
    fails, or the DXF contains no ACIS bodies — never raises. Callers
    should treat absence as "no mesh available, skip this body".

    Every ACIS body on every layer is extracted. Layer filtering was
    tried (derive an ssget filter from the active profile) but reverted:
    equipment INSERTs frequently nest inside container blocks placed on
    layer "0", so any top-level layer filter on the Phase-2 INSERT select
    silently dropped whole equipment assemblies. The mapper drops
    unmapped geometry downstream anyway.

    ``skip_magicad`` (default False): when True, the Phase-2 INSERT-
    explode loop additionally skips any block whose name matches
    ``MAGI*`` / ``*MAGICAD*`` / ``MAG_*``. Set to True by the
    orchestrator whenever the caller supplied ``--magicad-ifc`` so
    accoreconsole does not attempt to ``_.EXPLODE`` MagiCAD blocks
    that the merged-in IFC will replace anyway. On colleague machines
    with FULL MagiCAD ARX loaded, an ``_.EXPLODE`` on a MagiCAD
    PathwayDevice/PipeSegment may crash inside the MagiCAD ARX —
    skipping them avoids the AutoCAD CER popup.
    """
    input_path = Path(dxf_path).resolve()
    if not input_path.is_file():
        return {}

    if not dxf_contains_acis_bodies(input_path):
        return {}

    # Compute which blocks are worth EXPLODEing in Phase 2 (contain ACIS
    # bodies directly or transitively). Phase 2 skips the rest, saving an
    # EXPLODE round-trip per dynamic-block shelf / 2D symbol. Non-ASCII /
    # unsafe / over-long names are dropped from the literal by
    # ``_worthlist_literal``; Phase 2 still EXPLODEs non-ASCII-named
    # blocks via its ``(not (asciip ...))`` escape. ``nil`` ⇒ explode
    # everything (the safe-but-slow fallback).
    worthlist_lisp = "nil"
    handle_world_min_z: dict[str, float] = {}
    try:
        _doc = ezdxf.readfile(str(input_path))
        worthlist_lisp = _worthlist_literal(_acis_bearing_block_names(_doc))
        # Capture each body's true world min Z so the STLOUT positive-Z
        # shift can be undone after the meshes come back (see
        # ``_undo_stlout_z_shift``).
        handle_world_min_z = _world_min_z_by_handle(_doc)
    except Exception:  # noqa: BLE001 — never block extraction on the scan
        worthlist_lisp = "nil"

    accoreconsole = find_accoreconsole()
    if accoreconsole is None:
        if progress is not None:
            progress("accoreconsole.exe not found — ACIS bodies will be skipped")
        return {}

    workdir = Path(tempfile.mkdtemp(prefix="dxf2ifc_acis_"))
    preserve_workdir = False
    try:
        # Phase 1 writes raw-solid STLs into out/solid/, Phase 2 writes
        # INSERT-explode children into out/insert/. The split lets the
        # Python aggregator decide which handles get full-mesh treatment
        # (raw bodies — cable carriers, ladder racks) and which collapse
        # to a bbox cube (INSERT block contents — evaporators, fans —
        # whose internal curves would otherwise blow up to millions of
        # triangles at any meaningful FACETRES).
        out_dir = workdir / "stl"
        solid_dir = out_dir / "solid"
        insert_dir = out_dir / "insert"
        solid_dir.mkdir(parents=True)
        insert_dir.mkdir(parents=True)
        solid_posix = solid_dir.as_posix() + "/"
        insert_posix = insert_dir.as_posix() + "/"
        out_posix = out_dir.as_posix() + "/"  # for extract.log only

        # accoreconsole's .scr line buffer is hard-capped at 2048 chars
        # per Enter-terminated input line (verified by bisection: 2048 →
        # OK, 2092 → parser hangs in "((_>" multi-paren prompt forever).
        # The LISP body grew past 2048 once tempdir paths substituted in.
        # Solution: write each phase as its own line. setq globals
        # (``logf``, ``solid_out``, ``insert_out``) persist across forms
        # because they share one accoreconsole LISP environment.
        # ``(load …)`` from a single big .lsp file is NOT an option:
        # accoreconsole's SECURELOAD policy auto-cancels LSP loads from
        # %TEMP% with "; error: File load canceled".
        # Phase 2 ``wcmatch`` skip pattern. POSITIO blocks are always
        # skipped (their explode pollutes per-handle STL counter with
        # letter-shaped meshes). MagiCAD blocks are also always skipped:
        # ``_.EXPLODE`` on a MagiCAD entity crashes accoreconsole on
        # machines with FULL MagiCAD ARX loaded (AutoCAD CER popup), and
        # ``.arx`` modules don't load in accoreconsole anyway — so the
        # tessellation would produce nothing useful even when it didn't
        # crash. The ``skip_magicad`` kwarg is kept for the dxf_reader
        # side-channel filter; this preprocessing step ignores it.
        skip_blocks = "*POSITIO*,MAGI*,*MAGICAD*,MAG_*"

        scr_path = workdir / "extract.scr"
        forms = [
            _LISP_SETUP.format(
                solid_out=solid_posix,
                insert_out=insert_posix,
                log_out=out_posix,
                worthlist=worthlist_lisp,
            ),
            _LISP_PHASE1,
            _LISP_PHASE2.format(skip_blocks=skip_blocks),
            _LISP_CLEANUP,
        ]
        # Write in binary mode to keep our explicit ``\r\n`` separators
        # exact. ``write_text`` opens in text mode on Windows, which
        # translates ``\n`` to ``\r\n`` again and turns our ``\r\n`` into
        # ``\r\r\n`` — accoreconsole has been observed to lose forms when
        # the file contains those double-CRs.
        scr_path.write_bytes(("\r\n".join(forms) + "\r\n").encode("utf-8"))

        if progress is not None:
            progress("Triangulating ACIS bodies via accoreconsole…")

        creationflags = 0
        if sys.platform == "win32":
            # DETACHED_PROCESS = 0x00000008 — give accoreconsole its own
            # standalone process (no inherited console). When dxf2ifc is
            # launched as a windowed PyInstaller exe (``console=False``)
            # it has no console of its own; passing CREATE_NO_WINDOW from
            # such a parent makes accoreconsole's console host hang
            # waiting for a parent console that never comes. DETACHED is
            # the safer flag — accoreconsole still runs hidden because it
            # has no UI of its own, just no inherited console plumbing.
            creationflags = 0x00000008

        try:
            # Discard accoreconsole's chatty stdout/stderr to file, not to
            # PIPE — capture_output=True deadlocks once the pipe buffer
            # fills (it emits ~10 KB per body during STLOUT). The actual
            # results live in ``out_dir/*.stl``; the log is only useful
            # for debugging and is preserved as ``extract.log`` by the
            # LISP body itself.
            log_path = workdir / "accoreconsole.log"
            with log_path.open("w", encoding="utf-8") as log_fh:
                completed = subprocess.run(
                    [
                        str(accoreconsole),
                        "/i",
                        str(input_path),
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
            # accoreconsole's exit code reflects whether the process exited
            # cleanly OR whether AutoCAD crashed mid-script. A crash inside
            # the LISP (e.g. MagiCAD ARX failing _.EXPLODE on a MagiCAD
            # entity) shows up as a non-zero rc + an AutoCAD CER popup.
            # Surface the workdir to the user so they can attach the logs
            # for diagnosis without us having to ship a debug build.
            if completed.returncode != 0:
                # Keep the workdir on disk so the extract.log per-body
                # trace + extract.scr + accoreconsole.log survive for
                # diagnosis. The ``finally`` below only cleans up on a
                # clean (rc == 0) run.
                preserve_workdir = True
                if progress is not None:
                    progress(
                        f"accoreconsole exited with code {completed.returncode}; "
                        f"diagnostics preserved in {workdir}"
                    )
        except subprocess.TimeoutExpired:
            if progress is not None:
                progress(
                    f"accoreconsole timed out after {timeout_s:.0f} s — "
                    f"ACIS bodies will be skipped (diagnostics in {workdir})"
                )
            return {}
        except OSError as exc:
            if progress is not None:
                progress(
                    f"accoreconsole failed: {exc} — ACIS bodies will be "
                    f"skipped (diagnostics in {workdir})"
                )
            return {}

        meshes: dict[str, AcisMeshData] = {}

        # Phase 1 — raw 3DSOLIDs: keep full mesh fidelity
        for stl_file in solid_dir.glob("*.stl"):
            handle = stl_file.stem.upper()
            try:
                mesh = _parse_stl(stl_file)
            except Exception:  # noqa: BLE001 — corrupt STL must not crash
                continue
            if mesh.vertices and mesh.faces:
                meshes[handle] = _undo_stlout_z_shift(
                    handle, mesh, handle_world_min_z
                )

        # Phase 2 — INSERT block contents: PHASE2 STLOUTs the entire
        # exploded body selection per INSERT into ONE ``<ih>.stl``, so
        # each file is already the complete per-INSERT mesh (STLOUT
        # concatenates every selected solid's triangles). No cross-file
        # merge needed — just parse each file like Phase 1. ``_parse_stl``
        # already deduplicates the vertex pool.
        for stl_file in insert_dir.glob("*.stl"):
            handle = stl_file.stem.upper()
            try:
                mesh = _parse_stl(stl_file)
            except Exception:  # noqa: BLE001 — corrupt STL must not crash
                continue
            if mesh.vertices and mesh.faces:
                meshes[handle] = _undo_stlout_z_shift(
                    handle, mesh, handle_world_min_z
                )

        # Inject MESH entities embedded in INSERT blocks (e.g. mounting
        # brackets in evaporator blocks). STLOUT can't safely write these
        # — AutoCAD applies subdivision smoothing during STL export and
        # blows triangle count by ~1000× — so we read them via ezdxf,
        # transform by the INSERT's placement, and merge.
        try:
            _inject_block_meshes(input_path, meshes)
        except Exception as exc:  # noqa: BLE001 — never crash convert
            if progress is not None:
                progress(f"block-MESH injection skipped: {exc}")

        if progress is not None:
            progress(f"ACIS extraction produced {len(meshes)} meshes")
        return meshes
    finally:
        if not preserve_workdir:
            shutil.rmtree(workdir, ignore_errors=True)


def _inject_block_meshes(
    dxf_path: Path,
    meshes: dict[str, AcisMeshData],
) -> None:
    """Append MESH entities found inside INSERT blocks onto the per-handle
    AcisMeshData bundles in ``meshes``. Operates in-place.

    For each INSERT in modelspace whose handle is already a key in
    ``meshes`` (i.e. accoreconsole produced 3DSOLID STLs for it), find
    every MESH entity in the INSERT's block definition, transform the
    MESH vertices through the INSERT's world placement (translation +
    rotation around Z + per-axis scale), and append to the bundle's
    vertex/face pool with re-indexed faces.
    """
    import math as _math

    from ezdxf.render import MeshBuilder

    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()

    for entity in msp:
        if entity.dxftype() != "INSERT":
            continue
        handle = str(entity.dxf.handle).upper()
        if handle not in meshes:
            continue
        block_name = entity.dxf.name
        if block_name not in doc.blocks:
            continue

        ix = float(entity.dxf.insert.x)
        iy = float(entity.dxf.insert.y)
        iz = float(entity.dxf.insert.z)
        sx = float(entity.dxf.xscale or 1.0)
        sy = float(entity.dxf.yscale or 1.0)
        sz = float(entity.dxf.zscale or 1.0)
        rot = _math.radians(float(entity.dxf.rotation or 0.0))
        cos_r, sin_r = _math.cos(rot), _math.sin(rot)

        existing = meshes[handle]
        merged_v: list[tuple[float, float, float]] = list(existing.vertices)
        merged_f: list[tuple[int, ...]] = list(existing.faces)
        vertex_to_idx: dict[tuple[float, float, float], int] = {
            v: i for i, v in enumerate(merged_v)
        }

        for member in doc.blocks[block_name]:
            if member.dxftype() != "MESH":
                continue
            mb = MeshBuilder.from_mesh(member)
            local_to_merged: list[int] = []
            for v in mb.vertices:
                # Block-local vertex → world: scale, then rotate Z, then translate.
                lx = float(v.x) * sx
                ly = float(v.y) * sy
                lz = float(v.z) * sz
                wx = ix + (lx * cos_r - ly * sin_r)
                wy = iy + (lx * sin_r + ly * cos_r)
                wz = iz + lz
                key = (wx, wy, wz)
                idx = vertex_to_idx.get(key)
                if idx is None:
                    idx = len(merged_v)
                    vertex_to_idx[key] = idx
                    merged_v.append(key)
                local_to_merged.append(idx)
            for face in mb.faces:
                if len(face) < 3:
                    continue
                merged_f.append(tuple(local_to_merged[i] for i in face))

        if len(merged_v) != len(existing.vertices) or len(merged_f) != len(existing.faces):
            meshes[handle] = AcisMeshData(tuple(merged_v), tuple(merged_f))


# ---------------------------------------------------------------------------
# Backwards-compat shims
# ---------------------------------------------------------------------------


def maybe_preprocess(
    input_dxf: str | Path,
    *,
    timeout_s: float = 180.0,
    progress: Callable[[str], None] | None = None,
) -> Path:
    """No-op compatibility shim.

    The new pipeline extracts ACIS meshes via :func:`extract_acis_meshes`
    invoked from :func:`dxf2ifc.core.ifc_writer.convert_dxf` directly,
    keeping the DXF and the mesh side-channel as separate inputs to
    :func:`dxf2ifc.core.dxf_reader.read_dxf`. This shim exists so older
    callers (and tests) that imported ``maybe_preprocess`` keep working;
    they get the original input path back, which is what they ultimately
    feed to ezdxf.
    """
    del timeout_s, progress  # unused
    return Path(input_dxf)


def find_accoreconsole_legacy(_: object | None = None) -> Path | None:
    """Deprecated wrapper kept for legacy tests; prefer :func:`find_accoreconsole`."""
    return find_accoreconsole()
