# PROGRESS

**Current plan:** Plan A — Core CLI wall pipeline ✅ valmis (21/21).

**Current task:** Plan B kirjoittamatta. Seuraavaksi joko aloita Plan B:n kirjoittaminen `docs/superpowers/plans/`-kansioon (kattaa loput 10 elementtityyppiä: VS-väliseinät, AP/VP/YP-laatat, ovet, ikkunat, kylmäputket, viemäriputket, hyllyt, kaapelihyllyt, kylmäelementit, kylmälaitteet) tai aja manuaalisesti `python -m dxf2ifc convert <dxf> <out.ifc>` Solibri-tarkistusta varten.

**Seuraavaksi:** kirjoita `docs/superpowers/plans/2026-04-27-plan-b-full-element-set.md`. Käytä Plan A:n rakennetta (per-task: failing test → impl → pass → commit) ja kopioi sama pipeline-kaava kullekin uudelle ifc_type-haaralle. Arvio 30–40 tehtävää. Kun Plan B kirjoitettu, päivitä PROGRESS.md (Current task = Plan B Task 1) ja jatka TDD-rytmillä.

**Tämän session muutokset (Plan A loppuun):**
- Task 15 (`6c63c22`) — `WallExtrusion` + `line_to_wall_extrusion` (geometry.py).
- Task 16 (`05e8aca`) — `build_ifc_project_skeleton` + `write_ifc` (IFC 4, mm-yksiköt). Pudotettu `angle=`-kwarg `unit.assign_unit`-kutsusta koska ifcopenshell 0.8.x API ei hyväksy sitä.
- Task 17 (`6283cc6`) — `add_wall` (IfcExtrudedAreaSolid + spatial container) + `add_talo2000_classification` (IfcClassificationReference, IfcRelAssociatesClassification).
- Task 18 (`ea5a9a2`) — `convert_dxf` orchestrator (read_dxf → apply_profile → build skeleton → add walls → write).
- Task 19 (`3fd647b`) — argparse CLI + `__main__.py`. `python -m dxf2ifc convert input.dxf output.ifc [--profile p.toml]`.
- Task 20 (`3da2df0`) — integration test ajaa CLI:n subprocessina ja validoi IFC:n `ifcopenshell.validate.validate()`-kutsulla (ei ERROR-tason virheitä).
- Task 21 (`54140a5`) — `ruff check` clean, `ruff format` ajettu kaikkiin tiedostoihin, E402 korjattu test_ifc_writer.py:ssä. 41 testiä passed, 84 % coverage (CLI-moduuli mittaa 0 % subprocess-ajossa, mutta sen sisältö katetaan CLI-/integraatio-testeissä).

**Viimeisin tila:** Plan A 21/21 master-branchissa, viimeisin SHA `54140a5`. Remote `https://github.com/Mcrauli/dxf2ifc` synkassa. Kaikki 41 testiä passed, ruff clean.

**Kesken:** ei mitään. Plan A:n self-review checklist plan-tiedoston lopussa todettu suoritetuksi.

**Blokkerit:** ei.
