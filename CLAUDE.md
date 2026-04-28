# dxf2ifc — projektimuistio Claudelle

Lue tämä aina kun jatkat tätä projektia. Volatile state ja per-task SHA-historia: **`PROGRESS.md`**.

## Mikä tämä on

DXF → IFC -konvertteri suomalaisille kylmälaite- ja LVI-suunnittelijoille. Muuntaa AutoCAD-pohjassa piirretyn DXF:n IFC 4 -tiedostoksi, jossa on **Talo2000-luokittelu** (pakollinen YTV 2012:n mukaan). Desktop-appi GUI:lla + CLI.

- **Tekijä:** Lauri Rekola (Radika Oy, kylmälaitesuunnittelija)
- **Kohderyhmä:** muut kylmä-/LVI-suunnittelijat jotka piirtävät AutoCADilla mutta tarvitsevat IFC-luovutuksen Talo2000-koodeilla
- **Repo:** `https://github.com/Mcrauli/dxf2ifc` (PUBLIC, default branch `master`)

## Status

- ✅ **Plan A** 21/21 (`2026-04-24-plan-a-core-cli-wall-pipeline.md`) — CLI-core
- ✅ **Plan B** 50/50 (`2026-04-27-plan-b-full-element-set.md`) — kaikki 11 Talo2000-elementtityyppiä, 143 testiä
- ✅ **Plan C** 12/12 (`2026-04-27-plan-c-ifcsystem-grouping.md`) — IfcSystem-ryhmittely 4 järjestelmälle, 151 testiä
- ✅ **Plan D** 25/25 (`2026-04-27-plan-d-pyside6-gui.md`) — PySide6 GUI + profiili-editori, 200 testiä, coverage 89%
- 🟡 **Plan E** 10/23 (`2026-04-27-plan-e-pyinstaller.md`) — PyInstaller-paketointi käynnissä, Tasks 11-17 odottaa Workflow-PAT-scopea
- ⏳ **Plan F** kirjoittamatta — Spec verifiointi Solibrissä
- ⏳ **Plan G** kirjoittamatta — Coordinate System & Georeferenced IFC. Toteutetaan **Plan F:n jälkeen**. Avain-päätökset:
  - Default CRS: ETRS-TM35FIN, IfcProjectedCRS-kentät: `Name="EPSG:3067"`, `Description="ETRS-TM35FIN"`, `GeodeticDatum="ETRS89"` (kaikki kolme kirjoitetaan parhaan interop:in takaamiseksi)
  - IfcMapConversion linkittää LOCAL geometrian WORLD-koordinaateihin (Eastings/Northings profile-tiedostosta)
  - Geometria kirjoitetaan LOCAL-koordinaateissa (NEVER world coords + MapConversion samaan aikaan = double-transform-riski)
  - Full placement hierarchy: Site → Building → Storey → Element, IfcLocalPlacement-ketju
  - `storey_z_levels` pakollinen profiilissa (lista mm-arvoja, esim. `[0, 3500, 7000]`); virhe jos puuttuu
  - Validointi: max_coord-tarkistus, MapConversion-pakollinen-jos-CRS-määritelty, ei kaksoismuunnoksia
  - TrueNorth-rotaatio skipataan MVP:stä, mahdollinen Plan H:ssa myöhemmin
- 🔁 Routine `trig_014mxffDUvDZkafKftutpgwo` 3× päivässä (08/14/20 Helsinki)

## Päätetyt valinnat

| Päätös | Valinta |
|---|---|
| Scope | Kylmäsäilytystila + LVI/putket: seinät, laatat, ovet, hyllyt, putket, kaapelihyllyt, kylmälaitteet |
| Jakelumuoto | Desktop-appi GUI:lla (+ CLI rinnalla) |
| Tech stack | Python 3.12 + PySide6 + ezdxf + ifcopenshell + pydantic |
| IFC-skeema | **IFC 4 ainoa tavoite** — moderni skeema, oikeat MEP-entiteetit (`IfcEvaporator` / `IfcCondenser` / `IfcCompressor`) |
| Layer-mappaus | Hybridi: sisäänrakennettu "Kylmälaite Talo2000" -oletusprofiili + käyttäjän TOML-ylikirjoitukset (UI:sta editoitavissa) |
| Geometria | Hybridi: 3D-solidit suoraan, 2D-viivat ekstrudoidaan layer-default-korkeuksiin |

## Verifioidut Talo2000-koodit

Lähteet: Solibri `Talo2000.classification` + RT 10-10962 + YTV 2012 osat 1, 3, 4.

| Talo2000 | Nimi | Lyhenne | IFC |
|---|---|---|---|
| 1221 | Alapohjalaatat | AP | `IfcSlab` FLOOR |
| 1232 | Kantavat seinät | VK | `IfcWall` STANDARD |
| 1235 | Välipohjat | VP | `IfcSlab` FLOOR |
| 1236 | Yläpohjat | YP | `IfcSlab` ROOF |
| 1241 | Ulkoseinät | US | `IfcWall` STANDARD |
| 1242 | Ikkunat | — | `IfcWindow` |
| 1243 | Ulko-ovet | — | `IfcDoor` |
| 1311 | Väliseinät | VS | `IfcWall` PARTITIONING |
| 1312 | Lasiväliseinät | — | `IfcWall` PARTITIONING |
| 1315 | Väliovet | VO | `IfcDoor` |
| 1316 | Erityisovet | — | `IfcDoor` |
| 1331 | Vakiokiintokalusteet (hyllyt) | — | `IfcFurniture` |
| 1352 | Kylmähuone-elementit | — | `IfcBuildingElementProxy` |
| 21xx | Putkiosat (alakoodit TBD) | — | `IfcPipeSegment` |
| 23xx | Sähköosat → kaapelihyllyt | — | `IfcFlowSegment` + `IfcCableCarrierSegmentType` CABLETRUNKINGSEGMENT |
| 25xx | Laiteosat (alakoodit TBD) | — | tyyppikohtaisesti `IfcEvaporator` / `IfcCondenser` / `IfcCompressor` |

## YTV 2012 -keskeisiä havaintoja

- **Yksiköt:** millimetri pakollinen
- **Talo2000-luokittelu:** pakollinen rakennusosille
- **IFC-skeema:** YTV-minimi IFC 2x3, me tuotamme IFC 4 (täyttää minimin + tuo MEP-entiteetit kylmälaitteille)
- **Kerrosmallinnus:** per-kerros-eristetty
- **Seinätyypit:** US, VK, VS / horizontal: AP, VP, YP

## Visuaalinen design (Plan D GUI)

GUI seuraa **autocad-lisp-ohjeet-sivuston design-kieltä** (`https://github.com/Mcrauli/autocad-lisp-ohjeet`). PySide6 + QSS.

### Värit (älä keksi uusia)

| Rooli | Hex |
|---|---|
| Tausta gradient | `#0f172a` → `#020617` (slate radial) |
| Aksentti primääri (amber) | `#f59e0b` — napit, focus, brand-icon |
| Aksentti sekundääri (blue) | `#60a5fa` — info, badge, version |
| Brand white | `#f8fafc` |
| Body text | `#e2e8f0` / `#cbd5f5` |
| Heikko teksti | `#94a3b8` / `#64748b` |
| Border subtle | `rgba(255,255,255,0.05)` |
| Code text | `#f1f5f9` |

### Fontit

- **Inter** 400/500/600/700 — leipäteksti, napit
- **Space Grotesk** 500/600/700 — otsikot, brand
- **JetBrains Mono** 500 — koodi, versiot, labels

### Patternit

- Tumma slate-gradient main-windowin taustana
- Amber-painikkeet primääritoimille (Convert), sininen sekundääreille (Browse)
- Hover: amber-tinted (`rgba(245,158,11,0.12)`)
- Border-left 3px amber toast-viesteille
- Mahdollisuus: blueprint-grid 40×40 4% opacity, corner-crosshairit (harkinnanvaraisesti)

### Mitä EI saa muuttaa

- Värit + fontit eivät saa lisääntyä
- Cyan (`#22d3ee`) ja deep-blue (`#3b82f6`) varattu vain LISP-sivuston putki-animaatioihin
- Ei tracking-scriptejä / analytics

## Avoimet kysymykset

1. **MEP Talo2000 -alakoodit** (21xx putket, 25xx laitteet) — RT-kortisto tai NotebookLM-kysely YTV:stä
2. **YTV-pakolliset PropertySetit** per IFC-entiteetti — YTV osa 5 RAK + TATE
3. **Varastointihyllyt** (KLHYLLY LEVY/TIKAS) IFC-tyyppi — Lauri tarkistaa Solibri-referenssistä
4. **Kylmälaitteet** (höyrystin / lauhdutin / kompressori) — Granlund ei sisällyttänyt referenssimalliinsa, profiili aspirational kunnes referenssi löytyy

## Työtavat

- **Superpowers-skillit**: brainstorming, writing-plans, subagent-driven-development
- **TDD-kuri**: failing-test → minimal-impl → pass → commit
- **Auto mode**: Lauri preferoi "execute > plan"
- **Kieli**: suomi chatissa, englanti commit-viesteissä ja koodikommenteissa, englanti spec/plan-dokumenteissa
- **Git**: suora push mainiin, commit-viestissä `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>` trailer

## Työkalut

- **Claude Code** (päätyökalu)
- **Codex CLI** — toinen näkökulma koodiin
- **ChatGPT Go + NotebookLM** (YTV 2012 sisällä) — suomalaisten standardien haku
- **Solibri** (BIM validointi) — Talo2000.classification + Granlund/Sweco-referenssit
- **AutoCAD** — DXF-tuotanto
- **GitHub CLI** `C:\Program Files\GitHub CLI\`, tili **Mcrauli**
- **Poppler** PDF-extraktioon

## Yhteydet muihin projekteihin

- **`~/work/autocad-lisp-ohjeet`** (LISP-työkalusivusto) — sieltä layer/block-nimet:
  - `LT IMU`, `MT IMU`, `MT NESTE` (Putkityökalu 3PTK)
  - `KYL-LEVYHYLLY`, `KYL-TIKASHYLLY` (KLHYLLY-blokit → IfcFurniture / Talo2000 1331)
  - `POSITIO`-blokki (numerointi)
- **Tuleva viemäri-LISP** — `KYL-VIEMARI*`, profiili mappaa `IfcPipeSegment` DRAINPIPE
