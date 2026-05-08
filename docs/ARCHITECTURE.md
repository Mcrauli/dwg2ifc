# dxf2ifc — Architecture

Korkean tason yleiskuva. Ei spec, vaan pipeline-kartta jonka avulla
osaa lokalisoida muutoksen oikeaan moduuliin.

## Pipeline yhdellä silmäyksellä

```
┌────────────────────────────────────────────────────────────────────┐
│ INPUT                                                              │
├────────────────────────────────────────────────────────────────────┤
│  user.dxf  ──────────────────────────────────────────────┐         │
│                                                          ▼         │
├──────────────────────────────────────── DXF-pipeline ──────────────┤
│                                                                    │
│  core/preprocessing.py         accoreconsole.exe + STLOUT          │
│                                 3DSOLID/SURFACE/REGION → STL       │
│                                 → acis_meshes side-channel         │
│                                                                    │
│  core/dxf_reader.py            ezdxf-luenta:                       │
│                                 - 3DSOLID (acis_meshes)            │
│                                 - INSERT.virtual_entities()        │
│                                   → 3DFACE + LWPOLYLINE-extrusio   │
│                                 - LWPOLYLINE/POLYLINE (open/closed)│
│                                 - 3DFACE / POLYFACE / MESH         │
│                                 → list[EntityRecord]               │
│                                                                    │
│  core/mapper.py                apply_profile():                    │
│                                 layer pattern → IFC-tyyppi +       │
│                                 PredefinedType + system_name +     │
│                                 classification codes                │
│                                 → list[MappedEntity]               │
│                                                                    │
│  core/positio.py               POSITIO-blokit → (Koneikko,         │
│                                 Laitetunnus) per kylmälaite        │
│                                                                    │
│  core/energy_specs.py          Excel/CSV → FI_Tekninen-merge       │
│                                 (slash-otsikot, sektiot, FF)       │
│                                                                    │
├──────────────────────────────────────── IFC writer ────────────────┤
│                                                                    │
│  core/ifc_writer/skeleton.py        IfcProject → Site → Building   │
│                                      → list[IfcBuildingStorey]     │
│                                                                    │
│  core/ifc_writer/builders.py        per-tyyppi add_*-funktiot:     │
│                                      add_wall / add_pipe /         │
│                                      add_evaporator / etc          │
│                                                                    │
│  core/ifc_writer/mesh.py            IfcFacetedBrep (Brep) /        │
│                                      IfcTriangulatedFaceSet (mesh) │
│                                                                    │
│  core/ifc_writer/classification.py  Talo2000 + RAVA-LVI/TATE +     │
│                                      suunnittelualat (TATE/ARK)    │
│                                                                    │
│  core/finnish_psets.py              FI_Asennus / Geometria /       │
│                                      Komponentti / Tuote /         │
│                                      Tekninen / Sijainti           │
│                                                                    │
│  core/ifc_writer/orchestrator.py    convert_dxf() — yhdistää koko  │
│                                      ketjun, kutsuu builders:t,    │
│                                      lopuksi write_ifc()           │
│                                                                    │
├──────────────────────────────────────── Optional steps ────────────┤
│                                                                    │
│  core/ifc_merger.py            (optional) merge MagiCAD-IFC        │
│                                 master-IFC:hen append_asset:lla    │
│                                                                    │
│  core/quality.py               (optional, --validate) :            │
│                                 ifcopenshell.validate +            │
│                                 RAVA + Talo2000 + YTV-säännöt      │
│                                                                    │
├──────────────────────────────────────── Output ────────────────────┤
│  output.ifc                                                        │
└────────────────────────────────────────────────────────────────────┘
```

## Vastuujako (golden rule)

Pidä kolme kerrosta erillään:

| Kerros | Vastuu | Älä |
|---|---|---|
| **Mapper** | layer pattern → IFC-tyyppi + metadata | älä koske geometriaan |
| **Geometry / mesh** | shape (mesh, extrusion, brep) | älä koske mappaukseen |
| **IFC writer** | output (entiteetit, PSet:t, classification) | älä päättele tyyppiä uudelleen |

Esimerkki muutoksesta:

- "Lisää KYL-MUUNTIN-layer" → vain `mapper.py` + profile-TOML.
- "Hyllyjen 3DFACE-aggregaatio" → vain `dxf_reader.py`.
- "FI_Tekninen-kenttien laajennus" → vain `finnish_psets.py` + `energy_specs.py`.
- "Uusi IFC-tyyppi (esim. IfcChiller)" → `builders.py` + tarvittaessa
  `mesh.py` + `classification.py`. Mapperia kosketaan vain jos uusi
  layer-pattern.

## Side-channels

Pipeline välittää ylimääräistä tietoa side-channel:eilla — eivät kulje
`EntityRecord`-listana mutta `convert_dxf` orchestroi:

| Side-channel | Lähde → Kohde | Mitä |
|---|---|---|
| `acis_meshes` | `preprocessing.extract_acis_meshes()` → `dxf_reader.read_dxf(acis_meshes=...)` | per-handle binary STL-mesh:t 3DSOLID:eille |
| `proxy_layers` | accoreconsole LISP-manifest → `dxf_reader.read_dxf(proxy_layers=...)` | MAGI*-luokkien layer-tieto (ezdxf ei lue) |
| POSITIO `extra_props` | `positio.find_nearest_positio()` → `MappedEntity.extra_props` | Koneikko + Laitetunnus per kylmälaite |
| `energy_specs` lookup | `energy_specs.load_energy_specs()` → builder: `finnish_psets.add_finnish_psets()` | FI_Tekninen-kenttiarvot |

## Schema + units

- **IFC4 default**, `--schema=ifc4x3` valittavissa
- **Yksiköt mm** (IfcUnitAssignment LENGTHUNIT MILLI)
- **CRS**: ETRS-TM35FIN georeferensointi (`EPSG:3067`), geometria
  LOCAL-tasolla (Plan G, Mode A — IFC4)

## Profile (TOML)

`profiles/default_kylmalaite.toml` määrittelee layer-pattern → IFC-tyyppi
-mappauksen. Custom-profiilin voi antaa `--profile path.toml`. Skeema +
validointi `profiles/schema.py`-pydantic-modelilla.

```toml
[[rules]]
layer = "KYL-TIKASHYLLY"
ifc_type = "IfcCableCarrierSegment"
predefined_type = "CABLELADDERSEGMENT"
domain = "KYL"
talotekniikka_code = "T-TATE-01-01-001"
system_name = "Cable carriers"

[[rules.fi_komponentti]]
field = "Komponentti"
value = "Tikashylly"
```

## Rajat ulkomaailmaan

- **`accoreconsole.exe`** — AutoCAD 2018+ -asennuksen headless-ydin
  (3DSOLID-tessellaatio). Optional — DXF jossa ei 3DSOLID:eja toimii ilman.
- **`Solibri.exe`** — vain Plan F integration-testit (skipped jos ei
  PATH:ssa).
- **GitHub Releases API** — itsepäivitykseen (silent failure jos verkko
  off).
- **SignPath.io API** — code-signing (opt-in `release.yml`:ssä, ei
  aktivoitu ennen Foundation-hyväksyntää).

## Test-strategia

- ~520+ testiä `pytest`-pohjaisesti
- `pytest.mark.solibri` — vaatii Solibri.exe:n
- `pytest.mark.accoreconsole` — vaatii accoreconsole.exe:n
- GUI-testit: `pytest-qt` + `qtbot` + offscreen QPA platform
- Energy-spec testit: synteettinen Excel `openpyxl`-fixturella
- IFC-merger testit: hermeettiset, syntetisoivat IFC:t
  `ifcopenshell.api`:lla
