# dxf2ifc

**AutoCAD DXF → IFC 4 -konvertteri suomalaiseen kylmälaite- ja LVI-suunnitteluun. Tarjoaa Talo2000-luokittelun ja oikeat IFC-tyyppitiedot layer-pohjaisen mappauksen kautta.**

## Status

🚧 Plan A toteutuksessa (**13/21** tehtävää valmis). Seuraava askel ja per-task SHA-historia: [`PROGRESS.md`](PROGRESS.md).

| Vaihe | Tila |
|---|---|
| Design-spec | ✅ valmis |
| Plan A: Core CLI wall pipeline | 🟢 13/21 |
| Plan B: Full element set | ⏳ kirjoittamatta |
| Plan C: IfcSystem-ryhmittely | ⏳ kirjoittamatta |
| Plan D: PySide6 GUI | ⏳ kirjoittamatta |
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
