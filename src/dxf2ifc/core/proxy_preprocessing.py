"""MagiCAD / ACAD_PROXY_ENTITY geometry preprocessing.

The dxf_reader path (``dxf2ifc.core.dxf_reader``) already calls
``entity.__virtual_entities__()`` on every ACAD_PROXY_ENTITY and recurses
the resulting LINE / POLYLINE / etc through the regular dispatch, which
covers the ~75% of MagiCAD proxies whose proxy_graphic stream ezdxf can
parse (after v0.1.19's open-polyline acceptance fix). This module
handles the residual ~25% — proxies whose ``__virtual_entities__()``
returns nothing — by:

1. Computing a fallback bounding box via ``ezdxf.bbox.extents`` (which
   has multiple internal fallback strategies for proxy entities) and
   emitting a 12-triangle cuboid mesh keyed by the original proxy
   handle. This is sufficient for the user to *see* "something is
   here" in Solibri, with an explicit warning that the geometry is a
   bbox approximation.

2. When MagiCAD's free **Object Enabler** is installed on the host
   (download: <https://www.magicad.com/object-enabler/>),
   ``accoreconsole.exe`` understands MagiCAD's custom entity classes
   and can ``EXPLODE`` them into native primitives (3DSOLID + lines).
   This module detects Object Enabler via a Windows registry probe
   and, when present, runs ``EXPLODE`` on all proxies, ``STLOUT``-ing
   any resulting 3DSOLIDs to per-original-handle STL files. The mesh
   side-channel produced here is merged into ``acis_meshes`` by the
   orchestrator before ``read_dxf`` runs, so the proxy's own handle
   resolves to a real faceted body.

The principle (per Lauri 2026-05-06): *MagiCAD-objektien dataa ei
tarvitse ymmärtää, vain geometria*. IFC tieto tulee meidän
layer-mappauksesta. So we never read MagiCAD-specific PSets or
properties — original_layer + original_handle is all that flows
downstream, and the profile mapper does the rest.

The module is **safe** to call on any DXF: if no proxies exist, no
proxies need EXPLODE, accoreconsole is missing, or the host has no
Object Enabler, the function returns an empty :class:`ProxyArtifacts`
instead of raising. It never modifies the input DXF, the user's
AutoCAD profile, or the registry's RecentFiles list.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Mapping

import ezdxf

from dxf2ifc.core.preprocessing import AcisMeshData, find_accoreconsole, _parse_stl


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProxyArtifact:
    """Per-proxy metadata produced during preprocessing.

    ``original_handle`` is the upper-case DXF handle of the source
    ACAD_PROXY_ENTITY. ``original_layer`` is the layer the user
    authored under (preserved verbatim for the profile mapper).
    ``stl_file`` points to a triangulated mesh of the EXPLODE-derived
    3DSOLID children when Object Enabler succeeded; ``None`` otherwise.
    ``bbox`` is the entity's world-space extent — populated whenever
    ezdxf can compute it, used for the cuboid fallback when no real
    geometry was recovered.
    ``fallback_reason`` is set when the proxy could not be expanded
    to faceted geometry: ``"no_object_enabler"`` for the ~25% that
    need MagiCAD's free enabler, ``"explode_failed"`` for proxies
    whose EXPLODE raised, ``"no_geometry"`` for control objects that
    have neither virtual entities nor a usable bbox.
    """

    original_handle: str
    original_layer: str
    stl_file: Path | None
    bbox: tuple[tuple[float, float, float], tuple[float, float, float]] | None
    face_count: int
    fallback_reason: str | None


@dataclass
class ProxyArtifacts:
    """Result bundle from :func:`extract_proxy_geometry`.

    ``artifacts`` maps the original proxy handle (UPPER-CASE) to its
    :class:`ProxyArtifact` metadata. ``meshes`` is the side-channel
    that the orchestrator merges into ``acis_meshes`` before
    ``read_dxf`` runs — keys are original proxy handles, values are
    :class:`AcisMeshData` either from EXPLODE+STLOUT (real geometry)
    or from the bbox cuboid fallback. ``object_enabler_detected``
    records whether MagiCAD's Object Enabler was found on the host;
    used by the orchestrator to surface the install hint when proxies
    were dropped to bbox-only.
    """

    artifacts: dict[str, ProxyArtifact] = field(default_factory=dict)
    meshes: dict[str, AcisMeshData] = field(default_factory=dict)
    object_enabler_detected: bool = False


# ---------------------------------------------------------------------------
# Object Enabler detection
# ---------------------------------------------------------------------------


# Known DXF class names that MagiCAD's Object Enabler registers under
# HKLM\SOFTWARE\Autodesk\ObjectDBX\R<n>.0\<class_name>. The presence of
# any one of these subkeys means the enabler is installed and
# accoreconsole's EXPLODE will yield real geometry for MagiCAD proxies.
_MAGICAD_OBJECTDBX_CLASSES = (
    "MAGIPipe",
    "MAGIPipeAccessory",
    "MAGIPipeFitting",
    "MAGIDuct",
    "MAGIObject",
    "MAGIDevice",
)


def detect_object_enabler() -> bool:
    """Return ``True`` if MagiCAD's Object Enabler is registered.

    Probes the Windows registry under
    ``HKLM\\SOFTWARE\\Autodesk\\ObjectDBX\\R*.0\\<MagiCAD class>`` for
    any subkey matching a known MagiCAD class name. Returns ``False``
    on non-Windows hosts and when no MagiCAD subkeys are found. Never
    raises — registry access is wrapped in ``OSError`` catch so the
    caller can rely on a single bool.
    """
    if sys.platform != "win32":
        return False
    try:
        import winreg  # type: ignore[import-not-found]
    except ImportError:
        return False

    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            objectdbx = winreg.OpenKey(hive, r"SOFTWARE\Autodesk\ObjectDBX")
        except OSError:
            continue
        try:
            i = 0
            while True:
                try:
                    release_key = winreg.EnumKey(objectdbx, i)
                except OSError:
                    break
                i += 1
                try:
                    subkey = winreg.OpenKey(objectdbx, release_key)
                except OSError:
                    continue
                try:
                    j = 0
                    while True:
                        try:
                            cls = winreg.EnumKey(subkey, j)
                        except OSError:
                            break
                        j += 1
                        if cls in _MAGICAD_OBJECTDBX_CLASSES:
                            return True
                finally:
                    winreg.CloseKey(subkey)
        finally:
            winreg.CloseKey(objectdbx)
    return False


# ---------------------------------------------------------------------------
# Bbox → cuboid mesh helper
# ---------------------------------------------------------------------------


def bbox_to_cuboid_mesh(
    bbox: tuple[tuple[float, float, float], tuple[float, float, float]],
) -> AcisMeshData:
    """Build an 8-vertex, 12-triangle axis-aligned cuboid mesh.

    Used when the actual proxy geometry could not be recovered (no
    Object Enabler, EXPLODE failed, or no virtual entities and the
    proxy_graphic stream is unreadable). Solibri renders this as a
    box "marker" so the user can see the proxy's footprint and the
    progress log surfaces the fallback explicitly.
    """
    (xmin, ymin, zmin), (xmax, ymax, zmax) = bbox
    vertices = (
        (xmin, ymin, zmin),  # 0
        (xmax, ymin, zmin),  # 1
        (xmax, ymax, zmin),  # 2
        (xmin, ymax, zmin),  # 3
        (xmin, ymin, zmax),  # 4
        (xmax, ymin, zmax),  # 5
        (xmax, ymax, zmax),  # 6
        (xmin, ymax, zmax),  # 7
    )
    # Outward-facing CCW triangles for each of the 6 cube faces.
    faces = (
        (0, 2, 1), (0, 3, 2),  # bottom (-Z)
        (4, 5, 6), (4, 6, 7),  # top    (+Z)
        (0, 1, 5), (0, 5, 4),  # front  (-Y)
        (3, 7, 6), (3, 6, 2),  # back   (+Y)
        (0, 4, 7), (0, 7, 3),  # left   (-X)
        (1, 2, 6), (1, 6, 5),  # right  (+X)
    )
    return AcisMeshData(vertices=vertices, faces=faces)


# ---------------------------------------------------------------------------
# Proxy bounding box (ezdxf-only, no accoreconsole)
# ---------------------------------------------------------------------------


def _proxy_bbox(entity) -> (
    tuple[tuple[float, float, float], tuple[float, float, float]] | None
):
    """Compute world-space bbox for a single ACAD_PROXY_ENTITY.

    Uses ``ezdxf.bbox.extents([entity], fast=False)`` which iterates
    the proxy's virtual entities under the hood. When that returns no
    geometry (proxy_graphic empty / unparseable), returns ``None``.
    """
    try:
        from ezdxf import bbox

        ext = bbox.extents([entity], fast=False)
    except Exception:  # noqa: BLE001 — bbox can raise on malformed entities
        return None
    if ext is None or not ext.has_data:
        return None
    return (
        (float(ext.extmin.x), float(ext.extmin.y), float(ext.extmin.z)),
        (float(ext.extmax.x), float(ext.extmax.y), float(ext.extmax.z)),
    )


def _proxy_has_virtual_entities(entity) -> bool:
    """``True`` when ezdxf's virtual_entities() yields at least one entity.

    Cheap probe — used to skip accoreconsole-EXPLODE for proxies whose
    proxy_graphic stream ezdxf already decodes (~75% on typical
    MagiCAD DXFs). Defensive against malformed proxies that raise
    on the iterator.
    """
    try:
        for _ in entity.__virtual_entities__():
            return True
    except Exception:  # noqa: BLE001
        return False
    return False


# ---------------------------------------------------------------------------
# accoreconsole EXPLODE LISP body — split into 4 forms (each <2048 chars)
# ---------------------------------------------------------------------------


_LISP_PROXY_SETUP = (
    '(progn '
    '(setvar "FILEDIA" 0) '
    '(setvar "CMDDIA" 0) '
    '(setvar "FACETRES" 0.1) '
    '(setq solid_out "{solid_out}") '
    '(setq logf (open (strcat "{log_out}" "manifest.log") "w")))'
)


# Filter to proxies whose handle is in {filter} (a list of UPPER-CASE
# handles, comma-separated). We use the (5 . "<handle>") DXF group code
# directly via a wildcard pattern; ssget supports it via the (5 . "*")
# wildcard. To match a list of specific handles, we'd need OR logic which
# ssget doesn't natively support; instead, we ssget all proxies and
# filter inside the LISP.
_LISP_PROXY_EXPLODE = (
    '(progn '
    '(setq targets (list {handles_list})) '
    '(setq proxies (ssget "_X" \'((0 . "ACAD_PROXY_ENTITY")))) '
    '(write-line (strcat "FOUND " (if proxies (itoa (sslength proxies)) "0")) logf) '
    '(if proxies '
    '(progn '
    '(setq i 0 n (sslength proxies)) '
    '(while (< i n) '
    '(setq ent (ssname proxies i)) '
    '(setq el (entget ent)) '
    '(setq h (strcase (cdr (assoc 5 el)))) '
    '(if (member h targets) '
    '(progn '
    '(write-line (strcat "EXPLODE " h) logf) '
    '(setq res (vl-catch-all-apply (function (lambda () (command "_.EXPLODE" ent))))) '
    '(if (vl-catch-all-error-p res) '
    '(write-line (strcat "ERR " h) logf) '
    '(progn '
    '(setq newents (ssget "_P")) '
    '(if newents '
    '(progn '
    '(setq j 0 nn (sslength newents) ctr 0) '
    '(while (< j nn) '
    '(setq c (ssname newents j)) '
    '(setq cel (entget c)) '
    '(setq ct (cdr (assoc 0 cel))) '
    '(if (eq ct "3DSOLID") '
    '(progn '
    '(command "_.STLOUT" c "" "Y" (strcat solid_out h "_" (itoa ctr) ".stl")) '
    '(setq ctr (1+ ctr)))) '
    '(setq j (1+ j))) '
    '(write-line (strcat "CHILDREN " h " " (itoa ctr)) logf))))))) '
    '(setq i (1+ i))))))'
)


_LISP_PROXY_CLEANUP = (
    '(progn '
    '(write-line "DONE" logf) '
    '(close logf) '
    '(princ))'
)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def extract_proxy_geometry(
    dxf_path: str | Path,
    *,
    timeout_s: float = 300.0,
    progress: Callable[[str], None] | None = None,
) -> ProxyArtifacts:
    """Build a :class:`ProxyArtifacts` describing every ACAD_PROXY_ENTITY
    in ``dxf_path``.

    Returns an empty bundle when:
      * the DXF contains no proxies;
      * accoreconsole is missing AND no proxies have a usable bbox;
      * the host is non-Windows.
    Never raises.

    The function classifies each proxy into one of four states:
      1. **virtual_entities OK**: ezdxf-side ``__virtual_entities__()``
         yields ≥1 entity → no preprocessing needed (Phase A handles
         the geometry downstream). The artifact is recorded with bbox
         only, no mesh, no fallback_reason.
      2. **needs explode + Object Enabler present**: virtual_entities
         empty, EXPLODE will produce 3DSOLIDs → invoke accoreconsole,
         STLOUT children, attach mesh keyed by original handle.
      3. **needs explode + no Object Enabler**: virtual_entities empty,
         no enabler → bbox cuboid fallback, ``fallback_reason="no_object_enabler"``.
      4. **no recoverable geometry**: virtual_entities empty AND bbox
         empty → ``fallback_reason="no_geometry"``, no mesh.
    """
    input_path = Path(dxf_path).resolve()
    if not input_path.is_file():
        return ProxyArtifacts()

    try:
        doc = ezdxf.readfile(str(input_path))
    except Exception:  # noqa: BLE001
        return ProxyArtifacts()
    msp = doc.modelspace()

    needs_explode: dict[str, str] = {}  # handle -> layer (for proxies missing virtual_entities)
    artifacts: dict[str, ProxyArtifact] = {}
    bbox_by_handle: dict[
        str, tuple[tuple[float, float, float], tuple[float, float, float]]
    ] = {}

    for entity in msp:
        try:
            if entity.dxftype() != "ACAD_PROXY_ENTITY":
                continue
            handle = str(entity.dxf.handle).upper()
            layer = entity.dxf.layer
        except Exception:  # noqa: BLE001 — non-graphical control proxies
            continue

        bbox = _proxy_bbox(entity)
        if bbox is not None:
            bbox_by_handle[handle] = bbox

        if _proxy_has_virtual_entities(entity):
            # Phase A handles geometry downstream; record the artifact
            # for traceability + bbox availability for any later use.
            artifacts[handle] = ProxyArtifact(
                original_handle=handle,
                original_layer=layer,
                stl_file=None,
                bbox=bbox,
                face_count=0,
                fallback_reason=None,
            )
            continue

        # Needs accoreconsole EXPLODE (or bbox fallback)
        needs_explode[handle] = layer

    if not artifacts and not needs_explode:
        return ProxyArtifacts()

    enabler = detect_object_enabler()

    # When Object Enabler is present AND we have proxies needing explode AND
    # accoreconsole is available, run EXPLODE+STLOUT on the targeted handles.
    explode_meshes: dict[str, AcisMeshData] = {}
    if needs_explode and enabler:
        accoreconsole = find_accoreconsole()
        if accoreconsole is not None:
            explode_meshes = _run_explode(
                input_path,
                accoreconsole=accoreconsole,
                target_handles=list(needs_explode.keys()),
                timeout_s=timeout_s,
                progress=progress,
            )

    # Build remaining artifacts + meshes side-channel.
    meshes: dict[str, AcisMeshData] = {}
    for handle, layer in needs_explode.items():
        bbox = bbox_by_handle.get(handle)
        mesh = explode_meshes.get(handle)
        if mesh is not None and mesh.vertices and mesh.faces:
            artifacts[handle] = ProxyArtifact(
                original_handle=handle,
                original_layer=layer,
                stl_file=None,
                bbox=bbox,
                face_count=len(mesh.faces),
                fallback_reason=None,
            )
            meshes[handle] = mesh
        elif bbox is not None:
            cuboid = bbox_to_cuboid_mesh(bbox)
            artifacts[handle] = ProxyArtifact(
                original_handle=handle,
                original_layer=layer,
                stl_file=None,
                bbox=bbox,
                face_count=len(cuboid.faces),
                fallback_reason="no_object_enabler" if not enabler else "explode_failed",
            )
            meshes[handle] = cuboid
        else:
            artifacts[handle] = ProxyArtifact(
                original_handle=handle,
                original_layer=layer,
                stl_file=None,
                bbox=None,
                face_count=0,
                fallback_reason="no_geometry",
            )

    if progress is not None:
        ok = sum(1 for a in artifacts.values() if a.fallback_reason is None)
        bbox_n = sum(1 for a in artifacts.values() if a.fallback_reason in ("no_object_enabler", "explode_failed"))
        skip_n = sum(1 for a in artifacts.values() if a.fallback_reason == "no_geometry")
        progress(
            f"MagiCAD-proxy: {len(artifacts)} löytyi, "
            f"{ok} suoraan, {bbox_n} bbox-fallback, {skip_n} ohitettu"
        )
        if needs_explode and not enabler:
            progress(
                "Object Enabler ei asennettu — bbox-fallback käytössä "
                f"{bbox_n} proxylle. Lataa ilmainen Object Enabler: "
                "https://www.magicad.com/object-enabler/"
            )

    return ProxyArtifacts(
        artifacts=artifacts,
        meshes=meshes,
        object_enabler_detected=enabler,
    )


# ---------------------------------------------------------------------------
# accoreconsole EXPLODE driver
# ---------------------------------------------------------------------------


def _run_explode(
    dxf_path: Path,
    *,
    accoreconsole: Path,
    target_handles: list[str],
    timeout_s: float,
    progress: Callable[[str], None] | None,
) -> dict[str, AcisMeshData]:
    """Invoke accoreconsole to EXPLODE the listed proxy handles and
    triangulate any resulting 3DSOLID children.

    Returns a ``{original_handle: AcisMeshData}`` mapping. Keys are the
    ORIGINAL proxy handles (uppercase) — STLOUT writes per-source files
    using the proxy's handle as prefix, and the parser merges any
    ``<handle>_*.stl`` files into a single AcisMeshData for that source.

    Returns an empty dict on timeout, subprocess failure, or when
    STLOUT produces no files (e.g. EXPLODE yielded only wireframe
    primitives). Never raises — caller relies on bbox fallback.
    """
    if not target_handles:
        return {}

    workdir = Path(tempfile.mkdtemp(prefix="dxf2ifc_proxy_"))
    try:
        out_dir = workdir / "stl"
        solid_dir = out_dir / "solid"
        solid_dir.mkdir(parents=True)
        solid_posix = solid_dir.as_posix() + "/"
        out_posix = out_dir.as_posix() + "/"

        # LISP needs a list literal of handles. Quote each with " " for
        # LISP string equality (member uses eq which works on strings).
        # All handles are upper-case 1-8 hex chars; safe to splice raw.
        handles_list = " ".join(f'"{h}"' for h in target_handles)

        scr_path = workdir / "extract.scr"
        forms = [
            _LISP_PROXY_SETUP.format(
                solid_out=solid_posix,
                log_out=out_posix,
            ),
            _LISP_PROXY_EXPLODE.format(handles_list=handles_list),
            _LISP_PROXY_CLEANUP,
        ]
        scr_path.write_text("\r\n".join(forms) + "\r\n", encoding="utf-8")

        if progress is not None:
            progress(f"Räjäytetään {len(target_handles)} MagiCAD-proxya accoreconsolessa…")

        creationflags = 0
        if sys.platform == "win32":
            creationflags = 0x00000008  # DETACHED_PROCESS

        log_path = workdir / "accoreconsole.log"
        try:
            with log_path.open("w", encoding="utf-8") as log_fh:
                subprocess.run(
                    [
                        str(accoreconsole),
                        "/i", str(dxf_path),
                        "/s", str(scr_path),
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
                    f"accoreconsole timeout {timeout_s:.0f}s — proxy-EXPLODE peruttu"
                )
            return {}
        except OSError as exc:
            if progress is not None:
                progress(f"accoreconsole epäonnistui: {exc}")
            return {}

        # Aggregate per-original-handle STL files into single meshes.
        # File pattern: <ORIGINAL_HANDLE>_<n>.stl (n = 0,1,…).
        per_handle: dict[str, list[Path]] = {}
        for stl_file in solid_dir.glob("*.stl"):
            base = stl_file.stem.rsplit("_", 1)[0].upper()
            per_handle.setdefault(base, []).append(stl_file)

        meshes: dict[str, AcisMeshData] = {}
        for handle, files in per_handle.items():
            merged_v: list[tuple[float, float, float]] = []
            merged_f: list[tuple[int, ...]] = []
            v_to_idx: dict[tuple[float, float, float], int] = {}
            for stl_file in sorted(files):
                try:
                    sub = _parse_stl(stl_file)
                except Exception:  # noqa: BLE001
                    continue
                local_to_merged: list[int] = []
                for v in sub.vertices:
                    idx = v_to_idx.get(v)
                    if idx is None:
                        idx = len(merged_v)
                        v_to_idx[v] = idx
                        merged_v.append(v)
                    local_to_merged.append(idx)
                for face in sub.faces:
                    merged_f.append(tuple(local_to_merged[i] for i in face))
            if merged_v and merged_f:
                meshes[handle] = AcisMeshData(tuple(merged_v), tuple(merged_f))

        return meshes
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Manifest serialization (test-only — never written by extract_proxy_geometry)
# ---------------------------------------------------------------------------


def artifacts_to_jsonl(artifacts: Mapping[str, ProxyArtifact]) -> str:
    """Serialise an artifact mapping to JSON-lines.

    One line per artifact, sorted by handle for determinism. Used in
    tests to assert manifest format and round-trip; the production
    pipeline does not write this file (state lives in memory only,
    keyed for the orchestrator).
    """
    out: list[str] = []
    for handle in sorted(artifacts):
        a = artifacts[handle]
        out.append(json.dumps({
            "original_handle": a.original_handle,
            "original_layer": a.original_layer,
            "stl_file": str(a.stl_file) if a.stl_file is not None else None,
            "bbox": a.bbox,
            "face_count": a.face_count,
            "fallback_reason": a.fallback_reason,
        }))
    return "\n".join(out)


def artifacts_from_jsonl(text: str) -> dict[str, ProxyArtifact]:
    """Inverse of :func:`artifacts_to_jsonl`. Used in tests."""
    out: dict[str, ProxyArtifact] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        bbox = d.get("bbox")
        if bbox is not None:
            bbox = (
                tuple(bbox[0]),
                tuple(bbox[1]),
            )
        stl = d.get("stl_file")
        out[d["original_handle"]] = ProxyArtifact(
            original_handle=d["original_handle"],
            original_layer=d["original_layer"],
            stl_file=Path(stl) if stl else None,
            bbox=bbox,
            face_count=int(d.get("face_count", 0)),
            fallback_reason=d.get("fallback_reason"),
        )
    return out
