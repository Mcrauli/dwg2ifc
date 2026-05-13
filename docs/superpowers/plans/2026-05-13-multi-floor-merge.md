# Multi-floor DWG Merge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert N DXF/DWG inputs into one IFC, one IfcBuildingStorey per file, with user-supplied floor labels and per-floor Z elevations.

**Architecture:** Per-file pipeline (preprocess → read → map → POSITIO → energy-spec → per-floor Z offset → tag with `storey_index`) is run inside a new `orchestrator.convert(files: list[FileEntry], …)` entry point. All resulting `MappedEntity` records are passed to one skeleton builder (N storeys, one per file) and one builder dispatch pass. The legacy `convert_dxf(...)` is kept as a thin shim that wraps a single file into a one-entry list. Profile schema loses `storey_z_levels_mm`; GUI gains a `(file, label, elevation_mm)` table replacing the single elevation checkbox+spinbox.

**Tech Stack:** Python 3.12, PySide6 (GUI), pydantic v2 (profile schema), ezdxf (DXF reader), ifcopenshell (IFC writer), pytest + pytest-qt (tests).

**Reference spec:** `docs/superpowers/specs/2026-05-13-multi-floor-merge-design.md`.

---

## File map

| File | Action | Responsibility |
|---|---|---|
| `src/dxf2ifc/core/types.py` | Modify | Add `FileEntry` dataclass; extend `MappedEntity` with `storey_index` |
| `src/dxf2ifc/core/ifc_writer/skeleton.py` | Modify | Accept `storey_names` parameter; build per-storey Name from list |
| `src/dxf2ifc/core/ifc_writer/orchestrator.py` | Modify | Extract per-file work to `_process_one_file`; add `convert(files=…)` entry point; reduce `convert_dxf` to shim |
| `src/dxf2ifc/core/ifc_writer/__init__.py` | Modify | Re-export `convert` and `FileEntry` |
| `src/dxf2ifc/profiles/schema.py` | Modify | Remove `Profile.storey_z_levels_mm` and its validator |
| `src/dxf2ifc/profiles/default_kylmalaite.toml` | Modify | Delete `storey_z_levels_mm = [0.0]` line |
| `src/dxf2ifc/cli.py` | Modify | Add `--floor PATH:LABEL:ELEV` (repeatable); keep positional `IN OUT` |
| `src/dxf2ifc/gui/file_panel.py` | Rewrite | Replace single-file controls with multi-row table |
| `src/dxf2ifc/gui/convert_worker.py` | Modify | Accept `list[FileEntry]`; call new `convert(...)` |
| `src/dxf2ifc/gui/main_window.py` | Modify | Wire updated signal payload from `FilePanel` to worker |
| `tests/test_types.py` | Create | Tests for `FileEntry` and `MappedEntity.storey_index` defaults |
| `tests/test_skeleton.py` | Extend | `storey_names` argument names storeys; default fallback |
| `tests/test_orchestrator_multi_floor.py` | Create | End-to-end 2-file → 2-storey IFC; world-Z math; storey index dispatch |
| `tests/test_orchestrator_convert_dxf_shim.py` | Create | Single-file legacy entrypoint still works |
| `tests/test_cli_multi_floor.py` | Create | `--floor` parsing variants; validation |
| `tests/test_gui_file_panel.py` | Rewrite | Multi-row add/remove/edit; defaults; duplicate-label validation |
| `tests/test_gui_convert_worker.py` | Modify | New signature shape |
| `tests/test_profile_schema.py` | Modify | Remove the 6 storey_z_levels_mm tests |
| `CHANGELOG.md` | Modify | alpha22 entry (breaking: profile field, GUI controls) |
| `PROGRESS.md` | Modify | New `Current state` line |
| `README.md` | Modify | GUI screenshot text + CLI examples |
| `CLAUDE.md` | Modify | Pipeline diagram reflects per-file loop |
| `docs/ARCHITECTURE.md` | Modify | Pipeline section reflects per-file loop |
| `src/dxf2ifc/_version.py` | Modify | Bump to `0.2.0a22` |
| `pyproject.toml` | Modify | Bump version |

---

## Task 1 — `FileEntry` dataclass

**Files:**
- Modify: `src/dxf2ifc/core/types.py` (append new dataclass)
- Create: `tests/test_types.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_types.py`:

```python
"""Plain-data-container tests for core/types.py."""
from pathlib import Path

from dxf2ifc.core.types import FileEntry, MappedEntity


def test_file_entry_holds_path_label_elevation():
    entry = FileEntry(path=Path("1krs.dwg"), floor_label="1.krs", elevation_mm=0.0)
    assert entry.path == Path("1krs.dwg")
    assert entry.floor_label == "1.krs"
    assert entry.elevation_mm == 0.0


def test_file_entry_is_frozen():
    import dataclasses

    entry = FileEntry(path=Path("a.dwg"), floor_label="1.krs", elevation_mm=0.0)
    with __import__("pytest").raises(dataclasses.FrozenInstanceError):
        entry.elevation_mm = 5.0  # type: ignore[misc]


def test_mapped_entity_storey_index_defaults_to_zero():
    m = MappedEntity(layer="X", dxf_type="LINE", geometry=None)
    assert m.storey_index == 0


def test_mapped_entity_storey_index_settable():
    m = MappedEntity(layer="X", dxf_type="LINE", geometry=None, storey_index=2)
    assert m.storey_index == 2
```

- [ ] **Step 2: Run test, expect ImportError / AttributeError**

Run: `.venv/Scripts/python -m pytest tests/test_types.py -v`
Expected: 4 fails on missing `FileEntry` / `storey_index`.

- [ ] **Step 3: Add `FileEntry` and `MappedEntity.storey_index`**

Append to `src/dxf2ifc/core/types.py`:

```python
@dataclass(frozen=True)
class FileEntry:
    """One input file with its assigned floor label and Z elevation.

    A multi-floor conversion run takes a ``list[FileEntry]``; each entry
    becomes one ``IfcBuildingStorey``. ``elevation_mm`` is added to every
    entity's Z coordinate read from this file, so when all entries are
    at ``elevation_mm=0`` the DXF Z coordinates pass through to the IFC
    unchanged.
    """

    path: Path
    floor_label: str
    elevation_mm: float = 0.0
```

Add to the top imports of `types.py`:

```python
from pathlib import Path
```

Extend `MappedEntity` (in the same file) with:

```python
    storey_index: int = 0
```

inserted after `extra_props: dict[str, Any] = field(default_factory=dict)` (keep it as the last field so existing positional uses still work).

- [ ] **Step 4: Run tests**

Run: `.venv/Scripts/python -m pytest tests/test_types.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/dxf2ifc/core/types.py tests/test_types.py
git commit -m "feat(core): FileEntry dataclass + MappedEntity.storey_index"
```

---

## Task 2 — Skeleton accepts `storey_names`

**Files:**
- Modify: `src/dxf2ifc/core/ifc_writer/skeleton.py:42-67` and the storey-creation loop at lines ~107-120
- Modify: existing tests in `tests/test_skeleton.py` if any; extend with new ones

- [ ] **Step 1: Find and read existing skeleton tests**

```bash
.venv/Scripts/python -m pytest tests/test_skeleton.py -v --collect-only
```

Note which tests exist so they can be kept passing.

- [ ] **Step 2: Write the failing test**

Append to `tests/test_skeleton.py` (create if missing):

```python
def test_storey_names_supplied_uses_those_names():
    from dxf2ifc.core.ifc_writer.skeleton import build_ifc_project_skeleton

    skel = build_ifc_project_skeleton(
        project_name="Multi",
        storey_z_levels_mm=[0.0, 3500.0, 7000.0],
        storey_names=["1.krs", "2.krs", "kellari"],
    )
    assert [s.Name for s in skel.storeys] == ["1.krs", "2.krs", "kellari"]
    assert [s.Elevation for s in skel.storeys] == [0.0, 3500.0, 7000.0]


def test_storey_names_omitted_falls_back_to_kerros_n():
    from dxf2ifc.core.ifc_writer.skeleton import build_ifc_project_skeleton

    skel = build_ifc_project_skeleton(
        project_name="One",
        storey_z_levels_mm=[0.0, 3500.0],
    )
    assert [s.Name for s in skel.storeys] == ["Kerros 1", "Kerros 2"]


def test_storey_names_length_mismatch_raises():
    import pytest

    from dxf2ifc.core.ifc_writer.skeleton import build_ifc_project_skeleton

    with pytest.raises(ValueError, match="storey_names"):
        build_ifc_project_skeleton(
            project_name="x",
            storey_z_levels_mm=[0.0, 3500.0],
            storey_names=["1.krs"],  # too few
        )
```

- [ ] **Step 3: Run test, expect failures**

Run: `.venv/Scripts/python -m pytest tests/test_skeleton.py -v -k "storey_names"`
Expected: FAIL (unknown kwarg).

- [ ] **Step 4: Update `build_ifc_project_skeleton`**

In `src/dxf2ifc/core/ifc_writer/skeleton.py`, change the signature:

```python
def build_ifc_project_skeleton(
    *,
    project_name: str = "Untitled",
    site_name: str = "Default Site",
    building_name: str = "Default Building",
    schema: str = "IFC4",
    storey_z_levels_mm: list[float] | None = None,
    storey_names: list[str] | None = None,
    floor_elevation_mm: float = 0.0,
    discipline_label: str | None = None,
) -> IfcSkeleton:
```

After the line `if storey_z_levels_mm is None:` block, validate name list length:

```python
    if storey_names is not None and len(storey_names) != len(storey_z_levels_mm):
        raise ValueError(
            "storey_names must have the same length as storey_z_levels_mm "
            f"(got {len(storey_names)} names for {len(storey_z_levels_mm)} levels)"
        )
```

In the storey creation loop, replace:

```python
        storey = ifcopenshell.api.run(
            "root.create_entity",
            ifc,
            ifc_class="IfcBuildingStorey",
            name=f"Kerros {index}",
        )
```

with:

```python
        storey_name = (
            storey_names[index - 1]
            if storey_names is not None
            else f"Kerros {index}"
        )
        storey = ifcopenshell.api.run(
            "root.create_entity",
            ifc,
            ifc_class="IfcBuildingStorey",
            name=storey_name,
        )
```

- [ ] **Step 5: Run tests**

Run: `.venv/Scripts/python -m pytest tests/test_skeleton.py -v`
Expected: PASS (all, including the three new ones).

- [ ] **Step 6: Commit**

```bash
git add src/dxf2ifc/core/ifc_writer/skeleton.py tests/test_skeleton.py
git commit -m "feat(skeleton): accept storey_names list for per-storey naming"
```

---

## Task 3 — Refactor orchestrator to extract per-file work

Goal: pull every "per-file" step (preprocess, read, map, POSITIO, energy-spec, Z-offset, mesh-tagging) into a helper `_process_one_file(file_entry, *, profile, …) -> list[MappedEntity]`. Leave behaviour identical for single-file callers.

**Files:**
- Modify: `src/dxf2ifc/core/ifc_writer/orchestrator.py` (the bulk of `convert_dxf`)

- [ ] **Step 1: Run the existing orchestrator tests to capture baseline**

Run: `.venv/Scripts/python -m pytest tests/ -k "orchestrator or convert_dxf" -v`
Note: tests should currently pass. Snapshot the list of PASSing tests.

- [ ] **Step 2: Add `_process_one_file` helper (no behaviour change yet)**

Inside `orchestrator.py`, define a new private function above `convert_dxf`:

```python
def _process_one_file(
    file_entry: "FileEntry",
    *,
    profile: Profile,
    schema: str,
    preprocess_acis: bool,
    skip_magicad: bool,
    energy_specs_path: str | Path | None,
    progress: object | None,
) -> list[MappedEntity]:
    """Run preprocess+read+map+POSITIO+energy+Z-offset for one file.

    Returns ``MappedEntity`` records tagged with this file's
    ``storey_index`` (caller assigns the index before invoking).
    """
    input_path = Path(file_entry.path)
    if input_path.suffix.lower() == ".dwg":
        from dxf2ifc.core.dwg_preconvert import convert_dwg_to_dxf
        dwg_workdir = Path(tempfile.mkdtemp(prefix="dxf2ifc_dwgin_"))
        dxf_path = convert_dwg_to_dxf(
            input_path,
            dwg_workdir,
            progress=progress if callable(progress) else None,
        )
    else:
        dxf_path = input_path

    acis_meshes: dict[str, object] = {}
    if preprocess_acis:
        from dxf2ifc.core.preprocessing import extract_acis_meshes
        acis_meshes = extract_acis_meshes(  # type: ignore[arg-type,assignment]
            dxf_path,
            progress=progress,
            skip_magicad=skip_magicad,
        )

    entities = read_dxf(dxf_path, acis_meshes=acis_meshes, skip_magicad=skip_magicad)

    if progress is not None:
        _emit_read_diagnostics(progress, entities, label=file_entry.floor_label)

    mapped = apply_profile(entities, profile)

    if progress is not None:
        _emit_map_diagnostics(progress, mapped, label=file_entry.floor_label)

    if profile.positio is not None:
        _run_positio_lookup(mapped, dxf_path, profile)

    if energy_specs_path is not None:
        _run_energy_spec_lookup(mapped, energy_specs_path, profile=profile, progress=progress)

    _apply_floor_elevation_offset(mapped, file_entry.elevation_mm)

    # Tag entities with their floor (storey_index is set by the caller).
    return mapped
```

Note: this introduces `_emit_read_diagnostics`, `_emit_map_diagnostics`, `_run_positio_lookup` — these are extractions of the inline blocks in current `convert_dxf`. Move those blocks verbatim into three small private helpers (above `_process_one_file`):

```python
def _emit_read_diagnostics(progress, entities, *, label: str = "") -> None:
    polyface_count = sum(
        1 for e in entities
        if isinstance(e.geometry, MeshGeometry)
        and e.geometry.source in {"polyface", "3dface", "mesh"}
    )
    acis_count = sum(
        1 for e in entities
        if isinstance(e.geometry, MeshGeometry)
        and e.geometry.source == "acis"
    )
    layers_with_mesh: dict[str, int] = {}
    for e in entities:
        if isinstance(e.geometry, MeshGeometry):
            layers_with_mesh[e.layer] = layers_with_mesh.get(e.layer, 0) + 1
    prefix = f"[{label}] " if label else ""
    progress(
        f"{prefix}DXF-luettu: {polyface_count} polyface/3DFACE/MESH + "
        f"{acis_count} ACIS-mesh (yhteensä {len(entities)} entiteettiä)"
    )
    if layers_with_mesh:
        top = sorted(layers_with_mesh.items(), key=lambda x: -x[1])[:5]
        progress(f"{prefix}Mesh-layerit (top 5): " + ", ".join(f"{lyr}={n}" for lyr, n in top))


def _emit_map_diagnostics(progress, mapped, *, label: str = "") -> None:
    mapped_mesh = sum(1 for m in mapped if isinstance(m.geometry, MeshGeometry))
    mapped_types: dict[str, int] = {}
    for m in mapped:
        if isinstance(m.geometry, MeshGeometry):
            mapped_types[m.ifc_type] = mapped_types.get(m.ifc_type, 0) + 1
    prefix = f"[{label}] " if label else ""
    progress(
        f"{prefix}Profile-mappaus: {len(mapped)} entiteettiä, joista "
        f"{mapped_mesh} mesh-pohjaisia"
    )
    if mapped_types:
        top = sorted(mapped_types.items(), key=lambda x: -x[1])[:5]
        progress(f"{prefix}Mesh→IFC-tyypit: " + ", ".join(f"{t}={n}" for t, n in top))


def _run_positio_lookup(mapped, dxf_path, profile) -> None:
    # Move the existing POSITIO block (orchestrator.py lines ~348-431)
    # here verbatim — replace ``progress`` references with no-op since
    # POSITIO has no progress messages currently.
    from dxf2ifc.core.positio import find_nearest_positio, index_positio_markers
    import ezdxf as _ezdxf

    positio_markers = index_positio_markers(
        dxf_path, block_pattern=profile.positio.block_pattern
    )
    if not positio_markers:
        return
    scope = set(profile.positio.apply_to)
    radius = profile.positio.max_distance_mm
    insert_xy_by_handle: dict[str, tuple[float, float]] = {}
    try:
        _doc = _ezdxf.readfile(str(dxf_path))
        for _ent in _doc.modelspace():
            if _ent.dxftype() != "INSERT":
                continue
            try:
                _h = str(_ent.dxf.handle).upper()
                insert_xy_by_handle[_h] = (
                    float(_ent.dxf.insert.x),
                    float(_ent.dxf.insert.y),
                )
            except Exception:  # noqa: BLE001
                continue
    except Exception:  # noqa: BLE001 — POSITIO link is best-effort
        pass

    for m in mapped:
        if m.ifc_type not in scope:
            continue
        target_xy: tuple[float, float] | None = None
        handle = getattr(m, "handle", None)
        if handle and str(handle).upper() in insert_xy_by_handle:
            target_xy = insert_xy_by_handle[str(handle).upper()]
        elif isinstance(m.geometry, BlockInstance):
            target_xy = (m.geometry.insertion_point.x, m.geometry.insertion_point.y)
        elif isinstance(m.geometry, MeshGeometry) and m.geometry.vertices:
            xs = [v.x for v in m.geometry.vertices]
            ys = [v.y for v in m.geometry.vertices]
            target_xy = ((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0)
        if target_xy is None:
            continue
        marker = find_nearest_positio(target_xy, positio_markers, max_distance_mm=radius)
        if marker is None:
            continue
        if m.extra_props is None:
            m.extra_props = {}
        if marker.teksti:
            m.extra_props["koneikko"] = marker.teksti
        if marker.numero:
            m.extra_props["laitetunnus"] = marker.numero
```

- [ ] **Step 3: Rewire `convert_dxf` to use the helpers (still single-file)**

In `convert_dxf`, replace the body from the `input_path = Path(dxf_path)` line up to and including `_apply_floor_elevation_offset(mapped, floor_elevation_mm)` with:

```python
    input_path = Path(dxf_path)
    file_entry = FileEntry(
        path=input_path,
        floor_label="1.krs",
        elevation_mm=floor_elevation_mm,
    )
    skip_magicad = magicad_ifc_path is not None
    mapped = _process_one_file(
        file_entry,
        profile=profile,
        schema=schema,
        preprocess_acis=preprocess_acis,
        skip_magicad=skip_magicad,
        energy_specs_path=energy_specs_path,
        progress=progress,
    )
    for m in mapped:
        m.storey_index = 0
    name = project_name or input_path.stem
```

Below this, the existing skeleton building stays but switches to `storey_z_levels_mm=[file_entry.elevation_mm]` and adds `storey_names=[file_entry.floor_label]` so the storey is named "1.krs":

```python
    skeleton = build_ifc_project_skeleton(
        project_name=name,
        schema=schema,
        floor_elevation_mm=0.0,
        storey_z_levels_mm=[file_entry.elevation_mm],
        storey_names=[file_entry.floor_label],
        discipline_label=project_discipline,
    )
```

The `_storey_for(m)` inner function changes to use the index:

```python
    def _storey_for(m) -> object:
        return skeleton.storeys[m.storey_index]
```

(The fallback `resolve_storey(skeleton.storeys, _entity_anchor_z(m.geometry))` is no longer needed — every mapped entity has a known `storey_index`. We can remove the import of `resolve_storey` from this file.)

- [ ] **Step 4: Run the baseline orchestrator tests**

Run: `.venv/Scripts/python -m pytest tests/ -k "orchestrator or convert_dxf" -v`
Expected: every previously-PASSing test still PASSes.

Also run the broader test sweep to catch regressions in builders/classification:

Run: `.venv/Scripts/python -m pytest -x -q`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/dxf2ifc/core/ifc_writer/orchestrator.py
git commit -m "refactor(orchestrator): extract per-file pipeline to _process_one_file"
```

---

## Task 4 — `orchestrator.convert(files=[...])` entry point

**Files:**
- Modify: `src/dxf2ifc/core/ifc_writer/orchestrator.py`
- Modify: `src/dxf2ifc/core/ifc_writer/__init__.py` (re-export `convert` and `FileEntry`)
- Create: `tests/test_orchestrator_multi_floor.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_orchestrator_multi_floor.py`:

```python
"""Multi-floor: two DXF files -> one IFC with two storeys."""
from pathlib import Path

import ifcopenshell
import pytest

from dxf2ifc.core.ifc_writer.orchestrator import FileEntry, convert
from dxf2ifc.profiles.loader import load_default_profile


def _write_minimal_dxf(path: Path, layer: str = "KYL-LEVYHYLLY", z: float = 0.0) -> None:
    """Write a tiny DXF with one closed LWPOLYLINE on the given layer."""
    import ezdxf

    doc = ezdxf.new("R2018")
    msp = doc.modelspace()
    msp.add_lwpolyline(
        [(0, 0), (1000, 0), (1000, 1000), (0, 1000)],
        format="xy",
        close=True,
        dxfattribs={"layer": layer, "elevation": z},
    )
    doc.layers.add(layer)
    doc.saveas(str(path))


def test_multi_floor_produces_two_storeys(tmp_path):
    floor1 = tmp_path / "1krs.dxf"
    floor2 = tmp_path / "2krs.dxf"
    _write_minimal_dxf(floor1, z=0.0)
    _write_minimal_dxf(floor2, z=0.0)
    out = tmp_path / "out.ifc"

    convert(
        files=[
            FileEntry(path=floor1, floor_label="1.krs", elevation_mm=0.0),
            FileEntry(path=floor2, floor_label="2.krs", elevation_mm=3500.0),
        ],
        output_path=out,
        profile=load_default_profile(),
        preprocess_acis=False,
    )

    ifc = ifcopenshell.open(str(out))
    storeys = ifc.by_type("IfcBuildingStorey")
    assert len(storeys) == 2
    assert sorted(s.Name for s in storeys) == ["1.krs", "2.krs"]
    elevations = {s.Name: s.Elevation for s in storeys}
    assert elevations["1.krs"] == 0.0
    assert elevations["2.krs"] == 3500.0


def test_multi_floor_rejects_empty_list(tmp_path):
    out = tmp_path / "x.ifc"
    with pytest.raises(ValueError, match="at least one"):
        convert(
            files=[],
            output_path=out,
            profile=load_default_profile(),
            preprocess_acis=False,
        )


def test_multi_floor_rejects_duplicate_labels(tmp_path):
    floor1 = tmp_path / "1krs.dxf"
    floor2 = tmp_path / "duplicate.dxf"
    _write_minimal_dxf(floor1)
    _write_minimal_dxf(floor2)
    out = tmp_path / "x.ifc"

    with pytest.raises(ValueError, match="duplicate"):
        convert(
            files=[
                FileEntry(path=floor1, floor_label="1.krs", elevation_mm=0.0),
                FileEntry(path=floor2, floor_label="1.krs", elevation_mm=3500.0),
            ],
            output_path=out,
            profile=load_default_profile(),
            preprocess_acis=False,
        )
```

- [ ] **Step 2: Run test, expect ImportError**

Run: `.venv/Scripts/python -m pytest tests/test_orchestrator_multi_floor.py -v`
Expected: FAIL (`convert` not exported).

- [ ] **Step 3: Implement `convert`**

Add to `src/dxf2ifc/core/ifc_writer/orchestrator.py`, near the existing `convert_dxf`:

```python
def convert(
    *,
    files: list[FileEntry],
    output_path: str | Path,
    profile: Profile,
    project_name: str | None = None,
    validate: bool = False,
    schema: str = "IFC4",
    preprocess_acis: bool = True,
    progress: object | None = None,
    energy_specs_path: str | Path | None = None,
    magicad_ifc_path: str | Path | None = None,
) -> tuple[dict[str, list], ValidationReport | None]:
    """Multi-file → single IFC. Each file becomes one IfcBuildingStorey.

    See ``convert_dxf`` for parameter semantics that are not per-file
    (``project_name``, ``validate``, ``schema``, ``progress``,
    ``energy_specs_path``, ``magicad_ifc_path``). The legacy single-file
    entry point is now a shim that wraps a one-entry ``files`` list.
    """
    if not files:
        raise ValueError("convert() requires at least one FileEntry")
    labels_lower = [fe.floor_label.strip().lower() for fe in files]
    if len(set(labels_lower)) != len(labels_lower):
        raise ValueError(f"duplicate floor labels in files: {[fe.floor_label for fe in files]}")
    for fe in files:
        if not fe.floor_label.strip():
            raise ValueError(f"floor_label cannot be empty (file {fe.path})")

    skip_magicad = magicad_ifc_path is not None

    all_mapped: list[MappedEntity] = []
    for index, fe in enumerate(files):
        if progress is not None:
            progress(f"[{fe.floor_label}] käsitellään {Path(fe.path).name} ({index+1}/{len(files)})")
        mapped = _process_one_file(
            fe,
            profile=profile,
            schema=schema,
            preprocess_acis=preprocess_acis,
            skip_magicad=skip_magicad,
            energy_specs_path=energy_specs_path,
            progress=progress,
        )
        for m in mapped:
            m.storey_index = index
        all_mapped.extend(mapped)

    domains = {m.domain for m in all_mapped if m.domain}
    project_discipline = (
        discipline_label(next(iter(domains))) if len(domains) == 1 else None
    )

    name = project_name or Path(output_path).stem

    skeleton = build_ifc_project_skeleton(
        project_name=name,
        schema=schema,
        floor_elevation_mm=0.0,
        storey_z_levels_mm=[fe.elevation_mm for fe in files],
        storey_names=[fe.floor_label for fe in files],
        discipline_label=project_discipline,
    )

    ifc = skeleton.file
    systems: dict[str, list] = {}

    def _storey_for(m) -> object:
        return skeleton.storeys[m.storey_index]

    # … reuse the existing builder dispatch loop from convert_dxf …
    # (extract it to a helper `_write_products(ifc, mapped, skeleton, …)`
    #  if duplication grows; for now copy it once into `convert`.)
```

For the builder dispatch loop body: extract the existing for-loop in `convert_dxf` (currently the `try: for m in mapped: if m.ifc_type == "IfcWall": …` block, plus the `for system_name, products in systems.items(): …` and `write_ifc(ifc, output_path)` and MagiCAD merge afterwards) into a new private helper:

```python
def _write_products(
    ifc: object,
    skeleton: "IfcSkeleton",
    mapped: list[MappedEntity],
    output_path: str | Path,
    *,
    magicad_ifc_path: str | Path | None,
    progress: object | None,
    validate: bool,
) -> tuple[dict[str, list], ValidationReport | None]:
    """Dispatch builders, assign systems, write IFC, optionally merge MagiCAD."""
    # Move the existing dispatch body verbatim. Replace _storey_for closure
    # with: skeleton.storeys[m.storey_index].
    ...
```

Then `convert(...)` ends with:

```python
    return _write_products(
        ifc, skeleton, all_mapped, output_path,
        magicad_ifc_path=magicad_ifc_path,
        progress=progress,
        validate=validate,
    )
```

And `convert_dxf(...)` ends with the same call (after building its one-entry list).

- [ ] **Step 4: Update `src/dxf2ifc/core/ifc_writer/__init__.py`**

Read the file; ensure it exports `convert` alongside `convert_dxf`:

```python
from dxf2ifc.core.ifc_writer.orchestrator import FileEntry, convert, convert_dxf

__all__ = ["FileEntry", "convert", "convert_dxf"]
```

Also export `FileEntry` from `dxf2ifc.core.types` (no change needed if Task 1 added it to `types.py`; orchestrator re-imports from there).

- [ ] **Step 5: Run multi-floor tests**

Run: `.venv/Scripts/python -m pytest tests/test_orchestrator_multi_floor.py -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Run the whole test suite to catch regressions**

Run: `.venv/Scripts/python -m pytest -x -q`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add src/dxf2ifc/core/ifc_writer/orchestrator.py src/dxf2ifc/core/ifc_writer/__init__.py tests/test_orchestrator_multi_floor.py
git commit -m "feat(orchestrator): multi-file convert() entry point"
```

---

## Task 5 — `convert_dxf` shim test (single-file regression guard)

**Files:**
- Create: `tests/test_orchestrator_convert_dxf_shim.py`

- [ ] **Step 1: Write the test**

```python
"""convert_dxf must keep working as a single-file shim around convert()."""
from pathlib import Path

import ifcopenshell

from dxf2ifc.core.ifc_writer import convert_dxf
from dxf2ifc.profiles.loader import load_default_profile


def _write_minimal_dxf(path: Path, layer: str = "KYL-LEVYHYLLY") -> None:
    import ezdxf
    doc = ezdxf.new("R2018")
    msp = doc.modelspace()
    msp.add_lwpolyline(
        [(0, 0), (1000, 0), (1000, 1000), (0, 1000)],
        format="xy", close=True,
        dxfattribs={"layer": layer},
    )
    doc.layers.add(layer)
    doc.saveas(str(path))


def test_convert_dxf_single_file_emits_one_storey(tmp_path):
    src = tmp_path / "in.dxf"
    out = tmp_path / "out.ifc"
    _write_minimal_dxf(src)

    convert_dxf(
        dxf_path=src,
        output_path=out,
        profile=load_default_profile(),
        preprocess_acis=False,
    )

    ifc = ifcopenshell.open(str(out))
    storeys = ifc.by_type("IfcBuildingStorey")
    assert len(storeys) == 1
    assert storeys[0].Name == "1.krs"
    assert storeys[0].Elevation == 0.0


def test_convert_dxf_with_floor_elevation_passes_through(tmp_path):
    src = tmp_path / "in.dxf"
    out = tmp_path / "out.ifc"
    _write_minimal_dxf(src)

    convert_dxf(
        dxf_path=src,
        output_path=out,
        profile=load_default_profile(),
        floor_elevation_mm=3500.0,
        preprocess_acis=False,
    )

    ifc = ifcopenshell.open(str(out))
    storey = ifc.by_type("IfcBuildingStorey")[0]
    assert storey.Elevation == 3500.0
```

- [ ] **Step 2: Run test**

Run: `.venv/Scripts/python -m pytest tests/test_orchestrator_convert_dxf_shim.py -v`
Expected: PASS (already works thanks to Task 3's shim wiring).

- [ ] **Step 3: Commit**

```bash
git add tests/test_orchestrator_convert_dxf_shim.py
git commit -m "test(orchestrator): single-file shim regression guard"
```

---

## Task 6 — Remove `Profile.storey_z_levels_mm`

**Files:**
- Modify: `src/dxf2ifc/profiles/schema.py` (remove the field and its validator)
- Modify: `src/dxf2ifc/profiles/default_kylmalaite.toml` (drop the line)
- Modify: `tests/test_profile_schema.py` (remove 6 storey-level tests)
- Verify: nothing else references `storey_z_levels_mm`

- [ ] **Step 1: Find references**

Run: `Grep` for `storey_z_levels_mm` in `src/` and `tests/`. The remaining references should be only in: schema, default profile TOML, schema tests, and any docs. The orchestrator no longer references it after Task 4.

- [ ] **Step 2: Remove from schema**

In `src/dxf2ifc/profiles/schema.py`:
- Delete the `storey_z_levels_mm: list[float] = Field(...)` line on `Profile`.
- Delete the `@model_validator(mode="after") _validate_storey_z_levels` method.

- [ ] **Step 3: Remove from default profile TOML**

Delete the line `storey_z_levels_mm = [0.0]` from `src/dxf2ifc/profiles/default_kylmalaite.toml`.

- [ ] **Step 4: Remove the now-stale schema tests**

Delete these 6 tests from `tests/test_profile_schema.py`:
- `test_profile_default_storey_levels_single_zero`
- `test_profile_accepts_three_storey_z_levels`
- `test_profile_rejects_descending_storey_levels`
- `test_profile_rejects_empty_storey_levels`
- `test_profile_rejects_storey_level_above_cap`
- `test_profile_rejects_negative_storey_level`

- [ ] **Step 5: Run all tests**

Run: `.venv/Scripts/python -m pytest -x -q`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add src/dxf2ifc/profiles/schema.py src/dxf2ifc/profiles/default_kylmalaite.toml tests/test_profile_schema.py
git commit -m "feat(profile)!: remove storey_z_levels_mm — GUI/CLI controls storeys per file"
```

(Note `!` after type — breaking change marker.)

---

## Task 7 — CLI `--floor` flag

**Files:**
- Modify: `src/dxf2ifc/cli.py`
- Create: `tests/test_cli_multi_floor.py`

- [ ] **Step 1: Write the failing tests**

```python
"""CLI multi-floor parsing and validation."""
from pathlib import Path

import pytest

from dxf2ifc.cli import build_parser, _parse_floor_arg


def test_parse_floor_path_only():
    fe = _parse_floor_arg("1krs.dwg", default_index=0)
    assert fe.path == Path("1krs.dwg")
    assert fe.floor_label == "1.krs"
    assert fe.elevation_mm == 0.0


def test_parse_floor_path_and_label():
    fe = _parse_floor_arg("kellari.dwg:kellari", default_index=2)
    assert fe.floor_label == "kellari"
    assert fe.elevation_mm == 0.0


def test_parse_floor_full():
    fe = _parse_floor_arg("2krs.dwg:2.krs:3500", default_index=1)
    assert fe.floor_label == "2.krs"
    assert fe.elevation_mm == 3500.0


def test_parse_floor_default_label_uses_index():
    fe = _parse_floor_arg("any.dwg", default_index=4)  # 0-based → "5.krs"
    assert fe.floor_label == "5.krs"


def test_parse_floor_rejects_non_numeric_elevation():
    with pytest.raises(ValueError):
        _parse_floor_arg("a.dwg:1.krs:huono", default_index=0)


def test_build_parser_accepts_repeatable_floor():
    parser = build_parser()
    args = parser.parse_args([
        "convert", "out.ifc",
        "--floor", "1krs.dwg:1.krs:0",
        "--floor", "2krs.dwg:2.krs:3500",
    ])
    assert args.floor == ["1krs.dwg:1.krs:0", "2krs.dwg:2.krs:3500"]
```

- [ ] **Step 2: Run, expect failures**

Run: `.venv/Scripts/python -m pytest tests/test_cli_multi_floor.py -v`
Expected: FAIL (missing `_parse_floor_arg` and `--floor`).

- [ ] **Step 3: Implement CLI changes**

In `src/dxf2ifc/cli.py`:

Add the parse helper:

```python
def _parse_floor_arg(value: str, *, default_index: int) -> "FileEntry":
    """Parse a ``--floor PATH[:LABEL[:ELEV_MM]]`` value into a FileEntry."""
    from dxf2ifc.core.types import FileEntry

    parts = value.split(":")
    if len(parts) > 3:
        raise ValueError(
            f"--floor expects PATH[:LABEL[:ELEV_MM]], got {value!r}"
        )
    path = Path(parts[0])
    label = parts[1] if len(parts) >= 2 and parts[1] else f"{default_index + 1}.krs"
    elev_str = parts[2] if len(parts) == 3 else "0"
    try:
        elev_mm = float(elev_str)
    except ValueError as exc:
        raise ValueError(f"--floor elevation must be a number, got {elev_str!r}") from exc
    return FileEntry(path=path, floor_label=label, elevation_mm=elev_mm)
```

Modify the `convert` subparser to make `input` optional and add `--floor` repeatable:

```python
    convert = subparsers.add_parser("convert", help="Convert DXF/DWG file(s) to IFC.")
    convert.add_argument(
        "input",
        type=Path,
        nargs="?",
        default=None,
        help=(
            "Single DXF/DWG input (legacy form). Mutually exclusive with --floor. "
            "DWG inputs are preconverted via accoreconsole + DXFOUT."
        ),
    )
    convert.add_argument("output", type=Path, help="Path for the IFC output file.")
    convert.add_argument(
        "--floor",
        action="append",
        default=[],
        metavar="PATH[:LABEL[:ELEV_MM]]",
        help=(
            "Multi-floor input. Repeatable: each occurrence adds one storey. "
            "LABEL defaults to '<N>.krs' (1-based by --floor order). "
            "ELEV_MM defaults to 0. Mutually exclusive with the positional INPUT."
        ),
    )
```

In `main(...)`, replace the convert branch's body with:

```python
    if args.command == "convert":
        profile = load_profile(args.profile) if args.profile else load_default_profile()
        if args.floor and args.input is not None:
            parser.error("--floor and positional INPUT are mutually exclusive")
        if not args.floor and args.input is None:
            parser.error("convert requires either a positional INPUT or one or more --floor flags")

        if args.floor:
            from dxf2ifc.core.ifc_writer import convert as convert_multi
            files = [_parse_floor_arg(v, default_index=i) for i, v in enumerate(args.floor)]
            convert_multi(
                files=files,
                output_path=args.output,
                profile=profile,
                schema=args.schema.upper(),
                energy_specs_path=args.energy_specs,
                magicad_ifc_path=args.magicad_ifc,
            )
        else:
            convert_dxf(
                dxf_path=args.input,
                output_path=args.output,
                profile=profile,
                schema=args.schema.upper(),
                energy_specs_path=args.energy_specs,
                floor_elevation_mm=args.floor_elevation,
                magicad_ifc_path=args.magicad_ifc,
            )
        print(f"Wrote {args.output}", file=sys.stderr)
        if args.validate:
            report = validate_ifc(args.output)
            print(report.summary, file=sys.stderr)
            for warning in report.warnings:
                print(f"WARNING: {warning.get('message', warning)}", file=sys.stderr)
            if report.errors:
                for error in report.errors:
                    print(f"ERROR: {error.get('message', error)}", file=sys.stderr)
                return 1
        return 0
```

- [ ] **Step 4: Run tests**

Run: `.venv/Scripts/python -m pytest tests/test_cli_multi_floor.py -v`
Expected: PASS.

Run: `.venv/Scripts/python -m pytest tests/ -k "cli" -v`
Expected: all PASS (existing CLI tests untouched).

- [ ] **Step 5: Commit**

```bash
git add src/dxf2ifc/cli.py tests/test_cli_multi_floor.py
git commit -m "feat(cli): --floor PATH[:LABEL[:ELEV_MM]] (repeatable) for multi-floor merge"
```

---

## Task 8 — GUI `file_panel` multi-row table

**Files:**
- Rewrite: `src/dxf2ifc/gui/file_panel.py`
- Rewrite: `tests/test_gui_file_panel.py`

- [ ] **Step 1: Capture current `tests/test_gui_file_panel.py` signature**

Read the existing tests to know which behaviours/attrs (e.g. `dialog.input_edit`) test_gui_main_module / test_gui_integration also depend on. Note: integration tests may need updating in Task 9.

- [ ] **Step 2: Write the new failing tests**

Rewrite `tests/test_gui_file_panel.py` to:

```python
"""Multi-row file panel: file/label/elevation table + add/remove."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
from unittest.mock import patch


def test_panel_starts_empty(qtbot):
    from dxf2ifc.gui.file_panel import FilePanel

    panel = FilePanel()
    qtbot.addWidget(panel)
    assert panel.files_table.rowCount() == 0
    assert not panel.convert_button.isEnabled()


def test_add_file_appends_row_with_defaults(qtbot, tmp_path):
    from dxf2ifc.gui.file_panel import FilePanel

    panel = FilePanel()
    qtbot.addWidget(panel)
    path = tmp_path / "1krs.dwg"
    path.write_bytes(b"")
    with patch(
        "dxf2ifc.gui.file_panel.QtWidgets.QFileDialog.getOpenFileNames",
        return_value=([str(path)], "AutoCAD-piirustukset (*.dxf *.dwg)"),
    ):
        panel.add_files_button.click()
    assert panel.files_table.rowCount() == 1
    assert panel.files_table.item(0, 0).text() == str(path)
    assert panel.files_table.item(0, 1).text() == "1.krs"
    assert panel.files_table.item(0, 2).text() == "0"


def test_add_multiple_files_auto_increments_label(qtbot, tmp_path):
    from dxf2ifc.gui.file_panel import FilePanel

    panel = FilePanel()
    qtbot.addWidget(panel)
    p1, p2, p3 = (tmp_path / f"{n}.dwg" for n in ("a", "b", "c"))
    for p in (p1, p2, p3):
        p.write_bytes(b"")
    with patch(
        "dxf2ifc.gui.file_panel.QtWidgets.QFileDialog.getOpenFileNames",
        return_value=([str(p1), str(p2), str(p3)], "*"),
    ):
        panel.add_files_button.click()
    labels = [panel.files_table.item(i, 1).text() for i in range(3)]
    assert labels == ["1.krs", "2.krs", "3.krs"]


def test_remove_button_drops_selected_row(qtbot, tmp_path):
    from dxf2ifc.gui.file_panel import FilePanel

    panel = FilePanel()
    qtbot.addWidget(panel)
    p1, p2 = (tmp_path / f"{n}.dwg" for n in ("a", "b"))
    for p in (p1, p2):
        p.write_bytes(b"")
    with patch(
        "dxf2ifc.gui.file_panel.QtWidgets.QFileDialog.getOpenFileNames",
        return_value=([str(p1), str(p2)], "*"),
    ):
        panel.add_files_button.click()
    panel.files_table.selectRow(0)
    panel.remove_button.click()
    assert panel.files_table.rowCount() == 1


def test_duplicate_label_disables_convert(qtbot, tmp_path):
    from PySide6 import QtWidgets

    from dxf2ifc.gui.file_panel import FilePanel

    panel = FilePanel()
    qtbot.addWidget(panel)
    panel.output_edit.setText(str(tmp_path / "out.ifc"))
    p1, p2 = (tmp_path / f"{n}.dwg" for n in ("a", "b"))
    for p in (p1, p2):
        p.write_bytes(b"")
    with patch(
        "dxf2ifc.gui.file_panel.QtWidgets.QFileDialog.getOpenFileNames",
        return_value=([str(p1), str(p2)], "*"),
    ):
        panel.add_files_button.click()
    # Force a duplicate label
    panel.files_table.setItem(1, 1, QtWidgets.QTableWidgetItem("1.krs"))
    assert not panel.convert_button.isEnabled()


def test_convert_requested_emits_file_entries(qtbot, tmp_path):
    from dxf2ifc.gui.file_panel import FilePanel

    panel = FilePanel()
    qtbot.addWidget(panel)
    panel.output_edit.setText(str(tmp_path / "out.ifc"))
    p1 = tmp_path / "1krs.dwg"
    p1.write_bytes(b"")
    with patch(
        "dxf2ifc.gui.file_panel.QtWidgets.QFileDialog.getOpenFileNames",
        return_value=([str(p1)], "*"),
    ):
        panel.add_files_button.click()

    received = []
    panel.convert_requested.connect(lambda payload: received.append(payload))
    panel.convert_button.click()
    assert len(received) == 1
    payload = received[0]
    assert payload["output_path"] == str(tmp_path / "out.ifc")
    assert len(payload["files"]) == 1
    fe = payload["files"][0]
    assert fe.path == Path(p1)
    assert fe.floor_label == "1.krs"
    assert fe.elevation_mm == 0.0
```

- [ ] **Step 3: Run tests, expect failures**

Run: `.venv/Scripts/python -m pytest tests/test_gui_file_panel.py -v`
Expected: FAIL (FilePanel does not have `files_table`, `add_files_button`, etc.).

- [ ] **Step 4: Rewrite `src/dxf2ifc/gui/file_panel.py`**

```python
"""Widget for picking DXF/DWG inputs (multi-floor) and requesting conversion."""

from __future__ import annotations

from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from dxf2ifc.core.types import FileEntry


class FilePanel(QtWidgets.QWidget):
    """Multi-row file table → emits `convert_requested(dict)` payload.

    Payload shape::

        {
            "files": list[FileEntry],
            "output_path": str,
            "energy_specs_path": str,   # "" if unset
            "magicad_ifc_path": str,    # "" if unset
        }
    """

    convert_requested = QtCore.Signal(dict)

    _HEADERS = ("Tiedosto", "Kerros", "Z (mm)")

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(10)

        # --- File table --------------------------------------------------
        self.files_table = QtWidgets.QTableWidget(0, 3)
        self.files_table.setHorizontalHeaderLabels(list(self._HEADERS))
        self.files_table.horizontalHeader().setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        self.files_table.horizontalHeader().setSectionResizeMode(
            1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        self.files_table.horizontalHeader().setSectionResizeMode(
            2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        self.files_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.files_table.verticalHeader().setVisible(False)
        layout.addWidget(self.files_table, 0, 0, 1, 3)

        # Add/Remove buttons
        toolbar = QtWidgets.QHBoxLayout()
        self.add_files_button = QtWidgets.QPushButton("Lisää tiedosto(t)…")
        self.add_files_button.setProperty("secondary", "true")
        self.add_files_button.clicked.connect(self._on_add_files)
        self.remove_button = QtWidgets.QPushButton("Poista")
        self.remove_button.setProperty("secondary", "true")
        self.remove_button.clicked.connect(self._on_remove)
        toolbar.addWidget(self.add_files_button)
        toolbar.addWidget(self.remove_button)
        toolbar.addStretch(1)
        layout.addLayout(toolbar, 1, 0, 1, 3)

        # --- Output IFC --------------------------------------------------
        layout.addWidget(self._caption("IFC output"), 2, 0)
        self.output_edit = QtWidgets.QLineEdit()
        self.output_edit.setPlaceholderText("Path to .ifc")
        layout.addWidget(self.output_edit, 2, 1)
        self.browse_output_button = QtWidgets.QPushButton("Browse…")
        self.browse_output_button.setProperty("secondary", "true")
        self.browse_output_button.clicked.connect(self._on_browse_output)
        layout.addWidget(self.browse_output_button, 2, 2)

        # --- Energy specs ------------------------------------------------
        layout.addWidget(self._caption("Energiateho-listasta"), 3, 0)
        self.energy_edit = QtWidgets.QLineEdit()
        self.energy_edit.setPlaceholderText(
            "Valinnainen .xlsx tai .csv jossa Koneikko, Laitetunnus + tehot"
        )
        layout.addWidget(self.energy_edit, 3, 1)
        self.browse_energy_button = QtWidgets.QPushButton("Browse…")
        self.browse_energy_button.setProperty("secondary", "true")
        self.browse_energy_button.clicked.connect(self._on_browse_energy)
        layout.addWidget(self.browse_energy_button, 3, 2)

        # --- MagiCAD IFC -------------------------------------------------
        layout.addWidget(self._caption("MagiCAD-IFC"), 4, 0)
        self.magicad_ifc_edit = QtWidgets.QLineEdit()
        self.magicad_ifc_edit.setPlaceholderText(
            "Valinnainen -MAGIIFCCD-tuotos (kollegan IFC mergetään master-IFC:hen)"
        )
        layout.addWidget(self.magicad_ifc_edit, 4, 1)
        self.browse_magicad_ifc_button = QtWidgets.QPushButton("Browse…")
        self.browse_magicad_ifc_button.setProperty("secondary", "true")
        self.browse_magicad_ifc_button.clicked.connect(self._on_browse_magicad_ifc)
        layout.addWidget(self.browse_magicad_ifc_button, 4, 2)

        # --- Convert button ----------------------------------------------
        self.convert_button = QtWidgets.QPushButton("Convert")
        self.convert_button.setProperty("primary", "true")
        self.convert_button.setEnabled(False)
        self.convert_button.clicked.connect(self._on_convert)
        layout.addWidget(self.convert_button, 5, 1, 1, 2)

        layout.setColumnStretch(1, 1)

        self.files_table.itemChanged.connect(self._refresh_convert_enabled)
        self.output_edit.textChanged.connect(self._refresh_convert_enabled)

    # -------------------------------------------------------------- helpers

    def _caption(self, text: str) -> QtWidgets.QLabel:
        label = QtWidgets.QLabel(text)
        label.setProperty("role", "caption")
        return label

    def _on_add_files(self) -> None:
        paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "Avaa DXF- tai DWG-tiedostot",
            "",
            "AutoCAD-piirustukset (*.dxf *.dwg);;DXF (*.dxf);;DWG (*.dwg);;All files (*)",
        )
        for path in paths:
            self._append_row(path)
        self._refresh_convert_enabled()

    def _append_row(self, path: str) -> None:
        row = self.files_table.rowCount()
        self.files_table.insertRow(row)
        # File path: read-only (the table edits label + Z only).
        path_item = QtWidgets.QTableWidgetItem(path)
        path_item.setFlags(path_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
        self.files_table.setItem(row, 0, path_item)
        self.files_table.setItem(row, 1, QtWidgets.QTableWidgetItem(f"{row + 1}.krs"))
        self.files_table.setItem(row, 2, QtWidgets.QTableWidgetItem("0"))

    def _on_remove(self) -> None:
        rows = sorted(
            {index.row() for index in self.files_table.selectedIndexes()},
            reverse=True,
        )
        for row in rows:
            self.files_table.removeRow(row)
        self._refresh_convert_enabled()

    def _on_browse_output(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save IFC", "", "IFC files (*.ifc)")
        if path:
            self.output_edit.setText(path)

    def _on_browse_energy(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Avaa energiateho-lista", "",
            "Excel & CSV (*.xlsx *.xlsm *.csv *.tsv);;All files (*)",
        )
        if path:
            self.energy_edit.setText(path)

    def _on_browse_magicad_ifc(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Avaa MagiCAD-IFC", "", "IFC-tiedostot (*.ifc);;All files (*)",
        )
        if path:
            self.magicad_ifc_edit.setText(path)

    def _collect_file_entries(self) -> list[FileEntry] | None:
        rows = self.files_table.rowCount()
        if rows == 0:
            return None
        entries: list[FileEntry] = []
        for row in range(rows):
            path_item = self.files_table.item(row, 0)
            label_item = self.files_table.item(row, 1)
            elev_item = self.files_table.item(row, 2)
            if path_item is None or label_item is None or elev_item is None:
                return None
            path = path_item.text().strip()
            label = label_item.text().strip()
            if not path or not label:
                return None
            try:
                elev = float(elev_item.text().strip() or "0")
            except ValueError:
                return None
            entries.append(FileEntry(path=Path(path), floor_label=label, elevation_mm=elev))
        labels_lower = [e.floor_label.lower() for e in entries]
        if len(set(labels_lower)) != len(labels_lower):
            return None
        return entries

    def _refresh_convert_enabled(self) -> None:
        entries = self._collect_file_entries()
        has_output = bool(self.output_edit.text().strip())
        self.convert_button.setEnabled(bool(entries) and has_output)

    def _on_convert(self) -> None:
        entries = self._collect_file_entries()
        if not entries:
            return
        self.convert_requested.emit({
            "files": entries,
            "output_path": self.output_edit.text(),
            "energy_specs_path": self.energy_edit.text(),
            "magicad_ifc_path": self.magicad_ifc_edit.text(),
        })


# Imported for downstream signal-typing helpers.
__all__ = ["FilePanel"]
_ = QtGui
```

- [ ] **Step 5: Run file_panel tests**

Run: `.venv/Scripts/python -m pytest tests/test_gui_file_panel.py -v`
Expected: PASS (6 tests).

- [ ] **Step 6: Commit**

```bash
git add src/dxf2ifc/gui/file_panel.py tests/test_gui_file_panel.py
git commit -m "feat(gui): multi-row file table replacing single-file + elevation checkbox"
```

---

## Task 9 — `convert_worker` + `main_window` wiring

**Files:**
- Modify: `src/dxf2ifc/gui/convert_worker.py`
- Modify: `src/dxf2ifc/gui/main_window.py`
- Modify: `tests/test_gui_convert_worker.py`
- Possibly: `tests/test_gui_integration.py`, `tests/test_gui_main_module.py` (broken by new signal shape)

- [ ] **Step 1: Read current `convert_worker.py` + `main_window.py` to identify call sites**

Read both files. Note where `convert_requested` is `connect()`-ed in `main_window.py` and what arguments the slot expects.

- [ ] **Step 2: Update `convert_worker.py`**

Replace the worker's `run(...)` signature and `_ConvertRunnable` to accept `files: list[FileEntry]` and call `convert(...)` instead of `convert_dxf(...)`:

```python
"""Background worker that wraps multi-floor convert() so the GUI thread stays responsive."""

from __future__ import annotations

from PySide6 import QtCore

from dxf2ifc.core.ifc_writer import convert
from dxf2ifc.core.types import FileEntry
from dxf2ifc.profiles.schema import Profile


class ConvertWorker(QtCore.QObject):
    finished = QtCore.Signal(str)
    failed = QtCore.Signal(str)
    report_ready = QtCore.Signal(object)
    progress = QtCore.Signal(str)

    def run(
        self,
        *,
        files: list[FileEntry],
        out: str,
        profile: Profile,
        validate: bool = False,
        energy_specs: str | None = None,
        magicad_ifc: str | None = None,
    ) -> None:
        runnable = _ConvertRunnable(
            self,
            files=files,
            out=out,
            profile=profile,
            validate=validate,
            energy_specs=energy_specs,
            magicad_ifc=magicad_ifc,
        )
        QtCore.QThreadPool.globalInstance().start(runnable)


class _ConvertRunnable(QtCore.QRunnable):
    def __init__(
        self,
        worker: ConvertWorker,
        *,
        files: list[FileEntry],
        out: str,
        profile: Profile,
        validate: bool,
        energy_specs: str | None,
        magicad_ifc: str | None,
    ) -> None:
        super().__init__()
        self._worker = worker
        self._files = files
        self._out = out
        self._profile = profile
        self._validate = validate
        self._energy_specs = energy_specs
        self._magicad_ifc = magicad_ifc

    def run(self) -> None:  # type: ignore[override]
        try:
            _, report = convert(
                files=self._files,
                output_path=self._out,
                profile=self._profile,
                validate=self._validate,
                progress=self._worker.progress.emit,
                energy_specs_path=self._energy_specs or None,
                magicad_ifc_path=self._magicad_ifc or None,
            )
        except Exception as exc:  # noqa: BLE001
            self._worker.failed.emit(f"{type(exc).__name__}: {exc}")
            return
        if report is not None:
            self._worker.report_ready.emit(report)
        self._worker.finished.emit(self._out)
```

- [ ] **Step 3: Update `main_window.py`**

Find the slot connected to `FilePanel.convert_requested`. It currently receives `(str, str, str, float, str)`. Change it to accept the new `dict` payload:

```python
def _on_convert_requested(self, payload: dict) -> None:
    self.worker.run(
        files=payload["files"],
        out=payload["output_path"],
        profile=self._current_profile(),
        energy_specs=payload["energy_specs_path"],
        magicad_ifc=payload["magicad_ifc_path"],
    )
```

(Look up the exact name of the slot in the existing code and adjust accordingly. Update the signal connection if the slot signature signature was decorated with `@QtCore.Slot(...)`.)

- [ ] **Step 4: Update `tests/test_gui_convert_worker.py`**

The existing test probably calls `worker.run(dxf=..., out=..., floor_elevation_mm=...)`. Change it to the new signature using `files=[FileEntry(...)]`. If the test has mocking around `convert_dxf`, patch `convert` instead.

- [ ] **Step 5: Update broken GUI integration tests**

Run: `.venv/Scripts/python -m pytest tests/test_gui_integration.py tests/test_gui_main_module.py -v`
For any test that broke because the FilePanel signal changed shape, update the test to construct the new payload dict.

- [ ] **Step 6: Run full GUI test suite**

Run: `.venv/Scripts/python -m pytest tests/test_gui_*.py -v`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add src/dxf2ifc/gui/convert_worker.py src/dxf2ifc/gui/main_window.py tests/test_gui_*.py
git commit -m "feat(gui): wire FilePanel multi-floor payload through worker to convert()"
```

---

## Task 10 — Final full-suite verification

- [ ] **Step 1: Run the whole test suite**

Run: `.venv/Scripts/python -m pytest -q`
Expected: all PASS (or all expected-PASS — note any pre-existing skipped tests).

- [ ] **Step 2: Smoke-test the GUI manually**

```
.venv/Scripts/python -m dxf2ifc.gui
```

1. Click "Lisää tiedosto(t)…", pick `~/OneDrive - RADIKA OY/Tiedostot/4001_1krs.dxf`.
2. Edit the row label to `1.krs` (or confirm auto-fill).
3. Click "Lisää tiedosto(t)…" again, pick `~/OneDrive - RADIKA OY/Tiedostot/Drawing2.dxf`.
4. Edit row 2 label to `2.krs`, Z to `3500`.
5. Set output to a tmp .ifc path.
6. Click Convert. Observe progress log: two file processing passes, then write.
7. Open the resulting .ifc in Solibri (or `ifcopenshell.open`). Confirm 2 IfcBuildingStorey with the right names and elevations, with elements under each.

Report observations in the commit message of the next step if anything needed adjusting.

- [ ] **Step 3: Smoke-test the CLI**

```
.venv/Scripts/python -m dxf2ifc convert out.ifc \
    --floor "C:\path\to\1krs.dxf:1.krs:0" \
    --floor "C:\path\to\2krs.dxf:2.krs:3500"
```

Confirm exit 0 and the IFC opens with 2 storeys.

---

## Task 11 — Documentation + version bump

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `PROGRESS.md`
- Modify: `CLAUDE.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `src/dxf2ifc/_version.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Update `_version.py` and `pyproject.toml`**

Set version to `0.2.0a22` in both.

- [ ] **Step 2: Update `CHANGELOG.md`**

Prepend at the top:

```markdown
## v0.2.0-alpha22 (2026-05-13)

### Breaking changes

- **Multi-floor merge** — single-file conversion replaced by multi-file
  workflow. Each input DWG/DXF becomes one IfcBuildingStorey. GUI uses a
  multi-row table (File / Floor label / Z mm); CLI uses repeatable
  `--floor PATH[:LABEL[:ELEV_MM]]`.
- `Profile.storey_z_levels_mm` field removed from profile TOML schema —
  the GUI/CLI now drives storey elevations.
- GUI "Lisää 1.krs absoluuttinen korko" checkbox and single elevation
  spinbox removed; set elevation per-floor in the table instead.

### Internal

- `orchestrator.convert(files: list[FileEntry], …)` is the new entry
  point. `convert_dxf(...)` is preserved as a single-file shim.
- `MappedEntity.storey_index` carries each entity's owning storey
  through the writer; `skeleton.resolve_storey` is no longer called by
  the orchestrator.
```

- [ ] **Step 3: Update `PROGRESS.md`**

Add a new "Current state" entry at the top of the Alpha-changes list:

```markdown
- **alpha22** (2026-05-13): **Multi-floor merge.** N DXF/DWG inputs → 1 IFC
  with N IfcBuildingStorey, one per file, each with user-supplied label
  and Z elevation. GUI: new file table. CLI: `--floor` repeatable.
  Breaking: `Profile.storey_z_levels_mm` removed; GUI elevation checkbox
  removed. Suunnitelma:
  [`docs/superpowers/specs/2026-05-13-multi-floor-merge-design.md`](docs/superpowers/specs/2026-05-13-multi-floor-merge-design.md).
```

Update the "Current state" heading version line.

- [ ] **Step 4: Update `README.md`**

Replace the "Käyttö" / GUI screenshots section's references to a single DXF input with the multi-floor flow (table, "Lisää tiedosto(t)…" button). Update the CLI example block to show `--floor` syntax. Bump the "Nykyinen versio" line.

- [ ] **Step 5: Update `CLAUDE.md`**

Update the pipeline diagram to show the per-file loop. Add a line under "Working rules": "Multi-floor input: N DWG → N storey. GUI ja CLI ajavat sisäisesti `convert(files=…)`. `convert_dxf` on yhden tiedoston shim."

- [ ] **Step 6: Update `docs/ARCHITECTURE.md`**

Pipeline diagram should reflect the per-file loop with the convergence point at skeleton build.

- [ ] **Step 7: Commit docs + version**

```bash
git add README.md CHANGELOG.md PROGRESS.md CLAUDE.md docs/ARCHITECTURE.md src/dxf2ifc/_version.py pyproject.toml
git commit -m "docs: alpha22 multi-floor merge — bump + changelog + readme"
```

- [ ] **Step 8: Hold publish**

Do NOT push or tag yet. Per user direction the release waits for a second concurrent update to land. When user says "publish", run `git push origin master` and let `.github/workflows/release.yml` build the installer.

---

## Self-review

After plan completion, against the spec:

- ✅ FileEntry dataclass — Task 1
- ✅ MappedEntity.storey_index — Task 1
- ✅ Skeleton storey_names — Task 2
- ✅ Per-file pipeline refactor — Task 3
- ✅ Multi-file convert() — Task 4
- ✅ convert_dxf shim — Task 3 + Task 5 regression test
- ✅ Profile.storey_z_levels_mm removal — Task 6
- ✅ CLI --floor — Task 7
- ✅ GUI multi-row table — Task 8
- ✅ Worker + main_window wiring — Task 9
- ✅ End-to-end smoke + IFC verification — Task 10
- ✅ Docs + version bump — Task 11
- ✅ Release hold — Task 11 Step 8

No "TBD". Each step has either concrete code or a verbatim command. Method names match across tasks (`convert`, `_process_one_file`, `_write_products`, `_storey_for`, `FileEntry`).
