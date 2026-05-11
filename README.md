# dxf2ifc

[![Latest release](https://img.shields.io/github/v/release/Mcrauli/dxf2ifc?include_prereleases&sort=semver)](https://github.com/Mcrauli/dxf2ifc/releases/latest)

**AutoCAD DXF → IFC 4 -konvertteri suomalaiseen kylmälaite- ja
LVI-suunnitteluun.** Layer-pohjainen mappaus tuottaa Talo2000-luokituksen
(ARK) ja RAVA-LVI / RAVA-TATE -luokituksen (TATE), 6 suomalaista
PropertySettiä per IFC-tuote (`FI_Asennus` / `FI_Geometria` /
`FI_Komponentti` / `FI_Tuote` / `FI_Tekninen` / `FI_Sijainti`), ja
Solibri-yhteensopivan IFC4-tiedoston yhdellä konversio-ajolla.

Nykyinen versio: **v0.2.0-alpha14** (2026-05-11). Pre-release-vaiheessa.

## Lataa (Windows)

Uusin Windows-build on aina [Releases-sivulla](https://github.com/Mcrauli/dxf2ifc/releases/latest):

- `dxf2ifc-Setup-vX.Y.Z.exe` — Inno Setup -installeri (per-user, ei
  UAC-promptia, Start-menu + valinnainen desktop-shortcut)
- `dxf2ifc-vX.Y.Z.exe` — paljas exe ilman asennusta (tuplaklikkaus
  käynnistää GUI:n)
- `*.sha256` — checksumit, vahvista PowerShellissä:

```powershell
Get-FileHash -Algorithm SHA256 dxf2ifc-Setup-vX.Y.Z.exe
```

> **Windows SmartScreen** näyttää "Windows protected your PC" -dialogin —
> binäärit eivät ole code-signattu pre-release-vaiheessa. Napauta
> **More info → Run anyway**. SignPath OSS Foundation -hakemus on jätetty
> ja allekirjoitus aktivoituu kun Foundation hyväksyy hakemuksen.

GUI:n itsepäivitys-banneri tarjoaa uudet pre-release-tagit automaattisesti
seuraavalla käynnistyksellä.

## Mitä se osaa

| Input | Tuotos |
|---|---|
| **DXF** (KYL-* layerit, dynamic blockit, 3DSOLID, 3DFACE, INSERT, polylinet) | IFC4 + Talo2000/RAVA + FI_*-PSet:t |
| **Energiateho-Excel** (xlsx/csv, valinnainen) | tehot → FI_Tekninen-merge POSITIO-linkityksen kautta |
| **MagiCAD-IFC** (kollegan `-MAGIIFCCD`-tuotos, valinnainen) | yhdistetään master-IFC:hen samaan storey:hin |

**KYL-LISP-elementit** (Lauri:n omat AutoLISP-piirtotyökalut):

- KYL-TIKASHYLLY → IfcCableCarrierSegment / CABLELADDERSEGMENT
- KYL-LEVYHYLLY → IfcCableCarrierSegment / CABLETRAYSEGMENT
- KYL-HÖYRYSTIMET → IfcEvaporator (T-LVI-01-01-023)
- KYL-LAUHDUTIN, KYL-KOMPRESSORI, KYL-JV-putket, jne.

Dynamic block -muotoiset hyllyt (anonyymit `*U*`-blockit joissa
`closed LWPOLYLINE` + `3DFACE`) luetaan ezdxf:n
`INSERT.virtual_entities()`-kautta — soveltaa INSERT-transformaation
automaattisesti, ei tarvitse accoreconsole:a tai AutoCAD COM:ia.

## MagiCAD-tuki

dxf2ifc ei yritä tuottaa MagiCAD-osille natiivia 3D-geometriaa
DXF:stä — käytä MagiCAD:in omaa IFC-exportia ja merge:ä:

1. **Kollega ajaa AutoCAD:in command-linelle `-MAGIIFCCD`** (FULL-MagiCAD).
   MagiCAD tuottaa korkealaatuisen IFC:n oikeilla
   `IfcDuctSegment` / `IfcAirTerminal` / MagiCAD-PSet:eillä.
2. **Lauri valitsee dxf2ifc-GUI:ssa DXF + tuon MagiCAD-IFC:n**.
   Konvertteri yhdistää ne yhdeksi master-IFC:ksi
   (`core/ifc_merger.py`, `ifcopenshell.api.project.append_asset`).
3. **DXF:n MagiCAD-osat (MAGI*-natiivit luokat + ACAD_PROXY_ENTITY)
   skipataan automaattisesti** kun MagiCAD-IFC on annettu, jotta
   ei tule duplikaatteja.

Ilman MagiCAD-IFC:tä DXF-puolen MAGI*-luokat lukeutuvat
`IfcBuildingElementProxy`-mesh:ksi (jos Object Enabler on luonut
mesh-renderin), muuten ne pudottautuvat pois.

## Käyttö

### CLI

```bash
uv run dxf2ifc convert input.dxf output.ifc
uv run dxf2ifc convert input.dxf output.ifc --magicad-ifc colleague.ifc
uv run dxf2ifc convert input.dxf output.ifc --energy-specs teholuettelo.xlsx
```

Lisävalinnat:

- `--profile polku.toml` — custom layer→IFC-tyyppi-mappaus
- `--validate` — `ifcopenshell.validate` + RAVA/Talo2000-säännöt
- `--schema ifc4 | ifc4x3` (default `ifc4`)
- `--floor-elevation 12000` — 1.krs absoluuttinen Z-korko (mm)

### GUI

```bash
uv pip install -e ".[gui]"
dxf2ifc-gui   # tai: python -m dxf2ifc.gui
```

GUI tukee: DXF/DWG-tiedoston valinnan, layerien esikatselun +
luokitus-resoluution, energiateho-Excel:n + MagiCAD-IFC:n
filepicker:in, taustasäikeen konversion, profiilin editoinnin
(Profile → Edit profile…), itsepäivityksen GitHub Releases:istä,
ja 1.krs-koron säätämisen.

## Tekniikka

- Python 3.12+
- `ezdxf 1.4+` — DXF-parsinta + ACIS (SAT/SAB)
- `ifcopenshell 0.8+` — IFC4-kirjoitus + `project.append_asset`
- `pydantic 2` — profiili-skeeman validointi
- `openpyxl` — energiateho-Excel
- `PySide6` — GUI (`gui`-extra)
- PyInstaller + Inno Setup — Windows-jakelu

## Dokumentaatio

| | Mihin |
|---|---|
| **Käyttäjälle** | Tämä README + GUI-tooltipit |
| **Kontribuutio / arkkitehtuuri** | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| **MagiCAD-merge-ratkaisun historia** | [`docs/DWG_MAGICAD_PREPROCESSING.md`](docs/DWG_MAGICAD_PREPROCESSING.md) |
| **Claude / fresh sessio** | [`CLAUDE.md`](CLAUDE.md) + [`docs/CLAUDE_TASKS.md`](docs/CLAUDE_TASKS.md) |
| **Volatile state + open todos** | [`PROGRESS.md`](PROGRESS.md) |
| **Versiohistoria** | [`CHANGELOG.md`](CHANGELOG.md) |
| **Plan A→H -spec (historiallinen)** | [`docs/plans/`](docs/plans/) |
| **Build #1–#36 -arkisto** | [`docs/PROGRESS-archive.md`](docs/PROGRESS-archive.md) |

## Lisenssi

MIT — [`LICENSE`](LICENSE). Tekijä: **Lauri Rekola**.
