# Claude task map

Per-tehtävä lukulista — minkä tiedostot avata ENSIN ja minkä JÄTTÄÄ
LUKEMATTA. Pidä konteksti pienenä; lisää tiedostoja vain jos tehtävä
sitä vaatii.

## Layer mapping / profile

**Tehtävä**: lisää uusi layer, muuta IFC-tyyppi-mappausta, säädä
classification-koodeja, päivitä `default_kylmalaite.toml`.

Lue ensin:
- `src/dxf2ifc/profiles/default_kylmalaite.toml`
- `src/dxf2ifc/profiles/schema.py` (pydantic-mallit)
- `src/dxf2ifc/core/mapper.py` (`apply_profile`)

Älä lue:
- `core/dxf_reader.py`, `ifc_writer/builders.py`
- `gui/`-puuta

Testit: `tests/test_mapper.py`, `tests/test_profile_*.py`.

## DXF reading

**Tehtävä**: uusi entity-tyyppi, INSERT-aggregointi-bugi, polyline-
extrusion-säännöt, OCS/WCS-muunnokset.

Lue ensin:
- `src/dxf2ifc/core/dxf_reader.py` (759 r — huomaa että iso, mutta
  paikalliset muutokset ovat usein dispatch-tason `if dxftype == ...`-
  haaroissa)
- `src/dxf2ifc/core/types.py` (Point3D, MeshGeometry, BlockInstance, …)
- `src/dxf2ifc/core/geometry.py` (extrusion-dataclassit)

Älä lue:
- `ifc_writer/`-puuta

Testit: `tests/test_dxf_reader*.py` (dxf_reader, dxf_reader_proxy,
dxf_reader_polyface, dxf_reader_insert_3dface).

## MagiCAD / DWG / COM / Object Enabler -tehtävät

**Tehtävä**: mitä tahansa joka koskee MagiCAD-osia, DWG-tuen palauttamista,
AutoCAD COM:ia, render-only Object Enableria tai MAGIEXPLODE-ratkaisua.

Lue ensin:
- [`docs/DWG_MAGICAD_PREPROCESSING.md`](DWG_MAGICAD_PREPROCESSING.md) —
  historiallinen päätös ja säännöt.

**Tunne säännöt ennen koodimuutosta**:
- DWG-input ja `dwg_preconvert.py` on poistettu v0.2.0-alpha10:ssä.
  Älä palauta niitä ilman käyttäjän eksplisiittistä lupaa.
- AutoCAD COM / `pywin32` ei kuulu enää dependencyihin. Älä lisää
  takaisin ilman keskustelua.
- MagiCAD-osille ainoa luotettava reitti: kollegan `-MAGIIFCCD` + merge.

## MagiCAD-IFC merge (kollegan -MAGIIFCCD)

**Tehtävä**: kollegan tuottaman MagiCAD-IFC:n yhdistäminen master-IFC:hen,
append_asset, container-linkitys, MAGI*-skip DXF-puolella.

Lue ensin:
- [`docs/DWG_MAGICAD_PREPROCESSING.md`](DWG_MAGICAD_PREPROCESSING.md) —
  miksi DWG-input poistettiin ja miksi merge on oikea reitti
- `src/dxf2ifc/core/ifc_merger.py` (186 r — pieni, lue koko)
- `tests/test_ifc_merger.py`

Älä lue:
- `dxf_reader.py` (paitsi `skip_magicad`-lippuun liittyen)
- `ifc_writer/builders.py`

## Geometry extraction (3DSOLID, mesh, extrusion)

**Tehtävä**: 3DSOLID-tessellaatio, polyline-extrusion, INSERT-aggregaatio,
mesh-vertex-deduplikointi.

Lue ensin:
- `src/dxf2ifc/core/preprocessing.py` (accoreconsole + STL parser)
- `src/dxf2ifc/core/dxf_reader.py` — `_aggregate_3dface_from_insert`,
  `_record_from_entity`
- `src/dxf2ifc/core/geometry.py`

Älä lue:
- `mapper.py`, `ifc_writer/builders.py` — geometriastrategia ei vaikuta
  IFC-tyypin valintaan

Testit: `tests/test_acis_extraction.py`, `tests/test_dxf_reader_polyface.py`,
`tests/test_dxf_reader_insert_3dface.py`.

## IFC writer (builders, classification, PSets)

**Tehtävä**: uusi IFC-tyyppi (esim. IfcChiller), Brep/mesh-rep, PSet-
laajennus, suunnittelualat-luokitus.

Lue ensin:
- `src/dxf2ifc/core/ifc_writer/orchestrator.py` (733 r — kutsuu kaiken)
- `src/dxf2ifc/core/ifc_writer/builders.py` (1321 r — ISO, mutta
  `add_*`-funktiot ovat itsenäisiä; lue vain ne joita muutat)
- `src/dxf2ifc/core/ifc_writer/skeleton.py` (CRS + storey)
- `src/dxf2ifc/core/ifc_writer/mesh.py` (Brep helpers)
- `src/dxf2ifc/core/ifc_writer/classification.py`
- `src/dxf2ifc/core/finnish_psets.py`

Älä lue:
- `dxf_reader.py`, `dwg_preconvert.py`, `mapper.py`
- `gui/`

Testit: `tests/test_finnish_psets.py`, `tests/test_classification.py`,
`tests/test_mesh_writer*.py`, `tests/test_ifc_writer*.py`.

## Energy specs (Excel/CSV)

**Tehtävä**: alias-laajennus, slash-otsikoiden parsinta, sektio-
tunnistus, forward-fill, uusien Excel-pohjien tuki.

Lue ensin:
- `src/dxf2ifc/core/energy_specs.py` (589 r)
- `src/dxf2ifc/core/positio.py` (POSITIO-linkitys joka tuottaa lookup-
  avaimen)

Älä lue:
- `dxf_reader.py`, `ifc_writer/`

Testit: `tests/test_energy_specs.py`, `tests/test_positio.py`.

## GUI (PySide6)

**Tehtävä**: uusi filepicker, signal-rajapinnan muutos, profile-editori,
itsepäivitys-banneri, layer-table.

Lue ensin:
- `src/dxf2ifc/gui/main_window.py` (yhdistää kaiken)
- Kohdennettu widget-tiedosto: `file_panel.py`, `convert_worker.py`,
  `profile_editor.py`, `update_banner.py`, `layer_table.py`,
  `preview_log.py`

Älä lue:
- `core/`-puuta (ellei convert_worker tarvitse uutta core-API:a)
- `style.qss` (paitsi jos tehtävä on visuaalinen)

Testit: `tests/test_gui_*.py`.

GUI-testit vaativat: `os.environ["QT_QPA_PLATFORM"] = "offscreen"`.

## Packaging / release

**Tehtävä**: PyInstaller-spec, Inno Setup, GitHub Actions release-
workflow, version-bump, CHANGELOG-päivitys.

Lue ensin:
- `pyproject.toml`
- `build/dxf2ifc.spec`
- `build/installer.iss`
- `build/version_info.py`
- `scripts/build_installer.ps1`
- `.github/workflows/release.yml`
- `CHANGELOG.md` + `src/dxf2ifc/_version.py`

Älä lue:
- Lähdekoodia (paitsi jos versio-bump tai metadata)

## Quality gates

**Tehtävä**: `ifcopenshell.validate`-säännöt, RAVA-validointi, Solibri-
BCF-export, snapshot-chain.

Lue ensin:
- `src/dxf2ifc/core/quality.py`
- `tools/solibri/` (BCF-export + snapshot)
- [`docs/quality-gates.md`](quality-gates.md)
- [`docs/solibri-rules.md`](solibri-rules.md)

Älä lue:
- Builder/writer-puuta (paitsi jos validointi tarvitsee uuden tyypin)

Testit: `tests/test_quality*.py`, `tests/test_solibri*.py`.

## Memory

**Tehtävä**: Lauri:n mieltymysten / projektin tilan tallentaminen
muistiin, vanhan poisto.

Lue ensin:
- `~/.claude/projects/C--Users-LauriRekola/memory/MEMORY.md` (index)
- `~/.claude/projects/C--Users-LauriRekola/memory/project_dxf2ifc.md`
- Muut `feedback_*.md` / `project_*.md` jos relevantteja

Älä lue:
- POC v4 -tiedostoja jos kysymys on alpha7-tilasta

## Yleissääntö

**Älä skannaa koko repoa ellei käyttäjä pyydä tai task map ei riitä.**
Per-tehtävä-lukulista yllä riittää 95 %:iin muutoksista. Koko `src/`-
puun lukeminen tuhlaa kontekstia ja heikentää muutoksen täsmällisyyttä.

## Documentation sync checklist

Jokaisen koodimuutoksen jälkeen tarkista pitääkö päivittää dokumentit.
Muutos ei ole valmis ennen kuin dokumentit vastaavat koodin nykytilaa.

| Muutoksen luonne | Päivitä |
|---|---|
| CLI-komento / -optio | `README.md`, `CLAUDE.md` |
| GUI-käyttö (näkyvä) | `README.md`, tarvittaessa `docs/` |
| Pipeline-rakenne | `docs/ARCHITECTURE.md` |
| MagiCAD / DWG / Object Enabler / COM / MAGIEXPLODE | `docs/DWG_MAGICAD_PREPROCESSING.md`, `PROGRESS.md` |
| Mapper / profiili / layer-logiikka | `README.md`, `docs/ARCHITECTURE.md`, esimerkki­profiilit |
| Release / build / signing | `README.md`, `CHANGELOG.md` |
| Uusi feature | `CHANGELOG.md`, `PROGRESS.md` |
| Poistettu / hylätty feature | Merkitse kaikkialle selkeästi, ei ristiriitaisia ohjeita |
| Versiopumppi | `pyproject.toml`, `src/dxf2ifc/_version.py`, `CHANGELOG.md`, `README.md` "Nykyinen versio" -rivi, `PROGRESS.md` "Current state"-otsikko |

**Definition of Done**: testit menevät läpi ja dokumentit vastaavat
koodin nykytilaa. Jos joko-tai puuttuu, muutos on kesken.
