# Changelog

All notable user-facing changes to dxf2ifc are documented here. The format
loosely follows [Keep a Changelog](https://keepachangelog.com/), and the
project uses semantic versioning.

## v0.1.0-alpha — 2026-04-30

Ensimmäinen julkinen alpha-release. Build #29 (SHA `76A4F5CB606034E0`) —
sopiva demoamiseen / asiakaspilotteihin.

**Mitä toimii**:
- Suomalainen Talo2000 + RAVA-LVI / RAVA-TATE -luokitus, IFC 4 default
  (`--schema=ifc4x3` saatavilla)
- 6 RAVA3Pro-PSetia per IFC-tuote: `FI_Asennus` / `FI_Geometria` /
  `FI_Komponentti` / `FI_Tuote` / `FI_Tekninen` / `FI_Sijainti`
- POSITIO-blokin (`positiov2`) lukeminen → automaattinen Koneikko + Laitetunnus
  -linkitys kylmälaitteille (≤ 3 m säde)
- ACIS-bodyjen tessellaatio headlessisti `accoreconsole.exe`:lla — ei
  AutoCAD-ikkuna-pop-uppia, ei recent-files-saastutusta, ei pywin32:ta
- Suunnittelualat-luokittelu (TATE/ARK) eksplisiittisesti — Solibri ei enää
  päättele ARK:ksi
- IfcSystem-ryhmittely (Refrigeration LT/MT, Drainage, Cable carriers,
  Refrigeration plant)
- ETRS-TM35FIN georeferensointi (`EPSG:3067`), geometria pysyy LOCAL
- PySide6-GUI: layer-preview, profiili-editori, taustasäikeen konversio,
  CRS-dialogi
- `ifcopenshell.validate` + YTV/RAVA-säännöt + Solibri-snapshot-verifiointi
- Windows-bundlattu `.exe` (PyInstaller, ~95 MB)

**Tunnetut rajoitukset**:
- `accoreconsole.exe` vaaditaan AutoCAD 2018+ -asennuksesta ACIS-bodyjen
  tessellaatioon. Jos puuttuu, 3DSOLID-pohjaiset elementit dropataan.
- GUI Profile Editor ei vielä näytä FI_*-kenttiä (TOML-edit toimii käsin).
- Curved 3DSOLID-bodyt (kaarevat pinnat) tessellataan FACETRES 0.1:llä —
  silhuetti voi olla karkea, mut IFC pysyy hallittavan kokoisena.

## v0.1.0 — 2026-04-XX (TBD)

First public release. The MVP covers the full Talo2000 element set for
Finnish refrigeration / HVAC design, an IfcSystem-aware orchestrator and a
PySide6 desktop GUI with a profile editor.

### Added

- **CLI core** — `dxf2ifc convert input.dxf output.ifc` writes IFC 4 with
  millimetre units, a default Site → Building → Storey hierarchy and a
  per-rule Talo2000 classification reference (Plan A).
- **All 11 Talo2000 element types** — exterior / partition / glass walls
  (`IfcWall` STANDARD/PARTITIONING, codes 1241/1311/1312), floor / mezzanine /
  roof slabs (`IfcSlab` FLOOR/ROOF, codes 1221/1235/1236), exterior /
  interior / special doors (`IfcDoor`, codes 1243/1315/1316), windows
  (`IfcWindow` 1242), refrigeration & drain pipes (`IfcPipeSegment`
  REFRIGERATION/DRAINPIPE, codes 21xx), storage shelves (`IfcFurniture`
  1331), cable trays (`IfcCableCarrierSegment` CABLETRUNKINGSEGMENT, code
  2380), cold-room panels (`IfcBuildingElementProxy`, code 1352) and cooling
  equipment (`IfcEvaporator` / `IfcCondenser` / `IfcCompressor`, codes
  2510/2520/2530) (Plan B).
- **IfcSystem grouping** — refrigeration LT, refrigeration MT, drainage,
  cable carriers and refrigeration plant systems are auto-created from the
  active profile and members are wired through `IfcRelAssignsToGroup`
  (Plan C).
- **PySide6 GUI** (`dxf2ifc-gui`) — Inter / Space Grotesk / JetBrains Mono
  brand fonts, layered slate / amber / blue palette, file panel with Convert
  worker on a background thread, layer table preview, profile editor with
  Add/Edit/Remove/Save and a recent-files store backed by QSettings
  (Plan D).
- **Profile load/persist** — Profile editor's Load button reads any TOML
  profile, MainWindow remembers the last-used profile path between sessions.
- **Preview & log panel** — Right pane shows DXF entity counts per layer on
  open, then logs Convert progress (start, success, errors) with
  colour-coded JetBrains Mono lines.
- **Default profile** — TOML-based "Kylmälaite Talo2000" profile with the
  layer / block conventions used by the AutoCAD LISP toolkit
  (`KYL-ULKOSEINA`, `KYL-VALISEINA`, `LT IMU`, `MT IMU`, `MT NESTE`,
  `KYL-VIEMARI*`, `KAAPELIHYLLY*`, `KYL-LEVYHYLLY`, `KYL-TIKASHYLLY`,
  `HOYRYSTIN`, `LAUHDUTIN`, `KOMPRESSORI`).
- **Windows .exe distribution** — PyInstaller bundle with full asset bundling
  (TOML profile, QSS, fonts, LICENSES), version resource, hidden imports
  for ifcopenshell + ezdxf + PySide6.QtSvg, and Win/Linux build workflows
  on GitHub Actions (Plan E in progress).
