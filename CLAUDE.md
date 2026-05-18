# dwg2ifc — projektikartta Claudelle

DWG/DXF → IFC4 -konvertteri suomalaiseen kylmälaite- ja LVI-suunnitteluun
(Talo2000 + RAVA-luokitus, 6 FI_*-PSettiä, Solibri-yhteensopiva).

> Projekti hyytyi nimellä `dxf2ifc` (v0.1.x–v0.2.0a37) mutta DWG on
> alpha21:stä lähtien ensisijainen syöte → v0.3.0a1:ssä rebrandattu
> `dwg2ifc`:ksi. Vanhat git-tagit + historialliset docit pysyvät
> `dxf2ifc`-nimellä viittaamassa silloiseen toteutukseen — älä lähde
> niitä rewriteamaan.

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

## Current pipeline

```
N x .dwg/.dxf (multi-floor)
  ↓  per file (jokainen → yksi IfcBuildingStorey):
  → core/dwg_preconvert.py            (DWG → DXF via accoreconsole + DXFOUT)
  → core/preprocessing.py             (accoreconsole + STLOUT 3DSOLID:eille)
  → core/dxf_reader.py                (ezdxf + INSERT.virtual_entities)
  → core/mapper.py                    (layer pattern → IFC-tyyppi)
  → core/positio.py + energy_specs.py (Koneikko/Laitetunnus + Excel-tehot)
  → Z-offset: world_z = floor_elev + dxf_z, storey_index tag
  ↓  yhdistetään:
  → core/ifc_writer/orchestrator.py   (skeleton + builders + classification)
  → core/ifc_merger.py                (optional: MagiCAD-IFC merge)
  → core/quality.py                   (optional: validate + RAVA/Talo2000)
  → output.ifc
```

`orchestrator.convert(files=[FileEntry(...), ...])` on pääentrypoint.
`convert_dxf(...)` säilyy yhden tiedoston shim:nä (legacy callers + tests).

Yksityiskohtainen pipeline: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Tärkeät tiedostot

| Tiedosto | Vastuu |
|---|---|
| `src/dwg2ifc/core/dwg_preconvert.py` | DWG → DXF preconversio (accoreconsole + DXFOUT) |
| `src/dwg2ifc/core/preprocessing.py` | accoreconsole + STLOUT 3DSOLID:eille (+ negatiivisen Z:n korjaus alpha35:stä) |
| `src/dwg2ifc/core/dxf_reader.py` | DXF-luenta + INSERT-aggregaatio (`_aggregate_3dface_from_insert`) |
| `src/dwg2ifc/core/mapper.py` | Layer-pattern → IFC-tyyppi |
| `src/dwg2ifc/core/energy_specs.py` | Excel/CSV → FI_Tekninen-merge |
| `src/dwg2ifc/core/positio.py` | POSITIO-blokki → Koneikko/Laitetunnus |
| `src/dwg2ifc/core/ifc_merger.py` | MagiCAD-IFC merge (optional) |
| `src/dwg2ifc/core/ifc_writer/orchestrator.py` | `convert` end-to-end |
| `src/dwg2ifc/core/ifc_writer/builders.py` | `add_*` per IFC-tyyppi |
| `src/dwg2ifc/core/ifc_writer/skeleton.py` | IfcProject → Site → Building → Storey |
| `src/dwg2ifc/core/ifc_writer/classification.py` | Talo2000 + RAVA + suunnittelualat |
| `src/dwg2ifc/core/ifc_writer/mesh.py` | IfcFacetedBrep / IfcTriangulatedFaceSet |
| `src/dwg2ifc/core/finnish_psets.py` | 6 FI_*-PSet:tä per tuote |
| `src/dwg2ifc/core/updater.py` + `gui/update_banner.py` | Itsepäivitys GitHub Releases:istä (alpha37:ssä cmd-launcher) |
| `src/dwg2ifc/profiles/default_kylmalaite.toml` | Default layer-mappaus (sis. KYL-KOTELO-säännön alpha36:sta) |
| `src/dwg2ifc/profiles/store.py` | Aktiivisen profiilin per-käyttäjä-persistointi (GUI:n "Tallenna") |
| `src/dwg2ifc/cli.py` | CLI entry point |
| `src/dwg2ifc/gui/main_window.py` | GUI (PySide6) |

Task-kohtainen lukulista: [`docs/CLAUDE_TASKS.md`](docs/CLAUDE_TASKS.md)
(viittaa vielä `dxf2ifc`-nimellä — sama sisältö, polut samat
src/dwg2ifc:n alla).

## Tärkeät opitut asiat (älä toista)

- **`accoreconsole.exe` ei voi ladata `.arx`-moduuleja** — Autodesk-rajoite.
  Älä yritä `(arxload "MagiCAD_*.arx")`.
- **DWG-syöte on tuettu** v0.2.0-alpha21:stä lähtien accoreconsole+DXFOUT-
  preconversiolla. EI keystroke-COM:ia (sen yritti alpha2..alpha10).
  Toteutus: `core/dwg_preconvert.py`.
- **Oikea reitti MagiCAD-osille**: kollega ajaa `-MAGIIFCCD` AutoCAD:issa,
  dwg2ifc mergee IFC:n `core/ifc_merger.py`:llä master-IFC:hen. MagiCAD-DWG-
  syöte EI tuota semanttisia osia (Object Enabler tuottaa 2D-fragmentteja).
  DXF-puolen MAGI*-luokat + ACAD_PROXY_ENTITY skipataan automaattisesti
  kun `magicad_ifc_path` on annettu.
- **AutoCADin STLOUT siirtää negatiiviset Z:t Z=0:aan** (alpha35:n
  korjaus). `preprocessing.py` lukee jokaisen ACIS-bodyn todellisen
  world-min-Z:n ezdxf:n ACIS-purulla (SAT+SAB) ja kumoaa siirron
  meshikohtaisesti. Älä yritä toista korjausta.
- **VLA / `vlax-ename->vla-object` ei toimi accoreconsolessa** — käytä
  cmd-batchia tai pure-AutoLISPiä headless-skripteissä.
- **Päivityslauncher**: alpha37:ssä vaihdettu hidden-powershell →
  cmd-batch (`timeout` + `start "" "<exe>"`). PowerShell-launcher kuoli
  hiljaisesti joillain Windows-asennuksilla.
- Historia ja umpikujat: [`docs/DWG_MAGICAD_PREPROCESSING.md`](docs/DWG_MAGICAD_PREPROCESSING.md).

## Komennot

```bash
# Testit
.venv/Scripts/python -m pytest -q

# CLI yhdellä tiedostolla (legacy single-floor, kerros = "1.krs" @ 0 mm)
.venv/Scripts/python -m dwg2ifc convert input.dwg output.ifc
.venv/Scripts/python -m dwg2ifc convert input.dxf output.ifc

# CLI multi-floor — --floor PATH[:LABEL[:ELEV_MM]] toistettavasti
.venv/Scripts/python -m dwg2ifc convert output.ifc \
    --floor 1krs.dwg:1.krs:0 \
    --floor 2krs.dwg:2.krs:3500

# CLI lisäoptiot
.venv/Scripts/python -m dwg2ifc convert input.dwg output.ifc --magicad-ifc colleague.ifc
.venv/Scripts/python -m dwg2ifc convert input.dwg output.ifc --energy-specs teho.xlsx

# GUI (monirivinen file-table — Lisää tiedosto(t)…)
.venv/Scripts/python -m dwg2ifc.gui

# Build (Windows)
.venv/Scripts/python -m PyInstaller build/dwg2ifc.spec --noconfirm
```

PyInstaller ~90 s. Inno Setup -installer: `scripts/build_installer.ps1`.

## Älä lue (token-säästö)

| Polku | Syy |
|---|---|
| `.venv/`, `__pycache__/`, `build/`, `dist/`, `.git/`, `tmp/` | Generoitu / tila / arkisto |
| `tests/` (koko hakemistoa) | Avaa vain relevantit testit |
| `src/` (koko puuta) | Yksi tiedosto kerrallaan |
| `docs/PROGRESS-archive.md` | Vanhaa Plan A-H -historiaa |
| `docs/plans/`, `docs/superpowers/` | Spec-tason design-doceja, ei nykytilakuvauksia |

Lisää konteksti vain silloin kun se on relevantti aktiiviselle tehtävälle.
[`docs/CLAUDE_TASKS.md`](docs/CLAUDE_TASKS.md) kertoo per-tehtävä mitä lukea.

## Working rules

- **Suomi chatissa, englanti** commit-viesteissä ja koodikommenteissa.
- **Auto mode default** — Lauri preferoi "execute > plan".
- **Suora push masteriin** sallittu (henkilökohtainen repo).
- **Commit trailer**: `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`
- **EI Radika Oy -mainintaa** uuteen koodiin/dokumentaatioon — Lauri:n
  henkilökohtainen projekti. Publisher = "Lauri Rekola", sisäinen namespace
  "Mcrauli".
- **EI multi-classification** — yksi luokitus per IFC-element.
- **EI Solibri-discipline-auto-detect** — manuaalinen valinta hyväksytty.
- **EI AutoCAD COM:ia missään** — vain `accoreconsole.exe` (3DSOLID-tess
  + DWG-preconversio alpha21:stä lähtien).
- **DWG-syöte OK**, MagiCAD-DWG ei. MagiCAD-osat: kollegan `-MAGIIFCCD`
  + `--magicad-ifc`-merge.

## Dokumentaation ylläpitosääntö

Kun muutat koodia, tarkista aina pitääkö päivittää `README.md`,
`PROGRESS.md`, `CHANGELOG.md`, `CLAUDE.md` tai `docs/*.md`. Jos muutos
vaikuttaa käyttäjän workflow:hon, CLI-optioihin, GUI:hin, pipelineen,
MagiCAD/DWG-polkuun, releaseen tai mapper-profiileihin, **dokumentit
päivitetään samassa commitissa kuin koodi**.

**Definition of Done**: muutos ei ole valmis ennen kuin testit menevät
läpi *ja* dokumentit vastaavat koodin nykytilaa.

## Visuaalinen design (GUI)

Slate-gradient, amber/blue aksentit. Fontit: Inter / Space Grotesk /
JetBrains Mono. Värit + fontit lukittuja — älä lisää uusia ilman lupaa.
Tyylit: `src/dwg2ifc/gui/style.qss`.

## Liittyvät projektit

- `~/work/autocad-lisp-ohjeet` — KYL-* layer/blokki-nimet, POSITIO-blokki,
  klhylly.lsp, kotelo.lsp. Sivusto viittaa vielä `dxf2ifc.html`-nimellä
  (URL-pinnaus pysyy stabiilina kunnes erikseen päivitetään).
- `~/Downloads/RAVA3Pro - LVI - Pilottimalli - Kerrostalo - 2023-11-30.ifc`
  — FI_*-PSet-skeeman referenssi
- <https://talotekniikka-sovellus.tietomallintaja.fi/> — RAVA-koodisto

## Onboarding

Tämä CLAUDE.md + auto-loaded muisti `~/.claude/projects/.../memory/project_dxf2ifc.md`
(muistin slug säilyy historiallisena) antaa kaiken tarvittavan kontekstin.
Lisää syvyyttä:

- [`PROGRESS.md`](PROGRESS.md) — current state + open todos
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — pipeline-yksityiskohdat
- [`docs/CLAUDE_TASKS.md`](docs/CLAUDE_TASKS.md) — per-tehtävä lukulista
- [`docs/DWG_MAGICAD_PREPROCESSING.md`](docs/DWG_MAGICAD_PREPROCESSING.md) — MagiCAD-totuus
- [`CHANGELOG.md`](CHANGELOG.md) — versiohistoria
- [`docs/PROGRESS-archive.md`](docs/PROGRESS-archive.md) — Plan A→H + Build-historia
