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

✅ **Plan A 21/21 + Plan B 50/50 + Plan C 12/12 + Plan D 25/25 + Plan E 23/23 + Plan F 16/16 + Plan H 22/22** — koko Talo2000-elementtisetti tuetaan, kylmäjärjestelmät on ryhmitelty IfcSystem-entiteeteiksi (Refrigeration LT/MT, Drainage, Cable carriers, Refrigeration plant) IfcRelAssignsToGroup-relaatiolla, PySide6-pohjainen desktop-GUI wrappaa CLI-coren (layer-preview, profiili-editori, taustasäikeen konversio, preview/log-paneeli), Windows `.exe` jaetaan tag-pohjaisen draft-releasen kautta GitHub Actions -workflow:lla, IFC-luovutus käy kahden tason laatuportin läpi (`ifcopenshell.validate` + YTV Talo2000- ja RAVA-warning automaattisesti CI:ssä, Solibri-snapshot-verify Lauri-driven ennen tag-releasea — ks. [`docs/quality-gates.md`](docs/quality-gates.md)) ja IFC 4.3 -skeema + suunnitteluala-domainit (ARK Talo2000, TATE RAVA-LVI / RAVA-TATE) ovat saatavilla `--schema=ifc4x3`-flagillä ja default-profiilin `domain`-kentillä (ks. [`docs/rava-classification.md`](docs/rava-classification.md)). Pytest 302 ei-GUI ✅ ruff format clean. Seuraava askel ja per-task SHA-historia: [`PROGRESS.md`](PROGRESS.md).

| Vaihe | Tila |
|---|---|
| Design-spec | ✅ valmis |
| Plan A: Core CLI wall pipeline | ✅ 21/21 |
| Plan B: Full element set | ✅ 50/50 |
| Plan C: IfcSystem-ryhmittely | ✅ 12/12 |
| Plan D: PySide6 GUI | ✅ 25/25 |
| Plan E: PyInstaller-pakkaus | ✅ 23/23 |
| Plan F: Spec verifiointi Solibrilla | ✅ 16/16 |
| Plan H: IFC 4.3 + RAVA-luokitus | ✅ 22/22 |
| Plan G: Coordinate System & georeferenced IFC | ⏳ Plan H:n jälkeen |

## Idea

Suomalaiset kylmälaite- ja LVI-suunnittelijat piirtävät AutoCADilla mutta tarvitsevat luovutuksen IFC BIM -mallina. Manuaalinen BIM-mallintaminen on hidasta ja Talo2000-luokittelu + IFC-tyyppitiedot ovat monimutkaisia. Tämä työkalu automatisoi muunnoksen.

Käyttäjä piirtää DXF:n tutuilla layer-nimillä ja työkalu generoi IFC 4 -tiedoston oikeilla Talo2000-koodeilla.

## Design

Koko design on dokumentissa [`docs/superpowers/specs/2026-04-24-dxf2ifc-design.md`](docs/superpowers/specs/2026-04-24-dxf2ifc-design.md).

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
