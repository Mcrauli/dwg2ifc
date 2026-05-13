# dxf2ifc

[![Latest release](https://img.shields.io/github/v/release/Mcrauli/dxf2ifc?include_prereleases&sort=semver)](https://github.com/Mcrauli/dxf2ifc/releases/latest)

**AutoCAD DXF/DWG → IFC 4 -konvertteri suomalaiseen kylmälaite- ja
LVI-suunnitteluun.** Layer-pohjainen mappaus tuottaa Talo2000-luokituksen
(ARK) ja RAVA-LVI / RAVA-TATE -luokituksen (TATE), 6 suomalaista
PropertySettiä per IFC-tuote (`FI_Asennus` / `FI_Geometria` /
`FI_Komponentti` / `FI_Tuote` / `FI_Tekninen` / `FI_Sijainti`), ja
Solibri-yhteensopivan IFC4-tiedoston yhdellä konversio-ajolla.

Nykyinen versio: **v0.2.0-alpha22** (2026-05-13). Pre-release-vaiheessa.

## Multi-floor merge (alpha22)

Yksi konversio = N DXF/DWG-tiedostoa = N `IfcBuildingStorey`-kerrosta
yhteen IFC:hen. Käyttäjä asettaa per kerros labelin (`"1.krs"`,
`"2.krs"`, `"kellari"`, …) ja Z-koron (mm). Maailman Z =
`kerroksen_korko + DXF-objektin Z`, joten kun kaikki kerrokset @ 0 mm,
AutoCADin absoluuttiset Z-koordinaatit menevät IFC:hen sellaisinaan.

GUI:ssä on monirivinen taulukko (`Tiedosto` / `Kerros` / `Z (mm)`) +
"Lisää tiedosto(t)…"-nappi. CLI:ssä toistettava `--floor`-lippu.

Vanhat profiili-TOML:t jotka käyttävät `storey_z_levels_mm`-kenttää
eivät enää validoidu — poista rivi. GUI:n "Lisää 1.krs absoluuttinen
korko" -valintaruutu on myös poistettu (korko per kerros).

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
| **DXF / DWG** (KYL-* layerit, dynamic blockit, 3DSOLID, 3DFACE, INSERT, polylinet) | IFC4 + Talo2000/RAVA + FI_*-PSet:t |
| **Energiateho-Excel** (xlsx/csv, valinnainen) | tehot → FI_Tekninen-merge POSITIO-linkityksen kautta |
| **MagiCAD-IFC** (kollegan `-MAGIIFCCD`-tuotos, valinnainen) | yhdistetään master-IFC:hen samaan storey:hin |

DWG-syöte preconvertataan DXF:ksi headless `accoreconsole.exe + DXFOUT`
-kutsulla (sama tekniikka kuin 3DSOLID-tessellaatiossa) — vaatii
AutoCAD-asennuksen. MagiCAD-DWG ei ole tuettu syöte; käytä `-MAGIIFCCD`
+ `--magicad-ifc`-mergeä.

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
# Yksi tiedosto (kerros = "1.krs" @ Z=0)
uv run dxf2ifc convert input.dxf output.ifc
uv run dxf2ifc convert input.dwg output.ifc
uv run dxf2ifc convert input.dxf output.ifc --magicad-ifc colleague.ifc
uv run dxf2ifc convert input.dxf output.ifc --energy-specs teholuettelo.xlsx

# Monta tiedostoa (per kerros: PATH[:LABEL[:ELEV_MM]])
uv run dxf2ifc convert output.ifc \
    --floor 1krs.dwg:1.krs:0 \
    --floor 2krs.dwg:2.krs:3500 \
    --floor pohja.dwg:kellari:-3000
```

Lisävalinnat:

- `--profile polku.toml` — custom layer→IFC-tyyppi-mappaus
- `--validate` — `ifcopenshell.validate` + RAVA/Talo2000-säännöt
- `--schema ifc4 | ifc4x3` (default `ifc4`)
- `--floor-elevation 12000` — 1.krs absoluuttinen Z-korko (mm) yhden-tiedoston tapauksessa

`--floor` ja positional INPUT ovat toisensa poissulkevia: anna jompi kumpi.

### GUI

```bash
uv pip install -e ".[gui]"
dxf2ifc-gui   # tai: python -m dxf2ifc.gui
```

GUI:n päänäkymässä on monirivinen file-table (`Tiedosto / Kerros / Z (mm)`).
Klikkaa **"Lisää tiedosto(t)…"**, valitse yksi tai useampi DXF/DWG;
labelit oletusasennetaan `"1.krs"`, `"2.krs"`, … ja Z=0. Muokkaa
tarvittaessa. Lisäksi: layerien esikatselu + luokitus-resoluutio,
energiateho-Excel:n + MagiCAD-IFC:n filepicker:it, taustasäikeen
konversio, profiilin editointi (Profile → Edit profile…),
itsepäivitys GitHub Releases:istä.

### Input-formaatit

`.dxf` ja `.dwg` (DWG preconvertataan headless `accoreconsole.exe + DXFOUT`
-kutsulla, vaatii AutoCAD-asennuksen). MagiCAD-DWG ei ole tuettu
sisältö — käytä kollegan `-MAGIIFCCD`-IFC:tä + `--magicad-ifc`-mergeä.

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
