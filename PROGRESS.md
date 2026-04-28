# PROGRESS

**Current plan:** Plan F (kirjoittamatta) — Spec verifiointi Solibrissa.

**Current task:** Plan F Task 1 — `src/dxf2ifc/core/quality.py` `validate_ifc(path) -> ValidationReport` -wrapper + failing-testi.

**Mode:** A.

**Seuraavaksi:** Lue plan-tiedostosta Task 1:n osio (`grep -nA 5 "Task 1:"`). TDD: failing-testi `tests/test_quality.py` joka antaa Plan B:n full-fixture-IFC:n ja odottaa `len(report.errors) == 0`. Toteuta `validate_ifc(path) -> ValidationReport` joka kutsuu `ifcopenshell.validate.validate(file, json=True, return_json=True)` ja palauttaa structured-tuloksen.

## Bugfix kierros (löydetty GUI-testissä 2026-04-28, ennen Plan E jatkoa)

Lauri testasi GUI:n paikallisesti ja löysi 3 bugia. Korjataan TDD:llä per task ennen Plan E Task 11:n jatkoa (PAT on päivitetty Workflow-scopella, mutta bugifx tehdään ensin).

- [x] **Bugfix 1** — `add_furniture` polygon-tuki: kun KYL-LEVYHYLLY/KYL-TIKASHYLLY on piirretty closed polylinena (PolygonGeometry), `add_furniture` heittää `TypeError: add_furniture expects BlockInstance, got PolygonGeometry`. Korjaus: laske bbox + extrude box, palauta IfcFurniture; jos polygon on degeneroitu (alle 50mm sivu), nosta selkeä virhe. Tiedostot: `src/dxf2ifc/core/ifc_writer.py`, `tests/test_ifc_writer.py`. (`8e7c9c8`)

- [x] **Bugfix 2** — Profiili load + persistointi GUI:ssa: ProfileEditorDialog tukee vain Save:n, ei Load:ia. Lisäksi GUI ei muista viimeksi käytettyä TOML:ia sessioiden välillä. Korjaus: a) lisää "Load profile..." -nappi ProfileEditorDialogiin (avaa file picker → load_profile(path) → täyttää rules-taulun); b) laajenna RecentFilesStore tukemaan "last_profile_path" + lataa appin käynnistyksessä jos olemassa. Tiedostot: `src/dxf2ifc/gui/profile_editor.py`, `src/dxf2ifc/gui/main_window.py`, `src/dxf2ifc/gui/recent_files.py`, vastaavat testit. (`4955ac2` + `9fe0395`)

- [x] **Bugfix 3** — Preview & log -paneeli kytkemättä: oikean laidan paneeli on tyhjä DXF:n latauksen ja Convert:in jälkeen. Korjaus: a) DXF-latauksessa näytä yhteenveto (entity-määrä per layer, kokonais-bbox, units); b) Convert-vaiheessa logaa per-layer-mappauksia ja valmistus/virhe; käytä JetBrains Mono -fonttia, värikoodit per status. Tiedostot: `src/dxf2ifc/gui/preview_log.py` (uusi widget), `src/dxf2ifc/gui/main_window.py` (kytkentä), vastaavat testit. (`52a5695`)

✅ Bugfix kierros valmis (1+2+3, `8e7c9c8` + `4955ac2` + `9fe0395` + `52a5695`). 230 testiä passed, ruff puhdas omalle koodille (build/version_info.py + tests/test_spec_file.py F821:t ovat pre-existing PyInstaller-DSL-poikkeuksia). Plan E Task 11 voi alkaa.

## Bugfix kierros 2 (löydetty Solibri-testissä 2026-04-28, ennen Plan H:ta)

Lauri testasi 4001_1krs.dxf:n GUI:lla ja näki 3 lisäongelmaa: 14 hyllystä vain 1 näkyy 3D:ssä, AR-prefix-layerit (xref-format "AR1241_US") eivät matchaa profiilin sääntöihin, default-profiili kattaa pelkästään KYL-* layereitä — sun real-world DXF:llä on 77 layeria mukaan lukien AR1241_US/AR1311_VS/AR1242_IKKUNA jne. joilla on Talo2000-koodit jo nimessä.

- [ ] **Bugfix 4** — `add_furniture` polygon-geometria väärin: 14 KYL-LEVYHYLLY/TIKASHYLLY-entiteettiä luodaan IFC:hen mutta vain 1 näkyy 3D:ssä Solibrissa. Bugfix 1 hoiti TypeErrorin mutta bbox/placement edelleen rikki — entiteetit menevät päällekkäin (0,0,0)-pisteeseen tai tulee degeneroituja. Korjaus: tutki LWPOLYLINE-polygonin world-coord-vertexien luenta, varmista että jokainen IfcFurniture saa oman placementin polygonin keskipisteen mukaan. Tiedostot: `src/dxf2ifc/core/ifc_writer.py` add_furniture, `src/dxf2ifc/core/geometry.py` (bbox-helper jos olemassa), `tests/test_ifc_writer.py`.

- [ ] **Bugfix 5** — Profile pattern matching ei tue xref-prefixiä: AutoCAD-DXF:t käyttävät usein layer-nimissä xref-prefixiä `<xref>|<layername>` (esim. `KCM Kauhajoki...|AR1241_US`). Nykyiset säännöt matchaavat vain täydellistä nimeä, joten oikeat layerit jäävät mappamatta. Korjaus: laajenna `mapper.layer_matches`-funktiota sallimaan suffix-match jos layer-nimi sisältää `|`-merkin (split + ota viimeinen pala vertailuun). Tiedostot: `src/dxf2ifc/core/mapper.py`, `tests/test_mapper.py`.

- [ ] **Bugfix 6** — Default-profiilin laajennus ARK-layereille: lisää säännöt yleisille AutoCAD-arkkitehtilayer-nimille jotka käyttävät Talo2000-koodi-prefixiä:
  - `AR1241_US` → IfcWall STANDARD, Talo2000 1241
  - `AR1242_IKKUNA` → IfcWindow, Talo2000 1242
  - `AR1245_LASIUS` → IfcWall STANDARD (lasi-US)
  - `AR1311_VS` → IfcWall PARTITIONING, Talo2000 1311
  - `AR1233_PILARI` → IfcColumn
  - `AR1314_KAIDE` → IfcRailing
  - `AR1317_TILAPORTAAT` → IfcStair
  - `AR1331_KIINTO` → IfcFurniture, Talo2000 1331
  - K-arkkitehtuuriset: `K-OVET` → IfcDoor, `K-SEINÄT_VÄLISEINÄT` → IfcWall PARTITIONING, `K-KALUSTEET`/`K-KIINTOKALUSTEET`/`K-RST-KALUSTEET` → IfcFurniture, `K-VALAISTUS` → IfcLightFixture
  - **HUOM:** KYL-* layerit (höyrystimet/hyllyt/laitteet) säilyvät nykyisellä mapping:lla kunnes Plan H toteutuu — Plan H vaihtaa nämä RAVA-koodeihin (LVI-TUOTEOSA + Talotekniikka-tuoteosa), siihen asti pidetään Talo2000-luokitus.
  Tiedostot: `src/dxf2ifc/profiles/default_kylmalaite_talo2000.toml`, `tests/test_default_profile.py`.

Bugfix kierros 2 ajoitus: kun Plan F valmistuu, ennen Plan H MODE B:tä. Päivitä Current plan + Current task, kun Plan F:n PLAN-LOPPUPISTE saavutettu.

## Plan A status (21/21) ✅
- [x] Task 1–14 — scaffolding, types, profile loader, dxf reader, mapper (commit-historia)
- [x] Task 15 — `WallExtrusion` + `line_to_wall_extrusion` (`6c63c22`)
- [x] Task 16 — `build_ifc_project_skeleton` + `write_ifc` (`05e8aca`)
- [x] Task 17 — `add_wall` + `add_talo2000_classification` (`6283cc6`)
- [x] Task 18 — `convert_dxf` orchestrator (`ea5a9a2`)
- [x] Task 19 — argparse CLI + `__main__.py` (`3fd647b`)
- [x] Task 20 — integration test + `ifcopenshell.validate` (`3da2df0`)
- [x] Task 21 — ruff clean + 41 testiä passed, 84 % coverage (`54140a5`)

## Plan B status (50/50) ✅

### Section 1: Profile-skeeman laajennus ✅
- [x] Task 1: laajenna `profiles/schema.py` Rule-malliin `entity_kind` (LINE/POLYLINE/CIRCLE/INSERT) ja `block_name` (`faaac8c`)
- [x] Task 2: lisää `extrusion_height` ja `pset_overrides`-kentät + INSERT-validointi (`29f01e4`)
- [x] Task 3: päivitä `profiles/loader.py` säilyttämään uudet kentät + `tests/test_profile_schema.py` (`a8cbe50`)
- [x] Task 4: laajenna default TOML kommentoiduilla placeholder-säännöillä joka elementtityypille (`35c18f6`)

### Section 2: VS / lasiväliseinät (1311 / 1312) ✅
- [x] Task 5: default-profiilin VS- ja lasiväliseinä-säännöt (`97ab1b0`)
- [x] Task 6: failing test `tests/test_mapper.py` partition-säännöille (`cb77e9c`)
- [x] Task 7: `ifc_writer.add_wall` + `predefined_type` -parametri (`b101565`)
- [x] Task 8: integraatiotesti VS-viivalla → IfcWall PARTITIONING 1311 (`f051083`)

### Section 3: Laatat AP / VP / YP (1221 / 1235 / 1236) ✅
- [x] Task 9: default-profiilin laattasäännöt (`62f0f2e`)
- [x] Task 10: `dxf_reader.py` LWPOLYLINE-luku + `PolygonGeometry`-tyyppi (`5d10e66`)
- [x] Task 11: `polygon_to_slab_extrusion` testi + impl (`88517c7`)
- [x] Task 12: `ifc_writer.add_slab` + classification (`3d9e15f`)
- [x] Task 13: orchestrator dispatch slab-rule (`0c13013`)

### Section 4: Ovet (1243 / 1315 / 1316)
- [x] Task 14: default-profiilin INSERT-ovisäännöt (`36c5c51`)
- [x] Task 15: `dxf_reader.py` INSERT-luku + `BlockInstance`-tyyppi (`6427278`)
- [x] Task 16: `door_block_to_box` testi + impl (`efd9f9a`)
- [x] Task 17: `ifc_writer.add_door` (`4848061`)
- [x] Task 18: orchestrator dispatch + integraatiotesti OVI-ULKO (`813e4a6`)

### Section 5: Ikkunat (1242)
- [x] Task 19: default-profiilin IKKUNA-INSERT-sääntö (`d5451df`)
- [x] Task 20: `tests/test_mapper.py` IKKUNA-mappaustesti (`2902de2`)
- [x] Task 21: `ifc_writer.add_window` (`4488a48`)
- [x] Task 22: orchestrator dispatch + integraatiotesti IKKUNA (`5db11be`)

### Section 6: Kylmäputket (21xx, IfcPipeSegment)
- [x] Task 23: default-profiilin LT IMU / MT IMU / MT NESTE -säännöt (`5db22b1`)
- [x] Task 24: `line_to_pipe_segment` testi + impl (`9f1a51c`)
- [x] Task 25: `ifc_writer.add_pipe_segment` + IfcPipeSegmentType (`b5ff242`)
- [x] Task 26: orchestrator dispatch + integraatiotesti LT IMU (`770978f`)

### Section 7: Viemäriputket (21xx DRAINPIPE)
- [x] Task 27: default-profiilin KYL-VIEMARI*-sääntö (`7cf669f`)
- [x] Task 28: `mapper.layer_matches` wildcard-suffix-tuki (`8904ce1`)
- [x] Task 29: `add_pipe_segment` predefined_type DRAINPIPE/REFRIGERATION (`1bc2082`)
- [x] Task 30: integraatiotesti KYL-VIEMARI-LATTIA (`a07f315`)

### Section 8: Varastointihyllyt (1331, IfcFurniture)
- [x] Task 31: default-profiilin KYL-LEVYHYLLY/TIKASHYLLY/KLHYLLYV-säännöt (`8d5b662`)
- [x] Task 32: `block_to_furniture_box` testi + impl (`fcca98e`)
- [x] Task 33: `ifc_writer.add_furniture` (`17a7358`)
- [x] Task 34: orchestrator dispatch + integraatiotesti KYL-LEVYHYLLY (`05c8f43`)

### Section 9: Kaapelihyllyt (23xx)
- [x] Task 35: default-profiilin KAAPELIHYLLY-LINE-sääntö (`e3af094`)
- [x] Task 36: `line_to_cable_carrier` testi + impl (`8dda18e`)
- [x] Task 37: `ifc_writer.add_cable_carrier_segment` + IfcCableCarrierSegmentType CABLETRUNKINGSEGMENT (`b2203f6`)
- [x] Task 38: orchestrator dispatch + integraatiotesti KAAPELIHYLLY (`ea1d99b`)

### Section 10: Kylmähuone-elementit (1352, IfcBuildingElementProxy)
- [x] Task 39: default-profiilin KYL-LEVY*/KYL-NURKKA*-säännöt (`9fdd6c4`)
- [x] Task 40: `panel_to_proxy_solid` testi + impl (`02077bd`)
- [x] Task 41: `ifc_writer.add_building_element_proxy` (`5fc61c6`)
- [x] Task 42: orchestrator dispatch + integraatiotesti KYL-LEVY (`be47f57`)

### Section 11: Kylmälaitteet (25xx)
- [x] Task 43: default-profiilin HOYRYSTIN/LAUHDUTIN/KOMPRESSORI-INSERT-säännöt (`ddb872f`)
- [x] Task 44: `tests/test_mapper.py` kylmälaitemappaustesti (`c4fce3e`)
- [x] Task 45: `ifc_writer.add_cooling_equipment` dispatcher (IfcEvaporator/IfcCondenser/IfcCompressor) (`e0e2c25`)
- [x] Task 46: orchestrator dispatch + integraatiotesti HOYRYSTIN (`1ba3a65`)

### Section 12: Integraatio + lint
- [x] Task 47: `tests/fixtures/full_kylmaelement.dxf` (kaikki section 2–11 elementtityypit) (`58ac2e4`)
- [x] Task 48: `tests/test_integration_full.py` (kaikki Talo2000-koodit löytyvät IFC:stä) (`536fa50`)
- [x] Task 49: ruff clean + ≥85 % coverage (`cab7ea7`, 143 passed, 91 %)
- [x] Task 50: README.md + CLAUDE.md status-päivitys (Plan B valmis) (`2494841`)

## Plan D status (25/25) ✅

### Section 1: Bootstrap & dependencies
- [x] Task 1: PySide6 + pytest-qt deps + smoke import (`10d50c2`)
- [x] Task 2: gui/app.py `run()` + placeholder QMainWindow + qtbot offscreen testi (`f87b09e`)
- [x] Task 3: `dxf2ifc-gui` console-script + `gui/__main__.py` (`ce1cba8`)

### Section 2: Brand assets
- [x] Task 4: Inter / Space Grotesk / JetBrains Mono fontit + LICENSES (`f3f5116`)
- [x] Task 5: `gui/style.qss` värit + typografia + valid-style testi (`4155720`)
- [x] Task 6: `gui/theme.py` `apply_theme(app)` + font registration testi (`dd6387a`)

### Section 3: MainWindow + layout
- [x] Task 7: `MainWindow` (otsikkorivi + QSplitter + QStatusBar) (`6275bc6`)
- [x] Task 8: `set_status(text, level)` info/success/error + QSS (`3f045d9`)
- [x] Task 9: menubar (Open DXF, Quit, About) (`f0bcd48`)

### Section 4: Convert flow
- [x] Task 10: `FilePanel` (DXF input + IFC output + Convert) (`e7935d3`)
- [x] Task 11: `ConvertWorker(QObject)` taustasäikeessä + signaalit (`8216c0b`)
- [x] Task 12: kytke Convert-nappi + statusbar-päivitys (`ff218ca`)
- [x] Task 13: integraatiotesti simple_wall.dxf → IFC GUI:n kautta (`9e96b6f`)

### Section 5: Layer preview
- [x] Task 14: `dxf_reader.list_layers(dxf_path)` (`205f4de`)
- [x] Task 15: `LayerTable` widget (Layer/IFC/Talo2000/System) (`6633e6e`)
- [x] Task 16: kytke LayerTable MainWindow:n vasempaan paneeliin (`5d6ed4a`)

### Section 6: Profile editor
- [x] Task 17: `profiles/loader.dump_profile(profile, path)` round-trip (`0e96db4`)
- [x] Task 18: `ProfileEditorDialog` rules-listalla + Add/Edit/Remove/Save (`de6d9ad`)
- [x] Task 19: `RuleEditDialog` lomake + pydantic-validointi (`f77acb1`)
- [x] Task 20: kytke menubariin + end-to-end custom-rule testi (`1e7f38f`)

### Section 7: Polish + packaging hooks
- [x] Task 21: `gui/about.py` show_about (`13e882d`)
- [x] Task 22: `gui/recent_files.py` QSettings:n kautta + Open recent (`54adf38`)
- [x] Task 23: pytest-qt config + offscreen QPA + shared QApplication (`cb5e14a`)
- [x] Task 24: README GUI-osio + docs/screenshots/.gitkeep placeholder (`b4141f9`)
- [x] Task 25: plan-loppupiste — 200 passed, coverage 89 %, ruff clean, README/CLAUDE.md status (`011bd5e`)

## Plan F status (0/16)

### Section 1: Automaattinen ifcopenshell.validate -gate
- [ ] Task 1: src/dxf2ifc/core/quality.py validate_ifc(path) wrapper + tests/test_quality.py
- [ ] Task 2: validate_ifc raportoi YTV-spesifit Talo2000-luokittelutarkistukset (warnings)
- [ ] Task 3: CLI-flag `dxf2ifc convert --validate` (exit 1 jos errors)
- [ ] Task 4: convert_dxf(..., validate: bool) palauttaa (IfcFile, ValidationReport | None) + GUI-näyttö

### Section 2: Solibri rule-set ja referenssimallit
- [ ] Task 5: tools/solibri/dxf2ifc.bcfzip BCF 2.1 rule-set (Talo2000 + YTV)
- [ ] Task 6: tests/fixtures/solibri_reference_full.ifc baseline-IFC
- [ ] Task 7: docs/solibri-rules.md sääntöjen suomenkielinen kuvaus

### Section 3: solibri-cli runner + raportin parsija
- [ ] Task 8: tools/solibri/verify.py Solibri.exe-CLI-wrapper (subprocess)
- [ ] Task 9: tools/solibri/parse_report.py XML→RuleResult dict (lxml)
- [ ] Task 10: `python -m dxf2ifc.tools.solibri verify` CLI-entry

### Section 4: Snapshot-raportit + diffaus
- [ ] Task 11: tests/snapshots/solibri/full_kylmaelement.json baseline
- [ ] Task 12: tools/solibri/diff_snapshot.py uusi-vs-baseline diffaus
- [ ] Task 13: pytest @solibri-marker (skipautuu jos Solibri.exe ei PATH:ssa)

### Section 5: CI-integraatio + dokumentaatio + plan-loppupiste
- [ ] Task 14: build.yml linux-jobissa pytest tests/test_quality.py
- [ ] Task 15: docs/quality-gates.md (auto + manuaali two-tier prosessi)
- [ ] Task 16: plan-loppupiste — pytest + coverage + ruff + status-päivitys

## Plan E status (23/23) ✅

### Section 1: PyInstaller bootstrap ✅
- [x] Task 1: pyinstaller>=6.10 dev-extraan + smoke import test (`22875d0`)
- [x] Task 2: build/dxf2ifc.spec base + tests/test_spec_file.py (`23179ec`)
- [x] Task 3: src/dxf2ifc/_version.py + tests/test_version.py (`394f6ed`)
- [x] Task 4: docs/packaging.md "Local build"-osio (`a655f0c`)

### Section 2: .spec-konfiguraatio + asset bundling ✅
- [x] Task 5: .spec datas (TOML/QSS/fontit/LICENSES) + spec-test (`eb3acf4`)
- [x] Task 6: .spec hidden_imports (ifcopenshell/ezdxf/QtSvg) + spec-test (`b7c1133`)
- [x] Task 7: .spec excludes (tkinter/pytest/pip jne.) + spec-test (`a65ef52`)
- [x] Task 8: .spec VSVersionInfo Windows-resourcesille + version_info.py (`da778e4`)
- [x] Task 9: .spec icon=None placeholder + docs/packaging.md "Icon TODO" + spec-testi (`bb08517`)

### Section 3: Windows build (paikallinen + CI matrix)
- [x] Task 10: scripts/build_exe.ps1 + scripts/build_exe.sh (`738caa7`)
- [x] Task 11: .github/workflows/build.yml Windows-runner + artifact upload (`e13b683`)
- [x] Task 12: build.yml ubuntu-matrix smoke-build (`1bdf320`)
- [x] Task 13: build.yml smoke-step (--version → exit 0) (`45b0d95`)
- [x] Task 14: docs/packaging.md "CI build"-osio (`a23b6bb`)

### Section 4: GitHub Actions release-workflow
- [x] Task 15: .github/workflows/release.yml tag-trigger + permissions (`a8430be`)
- [x] Task 16: release.yml checksum + LICENSES.md pakkaus (`3dfdd91`)
- [x] Task 17: release.yml gh release create --draft step (`47a7021`)
- [x] Task 18: CHANGELOG.md ensimmäinen versio (v0.1.0) (`d946ac5`)
- [x] Task 19: docs/packaging.md "Release-prosessi"-osio (`849b104`)

### Section 5: Smoke + checksum + dokumentointi
- [x] Task 20: docs/packaging-smoke.md manuaalinen Windows-checklist (`8a26b77`)
- [x] Task 21: README "Lataa .exe"-osio + version-badge (`787b72c`)
- [x] Task 22: docs/packaging.md "Troubleshooting"-osio (`2bb9055`)
- [x] Task 23: plan-loppupiste — pytest 246 + coverage 89% + ruff + status-päivitys (`b27b8c6`) 🎉 Plan E 23/23 valmis

## Plan C status (12/12) ✅

### Section 1: Profiili — system_name -arvot ✅
- [x] Task 1: LT IMU "Refrigeration LT" + MT IMU/MT NESTE "Refrigeration MT" (`13d9aea`)
- [x] Task 2: KYL-VIEMARI* "Drainage" + KAAPELIHYLLY* "Cable carriers" (`32ca4f0`)
- [x] Task 3: HOYRYSTIN/LAUHDUTIN/KOMPRESSORI "Refrigeration plant" (`8274d57`)

### Section 2: Mapper — system_name extra_propsiin ✅
- [x] Task 4: failing test custom Profile + apply_profile system_name extra_propsiin (`039211a`)
- [x] Task 5: default-profiili mapper-testi neljälle uniikille system_namelle (`9982994`)

### Section 3: ifc_writer.add_system + group assignment ✅
- [x] Task 6: `add_system` failing test (osa `5f460ba`)
- [x] Task 7: `add_system` toteutus + caching per name (`5f460ba`)
- [x] Task 8: `assign_to_system`-helper + testi (`76c32ff`)

### Section 4: Orchestrator — kerää ja kytke
- [x] Task 9: convert_dxf kerää {system_name → products} + testi (`5bebd67`)
- [x] Task 10: orchestrator luo IfcSystem-objektit ja kytkee + integraatiotesti (`288bac6`)

### Section 5: Integraatio + lint
- [x] Task 11: full_kylmaelement -testi varmistaa neljä IfcSystem-ryhmää (`7e09716`)
- [x] Task 12: ruff clean + 151 passed + 91 % coverage + README/CLAUDE.md "Plan C valmis"

**Viimeisin tila:** Plan A 21/21 + Plan B 50/50 + Plan C 12/12 + Plan D 25/25 valmis. Plan E kirjoitettu (5 sectionia, 23 taskia, `a3620f7`). Mode A toteutus alkaa Task 1:llä (pyinstaller dev-extraan).

**Tämän session muutokset:**
- Plan B Task 2: Rule-skeeman `extrusion_height` + `pset_overrides` -kentät, `model_validator` joka vaatii `block_name` INSERT-säännöille (`29f01e4`). 10 schema-testiä passed.
- Plan B Task 3: TOML-roundtrip-testit + loader negative test INSERT-without-block_name (`a8cbe50`). Loader itse ei vaatinut muutoksia. 17 schema+loader-testiä passed.
- Plan B Task 4: kommentoidut placeholder-säännöt section 2–11 element-tyypeille default TOML:ssa (`35c18f6`). 6 loader-testiä passed.
- Plan B Task 5: aktivoi KYL-VALISEINA ja KYL-LASIVALISEINA -säännöt default-profiiliin (PARTITIONING 1311/1312) (`97ab1b0`). 7 loader-testiä passed.
- Plan B Task 6: mapper-test joka varmistaa partition-mappingin default-profiililla (`cb77e9c`). 11 mapper-testiä passed.
- Plan B Task 7: `add_wall` ottaa explicit `predefined_type`-kwargia (default STANDARD), orchestrator forwardaa MappedEntity.predefined_type:n (`b101565`). 9 ifc_writer-testiä passed.
- Plan B Task 8: integraatiotesti joka generoi KYL-VALISEINA-DXF:n ezdxf:llä, ajaa convert_dxf:n ja varmistaa IfcWall PARTITIONING + Talo2000 1311 (`f051083`). 2 integration-testiä passed. ✅ Section 2 valmis.
- Plan B Task 9: aktivoi slab-säännöt KYL-ALAPOHJA/VALIPOHJA/YLAPOHJA default-profiiliin (1221 FLOOR / 1235 FLOOR / 1236 ROOF) (`62f0f2e`). 8 loader-testiä passed.
- Plan B Task 10: PolygonGeometry types.py:hen + dxf_reader lukemaan suljetut LWPOLYLINE-entiteetit (`5d10e66`). 11 reader+types-testiä passed.
- Plan B Task 11: SlabExtrusion-dataclass + polygon_to_slab_extrusion (`88517c7`). 8 geometry-testiä passed.
- Plan B Task 12: add_slab tuottaa IfcSlab + extruded outline + spatial containment (`3d9e15f`). 12 ifc_writer-testiä passed.
- Plan B Task 13: convert_dxf orchestrator dispatchaa IfcSlab + integraatiotesti KYL-ALAPOHJA → 1221 (`0c13013`). 15 ifc_writer+integration-testiä passed. ✅ Section 3 valmis.
- Plan B Task 14: aktivoi ovi-INSERT-säännöt KYL-OVET-ULKO/VALI/ERITYIS default-profiiliin (1243/1315/1316) (`36c5c51`). 9 loader-testiä passed.
- Plan B Task 15: BlockInstance types.py:hen + dxf_reader lukemaan INSERT-entiteetit (insertion_point/rotation_rad/scale) (`6427278`). 12 reader+types-testiä passed.
- Plan B Task 16: DoorBoxExtrusion-dataclass + door_block_to_box (`efd9f9a`). 12 geometry-testiä passed.
- Plan B Task 17: add_door tuottaa IfcDoor + OverallHeight/Width + box-extrusion + spatial containment (`4848061`). 17 ifc_writer-testiä passed.
- Plan B Task 18: convert_dxf dispatchaa IfcDoor + integraatiotesti OVI-ULKO BLOCK+INSERT → 1243 (`813e4a6`). 21 ifc_writer+integration-testiä passed. ✅ Section 4 valmis.
- Plan B Task 19: aktivoi KYL-IKKUNA INSERT-sääntö default-profiiliin (IfcWindow 1242) (`d5451df`). 10 loader-testiä passed.
- Plan B Task 20: mapper-testi joka mappaa IKKUNA INSERT default-profiililla → IfcWindow 1242 (`2902de2`). 12 mapper-testiä passed.
- Plan B Task 21: add_window tuottaa IfcWindow + OverallHeight/Width + box-extrusion (`4488a48`). 21 ifc_writer-testiä passed.
- Plan B Task 22: convert_dxf dispatchaa IfcWindow + integraatiotesti IKKUNA BLOCK+INSERT → 1242 (`5db11be`). 5 integration-testiä passed. ✅ Section 5 valmis.
- Plan B Task 23: aktivoi LT IMU / MT IMU / MT NESTE -säännöt default-profiiliin (IfcPipeSegment REFRIGERATION 2151/2152/2153 + DN pset_overrides) (`5db22b1`). 11 loader-testiä passed.
- Plan B Task 24: PipeSegmentExtrusion-dataclass + line_to_pipe_segment (`9f1a51c`). 16 geometry-testiä passed.
- Plan B Task 25: add_pipe_segment + IfcPipeSegmentType + USERDEFINED-fallback ei-validille IfcPipeSegmentTypeEnum-arvolle (`b5ff242`). 25 ifc_writer-testiä passed.
- Plan B Task 26: convert_dxf dispatchaa IfcPipeSegment + mapper välittää Pset_PipeSegmentOccurrence.NominalDiameter → extra_props default_diameter_mm + integraatiotesti LT IMU → 2151 (`770978f`). 18 integration+mapper-testiä passed. ✅ Section 6 valmis.
- Plan B Task 27: aktivoi KYL-VIEMARI* DRAINPIPE-sääntö default-profiiliin (`7cf669f`). 12 loader-testiä passed.
- Plan B Task 28: layer_matches wildcard-suffix regression-testit KYL-VIEMARI*:lle (`8904ce1`). 17 mapper-testiä passed.
- Plan B Task 29: add_pipe_segment-testit DRAINPIPE-arvolle (USERDEFINED + ObjectType + jaettu IfcPipeSegmentType) (`1bc2082`). 27 ifc_writer-testiä passed.
- Plan B Task 30: integraatiotesti KYL-VIEMARI-LATTIA → IfcPipeSegment DRAINPIPE + 2160 (`a07f315`). 7 integration-testiä passed. ✅ Section 7 valmis.
- Plan B Task 31: aktivoi KYL-LEVYHYLLY/TIKASHYLLY/TIKASHYLLY-V INSERT-säännöt default-profiiliin (IfcFurniture 1331) (`8d5b662`). 13 loader-testiä passed.
- Plan B Task 32: FurnitureBoxExtrusion + block_to_furniture_box (`fcca98e`). 20 geometry-testiä passed.
- Plan B Task 33: add_furniture tuottaa IfcFurniture + box-extrusion + spatial containment (`17a7358`). 30 ifc_writer-testiä passed.
- Plan B Task 34: convert_dxf dispatchaa IfcFurniture + integraatiotesti KYL-LEVYHYLLY KLHYLLY-LEVY → 1331 (`05c8f43`). 8 integration-testiä passed. ✅ Section 8 valmis.
- Plan B Task 35: aktivoi KAAPELIHYLLY*-sääntö default-profiiliin (IfcCableCarrierSegment CABLETRUNKINGSEGMENT 2380) (`e3af094`). 14 loader-testiä passed.
- Plan B Task 36: CableCarrierSegmentExtrusion-dataclass + line_to_cable_carrier (`8dda18e`). 24 geometry-testiä passed.
- Plan B Task 37: add_cable_carrier_segment + IfcCableCarrierSegmentType CABLETRUNKINGSEGMENT + USERDEFINED-fallback (`b2203f6`). 34 ifc_writer-testiä passed.
- Plan B Task 38: convert_dxf dispatchaa IfcCableCarrierSegment + integraatiotesti KAAPELIHYLLY → 2380 (`ea1d99b`). 9 integration-testiä passed. ✅ Section 9 valmis.
- Plan B Task 39: aktivoi KYL-LEVY*/KYL-NURKKA* POLYLINE-säännöt default-profiiliin (IfcBuildingElementProxy 1352) (`9fdd6c4`). 15 loader-testiä passed.
- Plan B Task 40: PanelExtrusion-dataclass + panel_to_proxy_solid (`02077bd`). 28 geometry-testiä passed.
- Plan B Task 41: add_building_element_proxy tuottaa IfcBuildingElementProxy + arbitrary closed profile -extrusion (`5fc61c6`). 37 ifc_writer-testiä passed.
- Plan B Task 42: convert_dxf dispatchaa IfcBuildingElementProxy + integraatiotesti KYL-LEVY → 1352 (`be47f57`). 10 integration-testiä passed. ✅ Section 10 valmis.
- Plan B Task 43: aktivoi HOYRYSTIN/LAUHDUTIN/KOMPRESSORI INSERT-säännöt default-profiiliin (Evaporator/Condenser/Compressor 2510/2520/2530) (`ddb872f`). 16 loader-testiä passed.
- Plan B Task 44: mapper-testit kylmälaite INSERT-mappauksille (`c4fce3e`). 18 mapper-testiä passed.
- Plan B Task 45: add_cooling_equipment dispatcher IfcEvaporator/IfcCondenser/IfcCompressor box-extrusion (`e0e2c25`). 42 ifc_writer-testiä passed.
- Plan B Task 46: convert_dxf dispatchaa cooling equipment + integraatiotesti KYL-HOYRYSTIN HOYRYSTIN → IfcEvaporator 2510 (`1ba3a65`). 11 integration-testiä passed. ✅ Section 11 valmis.
- Plan B Task 47: full_kylmaelement_dxf conftest-fixture (kaikki Section 2–11 elementit) (`58ac2e4`).
- Plan B Task 48: tests/test_integration_full.py joka varmistaa kaikki Section 2–11 Talo2000-koodit + IFC-validointi (`536fa50`). 3 testiä passed.
- Plan B Task 49: ruff format kolmelle uudelle tiedostolle, koko suite 143 passed, coverage 91 % (`cab7ea7`).
- Plan B Task 50: README + CLAUDE.md status-päivitys Plan B valmiiksi (`2494841`). 🎉 Plan B 50/50.
- Plan C kirjoitettu (Mode B): skeleton + 12 tehtävää 5 sectionia (`93f01fc` → `5586361` → `3f0dd6c` → `ec20cea`). CLAUDE.md "Plans B–F" -lista päivitetty (`8b00233`).
- Plan C Task 1: LT IMU "Refrigeration LT" + MT IMU/MT NESTE "Refrigeration MT" -system_name default-profiilissa (`13d9aea`).
- Plan C Task 2: KYL-VIEMARI* "Drainage" + KAAPELIHYLLY* "Cable carriers" (`32ca4f0`).
- Plan C Task 3: HOYRYSTIN/LAUHDUTIN/KOMPRESSORI "Refrigeration plant" (`8274d57`). ✅ Section 1 valmis.
- Plan C Task 4: mapper-testi varmistaa Rule.system_name → MappedEntity.extra_props välittäminen (`039211a`).
- Plan C Task 5: default-profile mapper-testi viidelle uniikille system_namelle (`9982994`). ✅ Section 2 valmis.
- Plan C Task 6+7: add_system kirjoitin + per-name cache (`5f460ba`).
- Plan C Task 8: assign_to_system helper IfcRelAssignsToGroupin avulla (`76c32ff`). ✅ Section 3 valmis.
- Plan C Task 9: convert_dxf kerää productit dict[system_name → list]:iin ja palauttaa dictin; integraatiotesti LT IMU + KYL-VIEMARI varmistaa kaksi system-nimeä (`5bebd67`). 12 integration-testiä passed.
- Plan C Task 10: convert_dxf luo IfcSystem-entiteetit kerätyistä nimistä ja kutsuu assign_to_system per nimi; integraatiotesti varmistaa IfcRelAssignsToGroup-jäsenyydet (`288bac6`). 13 integration-testiä passed. ✅ Section 4 valmis.
- Plan C Task 11: full-fixture-testi joka varmistaa neljä IfcSystem-ryhmää ja että jokaisella ≥1 jäsen IfcRelAssignsToGroup:n kautta (`7e09716`). 4 integration_full-testiä passed.
- Plan C Task 12: plan-loppupiste — pytest 151 passed, coverage 91 %, ruff clean; README + CLAUDE.md status päivitetty Plan C valmiiksi (`8cc4fc3`). 🎉 Plan C 12/12.
- Plan D Mode B: skeleton + 7 sectionia + 25 task-riviä (kommitit B2 → S7), CLAUDE.md "Plans B–F"-lista päivitetty (`7433ae8` → ...). PROGRESS.md sisältää nyt täyden Plan D -checklistin.
- Plan D Task 1: PySide6>=6.7 ja pytest-qt>=4.4 -depsit pyproject.tomlin gui+dev-extrojen alle, smoke-testi `tests/test_gui_smoke.py` (`10d50c2`). 2 smoketestiä passed (vaatii libEGL.so.1 hostissa).
- Plan D Task 2: `gui/app.py` `MainWindow` + `run()` + qtbot-testi (`f87b09e`). 2 gui-app-testiä passed.
- Plan D Task 3: `dxf2ifc-gui` console-script + `gui/__main__.py` (`ce1cba8`). 2 main-module-testiä passed. ✅ Section 1 valmis.
- Plan D Task 4: 8 OFL-fonttia (Inter Reg/Med/SemiBold/Bold + Space Grotesk Med/SemiBold/Bold + JetBrains Mono Med) + 3 LICENSE.txt + LICENSES.md `assets/fonts/`-kansiossa, hatchling force-include säännöt wheeliin (`f3f5116`). 3 font-asset-testiä passed.
- Plan D Task 5: `src/dxf2ifc/gui/style.qss` brand-paletilla + role/primary/secondary-selektoreilla (QMainWindow/QPushButton/QLabel/QStatusBar/QLineEdit/QHeaderView/QMenu); hatchling-include sääntö lisätty (`4155720`). 4 style-testiä passed.
- Plan D Task 6: `gui/theme.py` `apply_theme(app)` rekisteröi 7 TTF:ää (Inter Reg/Med/SemiBold/Bold + Space Grotesk Med/Bold + JetBrains Mono Med), asettaa style.qss + Inter 10pt default-fontin (`dd6387a`). 3 theme-testiä passed. Pudotettiin SpaceGrotesk-SemiBold koska upstream static-build ei ship sitä eikä Google Fonts ole sandbox-allowlistissa. ✅ Section 2 valmis.
- Plan D Task 7: `gui/main_window.py` MainWindow — title-rivi (H1 + caption), QSplitter (vasen+oikea stub), QStatusBar; `app.run()` kutsuu `apply_theme()` ennen showia (`6275bc6`). 4 gui-app-testiä passed.
- Plan D Task 8: `MainWindow.set_status(text, level)` asettaa statusbarin tekstin + level-property:n (info/success/error) + unpolish/polish-syklin QSS:n päivitykseen (`3f045d9`). 5 gui-app-testiä passed.
- Plan D Task 9: menubar File (Open DXF…, Quit) + Help (About) MainWindow:in konstruktorissa, action-objektit self-attribuutteina shiboken-GC:lle (`f0bcd48`). 7 gui-app-testiä passed. ✅ Section 3 valmis.
- Plan D Task 10: `gui/file_panel.py` `FilePanel` (DXF/IFC line-editit + Browse-napit + Convert-nappi) + `convert_requested(str, str)` -signaali (`e7935d3`). 3 file-panel-testiä passed.
- Plan D Task 11: `gui/convert_worker.py` `ConvertWorker(QObject)` + sisäinen `_ConvertRunnable` joka ajaa `convert_dxf` QThreadPoolissa; finished/failed-signaalit (`8216c0b`). 2 worker-testiä passed.
- Plan D Task 12: kytkin FilePanel + ConvertWorker MainWindow:iin: convert_requested → disable button + status "Converting…" → worker → finished re-emittoi `convert_finished(out)`-signaalin + status "Done", failed re-emittoi `convert_failed(msg)` + status "Error" (`ff218ca`). 9 gui-app-testiä passed.
- Plan D Task 13: end-to-end GUI integration test simple_wall.dxf → IfcWall (`9e96b6f`). 1 GUI-integration-testi passed. ✅ Section 4 valmis.
- Plan D Task 14: `core.dxf_reader.list_layers(path)` palauttaa sorted-uniikit layer-nimet model-spacestä (`205f4de`). 9 dxf-reader-testiä passed.
- Plan D Task 15: `gui/layer_table.py` `LayerTable(QTableWidget)` 4 kolumnia (Layer/IFC/Talo2000/System), `set_layers(layers, profile)`, JetBrains Mono Layer/Talo2000-kolumneille (`6633e6e`). 2 layer-table-testiä passed.
- Plan D Task 16: kytkin LayerTable MainWindow:n vasempaan paneeliin file_panel:n alle, editingFinished triggeröi list_layers + set_layers (`5d6ed4a`). 10 gui-app-testiä passed. ✅ Section 5 valmis.
- Plan D Task 17: `profiles/loader.dump_profile(profile, path)` + `tomli-w` runtime-dep, round-trip-testit (`0e96db4`). 18 loader-testiä passed.
- Plan D Task 18: `gui/profile_editor.py` `ProfileEditorDialog` + custom QAbstractTableModel + Add/Edit/Remove/Save-toolbar (Save → dump_profile + profile_saved-signaali) (`de6d9ad`). 3 profile-editor-testiä passed.
- Plan D Task 19: `gui/rule_dialog.py` `RuleEditDialog` QFormLayout + live-pydantic-validointi (OK disabloitu invalid-INSERT-no-block_name) (`f77acb1`). 3 rule-dialog-testiä passed.
- Plan D Task 20: kytkin ProfileEditorDialog MainWindow:n Profile-menubariin + `apply_profile_from_path` joka load_profile + päivitä layer_table + statusbar (`1e7f38f`). 12 gui-app-testiä passed. ✅ Section 6 valmis.
- Plan D Task 21: `gui/about.py` `AboutDialog` modal QDialog brand+version+GitHub-linkillä; Help → About kutsuu sitä (`13e882d`). 2 about-testiä passed.
- Plan D Task 22: `gui/recent_files.py` `RecentFilesStore` LRU 5 path:lla QSettings-backendillä (Radika/dxf2ifc) (`54adf38`). 3 recent-files-testiä passed.

- Plan D Task 24: README GUI-osio + docs/screenshots/.gitkeep placeholder (`b4141f9`, tehty edellisessä sessiossa, PROGRESS.md-checklist päivitetty tässä sessiossa).
- Plan D Task 25: ruff format six lingering files (file_panel/layer_table/profile_editor + kolme testiä), README + CLAUDE.md status Plan D ✅ (200 passed, coverage 89 %, ruff clean) (`011bd5e`). 🎉 Plan D 25/25.
- Plan E kirjoitettu (Mode B): skeleton + 5 sectionia + 23 task-riviä numeroitu globaalisti, CLAUDE.md "Plans B–F"-lista päivitetty (`432a277` → `a3620f7`). PROGRESS.md sisältää nyt täyden Plan E -checklistin.

- Plan E Task 1: pyinstaller>=6.10 dev-extraan + tests/test_pyinstaller_bootstrap.py smoke import + `python -m PyInstaller --version`-test (`22875d0`). 2 smoketestiä passed.
- Plan E Task 2: build/dxf2ifc.spec base (Analysis + EXE GUI-entrylla, console=False) + tests/test_spec_file.py + .gitignore-säätö (whitelist build/dxf2ifc.spec) (`23179ec`). 2 spec-testiä passed.
- Plan E Task 3: src/dxf2ifc/_version.py kanoninen versio-string + __init__ re-exportti + tests/test_version.py (metadata-roundtrip + module-level shape) (`394f6ed`). 2 version-testiä passed.
- Plan E Task 4: docs/packaging.md "Local build" -osio (`a655f0c`). ✅ Section 1 valmis.
- Plan E Task 5: .spec Analysis(datas=...) profile TOML + QSS + 7 fonttia + 4 LICENSE-tiedostoa (destinaatiot dxf2ifc/profiles, dxf2ifc/gui, dxf2ifc/gui/fonts) + tests/test_spec_file.py varmistaa jokaisen polun (`eb3acf4`). 3 spec-testiä passed.
- Plan E Task 6: .spec hiddenimports ifcopenshell.{api,geom,guid,template} + ezdxf.entities + PySide6.{QtSvg,QtSvgWidgets} + spec-testi (`b7c1133`). 4 spec-testiä passed.
- Plan E Task 7: .spec excludes tkinter + pytest + unittest + numpy.distutils + setuptools._distutils + pip + spec-testi (`a65ef52`). 5 spec-testiä passed.
- Plan E Task 8: build/version_info.py VSVersionInfo Win32-resource (Radika Oy + dxf2ifc + 0.1.0) + .spec EXE(version=...) + .gitignore-whitelist + spec/version_info-testi (`da778e4`). 7 spec-testiä passed.
- Plan E Task 9: .spec EXE(icon=None) placeholder TODO + docs/packaging.md "Icon TODO"-osio + spec-testi (`bb08517`). 8 spec-testiä passed. ✅ Section 2 valmis.
- Plan E Task 10: scripts/build_exe.ps1 + scripts/build_exe.sh + tests/test_build_scripts.py (uv sync, pyinstaller, version-stamping, SHA256, +x bit) (`738caa7`). 3 build-script-testiä passed.
- Plan E Task 11 yritetty: build.yml + tests/test_workflows.py kirjoitettu paikallisesti, mutta `git push` hylättiin (PAT:lla ei workflow-scopea). Paikalliset tiedostot poistettiin commitia ennen, työtä ei kommittoitu master:iin. ⚠ blokkeri.

**Tämän session muutokset:**
- Bugfix 1: `add_furniture` hyväksyy nyt PolygonGeometry-syötteen (closed polyline) — laskee bbox:n ja extrudaa boxin, default-korkeus 2000 mm extra_props:sta. Degeneroitu outline (sivu < 50 mm) → `ValueError`. 47 ifc_writer-testiä passed (`8e7c9c8`).
- Bugfix 2 part a: ProfileEditorDialog "Load profile…" -nappi + `load_from_path()` + `profile_loaded(str)`-signaali; rules-taulu rakennetaan uudelleen kun TOML ladataan (`4955ac2`).
- Bugfix 2 part b: RecentFilesStore.last_profile_path (QSettings property + setter joka tukee None-clearin); MainWindow ottaa optional `recent_files=`-parametrin, palauttaa cached profile-polun käynnistyksessä (fallback default jos puuttuu), ja persistoi polun joka apply-vaiheessa. ProfileEditorDialog.profile_loaded kytketty MainWindow:in apply_profile_from_path:iin (`9fe0395`). 25 GUI-testiä passed.
- Bugfix 3: `gui/preview_log.py` `PreviewLogPanel` (read-only QTextEdit JetBrains Monolla, append_info/success/error + set_dxf_summary). MainWindow:n right pane käyttää sitä; DXF-input-muutos printtaa yhteenvedon (entity-count + per-layer counts), Convert-vaihe logaa start/done/error värikoodattuna (`52a5695`). 230 testiä passed kokonaisuudessaan.
- Plan E Task 11: build.yml Windows-runner (windows-latest) joka ajaa scripts/build_exe.ps1 ja uploadaa dxf2ifc-windows-artifactin (`e13b683`). pyyaml lisätty dev-extraan tests/test_workflows.py:n driveriksi.
- Plan E Task 12: build.yml linux-smoke-job (ubuntu-latest) joka ajaa scripts/build_exe.sh:n spec-validointia varten + asentaa libegl1/libgl1/libxkbcommon0/libdbus-1-3 (`1bdf320`).
- Plan E Task 13: Windows-jobiin smoke-step joka ajaa `dxf2ifc-*.exe --version` + tarkistaa exit 0 + stdout sisältää "dxf2ifc"; smoke-step ennen artifact-uploadia (`45b0d95`).
- Plan E Task 14: docs/packaging.md "CI build"-osio (Windows job + Linux smoke job + Qt runtime libs + mitä CI ei tee) (`a23b6bb`).
- Plan E Task 15: .github/workflows/release.yml — `push: tags: ['v*.*.*']`-trigger + `permissions: contents: write` + sama Windows build + smoke-step (`a8430be`).
- Plan E Task 16: release.yml Bundle LICENSES.md -step joka aggregoi font OFL + ifcopenshell + PySide6 + Python -lisenssit `dist/LICENSES.md`:hen, upload-pathiin lisätty (`3dfdd91`).
- Plan E Task 17: release.yml `gh release create $TAG ... --draft` -step joka liittää .exe + .sha256 + LICENSES.md tag-pohjaiseen draft-releaseen (`47a7021`).
- Plan E Task 18: CHANGELOG.md v0.1.0 -versiomerkintä Plan A-D + Plan E in-progress feature-roadmapilla (`d946ac5`).
- Plan E Task 19: docs/packaging.md "Release-prosessi" -osio (5-step manuaalinen Lauri-driven release-flow + warning published tag deletion:sta) (`849b104`).
- Plan E Task 20: docs/packaging-smoke.md manuaalinen Windows-smoke-checklist (download → SHA256 → GUI → simple_wall.dxf → CLI → publish/discard) (`8a26b77`).
- Plan E Task 21: README.md version-badge (shields.io/github/v/release/Mcrauli/dxf2ifc) + "Lataa .exe (Windows)" -osio Releases-linkillä + SmartScreen-ohjeella (`787b72c`).
- Plan E Task 22: docs/packaging.md "Troubleshooting"-osio: Defender/SmartScreen, ifcopenshell schema not found, Qt platform plugin import error, --onefile vs --onedir trade-off (`2bb9055`).
- Plan E Task 23: plan-loppupiste — pytest 246 passed, coverage 89%, ruff clean. CLAUDE.md + README.md status päivitetty Plan E ✅ (`b27b8c6`). 🎉 Plan E 23/23.

- Plan F kirjoitettu (Mode B): skeleton + 5 sectionia + 16 task-riviä numeroitu globaalisti, CLAUDE.md "Plans B–F"-lista päivitetty (`3651f00` → `e921b35` → `086daa7` → `ae735fe` → `3866ab4` → `30404cb`). PROGRESS.md sisältää nyt täyden Plan F -checklistin.

**Kesken:** Plan F Mode A aloitus Task 1:llä seuraavalla sessiolla.

**Blokkerit:** ei.
