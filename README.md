# dxf2ifc

[![Latest release](https://img.shields.io/github/v/release/Mcrauli/dxf2ifc?include_prereleases&sort=semver)](https://github.com/Mcrauli/dxf2ifc/releases/latest)

**AutoCAD DXF → IFC 4 -konvertteri suomalaiseen kylmälaite- ja LVI-suunnitteluun. Tarjoaa Talo2000-luokittelun ja oikeat IFC-tyyppitiedot layer-pohjaisen mappauksen kautta.**

## Lataa .exe (Windows)

Uusin Windows-build on aina [Releases-sivulla](https://github.com/Mcrauli/dxf2ifc/releases/latest).
Lataa `dxf2ifc-vX.Y.Z.exe` ja (suositeltava) `dxf2ifc-vX.Y.Z.exe.sha256`,
ja vahvista checksum PowerShellissä:

```powershell
Get-FileHash -Algorithm SHA256 dxf2ifc-vX.Y.Z.exe
```

Tuplaklikkaa `.exe` käynnistyäkseen GUI:n, tai aja PowerShellissä
`.\dxf2ifc-vX.Y.Z.exe convert input.dxf output.ifc` CLI:lle.

> **Windows SmartScreen** näyttää "Windows protected your PC" -dialogin —
> binäärit eivät ole code-signattu MVP-vaiheessa. Napauta **More info →
> Run anyway**. Allekirjoitus arvioidaan myöhemmissä versioissa.

## Status

**Build #28** (2026-04-30) — käytössä:

- Talo2000 + RAVA-LVI / RAVA-TATE -luokitus, IFC 4 default (`--schema=ifc4x3` saatavilla)
- 6 suomalaista PropertySettiä per IFC-tuote (FI_Asennus / FI_Geometria / FI_Komponentti / FI_Tuote / FI_Tekninen / FI_Sijainti)
- POSITIO-blokin lukeminen → automaattinen Koneikko + Laitetunnus -linkitys kylmälaitteille
- ACIS-bodyjen tessellaatio headlessisti `accoreconsole.exe`:lla — ei AutoCAD-ikkuna-poppia, ei recent-files-saastutusta
- IfcSystem-ryhmittely (Refrigeration LT/MT, Drainage, Cable carriers, Refrigeration plant)
- "suunnittelualat" -luokittelu (TATE/ARK) per tuote — Solibri ei enää päättele ARK:ksi
- PySide6-GUI: layer-preview, profiili-editori, taustasäikeen konversio, CRS-dialogi
- ETRS-TM35FIN georeferensointi (`EPSG:3067`), geometria LOCAL
- Laaduntarkistus: `ifcopenshell.validate` + YTV/RAVA-säännöt + Solibri-snapshot
- Windows `.exe` GitHub Releases -tag-pohjaisesti
- 440 testiä passes

Per-rakennus-historia ja roadmap: [`PROGRESS.md`](PROGRESS.md). Plans A→H -arkkitehtuuri-spec: [`docs/plans/`](docs/plans/).

## Idea

Suomalaiset kylmälaite- ja LVI-suunnittelijat piirtävät AutoCADilla mutta tarvitsevat luovutuksen IFC BIM -mallina. Manuaalinen BIM-mallintaminen on hidasta ja Talo2000-luokittelu + IFC-tyyppitiedot ovat monimutkaisia. Tämä työkalu automatisoi muunnoksen.

Käyttäjä piirtää DXF:n tutuilla layer-nimillä ja työkalu generoi IFC 4 -tiedoston oikeilla Talo2000-koodeilla.

## Design

Koko design on dokumentissa [`docs/plans/2026-04-24-dxf2ifc-design.md`](docs/plans/2026-04-24-dxf2ifc-design.md).

## Tech stack

- Python 3.12
- `uv` (paketinhallinta + venv)
- `ezdxf` (DXF-parsinta)
- `ifcopenshell` (IFC 4 -generointi)
- `pydantic` (profiili-TOMLien validointi)
- `pytest` + `ruff` (testit ja lint)
- `PySide6` (desktop GUI, LGPL — Plan D)
- PyInstaller (.exe-jakelu — Plan E)

## Käyttö

### CLI

```bash
uv run dxf2ifc convert --input pohja.dxf --output pohja.ifc
```

CLI lukee DXF:n, mappaa layerit oletusprofiililla (Talo2000) ja kirjoittaa IFC 4 -tiedoston. Custom-profiilin voi antaa `--profile polku.toml`.

### GUI (Plan D)

```bash
uv pip install -e ".[gui]"     # tai pipx install "dxf2ifc[gui]"
dxf2ifc-gui                    # tai: python -m dxf2ifc.gui
```

GUI tukee: DXF-tiedoston valinnan, layerien esikatselun + Talo2000-resoluution, konversion taustasäikeessä ja profiilin editoinnin (Profile → Edit profile…) suoraan käyttöliittymästä. Custom layer-säännöt voi tallentaa TOML-tiedostoon ja ladata uudelleen.

Screenshot tulee Lauri otosta dxf2ifc-gui:n käynnistämisen jälkeen: [`docs/screenshots/gui-main.png`](docs/screenshots/gui-main.png) (placeholder).
