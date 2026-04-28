# PROGRESS

**Current plan:** Plan H (kirjoittamatta) — IFC 4.3 -migraatio + RAVA-luokitus.

**Current task:** Plan H Task 19 — Solibri rule-set: lisää "RAVA classification coverage".

**Mode:** A.

**Seuraavaksi:** Lue Task 19:n osio plan-tiedostosta. Päivitä `tools/solibri/dxf2ifc.bcfzip` rule-set: lisää sääntö "RAVA classification coverage" joka vaatii TATE-elementeille RAVA-LVI/RAVA-TATE-linkin. Päivitä `docs/solibri-rules.md` ja `tests/test_solibri_bcfzip.py`.

## Bugfix kierros (löydetty GUI-testissä 2026-04-28, ennen Plan E jatkoa)

Lauri testasi GUI:n paikallisesti ja löysi 3 bugia. Korjataan TDD:llä per task ennen Plan E Task 11:n jatkoa (PAT on päivitetty Workflow-scopella, mutta bugifx tehdään ensin).

- [x] **Bugfix 1** — `add_furniture` polygon-tuki: kun KYL-LEVYHYLLY/KYL-TIKASHYLLY on piirretty closed polylinena (PolygonGeometry), `add_furniture` heittää `TypeError: add_furniture expects BlockInstance, got PolygonGeometry`. Korjaus: laske bbox + extrude box, palauta IfcFurniture; jos polygon on degeneroitu (alle 50mm sivu), nosta selkeä virhe. Tiedostot: `src/dxf2ifc/core/ifc_writer.py`, `tests/test_ifc_writer.py`. (`8e7c9c8`)

- [x] **Bugfix 2** — Profiili load + persistointi GUI:ssa: ProfileEditorDialog tukee vain Save:n, ei Load:ia. Lisäksi GUI ei muista viimeksi käytettyä TOML:ia sessioiden välillä. Korjaus: a) lisää "Load profile..." -nappi ProfileEditorDialogiin (avaa file picker → load_profile(path) → täyttää rules-taulun); b) laajenna RecentFilesStore tukemaan "last_profile_path" + lataa appin käynnistyksessä jos olemassa. Tiedostot: `src/dxf2ifc/gui/profile_editor.py`, `src/dxf2ifc/gui/main_window.py`, `src/dxf2ifc/gui/recent_files.py`, vastaavat testit. (`4955ac2` + `9fe0395`)

- [x] **Bugfix 3** — Preview & log -paneeli kytkemättä: oikean laidan paneeli on tyhjä DXF:n latauksen ja Convert:in jälkeen. Korjaus: a) DXF-latauksessa näytä yhteenveto (entity-määrä per layer, kokonais-bbox, units); b) Convert-vaiheessa logaa per-layer-mappauksia ja valmistus/virhe; käytä JetBrains Mono -fonttia, värikoodit per status. Tiedostot: `src/dxf2ifc/gui/preview_log.py` (uusi widget), `src/dxf2ifc/gui/main_window.py` (kytkentä), vastaavat testit. (`52a5695`)

✅ Bugfix kierros valmis (1+2+3, `8e7c9c8` + `4955ac2` + `9fe0395` + `52a5695`). 230 testiä passed, ruff puhdas omalle koodille (build/version_info.py + tests/test_spec_file.py F821:t ovat pre-existing PyInstaller-DSL-poikkeuksia). Plan E Task 11 voi alkaa.

## Bugfix kierros 2 (löydetty Solibri-testissä 2026-04-28, ennen Plan H:ta)

Lauri testasi 4001_1krs.dxf:n GUI:lla ja näki 3 lisäongelmaa: 14 hyllystä vain 1 näkyy 3D:ssä, AR-prefix-layerit (xref-format "AR1241_US") eivät matchaa profiilin sääntöihin, default-profiili kattaa pelkästään KYL-* layereitä — sun real-world DXF:llä on 77 layeria mukaan lukien AR1241_US/AR1311_VS/AR1242_IKKUNA jne. joilla on Talo2000-koodit jo nimessä.

- [x] **Bugfix 4** — Placement 1000× world coords (is_si default-bug ifcopenshell.api 0.8.5:ssä): `geometry.edit_object_placement` -kutsut korjattu `is_si=False`-flagiksi 9 paikassa (wall/slab/door/window/pipe/furniture/cable/proxy/cooling). Bonus: `dxf_reader` muuntaa LWPOLYLINE-vertexit OCS→WCS:ksi (`entity.ocs().to_wcs()`), joten extrusion=(0,0,-1)-flippaus toimii. 3 uutta testiä, koko 297 passed. (`2f827ea`)

- [x] **Bugfix 5** — `mapper.layer_matches` strippaa xref-pipe-prefixin (`KCM Kauhajoki|AR1241_US` → `AR1241_US`) kun pattern ei sisällä pipea. 4 uutta testiä. (`230f327`)

- [x] **Bugfix 6** — Default-profiilin laajennus ARK / K-prefix layereille:
  - `AR1241_US` → IfcWall STANDARD, Talo2000 1241
  - `AR1242_IKKUNA` → IfcWindow, Talo2000 1242
  - `AR1245_LASIUS` → IfcWall STANDARD (lasi-US)
  - `AR1311_VS` → IfcWall PARTITIONING, Talo2000 1311
  - `AR1233_PILARI` → IfcColumn
  - `AR1314_KAIDE` → IfcRailing
  - `AR1317_TILAPORTAAT` → IfcStair
  - `AR1331_KIINTO` → IfcFurniture, Talo2000 1331
  - K-arkkitehtuuriset: `K-OVET` → IfcDoor, `K-SEINÄT_VÄLISEINÄT` → IfcWall PARTITIONING, `K-KALUSTEET`/`K-KIINTOKALUSTEET`/`K-RST-KALUSTEET` → IfcFurniture, `K-VALAISTUS` → IfcLightFixture
  - **HUOM:** KYL-* layerit (höyrystimet/hyllyt/laitteet) säilyvät nykyisellä mapping:lla kunnes Plan H toteutuu. 13 uutta testiä `tests/test_bugfix6_ark_layer_rules.py` + xref-yhdistelmä-testi. (`b1df8c3`)

✅ Bugfix kierros 2 valmis (Bugfix 4 + 5 + 6 = 314 testiä passed). Plan H Mode B alkaa seuraavalla sessiolla.

## Bugfix kierros 3 (löydetty Solibri-uusintatestissä 2026-04-28 klo 14, samanaikaisesti Plan H Section 3:n kanssa)

Lauri testasi 4001_1krs.dxf:n Bugfix kierros 2:n jälkeen (Plan F + Bugfix 4-6 + Plan H Section 1-2 valmiit). Placement-bugi (1000×) on korjattu ja 14/14 hyllyä näkyy 3D:ssä, mutta geometria on edelleen pielessä — hyllyt renderöityvät pitkinä ohuina palkkeina, ei LEVY-hyllyn muotoisina laatikoina (60mm × leveys × pituus). Lisäksi KYL-TIKASHYLLY puuttuu kokonaan vaikka layerissa pitäisi olla. Profile editor:n Load-nappi ei tuottanut tulosta.

- [ ] **Bugfix 7** — **KAIKEN element-tyypin geometria oikein** (ei vain KYL-LEVYHYLLY:n): testissä hyllyt renderöityvät pitkinä palkkeina, mutta vastaava ongelma todennäköisesti koskee KAIKKIA element-tyyppejä. **Pakko käydä KAIKKI add_*-funktiot läpi** (`add_wall`, `add_slab`, `add_door`, `add_window`, `add_furniture`, `add_pipe`, `add_cable_carrier`, `add_proxy`, `add_evaporator`, `add_condenser`, `add_compressor`) ja tarkistaa: a) bbox-laskenta polygon-syötteestä on oikein (X/Y/Z erotettu), b) extrusion-suunta on oikein per element-tyyppi (seinät: pystysuora Z+, slabit: vaakasuora -Z, hyllyt: pystysuora Z+), c) extrusion-pituus tulee oikeasta lähteestä (default_height_mm vs profile-rule), d) DXF:ssä jo 3D-piirretyt entiteetit (KLHYLLYV pystyhyllyt, HYLLYKORKO eri korkeuksilla) säilyttävät z-arvonsa eivätkä lapsuoraan z=0:lle. Tiedostot: `src/dxf2ifc/core/ifc_writer.py` (kaikki add_*-funktiot), `src/dxf2ifc/core/geometry.py`, `tests/test_ifc_writer.py`. Testi-fixture per element-tyyppi: yksinkertainen tunnetut DXF-mitat → vahvista IFC bbox vastaa ±1mm. Lisää myös **systemaattinen geometria-roundtrip-testi** `tests/test_geometry_roundtrip.py` joka pyörittää real-world fixture-DXF:n läpi (~10 element-tyyppiä) ja varmistaa: jokaiselle layer-tyypille tuotetaan odotettu määrä entiteettejä, IFC bbox-mitat ±5% DXF-mitoista, sijainnit ±50mm. Pyörii joka commitissa, varoittaa jos tuleva muutos rikkoo geometrian.

- [ ] **Bugfix 8** — KYL-TIKASHYLLY puuttuu kokonaan IFC:stä: layer-table:ssa preview näyttää että KYL-TIKASHYLLY-layerilla on entiteettejä (KLHYLLY tikas-tyyppi piirtää 2 kiskoa + poikkitikat eri sub-entiteetteinä), mutta dxf2ifc ei tuota niistä mitään IfcFurniture-entiteettiä outputiin. Mahdollinen syy: KLHYLLY tikas piirtää komposiittia DXF-blokkina + INSERT-entiteettinä, mutta nykyinen `add_furniture` ei tunnista INSERT-tyyppistä syötettä TIKAS-hyllylle. Korjaus: tutki KYL-TIKASHYLLY-layer:n DXF-entiteettien tyyppi ezdxf:llä (`doc.modelspace().query(*[layer==0])`), lisää tuki TIKAS-tyypille (kahden kiskon + poikkitikkujen yhdistelmä → 1 IfcFurniture per koko hylly).

- [ ] **Bugfix 9** — Profile editor Load-nappi ei toimi: Bugfix 2 piti hoitaa tämän mutta käyttäjän palautteen perusteella ei toimi. Repro: avaa GUI, Profile → Edit profile → Load profile…-nappi → valitse TOML → ei mitään. Korjaus: lisää virhelogi (try/except + log:iin per failure case) + varmista että `profile_loaded`-signaali laukeaa + UI päivittyy. Tiedostot: `src/dxf2ifc/gui/profile_editor.py`, vastaavat testit (testi joka simuloi load-buttonin painalluksen + varmistaa että rule-table:n sisältö muuttuu).

- [ ] **Bugfix 10** — KYL-* layer-säännöt suunnitteluala-domainiin TATE: nykyinen default-profiili merkitsee KYL-LEVYHYLLY/KYL-TIKASHYLLY ARK-domainiin (Talo2000 1331), mutta käyttäjän mukaan kylmälaiteasennukset ovat TATE-puolta. Plan H Section 4 (default profile RAVA-päivitys) hoitaa tämän automaattisesti — vaihtaa KYL-* säännöt domain=TATE + RAVA-koodit (LVI-TUOTEOSA tai TALOTEKNIIKKA-TUOTEOSA). HUOM: tämä bug on **redundantti Plan H Section 4:n kanssa** — mainitaan tässä viittauksena, mutta korjaus tapahtuu Plan H:n osana, ei erillisenä bugfixinä.

Bugfix kierros 3 ajoitus: kun Plan H valmistuu (Section 5 plan-loppupiste), käy nämä läpi (paitsi Bugfix 10 joka on jo Plan H Section 4:ssä). Sit Plan G.

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

## Plan H status (0/22)

### Section 1: IFC4X3-skeema-migraatio
- [x] Task 1: build_ifc_project_skeleton(schema="IFC4X3") + failing-testi (`5b0d414`)
- [x] Task 2: convert_dxf-pipeline regressio IFC4X3:lla (full-fixture, 11 IFC-luokkaa, ifcopenshell.validate clean) (`069f08e`)
- [x] Task 3: convert_dxf + CLI `--schema=ifc4x3`-flag (`c594e9e`)
- [x] Task 4: validate_ifc.summary näyttää IFC4X3:n (`83d6ddc`)

### Section 2: RAVA-koodien lataaminen
- [x] Task 5: tools/rava/sync_codes.py 4 codeset → JSON-cache (`326633e`)
- [x] Task 6: 4 RAVA-codeset-JSON committoitu src/dxf2ifc/profiles/rava/:hen (`31ecdb8`)
- [x] Task 7: dxf2ifc.profiles.rava.loader.load_rava_codes() (`fd9e8e5`)

### Section 3: Profile-skeeman domain-laajennus
- [x] Task 8: Rule.domain Literal["ARK", "TATE"] + lvi_code/talotekniikka_code + validointi (`2bd5be6`)
- [x] Task 9: loader.dump_profile + load_profile uudet kentät TOML round-trip (`e8bc454`)
- [x] Task 10: MappedEntity.domain + lvi_code + talotekniikka_code + apply_profile välitys (`be0ed2c`)

### Section 4: Default-profiilin uudistus
- [x] Task 11: git mv default_kylmalaite_talo2000.toml → default_kylmalaite.toml (`11c5801`)
- [x] Task 12: ARK-säännöt domain="ARK"-merkintä (`203306a`)
- [x] Task 13: TATE-säännöt (kylmälaitteet) domain="TATE" + lvi_code RAVA-koodit (`cca9882`)
- [x] Task 14: Kylmäaineputket + kaapelihylly domain="TATE" + RAVA-LVI-02 / RAVA-TATE (`fcf5492`)

### Section 5: Mapper + ifc_writer domain-luokitus
- [x] Task 15: add_classification(ifc, product, *, domain, code, name) — Talo2000/RAVA-LVI/RAVA-TATE (`e2bbf8d`)
- [x] Task 16: convert_dxf-orchestrator domain-tietoinen luokitus, multi-classification kielletty (`6b172e5`)
- [x] Task 17: validate_ifc Talo2000/RAVA-warning domain-aware (`3c1d514`)

### Section 6: Integraatio + dokumentointi + plan-loppupiste
- [x] Task 18: full-fixture- ja integration-testit IFC4X3 + domain (`1b771d3`)
- [ ] Task 19: Solibri rule-set: lisää "RAVA classification coverage" + docs/solibri-rules.md
- [ ] Task 20: rebuild solibri_reference_full.ifc + päivitä snapshot-baseline jos tarvitaan
- [ ] Task 21: docs/rava-classification.md
- [ ] Task 22: plan-loppupiste — pytest + coverage + ruff + status-päivitys

## Plan F status (16/16) ✅

### Section 1: Automaattinen ifcopenshell.validate -gate
- [x] Task 1: src/dxf2ifc/core/quality.py validate_ifc(path) wrapper + tests/test_quality.py (`b16f424`)
- [x] Task 2: validate_ifc raportoi YTV-spesifit Talo2000-luokittelutarkistukset (warnings) (`cdc9426`)
- [x] Task 3: CLI-flag `dxf2ifc convert --validate` (exit 1 jos errors) (`ea1f490`)
- [x] Task 4: convert_dxf(..., validate: bool) palauttaa (IfcFile, ValidationReport | None) + GUI-näyttö (`c5fa6f0`)

### Section 2: Solibri rule-set ja referenssimallit
- [x] Task 5: tools/solibri/dxf2ifc.bcfzip BCF 2.1 rule-set (Talo2000 + YTV) (`9ff1347`)
- [x] Task 6: tests/fixtures/solibri_reference_full.ifc baseline-IFC (`8d2a798`)
- [x] Task 7: docs/solibri-rules.md sääntöjen suomenkielinen kuvaus (`6042595`)

### Section 3: solibri-cli runner + raportin parsija
- [x] Task 8: tools/solibri/verify.py Solibri.exe-CLI-wrapper (subprocess) (`5b6bcea`)
- [x] Task 9: tools/solibri/parse_report.py XML→RuleResult dict (lxml-vapaa, ElementTree) (`797e740`)
- [x] Task 10: `python -m tools.solibri verify` CLI-entry (`25a38f4`)

### Section 4: Snapshot-raportit + diffaus
- [x] Task 11: tests/snapshots/solibri/full_kylmaelement.json baseline (`b7de018`)
- [x] Task 12: tools/solibri/diff_snapshot.py uusi-vs-baseline diffaus (`ae3e411`)
- [x] Task 13: pytest @solibri-marker + tests/test_solibri_snapshot_chain.py (`cbb3d76`)

### Section 5: CI-integraatio + dokumentaatio + plan-loppupiste
- [x] Task 14: build.yml linux-jobissa pytest tests/test_quality.py (`d6c78bd`)
- [x] Task 15: docs/quality-gates.md (auto + manuaali two-tier prosessi) (`fb7487d`)
- [x] Task 16: plan-loppupiste — pytest 294 + coverage 91% + ruff format clean + status-päivitys (`165a0db`) 🎉 Plan F 16/16 valmis

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

**Tämän session muutokset:**
- Plan F Task 1: `src/dxf2ifc/core/quality.py` `ValidationReport`-dataclass (errors/warnings/summary) + `validate_ifc(path)` joka wrappaa `ifcopenshell.validate.validate` json_loggerilla; `tests/test_quality.py` 3 testiä (dataclass-shape + full-fixture 0 errors + str-path) (`b16f424`).
- Plan F Task 2: `validate_ifc` skannaa IfcWall/IfcSlab/IfcDoor/IfcWindow-entiteetit ja emittaa "missing Talo2000 classification" -warningin jos `IfcRelAssociatesClassification`-linkki Talo2000-codesetiin puuttuu; helper `_talo2000_classified_products` keräilee classifiedien id:t. 2 uutta testiä (unclassified-wall warning + full-fixture clean). 5 quality-testiä passed (`cdc9426`).
- Plan F Task 3: `dxf2ifc convert --validate` argparse-flag joka kutsuu `validate_ifc(output_path)` muunnoksen jälkeen, printtaa summaryn + warnings stderriin, ja palauttaa exit 1 jos errors > 0. 3 uutta CLI-testiä (clean-exit-zero, monkeypatched-error-exit-one, no-validate-bypass) (`ea1f490`).
- Plan F Task 4: `convert_dxf(..., validate: bool = False)` palauttaa nyt `tuple[dict[str, list], ValidationReport | None]`; ConvertWorker.run sai validate-kwarg + uuden `report_ready(object)`-signaalin; MainWindow kytki signaalin uuteen `_on_report_ready`-slottiin joka logaa summary/warnings/errors PreviewLogPanelissa, ja kutsuu workerin validate=True (GUI ottaa YTV gate käyttöön defaultisti). Päivitti 1 vanhan integraatio-testin (systems-dict-unpack) + 6 uutta testiä. Koko 260 testiä passed (`c5fa6f0`).
- Plan F Task 5: `tools/solibri/build_bcfzip.py` deterministinen BCF 2.1 -arkistogeneraattori + `tools/solibri/dxf2ifc.bcfzip` (5 Topic-rule:ia: units, classification coverage, IfcSystem grouping, cold-room paneelit, kylmälaitteiden MEP-entiteetit). 3 uutta testiä (existence + version=2.1 + required-rule-titles) (`9ff1347`).
- Plan F Task 6: `tools/solibri/build_reference_ifc.py` luo `tests/fixtures/solibri_reference_full.ifc`-baselinen ajamalla saman DXF-patternin kuin conftest full_kylmaelement_dxf läpi convert_dxf:n default-profile:lla. 4 uutta testiä (existence + IFC4 + 11 Talo2000-koodia + 9 IFC-luokkaa) (`8d2a798`).
- Plan F Task 7: `docs/solibri-rules.md` dokumentoi kaikki 5 BCF-sääntöä suomeksi (Mitä validoi / Miksi / Viite / Solibri-säännön tyyppi / dxf2ifc:n vastaava automaattinen tarkistus). 2 uutta testiä (existence + heading-coverage) (`6042595`). ✅ Section 2 (Tasks 5–7) valmis.
- Plan F Task 8: `tools/solibri/verify.py` `build_command` + `run_solibri` Solibri Anywhere CLI-wrapper. Käyttää shutil.which:n etsimään Solibri.exe:n. 5 uutta testiä (argv-shape, subprocess-mock, missing-exe FileNotFoundError, non-zero-exit RuntimeError, shutil-attached). `tools/__init__.py` + `tools/solibri/__init__.py` muunsivat tools/-kansion paketiksi (`5b6bcea`).
- Plan F Task 9: `tools/solibri/parse_report.py` `parse_report(path) -> list[RuleResult]` joka iteroi `<Rule>` ja `<Result>` -nodet ElementTree:llä. tests/fixtures/solibri_report_sample.xml mock-fixture (1 passed + 3 failed) + 4 parser-testiä (`797e740`).
- Plan F Task 10: `tools/solibri/cli.py` `verify --ifc --ruleset --report` CLI-entry joka ketjuttaa run_solibri + parse_report; exit 0/1/2 (clean/violations/missing-solibri). `tools/solibri/__main__.py` mahdollistaa `python -m tools.solibri verify`-komentoaja. Plan-spec puhuu `python -m dxf2ifc.tools.solibri`-paketista mutta tools/-kansio on repo-rootissa Tasks 5–9 kompositiosta, joten CLI on `tools.solibri`-namespacessa. 4 uutta CLI-testiä (`25a38f4`). ✅ Section 3 (Tasks 8–10) valmis.
- Plan F Task 11: `tests/snapshots/solibri/full_kylmaelement.json` baseline-snapshot RuleResult-skeemalla; tällä hetkellä `results: []` koska full-fixture passaa cleanisti. 4 uutta testiä (existence + metadata + schema + clean) (`b7de018`).
- Plan F Task 12: `tools/solibri/diff_snapshot.py` `SnapshotDelta`-dataclass + `diff(baseline, current)` joka käyttää (rule_name, severity, ifc_guid, message)-fingerprintiä järjestys-riippumattomaan vertailuun. 5 uutta testiä (`ae3e411`).
- Plan F Task 13: `solibri` pytest-marker `pyproject.toml`:ssa + `tests/conftest.py:pytest_collection_modifyitems` skippaa kaikki marker-testit kun `Solibri.exe` ei PATH:ssa. tests/test_solibri_snapshot_chain.py ajaa täysketjun verify→parse→diff vs. baseline (`cbb3d76`). ✅ Section 4 (Tasks 11–13) valmis.
- Plan F Task 14: `.github/workflows/build.yml` Linux-jobiin uusi "Plan F quality gate"-step joka ajaa `uv sync --all-extras` + `uv run pytest tests/test_quality.py`. 1 uusi workflow-testi (`d6c78bd`).
- Plan F Task 15: `docs/quality-gates.md` two-tier prosessikuvaus suomeksi (Taso 1: ifcopenshell.validate-gate, Taso 2: Solibri-snapshot-verify); release-flow-tarkistuslista linkittää packaging-smoke.md:hen ja solibri-rules.md:hen. 2 uutta testiä (`fb7487d`).
- Plan F Task 16: plan-loppupiste — pytest 294 passed + 1 skipped (solibri-marker), coverage 91 %, `ruff format` applied 18 tiedostoon (uudet tiedostot pitkien rivien rikkomista varten), CLAUDE.md + README.md "Plan F ✅" -päivitys (`165a0db`). 🎉 Plan F 16/16 valmis. Ruff check edelleen flagaa `build/version_info.py` + `tests/test_spec_file.py` F821:t — pre-existing PyInstaller VS DSL placeholderit.
- **Bugfix 4** (`2f827ea`) — placement-bug 1000× world coords: ifcopenshell.api 0.8.5:n `geometry.edit_object_placement` defaultaa `is_si=True` joka kertoo matriisin translaation 1000:lla. Korjattu kaikki 9 paikkaa `is_si=False`. Bonus: dxf_reader LWPOLYLINE-vertexien OCS→WCS-muunnos (`entity.ocs().to_wcs()`). 3 uutta testiä.
- **Bugfix 5** (`230f327`) — mapper.layer_matches strippaa xref-pipe-prefixin (`KCM Kauhajoki|AR1241_US` → `AR1241_US`) kun pattern ei sisällä pipea. 4 uutta testiä.
- **Bugfix 6** (`b1df8c3`) — default-profiili laajennettiin 13 uudella säännöllä ARK / K-prefix arkkitehtilayer-nimille (AR1241_US, AR1242_IKKUNA, AR1245_LASIUS, AR1311_VS, AR1233_PILARI, AR1314_KAIDE, AR1317_TILAPORTAAT, AR1331_KIINTO, K-OVET, K-SEINÄT_VÄLISEINÄT, K-KALUSTEET-variantit, K-VALAISTUS). 13 uutta testiä. ✅ Bugfix kierros 2 valmis (314 passed).
- Plan H kirjoitettu (Mode B): skeleton (`8be315f`) + 6 sectionia + 22 task-riviä numeroitu globaalisti (`8c85f6a`); CLAUDE.md "Plan H 0/22"-päivitys (sama commit). PROGRESS.md koko Plan H -checklist.
- Plan H Task 1: `build_ifc_project_skeleton` sai `schema: str = "IFC4"`-kwargin joka välitetään `ifcopenshell.api.run("project.create_file", version=schema):lle`. 2 uutta testiä (default IFC4 + opt-in IFC4X3) (`5b0d414`).
- Plan H Task 2: `convert_dxf` sai `schema`-kwargin joka välittyy skeletoniin. Full-fixture-pipeline tuottaa IFC4X3:n joka validoituu cleanisti + jokainen 11 IFC-luokkaa syntyy. 3 uutta testiä, koko 319 passed (`069f08e`).
- Plan H Task 3: CLI `dxf2ifc convert --schema=ifc4x3`-flag (choices ifc4/ifc4x3, default ifc4); välittyy convert_dxf:lle .upper()-muodossa. 2 uutta testiä (`c594e9e`).
- Plan H Task 4: `validate_ifc.summary` jo dynaaminen `ifc.schema`-kentälle; 2 regression-testiä lukitsi IFC4X3:n + IFC4:n näyttäminen summaryssä (`83d6ddc`). ✅ Section 1 (Tasks 1–4) valmis.
- Plan H Task 5: `tools/rava/sync_codes.py` 4-codeset-sync (urllib stdlib, mock-friendly fetch_json) + cli_main + `python -m tools.rava.sync_codes`. 4 uutta testiä (`326633e`).
- Plan H Task 6: stub JSON:t neljälle RAVA-codesetille `src/dxf2ifc/profiles/rava/`-kansiossa (LVI-TUOTEOSA: 11 verifioitua koodia, TALOTEKNIIKKA-TUOTEOSA: 2 koodia, kaksi placeholderia). 3 uutta testiä (`31ecdb8`).
- Plan H Task 7: `dxf2ifc.profiles.rava.loader.load_rava_codes() -> dict[str, RAVACode]` kokoaa kaikki 4 JSON:ää codeValue-keyksiin; RAVACode-dataclass (code/name/codeset). 4 uutta testiä (`fd9e8e5`). ✅ Section 2 (Tasks 5–7) valmis.

**Kesken:** Plan H Task 8 — Rule.domain laajennus.

**Blokkerit:** ei.
