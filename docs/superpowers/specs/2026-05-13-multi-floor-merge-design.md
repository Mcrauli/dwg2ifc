# Multi-floor DWG merge — design

**Date**: 2026-05-13
**Status**: Approved (awaiting concurrent second update before publish)
**Scope**: dxf2ifc GUI + pipeline + CLI

## Goal

Allow a single dxf2ifc run to take **N input DXF/DWG files**, treat each as
**one IfcBuildingStorey**, and emit **one merged IFC**. Each storey gets a
user-supplied label (e.g. `"1.krs"`) and Z elevation (mm). Per-floor object
Z coordinates are added to the storey's elevation to land each object in
world space.

This replaces today's single-file pipeline with a list-of-files pipeline.
The single-file case becomes a list of length one.

## Out of scope

- **MagiCAD-IFC merge** (`--magicad-ifc`) is not adapted to per-floor in this
  iteration. Decision deferred. Existing single-IFC merge remains untouched
  at the orchestrator level but is not surfaced in the multi-floor GUI flow
  for now.
- **Drag-reorder of rows** in the GUI table — nice-to-have, deferred.

## User-facing behaviour

### GUI

The file panel becomes a multi-row table:

| Tiedosto | Kerros | Z (mm) |
|---|---|---|
| `…\4001_1krs.dwg` | `1.krs` | `0` |
| `…\4001_2krs.dwg` | `2.krs` | `3500` |
| `…\pohja.dwg` | `kellari` | `-3000` |

Operations:
- `[+ Lisää tiedosto(t)…]` opens `QFileDialog.getOpenFileNames` (multi-select,
  filter `*.dxf;*.dwg`). Each picked file appends a row; defaults populate
  the new row(s).
- Both **Kerros** and **Z** columns are editable inline (double-click).
- A row can be removed via a "Poista" button below the table or the
  Delete key when a row is selected.
- The previous controls `floor_elevation_enabled_checkbox` and
  `floor_elevation_edit` are removed.

Defaults for a newly-added row:
- **Kerros label**: `"<N>.krs"` where N is the 1-based row index.
- **Z (mm)**: `0`.

Validation (Convert button disabled when any of these fail):
- At least one row.
- All labels non-empty.
- No duplicate labels (case-insensitive after trim).

### CLI

```
# Single-file legacy form (unchanged):
python -m dxf2ifc convert input.dxf output.ifc

# Multi-floor:
python -m dxf2ifc convert output.ifc \
    --floor 1krs.dwg:1.krs:0 \
    --floor 2krs.dwg:2.krs:3500 \
    --floor pohja.dwg:kellari:-3000
```

`--floor` value is `PATH[:LABEL[:ELEV_MM]]`. Label defaults to `"<N>.krs"`,
elevation defaults to `0`. Mixing positional `input.dxf` with `--floor`
flags is an error.

`--energy-specs`, `--magicad-ifc`, `--profile`, `--name`, `--schema` remain
project-level flags applied once.

## Z model

For every mapped entity in floor F:
```
world_Z(object) = F.elevation_mm + dxf_object.Z
```
This is the same offset logic as today, applied per-storey instead of
project-wide. Two consequences:

1. **All floors at Z=0 ⇒ DXF Z coordinates pass through unchanged.** This
   replaces today's "checkbox off" mode. AutoCAD drawings that already
   encode absolute Z (e.g. 2.krs objects drawn at Z=3500) just work.
2. **Per-floor offset** is added by mutating each `MappedEntity.geometry`
   before the IFC builders consume it (same approach as today's
   `_apply_floor_elevation_offset`). Storey `Elevation` is set to the same
   `F.elevation_mm` so the storey label and element placements agree.

## Architecture

### Data flow

```
GUI (table rows) ─┐
                  ├──► list[FileEntry(path, floor_label, elevation_mm)]
CLI (--floor)  ──┘
                  ↓
        ┌─────────────────────────────────────────────┐
        │ for each FileEntry:                          │
        │   preprocessing.run_accoreconsole(path)      │
        │   dwg_preconvert.preconvert(path)  (if .dwg) │
        │   dxf_reader.read_dxf(path) → records        │
        │   mapper.apply_profile(records) → mapped     │
        │   _apply_floor_elevation_offset(mapped, dz)  │
        │   for m in mapped: m.storey_index = floor_i  │
        └─────────────────────────────────────────────┘
                  ↓
        ┌─────────────────────────────────────────────┐
        │ build_ifc_project_skeleton(                  │
        │   storey_names=[fe.floor_label for fe in fs],│
        │   storey_z_levels_mm=[fe.elevation_mm …]     │
        │ )                                             │
        └─────────────────────────────────────────────┘
                  ↓
        ┌─────────────────────────────────────────────┐
        │ for entry in all_mapped:                     │
        │   storey = skeleton.storeys[entry.storey_index]
        │   builders.add_*(entry, storey)              │
        └─────────────────────────────────────────────┘
                  ↓
              OUTPUT.ifc
```

### New types

```python
# core/types.py
@dataclass(frozen=True)
class FileEntry:
    path: Path
    floor_label: str          # "1.krs", "kellari", "IV-konehuone"
    elevation_mm: float       # Z added to every object Z in this file
```

```python
# core/mapper.py (existing MappedEntity gains a field)
@dataclass
class MappedEntity:
    ...                       # existing fields
    storey_index: int = 0     # 0-based index into skeleton.storeys
```

### Modified functions

- `orchestrator.convert_dxf(...)` is kept as a shim that delegates to a
  new entrypoint:
  - New entrypoint `orchestrator.convert(files: list[FileEntry], output, …)`
    drives the per-file loop and one-pass writer.
  - Shim signature `convert_dxf(input_path, output_path, …,
    floor_elevation_mm=0.0)` builds a one-entry `FileEntry`
    (`floor_label="1.krs"`, `elevation_mm=floor_elevation_mm`) and calls
    `convert`. Used by existing single-file tests so they keep passing
    without edits.
- `skeleton.build_ifc_project_skeleton(...)` gains
  `storey_names: list[str] | None = None`. When provided, names a storey
  per entry; falls back to `"Kerros N"` when None.
- `skeleton.resolve_storey(storeys, z_mm)` becomes unused by the
  orchestrator (per-file tagging supplies the index directly). Kept for
  one release marked deprecated, then removed. Z-based resolution had no
  remaining caller and risked mis-assigning multi-Z entities.

### Removed

- `profiles.schema.Profile.storey_z_levels_mm` — removed from schema and
  default TOML. GUI is the sole source.
- `gui.file_panel.floor_elevation_enabled_checkbox` and
  `floor_elevation_edit` spinbox — replaced by the per-row Z column.

## Storey IFC mapping

For each `FileEntry` at index `i` (0-based):

| IFC field | Value |
|---|---|
| `IfcBuildingStorey.Name` | `floor_label` (e.g. `"1.krs"`) |
| `IfcBuildingStorey.Elevation` | `elevation_mm` |
| `IfcBuildingStorey.ObjectPlacement` | local placement at `(0, 0, elevation_mm)` relative to `IfcBuilding` |

Aggregation chain unchanged: `IfcProject → IfcSite → IfcBuilding →
IfcBuildingStorey[*]` via `IfcRelAggregates`. Products are linked into the
storey via `IfcRelContainedInSpatialStructure` (existing builders'
behaviour). This is what makes Solibri's model tree show the floors
correctly.

## Validation rules

| Rule | Where enforced | Failure mode |
|---|---|---|
| ≥1 file | GUI + CLI | Convert button disabled / CLI exits 2 |
| Floor labels non-empty | GUI + CLI | Convert button disabled / CLI exits 2 |
| Floor labels unique (case-insensitive) | GUI + CLI | Convert button disabled / CLI exits 2 |
| `elevation_mm` ∈ [-100_000, 100_000] | GUI spinbox + CLI parse | GUI clamps; CLI exits 2 |
| File exists & readable | CLI + worker | CLI exits 2; worker emits error signal |

## Testing

New tests (additions, no existing tests removed):

1. **`tests/test_multi_floor_pipeline.py`** — 2 DXF files → 1 IFC with
   2 storeys at correct elevations; objects from each file land at the
   right world Z; storey-element aggregation is intact.
2. **`tests/test_gui_file_panel.py`** (extend) — table accepts add/remove/
   edit; defaults populate; duplicate-label disables Convert.
3. **`tests/test_cli_multi_floor.py`** — `--floor` repeatable; parses
   `path:label:elev` and `path:label` and `path`; mixing positional and
   `--floor` errors.
4. **`tests/test_skeleton.py`** (extend) — `storey_names` argument names
   storeys correctly; defaults to "Kerros N" when omitted.
5. **`tests/test_orchestrator_convert_dxf_shim.py`** — single-file
   legacy entrypoint still works with default `floor_label="1.krs"`,
   `elevation_mm=0.0`.

## Backward compatibility

- `convert_dxf(input, output, …)` keeps working — shim wraps the single
  file into a one-entry list.
- TOML profiles using `storey_z_levels_mm` will fail validation after
  the change. The bundled `default_kylmalaite.toml` is updated in the
  same commit. Users with custom profiles must delete the field.
  (Acceptable: this is a personal project; the breaking change is
  documented in `CHANGELOG.md` and surfaces a clear validation error.)

## Documentation updates (Definition of Done)

- `README.md` — replace single-file GUI/CLI screenshots/snippets with
  multi-floor flow.
- `CLAUDE.md` — pipeline diagram, the storey-naming rule.
- `docs/ARCHITECTURE.md` — pipeline section reflects per-file loop.
- `PROGRESS.md` — new "Current state" line under alpha22 (or next).
- `CHANGELOG.md` — breaking change note (profile schema, GUI controls
  replaced).

## Release timing

User has a second concurrent update coming. Build this branch to ready
state and pause publishing the release until the second change is also
in. Both ship as one alpha bump.
