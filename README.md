# dxf2ifc

**AutoCAD DXF → IFC 4 -konvertteri suomalaiseen kylmälaite- ja LVI-suunnitteluun. Tarjoaa Talo2000-luokittelun ja oikeat IFC-tyyppitiedot layer-pohjaisen mappauksen kautta.**

## Status

✅ **Plan A 21/21 + Plan B 50/50 + Plan C 12/12 + Plan D 25/25** — koko Talo2000-elementtisetti tuetaan, kylmäjärjestelmät on ryhmitelty IfcSystem-entiteeteiksi (Refrigeration LT/MT, Drainage, Cable carriers, Refrigeration plant) IfcRelAssignsToGroup-relaatiolla, ja PySide6-pohjainen desktop-GUI wrappaa CLI-coren (layer-preview, profiili-editori, taustasäikeen konversio). Pytest 200 ✅, coverage 89 %, `ifcopenshell.validate.validate` ei-ERROR full-fixture-suiteessa, ruff clean. Seuraava askel ja per-task SHA-historia: [`PROGRESS.md`](PROGRESS.md).

| Vaihe | Tila |
|---|---|
| Design-spec | ✅ valmis |
| Plan A: Core CLI wall pipeline | ✅ 21/21 |
| Plan B: Full element set | ✅ 50/50 |
| Plan C: IfcSystem-ryhmittely | ✅ 12/12 |
| Plan D: PySide6 GUI | ✅ 25/25 |
| Plan E: PyInstaller-pakkaus | ⏳ kirjoittamatta |
| Plan F: Spec verifiointi Solibrilla | ⏳ kirjoittamatta |

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
