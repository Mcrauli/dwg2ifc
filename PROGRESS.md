# PROGRESS

Volatile state — current build + known facts + open todos. Yksityiskohtainen
versiohistoria löytyy [`CHANGELOG.md`](CHANGELOG.md):stä, ja Plan A→H +
Build #1–#36 -arkisto on [`docs/PROGRESS-archive.md`](docs/PROGRESS-archive.md):ssä.

## Current state — v0.2.0-alpha20 (2026-05-12)

Tuorein julkaistu: **v0.2.0-alpha20** (2026-05-12).
Pre-release-vaiheessa GitHub Releases:ssä — itsepäivitysbanneri tarjoaa
sen automaattisesti kun käyttäjä avaa GUI:n.

Pakkaukset:
- `dxf2ifc-Setup-0.2.0a20.exe` — Inno Setup -installer
- `dxf2ifc-0.2.0a20.exe` — paljas exe
- `*.sha256` -checksumit + `LICENSES.md`

Alpha8–20:n korjaukset tiivistettynä (täysi historia
[`CHANGELOG.md`](CHANGELOG.md):ssä):

- **alpha20** (2026-05-12): Poistettu skip-ACIS-toggle GUI:sta + CLI:stä.
  Alpha17:n hätäkorjaus ei enää tarpeen (alpha18:n MagiCAD-skip
  ratkaisi varsinaisen ongelman). Sisäinen `preprocess_acis`-parametri
  jää testikäyttöön.
- **alpha19** (2026-05-12): 6 uutta sähkövaruste-mappausta (CO2-anturi,
  CO2-sireeni, Huolto-PC, RK-JK10, Säädinkeskus, hätäseispainike) →
  IfcSensor/Alarm/CommunicationsAppliance/ElectricDistributionBoard/
  Controller/SwitchingDevice + RAVA-tilavarauskoodit T-TATE-02-01-003/004.
  IFC4-yhteensopivuus korjattu (IfcDistributionBoard→IfcElectricDistributionBoard,
  PROGRAMMABLECONTROLLER→PROGRAMMABLE). Suunnitelma:
  [`docs/plans/2026-05-12-varusteet-design.md`](docs/plans/2026-05-12-varusteet-design.md).
- **alpha18** (2026-05-11): Skip MagiCAD-blokit accoreconsolen LISP-
  Phase 2:sta kun `--magicad-ifc` on annettu. Korjaa AutoCAD-CER-popupin
  kollegan koneella jossa FULL-MagiCAD-ARX latautuu. Lisäksi
  diagnostiikka-polku tulostuu preview-lokiin kun accoreconsole exit
  != 0.
- **alpha17** (2026-05-11): Skip-ACIS-toggle GUI-checkboxina + CLI-flagina
  `--skip-acis`. Käyttäjä voi nyt ohittaa accoreconsole-prosessin
  käynnistämisen yhdellä klikillä — auttaa kun AutoCAD-crash-report
  vilkkuu jokaisen konversion yhteydessä, tai kun DXF sisältää vain
  dynamic-block / INSERT-pohjaista geometriaa. Valinta persistoituu
  QSettings:iin.
- **alpha16** (2026-05-11): `DISCIPLINE_LABELS["KYL"]` `"Jäähdytys"`
  → `"KYL"` yhden­mukaisuuden vuoksi AutoCAD-puolen layer-prefix:in
  kanssa. Vaikuttaa IfcProject.LongName, suunnittelualat-luokitukseen
  (project + per-tuote) ja Pset_Disciplineen.
- **alpha15** (2026-05-11): `Pset_Discipline.Discipline`
  lisätty IfcProject-tasolle Solibri-role-auto-detect-kokeena (defence-
  in-depth aiempien Pset_Project.Authorization / suunnittelualat /
  STEP-header / IfcApplication -signaalien lisäksi).
- **alpha14** (2026-05-11): POSITIO tunnistaa anonyymit `*U*`-blokit
  attribuuttien perusteella (NUMERO + TEKSTI). Orchestrator käyttää
  POSITIO-haussa INSERT.xy:tä mesh-bbox-keskipisteen sijaan.
- **alpha13** (2026-05-08): `dxf_contains_acis_bodies` skannaa block-
  definitiot, ei vain modelspacea — block-sisäiset 3DSOLIDit
  (KONEIKKO, valmistajakirjastot) löytyvät.
- **alpha12** (2026-05-08): Phase 2 STLOUT layer-filterillä (oli
  block-name-filter). Nested INSERT-rekursio + kaikki ACIS-tyypit.
- **alpha10–11**: DWG-input lopullisesti poistettu, default-profiili
  laajeni 49 sääntöön (KONEIKKO/CHILLER/KOMPLAUH/PAKASTEKAAPPI jne.).
- **alpha8–9**: cooling-equipment-rakentajat (`IfcChiller`,
  `IfcUnitaryEquipment`, `IfcCoil`), distribution-element-dispatch.

## Current pipeline

```
INPUT  .dxf  ─────────────────────────────────────────────┐
                                                          ↓
core/preprocessing.py    accoreconsole.exe + STLOUT 3DSOLID-bodyille
                          (per-handle binary STL → mesh)
                                                          ↓
core/dxf_reader.py       ezdxf-luenta:
                          - 3DSOLID via acis_meshes
                          - INSERT.virtual_entities() →
                            3DFACE + closed LWPOLYLINE -aggregaatio
                          - LWPOLYLINE/POLYLINE → LineGeometry
                          - 3DFACE / POLYFACE → MeshGeometry
                                                         ↓
core/mapper.py           apply_profile(): layer → IFC-tyyppi
core/positio.py          POSITIO-blokki → Koneikko/Laitetunnus
core/energy_specs.py     Excel/CSV → FI_Tekninen-merge
                                                         ↓
core/ifc_writer/         orchestrator → builders → IFC4 file
  ├─ skeleton            IfcProject → Site → Building → Storey
  ├─ classification      Talo2000 + RAVA-LVI/TATE + suunnittelualat
  ├─ mesh                IfcFacetedBrep / IfcTriangulatedFaceSet
  ├─ builders            add_wall / add_pipe / add_evaporator / …
  └─ orchestrator        convert_dxf() entry point
                                                         ↓
core/ifc_merger.py       (optional) merge MagiCAD-IFC into master
                          ifcopenshell.api.project.append_asset
                                                         ↓
core/quality.py          (optional) ifcopenshell.validate +
                          YTV/RAVA/Talo2000-säännöt
                                                         ↓
                         OUTPUT: master.ifc
```

## Known facts that must NOT be rediscovered

### accoreconsole + ARX

- **`accoreconsole.exe` ei voi ladata `.arx`-moduuleja** — Autodesk-rajoite,
  vahvistettu Autodesk-doc:eilla + 4 spike-iteraatiolla.
  `(arxload "MagiCAD_r25x64.arx")` palauttaa `ARXLOAD failed`.
  Sama rajoite koskee sekä DXF että DWG -formaattia. **Älä yritä uudelleen.**

### MagiCAD-osat — yksi oikea reitti

- **Kollega ajaa `-MAGIIFCCD`** AutoCAD:issa, dxf2ifc mergee tuotetun
  IFC:n master-IFC:hen `core/ifc_merger.py`:llä. DXF-syötteellä ei tarvita
  AutoCAD COM:ia lainkaan.
- DXF-puolen MAGI*-luokat + ACAD_PROXY_ENTITY skipataan automaattisesti
  kun `magicad_ifc_path` on annettu — estää duplikaatit.
- DWG-input poistettu v0.2.0-alpha10:ssä (kaikki COM-keystroke-yritykset
  hauraita; `-MAGIIFCCD` + merge on luotettavampi).

### accoreconsole-rajoitukset

- `.scr`-rivipuskuri on **hard-cap 2048 merkkiä** (bisektoitu).
  LISP-bodyt jaetaan top-level-formeiksi.

### Solibri auto-detect

- **Älä rakenna automaattista discipline-detectiä** — Solibri-puolen
  per-installation-asetus, ei IFC-kenttä. Jopa Granlund-referenssi ei
  tunnistu Lauri:n Solibrissa automaattisesti. Hyväksytty: yksi
  manuaalinen klikkaus suunnittelualan valintaan avatessa.

### Layer-mappaus-päätökset (lukittuja)

- **ARK-puoli** → Talo2000 (seinät, laatat, ovet, ikkunat)
- **TATE/Kylmälaite** → RAVA-LVI / RAVA-TATE (höyrystimet, putket, hyllyt)
- **EI multi-classification** — yksi luokitus per element
- **IFC4 default** — `--schema=ifc4x3` valittavissa

## Test-DXF/DWG:t

- `~/Downloads/suunnittelutyokalut/Drawing10.dxf` — 5 KYL-LEVYHYLLY
  3DSOLIDia (regressio-testi)
- `~/OneDrive - RADIKA OY/Tiedostot/4001_1krs.dxf` — 9 TIKASHYLLY +
  12 LEVYHYLLY + 15 HÖYRYSTIN, baseline-testi (ei MagiCAD)
- `~/OneDrive - RADIKA OY/Tiedostot/Drawing2.dxf` — 8 dynamic-block
  KYL-hyllyä (5 tikashylly + 3 levyhylly), alpha4–6:n test fixture
- `~/OneDrive - RADIKA OY/Tiedostot/teholuettelo 2.xlsx` — RefDesign
  energy spec (JK1 + JK2, slash-otsikot, sektiot), alpha7:n test fixture

## Open todos

- [ ] **Code signing**: SignPath OSS Foundation -hakemus jätetty 2026-05-04,
  odottaa hyväksyntää. `release.yml` opt-in-muodossa, aktivoituu kun
  4 secret/var asetettu. SmartScreen-kitka kunnes.
- [ ] **`builders.py` (1321 r)** — split into `add_*.py` modules per
  IFC-tyyppi. Vaiheittain (split-suunnitelma `docs/SPLIT_PLAN.md`:ssä).
- [ ] **`dxf_reader.py` (759 r)** — split per geometry kind
  (`insert_aggregator.py`, `polyline_reader.py`, `mesh_reader.py`).
- [ ] **GUI Profile Editor** ei näytä FI_*-kenttiä (TOML-edit toimii käsin).

## Known limitations

- **Vain DXF-input**: DWG-input poistettu v0.2.0-alpha10:ssä. Käytä
  AutoCAD:in `DXFOUT`:ia tai `-MAGIIFCCD` + merge-reittiä.
- **MagiCAD-osat**: tulevat IFC:hen vain kollegan `-MAGIIFCCD`-exportin
  kautta `--magicad-ifc`-mergellä. Pelkkä DXF + Object Enabler ei tuota
  semanttista MagiCAD-IFC:tä.
- **DXF data quality**: konvertteri ei vielä korjaa DXF:n sisäistä
  outlier-geometriaa (esim. yksittäinen 3DSOLID 800m irrallaan), vain
  varoittaa.
- **Solibri discipline auto-detect**: ei tueta — manuaalinen valinta
  avatessa.

## Roadmap

Plan A→H valmiit (ks. [`docs/PROGRESS-archive.md`](docs/PROGRESS-archive.md)).
Plan I (TrueNorth-rotaatio + lisä-MEP-koodit) ei kirjoitettu — toteutetaan
jos tarve syntyy.

## Releases

<https://github.com/Mcrauli/dxf2ifc/releases>
