# PROGRESS

**Current plan:** Plan A — Core CLI wall pipeline.

**Current task:** Task 14 — `apply_profile` mapper.

**Seuraavaksi:** lue `docs/superpowers/plans/2026-04-24-plan-a-core-cli-wall-pipeline.md` → Task 14. Appendaa failing-testit tiedostoon `tests/test_mapper.py` (plan Step 1), aja `.venv\Scripts\pytest.exe tests/test_mapper.py` vahvistaaksesi `ImportError: cannot import name 'apply_profile'`, toteuta plan Step 3:n mukaan tiedostoon `src/dxf2ifc/core/mapper.py`, aja pytest uudelleen (odotus: 10 passed), committaa `feat(core): add apply_profile mapping DXF entities to MappedEntity`.

**Viimeisin tila:** Tasks 1–13 valmiit master-branchissa (viim. commit `3f54346` — PROGRESS.md promote). Task 13 SHA `b077fd8` (`mapper.layer_matches`). Remote `https://github.com/Mcrauli/dxf2ifc` synkassa.
