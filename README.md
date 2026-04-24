# dxf2ifc

**AutoCAD DXF → IFC 4 -konvertteri suomalaiseen kylmälaite- ja LVI-suunnitteluun. Tarjoaa Talo2000-luokittelun ja oikeat IFC-tyyppitiedot layer-pohjaisen mappauksen kautta.**

## Status

🚧 Plan A toteutuksessa (**13/21** tehtävää valmis).

| Vaihe | Tila |
|---|---|
| Design-spec | ✅ valmis |
| Plan A: Core CLI wall pipeline | 🟢 13/21 |
| Plan B: Full element set | ⏳ kirjoittamatta |
| Plan C: IfcSystem-ryhmittely | ⏳ kirjoittamatta |
| Plan D: PySide6 GUI | ⏳ kirjoittamatta |
| Plan E: PyInstaller-pakkaus | ⏳ kirjoittamatta |
| Plan F: Spec verifiointi Solibrilla | ⏳ kirjoittamatta |

### Plan A edistyminen

- ✅ Task 1 — Python 3.12 + uv asennus
- ✅ Task 2 — pyproject.toml + riippuvuudet
- ✅ Task 3 — pakettirunko (`src/dxf2ifc/`)
- ✅ Task 4 — tests/-kansio + conftest
- ✅ Task 5 — `Point3D`, `LineGeometry`, `EntityRecord` dataclassit
- ✅ Task 6 — `MappedEntity` dataclass
- ✅ Task 7 — `Profile` + `Rule` pydantic-skeemat (IFC4-lukittu)
- ✅ Task 8 — default profiili (ulkoseinäsääntö)
- ✅ Task 9 — profile loader (`importlib.resources`)
- ✅ Task 10 — `tests/fixtures/simple_wall.dxf`
- ✅ Task 11 — `dxf_reader.read_dxf` LINE-entiteeteille
- ✅ Task 12 — DXF readerin testit fixtuuria vasten
- ✅ Task 13 — `mapper.layer_matches` glob-mätsäri
- ⏳ Task 14 — `apply_profile` mapper
- ⏳ Task 15 — `line_to_wall_extrusion` 2D → 3D
- ⏳ Task 16 — IFC project skeleton (`IfcProject`/`Site`/`Building`/`Storey`)
- ⏳ Task 17 — `IfcWall` + Talo2000-luokitteluviittaus
- ⏳ Task 18 — `convert_dxf` end-to-end orchestrator
- ⏳ Task 19 — CLI (`dxf2ifc convert`)
- ⏳ Task 20 — integraatiotesti + `ifcopenshell.validate`
- ⏳ Task 21 — ruff-lint + täysi suite

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
