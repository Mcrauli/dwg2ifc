# Changelog

All notable user-facing changes to dxf2ifc are documented here. The format
loosely follows [Keep a Changelog](https://keepachangelog.com/), and the
project uses semantic versioning.

## Unreleased

**Changed**:
- **Discipline name in the IFC is now "Jäähdytys" (was "KYL")** — Solibri
  uses "Jäähdytys" as the canonical refrigeration discipline label, so
  the IFC matches the role names Solibri's UI presents. The internal
  `domain="KYL"` value in the profile schema is unchanged; only the
  string emitted in the `suunnittelualat` IfcClassificationReference
  was renamed.
- **Project-level discipline metadata for Solibri auto-role detection**:
  when every rule in the active profile shares one domain, the IFC now
  embeds the discipline label in `IfcProject.LongName` plus an
  `IfcRelAssociatesClassification` linking the project to the
  `suunnittelualat` classification. Solibri picks the Jäähdytys role
  automatically on file open, no prompt.

**Added**:
- **Energy-spec Excel/CSV import** — convert_dxf accepts an optional
  energy-spec file path (CLI `--energy-specs`, GUI third file picker)
  with rows keyed by Koneikko + Laitetunnus. After POSITIO linkage
  every refrigeration device's row is looked up and the Jäähdytysteho /
  Sähköteho / Kylmäaine / Ilmavirta / Ääniteho / Käyttölämpötila fields
  flow into FI_Tekninen automatically — no more hand-typing the energy
  list into the IFC. Column header matching is forgiving (`Q_kW`,
  `Cooling capacity [kW]`, `Jäähdytysteho [kW]` all map to the same
  canonical FI_Tekninen field). Adds openpyxl as runtime dep for .xlsx
  reading; .csv reading uses the stdlib.

**Changed**:
- **Outlier detection now adaptive (Tukey IQR)** — replaces the fixed
  100 m threshold that flagged whole models in wide buildings. Threshold
  becomes `max(50 m, Q3 + 3·IQR)` of the per-entity distance distribution,
  and the warning message is one-line short: `KYL-TIKASHYLLY handle 118A
  on 731 m irrallaan muusta mallista`. Detection can be disabled per-call
  via `convert_dxf(detect_outliers=False)`.
- **Refrigeration discipline is now `KYL` instead of `TATE`** in the
  default profile. The IFC `suunnittelualat` classification reference
  now reads `KYL` for kylmälaite/cooling items so Solibri's discipline
  view shows kylmälaitesuunnittelu, not generic Talotekniikka. Schema
  still accepts `TATE` for general LVI/HVAC mappings; only refrigeration
  rules switched.

**Added**:
- **In-app self-update**: GUI shows an amber banner at the top of the
  main window when a newer dxf2ifc release is on GitHub. "Päivitä nyt"
  downloads the bundled exe with progress, swaps the running exe via
  the Windows rename-running-exe trick, and restarts. Pre-releases are
  included by default. Silent on network failure. No-op when running
  from source.
- **Opt-in code signing in release.yml**: `signpath/github-action-submit-signing-request@v2`
  is wired in but gated on four GitHub repo secrets/vars
  (`SIGNPATH_API_TOKEN` + `SIGNPATH_ORGANIZATION_ID` +
  `SIGNPATH_PROJECT_SLUG` + `SIGNPATH_SIGNING_POLICY_SLUG`). Activates
  automatically once the SignPath.io OSS Foundation application is
  approved; until then releases continue to ship unsigned without
  failure.
- Pre-conversion geometric outlier scan: flags DXF entities whose centroid
  is more than 100 m from the median centroid of the rest. Catches stray
  xref leftovers and accidental drag operations BEFORE Solibri's generic
  "Mallit laajasti hajallaan" warning fires. Threshold configurable via
  `convert_dxf(outlier_threshold_mm=…)`. Warnings include layer + DXF
  handle so the user can find the offending entity in AutoCAD.
- `EntityRecord.handle` field carries the DXF entity handle through the
  pipeline for diagnostics.

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
