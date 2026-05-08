# dxf2ifc — projektikartta Claudelle

DXF → IFC4 -konvertteri suomalaiseen kylmälaite- ja LVI-suunnitteluun
(Talo2000 + RAVA-luokitus, 6 FI_*-PSettiä, Solibri-yhteensopiva).

## Golden rule (älä riko)

```
layer mapper          = metadata (mikä IFC-tyyppi tämä on)
geometry / mesh       = shape   (miten se piirretään)
IFC writer            = output  (miten se kirjoitetaan IFC:hen)
```

Pidä nämä kolme erillään. Jos lisäät uuden geometriastrategian, älä
sotke layer-mappausta. Jos lisäät uuden IFC-tyypin, älä lisää
geometriayksityiskohtia mapperiin.

## Current pipeline

```
.dxf
  → core/preprocessing.py             (accoreconsole + STLOUT 3DSOLID:eille)
  → core/dxf_reader.py                (ezdxf + INSERT.virtual_entities)
  → core/mapper.py                    (layer pattern → IFC-tyyppi)
  → core/positio.py + energy_specs.py (Koneikko/Laitetunnus + Excel-tehot)
  → core/ifc_writer/orchestrator.py   (skeleton + builders + classification)
  → core/ifc_merger.py                (optional: MagiCAD-IFC merge)
  → core/quality.py                   (optional: validate + RAVA/Talo2000)
  → output.ifc
```

Yksityiskohtainen pipeline: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Tärkeät tiedostot

| Tiedosto | Vastuu |
|---|---|
| `src/dxf2ifc/core/dxf_reader.py` (759 r) | DXF-luenta + INSERT-aggregaatio |
| `src/dxf2ifc/core/mapper.py` | Layer-pattern → IFC-tyyppi |
| `src/dxf2ifc/core/preprocessing.py` | accoreconsole + STLOUT |
| `src/dxf2ifc/core/energy_specs.py` (589 r) | Excel/CSV → FI_Tekninen-merge |
| `src/dxf2ifc/core/positio.py` | POSITIO-blokki → Koneikko/Laitetunnus |
| `src/dxf2ifc/core/ifc_merger.py` | MagiCAD-IFC merge (optional) |
| `src/dxf2ifc/core/ifc_writer/orchestrator.py` (733 r) | `convert_dxf` end-to-end |
| `src/dxf2ifc/core/ifc_writer/builders.py` (1321 r) | `add_*` per IFC-tyyppi |
| `src/dxf2ifc/core/ifc_writer/skeleton.py` | IfcProject → Site → Building → Storey |
| `src/dxf2ifc/core/ifc_writer/classification.py` | Talo2000 + RAVA + suunnittelualat |
| `src/dxf2ifc/core/ifc_writer/mesh.py` | IfcFacetedBrep / IfcTriangulatedFaceSet |
| `src/dxf2ifc/core/finnish_psets.py` | 6 FI_*-PSet:tä per tuote |
| `src/dxf2ifc/profiles/default_kylmalaite.toml` | Default layer-mappaus |
| `src/dxf2ifc/cli.py` | CLI entry point |
| `src/dxf2ifc/gui/main_window.py` | GUI (PySide6) |

Task-kohtainen lukulista: [`docs/CLAUDE_TASKS.md`](docs/CLAUDE_TASKS.md).

## MagiCAD-faktat (älä toista)

- **`accoreconsole.exe` ei voi ladata `.arx`-moduuleja** — Autodesk-rajoite.
  Älä yritä `(arxload "MagiCAD_*.arx")`.
- **DWG-input poistettiin v0.2.0-alpha10:ssä** kaikki keystroke-pohjaiset
  AutoCAD COM -ratkaisut osoittautuivat hauraiksi. Vain `.dxf`-input.
- **Oikea reitti MagiCAD-osille**: kollega ajaa `-MAGIIFCCD` AutoCAD:issa,
  dxf2ifc mergee IFC:n `core/ifc_merger.py`:llä master-IFC:hen.
- DXF-puolen MAGI*-luokat + ACAD_PROXY_ENTITY skipataan automaattisesti
  kun `magicad_ifc_path` on annettu (estää duplikaatit).
- Historia ja umpikujat: [`docs/DWG_MAGICAD_PREPROCESSING.md`](docs/DWG_MAGICAD_PREPROCESSING.md).

## Komennot

```bash
# Testit
.venv/Scripts/python -m pytest -q

# CLI
.venv/Scripts/python -m dxf2ifc convert input.dxf output.ifc
.venv/Scripts/python -m dxf2ifc convert input.dxf output.ifc --magicad-ifc colleague.ifc
.venv/Scripts/python -m dxf2ifc convert input.dxf output.ifc --energy-specs teho.xlsx

# GUI
.venv/Scripts/python -m dxf2ifc.gui

# Build (Windows)
.venv/Scripts/python -m PyInstaller build/dxf2ifc.spec --noconfirm
```

PyInstaller ~90 s. Inno Setup -installer: `scripts/build_installer.ps1`.

## Älä lue (token-säästö)

| Polku | Syy |
|---|---|
| `.venv/`, `__pycache__/`, `build/`, `dist/`, `.git/` | Generoitu / tila |
| `tests/` (koko hakemistoa) | Avaa vain relevantit testit |
| `src/` (koko puuta) | Yksi tiedosto kerrallaan |
| `docs/PROGRESS-archive.md` | 539 r, vanhaa Plan A-H -historiaa |
| `docs/plans/` | Spec-tason design-doceja, ei nykytilakuvauksia |

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
- **EI AutoCAD COM:ia missään** — vain `accoreconsole.exe` 3DSOLID-tess.
- **EI DWG-input-tukea** — vain `.dxf`. MagiCAD-osat tulevat erikseen
  `--magicad-ifc`-mergellä.

## Visuaalinen design (GUI)

Slate-gradient, amber/blue aksentit. Fontit: Inter / Space Grotesk /
JetBrains Mono. Värit + fontit lukittuja — älä lisää uusia ilman lupaa.
Tyylit: `src/dxf2ifc/gui/style.qss`.

## Liittyvät projektit

- `~/work/autocad-lisp-ohjeet` — KYL-* layer/blokki-nimet, POSITIO-blokki
- `~/Downloads/RAVA3Pro - LVI - Pilottimalli - Kerrostalo - 2023-11-30.ifc`
  — FI_*-PSet-skeeman referenssi
- <https://talotekniikka-sovellus.tietomallintaja.fi/> — RAVA-koodisto

## Onboarding

Tämä CLAUDE.md + auto-loaded muisti `~/.claude/projects/.../memory/project_dxf2ifc.md`
antaa kaiken tarvittavan kontekstin. Lisää syvyyttä:

- [`PROGRESS.md`](PROGRESS.md) — current state + open todos
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — pipeline-yksityiskohdat
- [`docs/CLAUDE_TASKS.md`](docs/CLAUDE_TASKS.md) — per-tehtävä lukulista
- [`docs/DWG_MAGICAD_PREPROCESSING.md`](docs/DWG_MAGICAD_PREPROCESSING.md) — MagiCAD-totuus
- [`CHANGELOG.md`](CHANGELOG.md) — versiohistoria
- [`docs/PROGRESS-archive.md`](docs/PROGRESS-archive.md) — Plan A→H + Build-historia
