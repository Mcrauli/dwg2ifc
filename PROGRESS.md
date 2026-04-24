# PROGRESS

**Current plan:** Plan A — Core CLI wall pipeline.

**Current task:** Task 15 — `line_to_wall_extrusion` (2D line → wall profile).

**Seuraavaksi:** lue `docs/superpowers/plans/2026-04-24-plan-a-core-cli-wall-pipeline.md` → Task 15. Luo `tests/test_geometry.py` failing-testeillä plan Step 1:n mukaan, aja `.venv\Scripts\pytest.exe tests/test_geometry.py` vahvistaaksesi `ModuleNotFoundError: dxf2ifc.core.geometry`, toteuta plan Step 3 tiedostoon `src/dxf2ifc/core/geometry.py`, aja pytest uudelleen (odotus: plan Step 4:n mukainen määrä passed), committaa `feat(core): add geometry.line_to_wall_extrusion` (tarkka viesti plan Step 5:stä).

**Viimeisin tila:** Tasks 1–14 valmiit master-branchissa. Task 14 SHA `31adae3` (`apply_profile`). Remote `https://github.com/Mcrauli/dxf2ifc` synkassa.
