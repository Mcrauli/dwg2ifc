# dxf2ifc — ohjeet Claudelle

DXF→IFC4-konvertteri suomalaisille kylmälaite-/LVI-suunnittelijoille
(Talo2000 + RAVA-luokitukset, Solibri-yhteensopiva). Volatile state +
build-historia: **`PROGRESS.md`**.

## Projektin rakenne

```
src/dxf2ifc/
  cli.py              komentorivisyöte
  __main__.py         python -m dxf2ifc … entrypoint
  core/
    dxf_reader.py     DXF luku (ezdxf) + 3DSOLID handler acis_meshes-väylällä
    geometry.py       Extrusion-dataclassit + extents_from_geometry
    ifc_writer.py     convert_dxf orchestrator + add_* tuoteputket  (ISO!)
    finnish_psets.py  FI_Asennus / Geometria / Komponentti / Tuote /
                      Tekninen / Sijainti
    positio.py        positiov2-blokin luku → Koneikko/Laitetunnus
    preprocessing.py  accoreconsole + STLOUT 3DSOLID-bodyille
    mapper.py         Layer-pattern → IFC-tyyppi (apply_profile)
    quality.py        ifcopenshell.validate + Talo2000/RAVA-säännöt
    types.py          Point3D, MeshGeometry, MappedEntity, …
  gui/                PySide6 (main_window, profile_editor, theme, …)
  profiles/
    default_kylmalaite.toml  oletusprofiili
    schema.py                pydantic-mallit + RAVA/Talo2000-validointi
    rava/                    koodisto-cache (JSON)
tests/                pytest, n. 460 testiä
tools/
  rava/               koodiston synkronointi
  solibri/            Solibri BCF-rule-export + verifiointi
build/dxf2ifc.spec    PyInstaller-spec
```

## Ydinriippuvuudet

- **ezdxf 1.4.3** — DXF + ACIS (SAT/SAB) parsinta
- **ifcopenshell 0.8** — IFC4 kirjoitus, pset-API
- **pydantic 2** — profiili-skeema + validointi
- **PySide6** — GUI (`gui`-extra)
- **pyinstaller** — bundlaus (`dev`-extra)

ACIS-bodyjen ulkoinen riippuvuus: `accoreconsole.exe` AutoCAD 2018+
asennuksesta (POSITIO-blokit + STLOUT-tessellaatio).

## IFC-skeema

**IFC4 default**, `--schema=ifc4x3` Plan H -valittavissa. Yksiköt mm.

## Komennot

```bash
# Testit
.venv/Scripts/python -m pytest -q

# CLI
.venv/Scripts/python -m dxf2ifc convert input.dxf output.ifc

# GUI
.venv/Scripts/python -m dxf2ifc.gui

# Build (Windows)
.venv/Scripts/python -m PyInstaller build/dxf2ifc.spec --noconfirm
Copy-Item dist/dxf2ifc.exe dist/dxf2ifc-0.1.0.exe -Force
```

## Latest delivery

**Build #28** (2026-04-30) ships:
- AutoCAD COM removed → accoreconsole+STLOUT
- 6 FI_*-PSetit per IFC-tuote
- POSITIO → Koneikko/Laitetunnus -linkitys
- Suunnittelualat-luokittelu (TATE/ARK)
- FI_Geometria Pituus hyllyille/putkille

## Token-säästöt Claudelle

Älä liitä:
- `.venv/`, `__pycache__/`, `build/`, `dist/`, `.git/`
- Koko `tests/` tai `src/`-puuta — yksi tiedosto kerrallaan riittää

Liitä:
- Yksi tiedosto + lyhyt kuvaus mitä haluat tehdä
- Pitkien tiedostojen kohdalle voi merkitä `# TÄMÄ MUUTETAAN` -kommentilla

## Visuaalinen design (GUI)

Slate-gradient, amber/blue aksentit; fontit Inter / Space Grotesk /
JetBrains Mono. Värit ja fontit on lukittuja — älä lisää uusia.
Värilista + tyylit: katso aiempi CLAUDE.md tai `gui/style.qss`.

## Työtavat

- Suomi chatissa, englanti commit-viesteissä ja koodikommenteissa
- Auto mode default — Lauri preferoi "execute > plan"
- Commit-trailer: `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`
- Suora push masteriin sallittu

## Yhteydet muihin projekteihin

- `~/work/autocad-lisp-ohjeet` — KYL-* layer/blokki-nimet, POSITIO-blokin
  rakenne (NUMERO + TEKSTI attribuutit)
- `~/Downloads/RAVA3Pro - LVI - Pilottimalli - Kerrostalo - 2023-11-30.ifc`
  — FI_*-PSet-skeeman referenssi
- <https://talotekniikka-sovellus.tietomallintaja.fi/> — RAVA-koodisto

## Avoimet todoit

Nähtävillä `~/.claude/projects/.../memory/project_dxf2ifc.md`.
