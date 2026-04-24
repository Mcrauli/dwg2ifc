# PROGRESS

> Authoritative volatile state for the dxf2ifc `next-task` routine.
> **Last synced:** 2026-04-24 (after commit `0ad79ca`)
>
> Update this file at the end of every task run. `README.md` is the
> user-facing status; this file is for the routine agent.

## Current task

**Task 14 — `apply_profile` mapper** (⏳ not started)

- Plan section: `docs/superpowers/plans/2026-04-24-plan-a-core-cli-wall-pipeline.md` → "Task 14: apply_profile mapper"
- First step: append the failing tests shown in plan Step 1 to `tests/test_mapper.py`, run pytest to confirm `ImportError: cannot import name 'apply_profile'`, then implement per plan Step 3.
- Files to touch: `src/dxf2ifc/core/mapper.py`, `tests/test_mapper.py`
- Commit subject (from plan): `feat(core): add apply_profile mapping DXF entities to MappedEntity`

## Blockers

None.

## Completed tasks

| # | Task | SHA |
|---|---|---|
| 1 | Install Python 3.12 + uv (environment, no commit) | — |
| 2 | Initialise pyproject.toml + dependencies | `4267ce6` |
| 3 | Create package skeleton | `b0d1689` |
| 4 | Set up tests package with conftest | `05d9ad8` |
| 5 | Point3D, LineGeometry, EntityRecord dataclasses | `c2c21aa` |
| 6 | MappedEntity dataclass | `2310b7d` |
| 7 | Profile + Rule pydantic schemas (IFC4-locked) | `ddc6b34` |
| 8 | Default profile TOML (wall rule only) | `f805097` |
| 9 | Profile loader (importlib.resources) | `78cf189` |
| 10 | simple_wall.dxf fixture | `bb0ee61` |
| 11–12 | dxf_reader.read_dxf + tests (combined commit) | `8ee5cd7` |
| 13 | mapper.layer_matches helper | `b077fd8` |

## Remaining tasks

- ⏳ 14 — `apply_profile` mapper
- ⏳ 15 — `line_to_wall_extrusion` (2D line → wall profile)
- ⏳ 16 — IFC project skeleton (`IfcProject` / `Site` / `Building` / `Storey`, mm units, IFC4)
- ⏳ 17 — `add_wall` + `add_talo2000_classification` (split candidate if ~90-min budget runs out)
- ⏳ 18 — `convert_dxf` end-to-end orchestrator
- ⏳ 19 — CLI (`dxf2ifc convert …`) + `__main__.py`
- ⏳ 20 — Integration test (CLI on `simple_wall.dxf`, validate with `ifcopenshell.validate`)
- ⏳ 21 — `ruff check` + `ruff format --check` + full `pytest` green gate

## Verification commands

Run these before every commit:

```
Set-Location $HOME\work\dxf2ifc
.venv\Scripts\pytest.exe
.venv\Scripts\ruff.exe check src tests
```

Both must pass.

## Notes for the routine

- Tasks 11 + 12 were landed in one commit (reader + tests together). Future tasks may likewise merge when a reader and its tests are the same change; the SHA column allows either granularity.
- `.venv/` is gitignored but must exist on the runner. If missing, recreate with `uv venv && uv pip install -e ".[dev]"` before starting the task.
- Direct pushes to `master` are allowed. If `git push` rejects, `git pull --rebase origin master` and retry. If rebase conflicts, abort and STOP — do not force-push.
- Writing Plans B–F is Lauri's call, not the routine's. When Task 21 passes, tag `v0.1.0-plan-a` and STOP.
