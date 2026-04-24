# dxf2ifc — Design Spec

**Date:** 2026-04-24
**Status:** Design approved, ready for implementation plan
**Owner:** Lauri Rekola

## Context

Lauri is a Finnish refrigeration/HVAC designer who draws refrigeration facility plans (cold rooms, freezer rooms, piping diagrams) in AutoCAD. Projects increasingly require IFC deliverables for BIM (per Talo2000 / YTV 2012 requirements), but manual BIM modelling alongside the existing 2D/3D AutoCAD drawings is slow and error-prone.

This project delivers a general-purpose desktop tool that converts DXF drawings into IFC 4 files with Finnish Talo2000 classification codes and correct IFC type information, targeted at refrigeration/HVAC designers who already work in AutoCAD but need IFC deliverables.

**Problems addressed:**
- Manual BIM authoring duplicates work already done in AutoCAD
- Talo2000 classification + IFC typing is complex — raises the entry bar to do correctly by hand
- No existing DXF→IFC converter specialises in refrigeration design with Finnish mapping rules

**Non-goals:**
- Full general-purpose BIM authoring
- Supporting every Talo2000 element type (scope is refrigeration + associated HVAC/MEP)
- Bidirectional IFC→DXF conversion
- Real-time collaboration / cloud features

## Decisions from brainstorming

| Decision | Choice |
|----------|--------|
| Scope | Cold storage (C) + HVAC/piping (D): walls, slabs, doors, shelves, equipment, pipes |
| Distribution | Desktop app with GUI |
| Tech stack | **Python + PySide6** — ifcopenshell and ezdxf are Python-native; PySide6 LGPL simplifies distribution |
| IFC schema | **IFC 4** — modern standard, rich MEP entity set, broadly supported by viewers |
| Layer mapping | **Hybrid**: built-in "Kylmälaite Talo2000" default profile, user may override and save a custom YAML/TOML profile |
| Geometry | **Hybrid**: 3D solids/extruded entities passed through directly, 2D lines/polylines extruded using layer-default heights |

## Goal (v0.1 MVP)

Working Windows desktop app that:
1. Opens a DXF file, reads layers and entities
2. Matches entities to the default "Kylmälaite Talo2000" profile's layer rules
3. Shows in the GUI what was detected and which IFC types entities will map to
4. Allows the user to pick a profile (default shipped or a TOML file) before conversion
5. Generates an IFC 4 file with correct types, Talo2000 classification references, and basic property sets
6. Packages into a single .exe via PyInstaller for Windows distribution

## Architecture

Layered design; each layer independently testable:

```
┌─────────────────────────────────────────────────┐
│ GUI (PySide6)                                    │
│ src/dxf2ifc/gui/                                 │
│   main_window.py, mapping_editor.py, preview.py  │
└────────────────────┬────────────────────────────┘
                     │ calls
┌────────────────────▼────────────────────────────┐
│ Core                                             │
│ src/dxf2ifc/core/                                │
│   dxf_reader.py  → EntityRecord list            │
│   mapper.py      → MappedEntity list            │
│   geometry.py    → 2D→3D extrude, 3D direct     │
│   ifc_writer.py  → ifcopenshell objects         │
└────────────────────┬────────────────────────────┘
                     │ uses
┌────────────────────▼────────────────────────────┐
│ Config / Profiles                                │
│ src/dxf2ifc/profiles/                            │
│   default_kylmalaite_talo2000.toml              │
│   schema.py (profile validation)                 │
└─────────────────────────────────────────────────┘
```

CLI (`src/dxf2ifc/cli.py`) is a parallel entry point to GUI; both call the same Core. Useful for scripting and batch / CI use.

## Components

### 1. `dxf_reader.py` — DXF parsing
- Uses `ezdxf`
- Reads: LINE, LWPOLYLINE, POLYLINE, 3DSOLID, INSERT, HATCH, TEXT
- Produces: `EntityRecord` dataclass list with fields `(layer: str, dxf_type: str, geometry: GeometryData, attributes: dict, block_name: str | None, xform: Matrix | None)`
- Handles XREF and block references — either expand or retain as references per profile rule
- No mapping logic — pure reader

### 2. `mapper.py` — layer → IFC type rule application
- Inputs: `EntityRecord` list + `Profile` object
- Output: `MappedEntity` list — original record + `ifc_type` (e.g. "IfcWall"), `predefined_type`, `talo2000_code`, derived property values
- Rules in profile: layer-name glob pattern → IFC type + Talo2000 code + default attributes (e.g. wall height, thickness)
- Reports: unrecognised layers, rule conflicts

### 3. `geometry.py` — DXF geometry → IFC geometry
- 2D→3D extrude: LINE/LWPOLYLINE + default height from profile → `IfcExtrudedAreaSolid`
- 3D direct: 3DSOLID → `IfcFacetedBrep` or `IfcAdvancedBrep`
- INSERT/block: detects block name (e.g. SIREENI, KLHYLLY_TIKAS) → maps to `IfcFurnishingElement` or the profile-specified type + preserves xform (placement, rotation, scale)
- Coordinate system: DXF WCS → `IfcLocalPlacement`

### 4. `ifc_writer.py` — IFC 4 generation
- Uses `ifcopenshell`
- Creates: `IfcProject → IfcSite → IfcBuilding → IfcBuildingStorey` hierarchy (single storey default since DXFs usually lack storey info)
- For each `MappedEntity`: correct IFC entity + geometric representation + classification (`IfcClassificationReference` → Talo2000 code) + basic property set (`PSet_WallCommon` etc.)
- Units: `IfcUnitAssignment` in millimetres (DXF convention)
- Final `file.write(output_path)` → .ifc

### 5. `profiles/default_kylmalaite_talo2000.toml`
TOML layout:
```toml
[profile]
name = "Kylmälaite Talo2000 v1"
ifc_schema = "IFC4"

[[rules]]
layer_pattern = "KYL-SEINA*"
ifc_type = "IfcWall"
predefined_type = "PARTITIONING"
talo2000_code = "1221"
talo2000_name = "Väliseinät"
default_height_mm = 3000
default_thickness_mm = 100

[[rules]]
layer_pattern = "KYL-ULKOSEINA*"
ifc_type = "IfcWall"
predefined_type = "STANDARD"
talo2000_code = "1211"
default_height_mm = 3000
default_thickness_mm = 200

[[rules]]
layer_pattern = "LT IMU"
ifc_type = "IfcPipeSegment"
predefined_type = "GASPIPE"
talo2000_code = "2241"
talo2000_name = "Kylmäaineputkistot"

[[rules]]
layer_pattern = "MT NESTE"
ifc_type = "IfcPipeSegment"
predefined_type = "GASPIPE"
talo2000_code = "2241"

[[rules]]
layer_pattern = "KYL-LEVYHYLLY"
ifc_type = "IfcFurniture"
talo2000_code = "145"
talo2000_name = "Kiinteät kalusteet"
block_handling = "geometry_direct"

# ... continues with cold-storage equipment, doors, slabs, drainage pipes etc.
```

Schema validation of profile TOML via `pydantic` — fail fast with a clear error on malformed profiles.

### 6. `gui/` — PySide6 GUI
- **MainWindow**: file pickers (DXF open, IFC save), profile dropdown (shipped default + "load custom…"), Convert button, status log
- **MappingEditor**: table view of detected layers alongside mapping rules, allows editing per row and saving a new profile (Phase 2 of MVP — initially the default profile is immutable and custom profiles live in TOML)
- **Preview**: textual list of detected entities by layer shown before conversion

### 7. `cli.py`
```
dxf2ifc convert input.dxf output.ifc --profile default
dxf2ifc convert input.dxf output.ifc --profile my-custom.toml
dxf2ifc list-layers input.dxf
```

## MVP scope (v0.1)

**In MVP:**
- DXF reading (LINE, LWPOLYLINE, 3DSOLID, INSERT)
- Default profile with 6 layer groups:
  1. External wall (`IfcWall`, Talo2000 1211)
  2. Partition wall (`IfcWall`, Talo2000 1221)
  3. Floor / upper slab (`IfcSlab`, Talo2000 1231/1232)
  4. Door (`IfcDoor`, Talo2000 1311)
  5. Refrigerant pipe LT IMU / MT IMU / MT NESTE (`IfcPipeSegment`, Talo2000 2241)
  6. KLHYLLY shelves (`IfcFurniture`, Talo2000 145)
- 2D→3D extrude (lines → walls at default height)
- 3D solids passed through directly
- GUI: open DXF → shows layers → pick profile → Convert → save IFC
- Basic property sets (`PSet_WallCommon`, `PSet_SlabCommon`, `PSet_DoorCommon`)
- `IfcClassificationReference` for every Talo2000 code
- CLI: basic conversion
- Windows single-file .exe via PyInstaller

**Out of MVP (Phase 2+):**
- GUI-based profile editing — initially load/swap TOML files only
- Drainage pipes (waiting for Lauri's upcoming LISP tool)
- Compressors, evaporators (requires block naming convention decision)
- `IfcMaterial` and `PSet_MaterialCommon`
- Quantity sets (`BaseQuantities`)
- 3D preview in GUI
- macOS / Linux builds
- Multilingual UI

## Open questions (resolve at implementation kickoff)

1. **Talo2000 code source document**: use official Rakennustieto Oy Talo2000 nomenclature? Default: codes lifted from public YTV 2012 and RT-kortisto; Lauri confirms exact codes as we populate the profile.
2. **Storey inference**: single-storey default. Can later derive from Z coordinate or add a user setting.
3. **Doors and windows in DXF**: door geometry is typically a block reference. Decide whether users must use a specific block name prefix (e.g. "DOOR-") or go purely by layer.
4. **Default heights / thicknesses**: profile carries defaults, but users must be able to override per project. GUI addresses this in Phase 2.

## File structure

```
~/work/dxf2ifc/
├── pyproject.toml           # uv/pip dependencies
├── README.md
├── LICENSE
├── .gitignore
├── src/
│   └── dxf2ifc/
│       ├── __init__.py
│       ├── __main__.py      # python -m dxf2ifc → GUI
│       ├── cli.py
│       ├── gui/
│       │   ├── __init__.py
│       │   ├── main_window.py
│       │   ├── mapping_editor.py
│       │   └── preview.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── dxf_reader.py
│       │   ├── mapper.py
│       │   ├── geometry.py
│       │   └── ifc_writer.py
│       ├── profiles/
│       │   ├── __init__.py
│       │   ├── default_kylmalaite_talo2000.toml
│       │   └── schema.py
│       └── config.py
├── tests/
│   ├── __init__.py
│   ├── test_dxf_reader.py
│   ├── test_mapper.py
│   ├── test_geometry.py
│   ├── test_ifc_writer.py
│   ├── test_integration.py
│   └── fixtures/
│       ├── simple_wall.dxf
│       ├── cold_storage_plan.dxf
│       └── expected_simple_wall.ifc
├── docs/
│   ├── superpowers/
│   │   └── specs/
│   │       └── 2026-04-24-dxf2ifc-design.md
│   ├── user-guide.md
│   ├── talo2000-mapping.md
│   └── dev-setup.md
└── dist/                     # PyInstaller output (.exe), gitignored
```

## Testing strategy

- **Unit tests** per module: `dxf_reader` (parses DXF → EntityRecord), `mapper` (applies rules), `geometry` (2D→3D), `ifc_writer` (produces IFC)
- **Integration tests**: round-trip on small DXF → IFC → validated with ifcopenshell
- **IFC schema validation**: `ifcopenshell.validate` → error list
- **Snapshot tests** on profiles: default profile must not drift unnoticed
- **Fixtures** for different cases: single wall, full floor plan, pipes only

## Distribution

- GitHub repo `Mcrauli/dxf2ifc`, GitHub Releases .exe (PyInstaller one-file)
- README + `docs/` content
- Eventually possibly a landing page at `mcrauli.github.io/dxf2ifc/` or a link from the existing `autocad-lisp-ohjeet` site

## Development environment

- Python 3.11+
- `uv` for package management (or pip + venv)
- Libraries: `ezdxf`, `ifcopenshell`, `PySide6`, `pydantic`, `tomli`/`tomllib`, `pytest`, `pytest-cov`, `pyinstaller`
- Dev tools: `ruff` (lint + format), `mypy` (type checks)

## Principles

- **YAGNI**: MVP minimal. Materials, quantity sets, in-GUI profile editor deferred to Phase 2.
- **No hard-coded defaults**: every layer mapping lives in a profile TOML — even the default profile.
- **No integration with existing repos**: entirely new project in a new directory.
- **No broken commits**: when something lands, it works and has tests.

## Next steps (after spec approval)

1. Install Python 3.11+ on Windows if not present
2. Install `uv`
3. Initialize git in `~/work/dxf2ifc/` and create GitHub repo `Mcrauli/dxf2ifc`
4. Scaffold `pyproject.toml` and module skeleton
5. Hand off to `writing-plans` skill to produce a task-by-task implementation plan
