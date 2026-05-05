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
from typing import Callable

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
    """Return ``True`` if the DXF model space contains any ACIS-backed entity."""
    doc = ezdxf.readfile(str(path))
    msp = doc.modelspace()
    return any(entity.dxftype() in ACIS_DXF_TYPES for entity in msp)


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


# The LISP body executed inside accoreconsole. Single-line so the .scr
# parser sees it as one Enter-terminated command. Placeholders ``{out}``
# and ``{filter}`` are substituted before write.
#
# Two extraction phases:
#   Phase 1 — raw ACIS bodies on the matching layer get STLOUTed directly,
#     filename = ``{handle}_0.stl``.
#   Phase 2 — INSERT block references on the matching layer are EXPLODEd,
#     each resulting 3DSOLID / MESH child entity gets STLOUTed under the
#     SOURCE INSERT's handle, filename = ``{insert_handle}_{counter}.stl``.
#     Python then aggregates ``*_0.stl, *_1.stl, …`` per handle into one
#     :class:`AcisMeshData`. Children inherit the INSERT's world placement
#     (EXPLODE applies the block transform), so the meshes are already in
#     world coordinates and need no additional reposition.
#
# Termination strategy: the .scr file ends right after this single LISP
# form (no explicit ``_QUIT``). When accoreconsole hits EOF on the
# script it exits cleanly without prompting for save — STLOUT writes
# external files only, the in-memory drawing is never persisted, and
# the EXPLODEs we run only mutate the throwaway in-memory copy.
_LISP_BODY = (
    '(progn '
    '(setvar "FILEDIA" 0) '
    '(setvar "CMDDIA" 0) '
    # FACETRES 0.1 — the lowest non-trivial value. Curved surfaces
    # (evaporator fans, hoses) tessellate VERY coarsely (chunky
    # silhouette) but planar faces (cable carrier panels, ladder rails)
    # are unaffected — they always emit minimum-triangle representations.
    # Higher values explode triangle count: at FACETRES 0.5 a single
    # evaporator weighed in at ~50k tri (15 × that = 750k tri = 600 MB
    # IFC); at FACETRES 10 it was ~800k tri / body (~12 GB IFC).
    # 0.1 is the sweet spot for "recognisable equipment shape, no GB
    # files".
    '(setvar "FACETRES" 0.1) '
    '(setq solid_out "{solid_out}") '
    '(setq insert_out "{insert_out}") '
    '(setq logf (open (strcat "{log_out}" "extract.log") "w")) '
    # ----- Phase 1: raw ACIS bodies on the layer filter ---------------
    '(setq ss (ssget "_X" \'((0 . "3DSOLID,SURFACE,REGION,BODY,PLANESURFACE,EXTRUDEDSURFACE,REVOLVEDSURFACE,SWEPTSURFACE,LOFTEDSURFACE,NURBSURFACE") (8 . "{filter}")))) '
    '(write-line (strcat "phase1_solids=" (if ss (itoa (sslength ss)) "0")) logf) '
    '(if ss '
    '(progn '
    '(setq i 0 n (sslength ss)) '
    '(while (< i n) '
    '(setq obj (ssname ss i)) '
    '(setq h (cdr (assoc 5 (entget obj)))) '
    '(command "_.STLOUT" obj "" "Y" (strcat solid_out h ".stl")) '
    '(setq i (1+ i))))) '
    # ----- Phase 2: explode equipment INSERTs and STLOUT children -----
    # Block-name filter restricts to:
    #  - refrigeration EQUIPMENT blocks (*yrystin* / *ahdutin* / *pressori*)
    #  - parametric cable carrier shelves authored in autocad-lisp-ohjeet
    #    (KLHYLLY-LEVY, KLHYLLY-TIKAS — see files/klhylly.lsp + klhylly.dwg)
    # Annotation blocks (e.g. "positiov2" position bubbles, 76 instances
    # in Lauri's reference DXF) on KYL-* layers must NOT be EXPLODEd —
    # they triple the conversion time AND inflate the IFC with thousands
    # of triangles for nothing. Ascii-only substring patterns avoid the
    # umlaut codepage issue (LISP `H*yrystin*` matches Höyrystin /
    # Hoyrystin alike via the leading `*`). KLHYLLY-* matches both
    # KLHYLLY-LEVY and KLHYLLY-TIKAS instances.
    '(setq inserts (ssget "_X" \'((0 . "INSERT") (2 . "*yrystin*,*ahdutin*,*pressori*,KLHYLLY-*")))) '
    '(write-line (strcat "phase2_inserts=" (if inserts (itoa (sslength inserts)) "0")) logf) '
    '(if inserts '
    '(progn '
    '(setq k 0 m (sslength inserts)) '
    '(while (< k m) '
    '(setq ins (ssname inserts k)) '
    '(setq ih (cdr (assoc 5 (entget ins)))) '
    '(command "_.EXPLODE" ins) '
    '(setq newents (ssget "_P")) '
    '(if newents '
    '(progn '
    '(setq j 0 nn (sslength newents) ctr 0) '
    '(while (< j nn) '
    '(setq ent (ssname newents j)) '
    '(setq etype (cdr (assoc 0 (entget ent)))) '
    # Only 3DSOLID children get STLOUTed. MESH children (in Lauri's
    # evaporator blocks: the mounting brackets, ~72 faces each at the
    # control cage but AutoCAD's STLOUT applies subdivision smoothing
    # to MESH that explodes triangle count by ~1000×) are read
    # natively by ezdxf in Python — see :func:`_inject_block_meshes`
    # which transforms block-local MESH vertices by each INSERT's
    # placement and merges the result into the per-handle bundle.
    '(if (eq etype "3DSOLID") '
    '(progn '
    '(command "_.STLOUT" ent "" "Y" (strcat insert_out ih "_" (itoa ctr) ".stl")) '
    '(setq ctr (1+ ctr)))) '
    '(setq j (1+ j))))) '
    '(setq k (1+ k))))) '
    '(write-line "done" logf) '
    '(close logf) '
    '(princ))'
)


def extract_acis_meshes(
    dxf_path: str | Path,
    *,
    layer_filter: str = "*",
    timeout_s: float = 180.0,
    progress: Callable[[str], None] | None = None,
) -> dict[str, AcisMeshData]:
    """Triangulate every ACIS body in ``dxf_path`` via accoreconsole.

    Returns a ``{handle.upper(): AcisMeshData}`` mapping. Returns an empty
    dict if accoreconsole is not installed, the subprocess times out or
    fails, or the DXF contains no ACIS bodies — never raises. Callers
    should treat absence as "no mesh available, skip this body".

    ``layer_filter`` is an AutoCAD wildcard pattern matched against entity
    layer names by ``ssget``. Default ``"*"`` extracts every ACIS body;
    pass e.g. ``"KYL-*,LT *,MT *"`` to limit by domain.
    """
    input_path = Path(dxf_path).resolve()
    if not input_path.is_file():
        return {}

    if not dxf_contains_acis_bodies(input_path):
        return {}

    accoreconsole = find_accoreconsole()
    if accoreconsole is None:
        if progress is not None:
            progress("accoreconsole.exe not found — ACIS bodies will be skipped")
        return {}

    workdir = Path(tempfile.mkdtemp(prefix="dxf2ifc_acis_"))
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

        scr_path = workdir / "extract.scr"
        scr_content = (
            _LISP_BODY.format(
                solid_out=solid_posix,
                insert_out=insert_posix,
                log_out=out_posix,
                filter=layer_filter,
            )
            + "\r\n"
        )
        scr_path.write_text(scr_content, encoding="utf-8")

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
                subprocess.run(
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
        except subprocess.TimeoutExpired:
            if progress is not None:
                progress(
                    f"accoreconsole timed out after {timeout_s:.0f} s — "
                    f"ACIS bodies will be skipped"
                )
            return {}
        except OSError as exc:
            if progress is not None:
                progress(f"accoreconsole failed: {exc} — ACIS bodies will be skipped")
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
                meshes[handle] = mesh

        # Phase 2 — INSERT block contents: merge every child STL into a
        # single :class:`AcisMeshData` per source INSERT handle, sharing a
        # vertex pool so the resulting MeshGeometry / IfcFacetedBrep is
        # de-duplicated. With FACETRES 0.5 each evaporator weighs in at
        # ~5–15k triangles total (cabinet panels + fan ring + hoses);
        # 15 evaporators ⇒ ≤ 250k triangles in IFC, manageable.
        per_insert: dict[str, list[Path]] = {}
        for stl_file in insert_dir.glob("*.stl"):
            handle = stl_file.stem.rsplit("_", 1)[0].upper()
            per_insert.setdefault(handle, []).append(stl_file)
        for handle, files in per_insert.items():
            merged_vertices: list[tuple[float, float, float]] = []
            merged_faces: list[tuple[int, ...]] = []
            vertex_to_idx: dict[tuple[float, float, float], int] = {}
            for stl_file in sorted(files):
                try:
                    sub = _parse_stl(stl_file)
                except Exception:  # noqa: BLE001
                    continue
                local_to_merged: list[int] = []
                for v in sub.vertices:
                    idx = vertex_to_idx.get(v)
                    if idx is None:
                        idx = len(merged_vertices)
                        vertex_to_idx[v] = idx
                        merged_vertices.append(v)
                    local_to_merged.append(idx)
                for face in sub.faces:
                    merged_faces.append(tuple(local_to_merged[i] for i in face))
            if merged_vertices and merged_faces:
                meshes[handle] = AcisMeshData(
                    tuple(merged_vertices), tuple(merged_faces)
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
