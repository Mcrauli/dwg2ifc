# dwg2ifc — kehittäjän ja AI-agentin opas

`dwg2ifc` on AutoCAD **DWG/DXF → IFC4** -konvertteri suomalaiseen
kylmälaite- ja LVI-suunnitteluun: layer-pohjainen mappaus tuottaa
Talo2000-luokituksen (ARK), RAVA-LVI / RAVA-TATE -luokituksen (TATE),
6 suomalaista PropertySettiä per IFC-tuote ja Solibri-yhteensopivan
IFC4-tiedoston yhdellä konversioajolla.

Tämä tiedosto on **kehittäjille ja AI-agenteille** (Claude, Codex, …):
miten projekti toimii, miten sitä kehitetään ja mitä **ei kannata
keksiä uudelleen**. Loppukäyttäjälle suunnattu kuvaus on
[`README.md`](README.md):ssä.

> **Nimi vaihtui `dxf2ifc` → `dwg2ifc` versiossa v0.3.0a1.** Projekti
> syntyi DXF-syötteellä, mutta DWG on alpha21:stä lähtien ensisijainen
> syöte. Vanhat git-tagit (v0.1.x–v0.2.0a37) ja git-historia pysyvät
> `dxf2ifc`-nimellä — älä lähde niitä uudelleenkirjoittamaan.

## Pikastartti

Vaatimukset: **Python 3.12+** ja **[uv](https://docs.astral.sh/uv/)**.
DWG-syöte ja 3DSOLID-tessellaatio vaativat lisäksi paikallisen
**AutoCAD 2018+** -asennuksen (`accoreconsole.exe`); pelkkä DXF ilman
3DSOLIDeja toimii ilman AutoCADia.

```bash
uv sync --extra gui                      # asenna riippuvuudet (sis. GUI)
uv run pytest -q                         # aja testit
uv run dwg2ifc convert input.dwg out.ifc # CLI: yksi tiedosto
uv run dwg2ifc-gui                       # GUI (PySide6)
```

Testit voi ajaa myös suoraan venvistä: `.venv/Scripts/python -m pytest -q`.
Windows-build: `uv run pyinstaller build/dwg2ifc.spec --noconfirm` (~90 s).
Inno Setup -installer: `scripts/build_installer.ps1`.

## Golden rule (älä riko)

```
layer mapper          = metadata / semantiikka (mikä IFC-tyyppi tämä on)
geometry / mesh       = shape (miten kappale piirretään)
IFC writer            = output (miten se kirjoitetaan IFC:hen)
```

Pidä nämä kolme erillään:

- **STL / mesh / 3DSOLID EI ole metadatan lähde.** Se on pelkkä muoto.
- **Parserin ei pidä päätellä IFC-luokkia geometriasta** — luokka tulee
  aina mapperista / profiilista layer-patternin perusteella.
- Jos lisäät uuden geometriastrategian, älä sotke layer-mappausta.
- Jos lisäät uuden IFC-tyypin, älä lisää geometriayksityiskohtia mapperiin.

| Kerros | Vastuu | Älä |
|---|---|---|
| **Mapper** | layer pattern → IFC-tyyppi + metadata | älä koske geometriaan |
| **Geometry / mesh** | shape (mesh, extrusion, brep) | älä koske mappaukseen |
| **IFC writer** | output (entiteetit, PSet:t, classification) | älä päättele tyyppiä uudelleen |

## Pipeline

```
N x .dwg/.dxf (multi-floor)
  ↓  per file (jokainen → yksi IfcBuildingStorey):
  → core/dwg_preconvert.py            (DWG → DXF via accoreconsole + DXFOUT)
  → core/preprocessing.py             (accoreconsole + STLOUT 3DSOLID:eille)
  → core/dxf_reader.py                (ezdxf + INSERT.virtual_entities)
  → core/mapper.py                    (layer pattern → IFC-tyyppi)
  → core/positio.py + energy_specs.py (Koneikko/Laitetunnus + Excel-tehot)
  → core/block_attribs.py             (INSERT-ATTRIB → FI_Tuote/Komponentti/Tekninen)
  → Z-offset: world_z = floor_elev + dxf_z, storey_index tag
  ↓  yhdistetään:
  → core/ifc_writer/orchestrator.py   (skeleton + builders + classification)
  → core/ifc_merger.py                (optional: MagiCAD-IFC merge)
  → core/quality.py                   (optional: validate + RAVA/Talo2000)
  → output.ifc
```

`orchestrator.convert(files=[FileEntry(...), ...])` on pääentrypoint.
`convert_dxf(...)` on yhden tiedoston legacy-shim (testit + vanhat
kutsujat). Yksityiskohtainen pipeline: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Tärkeät tiedostot

| Tiedosto | Vastuu |
|---|---|
| `src/dwg2ifc/core/dwg_preconvert.py` | DWG → DXF preconversio (accoreconsole + DXFOUT) |
| `src/dwg2ifc/core/preprocessing.py` | accoreconsole + STLOUT 3DSOLID:eille (+ negatiivisen Z:n korjaus) |
| `src/dwg2ifc/core/dxf_reader.py` | DXF-luenta + INSERT-aggregaatio (`_aggregate_3dface_from_insert`) |
| `src/dwg2ifc/core/mapper.py` | Layer-pattern → IFC-tyyppi |
| `src/dwg2ifc/core/block_attribs.py` | INSERT-ATTRIB → FI_Tuote / FI_Komponentti / FI_Tekninen |
| `src/dwg2ifc/core/energy_specs.py` | Excel/CSV → FI_Tekninen-merge |
| `src/dwg2ifc/core/positio.py` | POSITIO-blokki → Koneikko/Laitetunnus |
| `src/dwg2ifc/core/finnish_psets.py` | 6 FI_*-PSet:tä per tuote |
| `src/dwg2ifc/core/ifc_merger.py` | MagiCAD-IFC merge (optional) |
| `src/dwg2ifc/core/ifc_writer/orchestrator.py` | `convert` end-to-end |
| `src/dwg2ifc/core/ifc_writer/builders.py` | `add_*` per IFC-tyyppi |
| `src/dwg2ifc/core/ifc_writer/skeleton.py` | IfcProject → Site → Building → Storey |
| `src/dwg2ifc/core/ifc_writer/classification.py` | Talo2000 + RAVA + suunnittelualat |
| `src/dwg2ifc/core/ifc_writer/mesh.py` | IfcFacetedBrep / IfcTriangulatedFaceSet |
| `src/dwg2ifc/profiles/default_kylmalaite.toml` | Default layer-mappaus |
| `src/dwg2ifc/profiles/schema.py` | Profiili-skeema (pydantic) |
| `src/dwg2ifc/core/updater.py` + `gui/update_banner.py` | Itsepäivitys GitHub Releases:istä |
| `src/dwg2ifc/cli.py` | CLI entry point |
| `src/dwg2ifc/gui/main_window.py` | GUI (PySide6) |

## Näin teet tavallisimmat muutokset

Per-tehtävä lukulista — minkä tiedostot avata ENSIN ja minkä jättää
lukematta — on [`docs/task-map.md`](docs/task-map.md):ssä. Pidä konteksti
pienenä; koko `src/`-puun lukeminen ei kannata. Lyhyesti:

| Tehtävä | Aloita tästä |
|---|---|
| Uusi layer / IFC-tyyppi-mappaus | `mapper.py` + `profiles/default_kylmalaite.toml` |
| DXF-luenta / entity-bugi | `dxf_reader.py` + `core/types.py` |
| 3DSOLID / mesh / geometria | `preprocessing.py` + `dxf_reader.py` + `geometry.py` |
| Uusi IFC-tyyppi / PSet | `ifc_writer/builders.py` + `orchestrator.py` + `finnish_psets.py` |
| Blokin ATTRIB-kentät | `block_attribs.py` ([`docs/BLOCK_ATTRIBS.md`](docs/BLOCK_ATTRIBS.md)) |
| Excel-tehot | `energy_specs.py` + `positio.py` |
| GUI | `gui/main_window.py` + kohdennettu widget |
| Release / build | `pyproject.toml`, `build/`, `.github/workflows/release.yml` |

## Kovalla työllä opitut asiat — ÄLÄ keksi uudelleen

- **`accoreconsole.exe` ei voi ladata `.arx`-moduuleja** — Autodesk-rajoite,
  vahvistettu doc:eilla + 4 spike-iteraatiolla. Älä yritä
  `(arxload "MagiCAD_*.arx")`.
- **MagiCAD-osille on yksi oikea reitti**: kollega ajaa AutoCAD:issa
  `-MAGIIFCCD`, dwg2ifc mergee tuotetun IFC:n master-IFC:hen
  `core/ifc_merger.py`:llä. Pelkkä DWG/DXF-syöte EI tuota semanttisia
  MagiCAD-osia (Object Enabler tuottaa 2D-fragmentteja). DXF-puolen
  MAGI*-luokat + ACAD_PROXY_ENTITY skipataan automaattisesti kun
  `--magicad-ifc` on annettu. Tausta: [`docs/DWG_MAGICAD_PREPROCESSING.md`](docs/DWG_MAGICAD_PREPROCESSING.md).
- **DWG-syöte** on tuettu accoreconsole + DXFOUT -preconversiolla
  (`core/dwg_preconvert.py`). EI keystroke-COM:ia — se yritettiin ja
  hylättiin.
- **AutoCADin STLOUT siirtää negatiiviset Z:t Z=0:aan.** `preprocessing.py`
  lukee jokaisen ACIS-bodyn todellisen world-min-Z:n ezdxf:n ACIS-purulla
  (SAT+SAB) ja kumoaa siirron meshikohtaisesti. Älä yritä toista korjausta.
- **accoreconsolen `.scr`-rivipuskuri on hard-cap 2048 merkkiä** — LISP-
  bodyt jaetaan top-level-formeiksi.
- **VLA / `vlax-ename->vla-object` ei toimi accoreconsolessa** — käytä
  cmd-batchia tai pure-AutoLISPiä headless-skripteissä.
- **AutoCADin anonyymit blokit (`*U#`) uudelleennumeroituvat** DXF-
  latauksessa (ezdxf `*U8` ≠ accoreconsole `*U7`). Worthlist-optimoinnit
  eivät saa nojata anonyymiblokin nimeen — ne räjäytetään aina.
- **Älä rakenna automaattista Solibri-discipline-detectiä** — se on
  Solibrin per-asennus-asetus, ei IFC-kenttä. Hyväksytty: yksi
  manuaalinen klikkaus suunnittelualan valintaan.
- **EI AutoCAD COM:ia missään** — vain `accoreconsole.exe` (headless).

## Tunnetut rajoitukset

- **DWG-syöte vaatii AutoCAD-asennuksen** (`accoreconsole.exe`). LT- tai
  AutoCAD-vapaalla koneella tulee selkeä virheilmoitus.
- **MagiCAD-osat** tulevat IFC:hen vain kollegan `-MAGIIFCCD`-exportin +
  `--magicad-ifc`-mergen kautta.
- **Solibri-discipline auto-detect** ei ole tuettu — manuaalinen valinta.
- Konvertteri varoittaa DXF:n outlier-geometriasta mutta ei korjaa sitä.

## Keskeneräistä / karkeat reunat

- `ifc_writer/builders.py` on iso (~1300 r) — voisi jakaa `add_*.py`-
  moduuleiksi per IFC-tyyppi. `add_*`-funktiot ovat jo itsenäisiä.
- `dxf_reader.py` on iso (~760 r) — voisi jakaa geometriatyypeittäin.
- GUI:n profiilieditori ei näytä FI_*-kenttiä (TOML-editointi käsin toimii).

Nämä ovat siistimistä, eivät bugeja — projekti toimii.

## Testit

~520+ pytest-testiä. Aja `uv run pytest -q`.

- `pytest.mark.accoreconsole` — vaatii `accoreconsole.exe`:n PATH:ssa.
  **End-to-end-testit jotka ajavat `convert_dxf`:n DWG/accoreconsole-
  reittiä myöten voivat failata koneella jossa accoreconsole-ympäristö
  ei ole täysin kunnossa** — se ei tarkoita että koodimuutos on rikki.
  Varmista epäselvässä tilanteessa `git stash`:lla failaako testi myös
  ilman muutostasi.
- `pytest.mark.solibri` — vaatii `Solibri.exe`:n.
- GUI-testit vaativat `QT_QPA_PLATFORM=offscreen` (asetettu conftestissa).
- Energy-spec- ja IFC-merger-testit ovat hermeettisiä (syntetisoivat
  syötteen `openpyxl` / `ifcopenshell.api`:lla).

## Työskentelyn konventiot

- **Suomi** chatissa ja dokumenteissa, **englanti** commit-viesteissä ja
  koodikommenteissa.
- **Suora push masteriin** sallittu (henkilökohtainen repo, ei PR-flowta).
- **Commit-trailer** AI-avusteisissa commiteissa:
  `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`
- **Versiopumppi** koskettaa neljää paikkaa: `pyproject.toml`,
  `src/dwg2ifc/_version.py`, `build/version_info.py` (2 kenttää) ja
  `CHANGELOG.md`. `v*.*.*`-tagin push laukaisee GitHub Actions
  -release-workflow:n joka rakentaa exe:n + julkaisee prereleasen.
- **Yksi luokitus per IFC-element** — ei multi-classificationia.
- **EI Radika Oy -mainintaa** uuteen koodiin/dokumentaatioon — projektin
  publisher on "Lauri Rekola", sisäinen namespace "Mcrauli".

## Dokumentaation ylläpito

Kun muutat koodia, tarkista pitääkö päivittää `README.md`, `AGENTS.md`,
`CHANGELOG.md` tai `docs/*.md`. Jos muutos vaikuttaa käyttäjän
workflow:hon, CLI/GUI:hin, pipelineen, MagiCAD/DWG-polkuun, releaseen tai
mapper-profiileihin, **dokumentit päivitetään samassa commitissa kuin
koodi**. Per-muutostyyppi tarkistuslista on
[`docs/task-map.md`](docs/task-map.md):n lopussa.

**Definition of Done**: muutos ei ole valmis ennen kuin testit menevät
läpi *ja* dokumentit vastaavat koodin nykytilaa.

## GUI-tyyli

PySide6. Slate-gradient-tausta, amber/blue-aksentit. Fontit Inter /
Space Grotesk / JetBrains Mono. Värit + fontit lukittuja — älä lisää
uusia ilman lupaa. Tyylit: `src/dwg2ifc/gui/style.qss`.

## Liittyvä projekti

[`autocad-lisp-ohjeet`](https://github.com/Mcrauli/autocad-lisp-ohjeet) —
Lauri Rekolan AutoLISP-piirtotyökalut, joista syntyvät `KYL-*`-layerit ja
-blokit ovat dwg2ifc:n pääsyöte. Jos `KYL-*`-layerien nimet tai
blokki-attribuutit muuttuvat siellä, `default_kylmalaite.toml` ja
`block_attribs.py` voivat tarvita päivitystä.

## Hakemistorakenne

```
src/dwg2ifc/        lähdekoodi (core/ = pipeline, gui/ = PySide6, profiles/ = layer-säännöt)
tests/              ~520 pytest-testiä
docs/               arkkitehtuuri + reference-aineisto
build/              PyInstaller-spec + Inno Setup + version_info
scripts/            build/release-skriptit (PowerShell + bash)
tools/              rava/ = koodistosynkkaus, solibri/ = BCF-export
.github/workflows/  build.yml (CI) + release.yml (tag → release)
```
