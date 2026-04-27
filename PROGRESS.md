# PROGRESS

**Current plan:** Plan B — Full element set (kirjoitettu, 50 tehtävää, master `083f8cd`).

**Current task:** Plan B Task 2 — lisää `extrusion_height` ja `pset_overrides`-kentät, ja validointi joka vaatii `block_name` jos `entity_kind=INSERT`.

**Mode:** A (implementointi).

**Seuraavaksi:** kirjoita `tests/test_profile_schema.py`:hen failing test joka (a) varmistaa että INSERT-sääntö ilman block_name nostaa ValidationError ja (b) että `extrusion_height` ja `pset_overrides` (dict[str, Any]) -kentät hyväksyvät arvot. Sitten päivitä `schema.py`:n Rule-malli + `model_validator(mode="after")`. Aja pytest, commit + push + PROGRESS.md → Task 3.

## Plan A status (21/21) ✅
- [x] Task 1–14 — scaffolding, types, profile loader, dxf reader, mapper (commit-historia)
- [x] Task 15 — `WallExtrusion` + `line_to_wall_extrusion` (`6c63c22`)
- [x] Task 16 — `build_ifc_project_skeleton` + `write_ifc` (`05e8aca`)
- [x] Task 17 — `add_wall` + `add_talo2000_classification` (`6283cc6`)
- [x] Task 18 — `convert_dxf` orchestrator (`ea5a9a2`)
- [x] Task 19 — argparse CLI + `__main__.py` (`3fd647b`)
- [x] Task 20 — integration test + `ifcopenshell.validate` (`3da2df0`)
- [x] Task 21 — ruff clean + 41 testiä passed, 84 % coverage (`54140a5`)

## Plan B status (1/50)

### Section 1: Profile-skeeman laajennus
- [x] Task 1: laajenna `profiles/schema.py` Rule-malliin `entity_kind` (LINE/POLYLINE/CIRCLE/INSERT) ja `block_name` (`faaac8c`)
- [ ] Task 2: lisää `extrusion_height` ja `pset_overrides`-kentät + INSERT-validointi
- [ ] Task 3: päivitä `profiles/loader.py` säilyttämään uudet kentät + `tests/test_profile_schema.py`
- [ ] Task 4: laajenna default TOML kommentoiduilla placeholder-säännöillä joka elementtityypille

### Section 2: VS / lasiväliseinät (1311 / 1312)
- [ ] Task 5: default-profiilin VS- ja lasiväliseinä-säännöt
- [ ] Task 6: failing test `tests/test_mapper.py` partition-säännöille
- [ ] Task 7: `ifc_writer.add_wall` + `predefined_type` -parametri
- [ ] Task 8: integraatiotesti VS-viivalla → IfcWall PARTITIONING 1311

### Section 3: Laatat AP / VP / YP (1221 / 1235 / 1236)
- [ ] Task 9: default-profiilin laattasäännöt
- [ ] Task 10: `dxf_reader.py` LWPOLYLINE-luku + `PolygonGeometry`-tyyppi
- [ ] Task 11: `polygon_to_slab_extrusion` testi + impl
- [ ] Task 12: `ifc_writer.add_slab` + classification
- [ ] Task 13: orchestrator dispatch slab-rule

### Section 4: Ovet (1243 / 1315 / 1316)
- [ ] Task 14: default-profiilin INSERT-ovisäännöt
- [ ] Task 15: `dxf_reader.py` INSERT-luku + `BlockInstance`-tyyppi
- [ ] Task 16: `door_block_to_box` testi + impl
- [ ] Task 17: `ifc_writer.add_door`
- [ ] Task 18: orchestrator dispatch + integraatiotesti OVI-ULKO

### Section 5: Ikkunat (1242)
- [ ] Task 19: default-profiilin IKKUNA-INSERT-sääntö
- [ ] Task 20: `tests/test_mapper.py` IKKUNA-mappaustesti
- [ ] Task 21: `ifc_writer.add_window`
- [ ] Task 22: orchestrator dispatch + integraatiotesti IKKUNA

### Section 6: Kylmäputket (21xx, IfcPipeSegment)
- [ ] Task 23: default-profiilin LT IMU / MT IMU / MT NESTE -säännöt
- [ ] Task 24: `line_to_pipe_segment` testi + impl
- [ ] Task 25: `ifc_writer.add_pipe_segment` + IfcPipeSegmentType
- [ ] Task 26: orchestrator dispatch + integraatiotesti LT IMU

### Section 7: Viemäriputket (21xx DRAINPIPE)
- [ ] Task 27: default-profiilin KYL-VIEMARI*-sääntö
- [ ] Task 28: `mapper.layer_matches` wildcard-suffix-tuki
- [ ] Task 29: `add_pipe_segment` predefined_type DRAINPIPE/REFRIGERATION
- [ ] Task 30: integraatiotesti KYL-VIEMARI-LATTIA

### Section 8: Varastointihyllyt (1331, IfcFurniture)
- [ ] Task 31: default-profiilin KYL-LEVYHYLLY/TIKASHYLLY/KLHYLLYV-säännöt
- [ ] Task 32: `block_to_furniture_box` testi + impl
- [ ] Task 33: `ifc_writer.add_furniture`
- [ ] Task 34: orchestrator dispatch + integraatiotesti KYL-LEVYHYLLY

### Section 9: Kaapelihyllyt (23xx)
- [ ] Task 35: default-profiilin KAAPELIHYLLY-LINE-sääntö
- [ ] Task 36: `line_to_cable_carrier` testi + impl
- [ ] Task 37: `ifc_writer.add_cable_carrier_segment` + IfcCableCarrierSegmentType CABLETRUNKINGSEGMENT
- [ ] Task 38: orchestrator dispatch + integraatiotesti KAAPELIHYLLY

### Section 10: Kylmähuone-elementit (1352, IfcBuildingElementProxy)
- [ ] Task 39: default-profiilin KYL-LEVY*/KYL-NURKKA*-säännöt
- [ ] Task 40: `panel_to_proxy_solid` testi + impl
- [ ] Task 41: `ifc_writer.add_building_element_proxy`
- [ ] Task 42: orchestrator dispatch + integraatiotesti KYL-LEVY

### Section 11: Kylmälaitteet (25xx)
- [ ] Task 43: default-profiilin HOYRYSTIN/LAUHDUTIN/KOMPRESSORI-INSERT-säännöt
- [ ] Task 44: `tests/test_mapper.py` kylmälaitemappaustesti
- [ ] Task 45: `ifc_writer.add_cooling_equipment` dispatcher (IfcEvaporator/IfcCondenser/IfcCompressor)
- [ ] Task 46: orchestrator dispatch + integraatiotesti HOYRYSTIN

### Section 12: Integraatio + lint
- [ ] Task 47: `tests/fixtures/full_kylmaelement.dxf` (kaikki section 2–11 elementtityypit)
- [ ] Task 48: `tests/test_integration_full.py` (kaikki Talo2000-koodit löytyvät IFC:stä)
- [ ] Task 49: ruff clean + ≥85 % coverage
- [ ] Task 50: README.md + CLAUDE.md status-päivitys (Plan B valmis)

**Viimeisin tila:** Plan A 21/21 valmis. Plan B kirjoitettu (50 tehtävää, master `083f8cd`). Mode A Task 1 on seuraava.

**Tämän session muutokset:**
- Plan B skeleton (`6eb66ce`).
- Sectionit 1–12 täytetty yksitellen (`daa6398` … `c9c83a7`).
- Globaali numerointi + CLAUDE.md status (`083f8cd`).
- Plan B Task 1: Rule-skeeman `entity_kind` + `block_name` -kentät (`faaac8c`). 44 testiä passed, ruff clean. `uv.lock` committoitu mukaan.

**Kesken:** Plan B Task 2–50 (49 jäljellä). User pyysi stop:in Task 2:n alettua mutta ennen toteutusta — Task 2 ei aloitettu, tila puhdas.

**Blokkerit:** ei.
