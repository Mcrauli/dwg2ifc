# PROGRESS

Volatile state — current build + known facts + open todos. Yksityiskohtainen
versiohistoria löytyy [`CHANGELOG.md`](CHANGELOG.md):stä, ja Plan A→H +
Build #1–#36 -arkisto on [`docs/PROGRESS-archive.md`](docs/PROGRESS-archive.md):ssä.

## Current state — v0.2.0-alpha7 (2026-05-08)

Tuorein julkaistu: **v0.2.0-alpha7** (2026-05-07).
Pre-release-vaiheessa GitHub Releases:ssä — itsepäivitysbanneri tarjoaa
sen automaattisesti kun käyttäjä avaa GUI:n.

Pakkaukset:
- `dxf2ifc-Setup-0.2.0a7.exe` — Inno Setup -installer
- `dxf2ifc-0.2.0a7.exe` — paljas exe
- `*.sha256` -checksumit + `LICENSES.md`

## Current pipeline

```
INPUT
  ├─ .dxf  ─────────────────────────────────────────────┐
  └─ .dwg  → core/dwg_preconvert.py (AutoCAD COM)       │
              MAGIEXPLODE + EXPLODE + DXFOUT            │
              välitilanne-DXF                            │
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

### MagiCAD ja Object Enabler

- **MagiCAD Object Enabler on render-only** (Lauri:n koneella):
  ARX latautuu mutta `EXPLODE` ei tuota 3DSOLID-lapsia. `MAGIEXPLODE`
  tuottaa pelkkiä 2D-polylineja. **MagiCAD-osat pudottautuvat IFC:stä pois**
  pelkän Object Enabler:n kanssa.
- **FULL MagiCAD-lisenssi** tuottaa oikean 3D-geometrian `EXPLODE`-vaiheessa
  → tessellöityy `IfcBuildingElementProxy`-mesh:nä, mutta ilman MagiCAD:in
  semanttisia IFC-tyyppejä.
- **Suositeltu reitti**: kollega ajaa `-MAGIIFCCD` AutoCAD:issa, dxf2ifc
  yhdistää tuon IFC:n master-IFC:hen `core/ifc_merger.py`-modulilla.
  DXF-syötteellä **ei tarvita AutoCAD COM:ia** lainkaan.

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
- `~/OneDrive - RADIKA OY/Tiedostot/testimagi.dwg` — MagiCAD-DWG (POC v4)

## Open todos

- [ ] **Code signing**: SignPath OSS Foundation -hakemus jätetty 2026-05-04,
  odottaa hyväksyntää. `release.yml` opt-in-muodossa, aktivoituu kun
  4 secret/var asetettu. SmartScreen-kitka kunnes.
- [ ] **`builders.py` (1321 r)** — split into `add_*.py` modules per
  IFC-tyyppi. Vaiheittain (split-suunnitelma `docs/SPLIT_PLAN.md`:ssä).
- [ ] **`dxf_reader.py` (759 r)** — split per geometry kind
  (`insert_aggregator.py`, `polyline_reader.py`, `mesh_reader.py`).
- [ ] **`dwg_preconvert.py` (768 r)** — split COM-bootstrap erilleen
  AutoLISP-bodysta.
- [ ] **GUI Profile Editor** ei näytä FI_*-kenttiä (TOML-edit toimii käsin).
- [ ] **POSITIO-block-pattern** laajempi kattaus (nyt `positiov2*`).

## Known limitations

- **DWG-input**: vaatii AutoCAD asennettuna (COM Visible=False -istunto).
  Kokeellinen, ei core-pipelinen vakio-osa. Render-only Object Enabler
  -tilassa MagiCAD-osat pudottautuvat pois.
- **MagiCAD-osat ilman FULL-lisenssiä**: pudottautuvat pois IFC:stä.
  Suositeltu workaround: kollegan `-MAGIIFCCD`-export + `--magicad-ifc`-merge.
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
