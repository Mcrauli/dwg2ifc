# PROGRESS

Volatile state — current build + open todos. Aiempi Plan-historia (A–H) +
bugfixit on arkistoitu `docs/PROGRESS-archive.md`:hen.

## Onboarding fresh Claude — TL;DR (2026-05-06)

**Tuorein julkaisu**: **v0.1.17-alpha1** (2026-05-06) — kriittinen
geometriafix: tikashyllyt/levyhyllyt/höyrystimet ovat taas IFC:ssä.
Sivuston lataus pinnattu: <https://mcrauli.github.io/autocad-lisp-ohjeet/dxf2ifc.html>.

**Avoimet ongelmat 2026-05-06**:

1. ~~**Tikashyllyt (KYL-TIKASHYLLY) puuttuvat IFC:stä**~~ → **RATKAISTU
   v0.1.17:ssä**. Root cause: ``accoreconsole``:n .scr-rivipuskuri on
   hard-cap 2048 merkkiä; v0.1.14:n LISP-laajennus puski formin yli
   tempdir-polkusubstituution jälkeen → form katkesi → 0 STL:ää. Korjaus:
   LISP jaettu neljäksi top-level-formiksi.
2. **MagiCAD-proxy-objektit eivät vielä näy IFC:ssä** (tunnettu rajoitus).
   ezdxf:n ProxyGraphic-parser ei tunnista MagiCAD:in propietaarista
   encoding:ia → 145 proxya tuottaa 0 virtual_entity. Korjaus suunniteltu
   v0.1.18:aan via accoreconsole-LISP Phase 0 EXPLODE.

**Test-DXF MagiCAD-proxyilla**:
`C:\Users\LauriRekola\Downloads\suunnittelutyokalut\magicad_1krs.dxf`
(298 entityä, 145 ACAD_PROXY_ENTITY: MUUT_OSAT 64, KYL-JV1 39,
KYL-JV1-LAITE 36, TEKSTIT- 5, KERROS_ORIGO 1).

**Jatkosuunnitelma yksityiskohdissa**:
`~/.claude/plans/tota-voitais-alkaa-miettim-sequential-brooks.md`.

GUI:n itsepäivitys-banneri tarjoaa uudet tagit automaattisesti — kun
tagaat seuraavan version, banneri ilmestyy Lauri'n softassa itsestään.

**Älä rakenna seuraavalla iteraatiolla** Solibrin discipline-auto-detectiä
(per-installation-asetus Solibri-puolella, ei IFC-kenttä — Lauri:n
Solibrissa edes Granlund-referenssi ei tunnistu automaattisesti).
Hyväksytty: yksi manuaalinen klikkaus suunnittelualan valintaan.

**SignPath OSS Foundation -hakemus lähetetty 2026-05-04**, odottaa
1-2 viikon hyväksyntää sähköpostilla. `release.yml` on jo opt-in
muodossa — aktivoituu 4 secret/var:lla
(`SIGNPATH_API_TOKEN` + `SIGNPATH_ORGANIZATION_ID` +
`SIGNPATH_PROJECT_SLUG` + `SIGNPATH_SIGNING_POLICY_SLUG`) kun cert
myönnetään. Trial app.signpath.io-tilillä on auki — ÄLÄ luo CSR sinne,
se on maksullinen reitti. Foundation tulee erikseen.

Releases: <https://github.com/Mcrauli/dxf2ifc/releases>

## Latest

**v0.1.8 → v0.1.16** (2026-05-04 → 05): yksityiskohtainen historia
`CHANGELOG.md`:ssä. Lyhyt yhteenveto:
- **v0.1.16** (2026-05-05) — defensive try/except `dxf_reader`:ssä
  (MAGIFLOORORIGO ei kaada), GUI-checkbox "Pikakonversio (ohita 3D-
  tessellaatio)" Convert-napin yläpuolella.
- **v0.1.15** — ACAD_PROXY_ENTITY → __virtual_entities__() expansion
  (LINE/LWPOLYLINE/POLYLINE/MESH). Toimii standardi-proxyille mutta EI
  MagiCAD:in propietaariselle formaatille.
- **v0.1.14** — Höyrystin/Lauhdutin/Kompressori type+PSet, MUUT_OSAT-
  rule (IfcBuildingElementProxy + USERDEFINED).
- **v0.1.13** — ACI 175 -värit kaikille elementeille, MagiCAD type-
  PSet:it CableCarrier+Pipe:lle, KYL-domain valikkoon, layer-table
  "Luokitus", installer desktop icon default päälle, style.qss
  laajennus.
- **v0.1.12** — Z-offset siirtyy myös elementtien geometriaan, ei vain
  storey-Elevation.
- **v0.1.11** — CRS-feature poistettu, 1.krs korko -input GUI:hin,
  status-rivin versio-badge.
- **v0.1.10** — Itsepäivityksen "Failed to start embedded python
  interpreter" -bug korjattu (3 s viive PowerShell-launcher + SHA-256-
  verifiointi).
- **v0.1.9** — Help → Käyttöohjeet -menu (sittemmin v0.1.10:ssä
  poistettu duplikaattina), MIT-licensed-rivi pois About-dialogista.
- **v0.1.8** — Radika Oy -maininnat poistettu installerin metatiedoista.

**v0.1.7-alpha1** (2026-05-04, `d7fa86b`) — MEKA-spec FI_Tekninen
+ FI_Tuote tikashylly/levyhyllylle:
- Tikashylly: KS20-500 K L=6000 PG (Kuumasinkitty EN 10346)
- Levyhylly: KRA-60-500 L=3000 M (RAL 9010)
- Materiaali, Pinnoite, Korroosioluokka, Paloturvallisuusluokka,
  Levypaksuus, Paino + valmistaja-linkki näkyvät Solibrissa
- `_FI_TEKNINEN_DEFAULTS["IfcCableCarrierSegment"]` laajennettu

**v0.1.6-alpha1** (2026-05-04, `82287f7`) — Inno Setup installer:
- `build/installer.iss` + `scripts/build_installer.ps1` ketju
- Per-user `%LOCALAPPDATA%\Programs\dxf2ifc`, ei UAC
- `dxf2ifc-Setup-X.Y.Z.exe` rinnalla `dxf2ifc-X.Y.Z.exe`:n
- Inno Setup VersionInfoVersion+ProductVersion vaativat puhtaan
  `X.Y.Z.W`-numeron — PowerShell strippaa PEP 440 alpha-suffix:n

**v0.1.5-alpha1** (2026-05-04, `241ac8c`) — KRIITTINEN bugifix:
- v0.1.4:n `cleanup_stale_meipass_dirs` poisti exe:n oman _MEI:n
  → "Failed to execute pyi_rth_inspect" seuraavalla käynnistyksellä
- Bug Windows-polun short-form vs long-form -vertailussa
- Cleanup-funktio poistettu, Windows %TEMP% siivoaa itse

**Inno Setup -installeri** (branch `claude/parser-installer-setup-3kPsS`)

- `build/installer.iss` + `scripts/build_installer.ps1` ketju:
  PyInstaller exe → ISCC compile → `dist/dxf2ifc-Setup-<v>.exe`
- Per-user install (`PrivilegesRequired=lowest`) → ei UAC-promptia,
  vähemmän SmartScreen-kitkaa kuin paljaalla `.exe`:llä
- Stable AppId GUID upgrade/uninstall-identiteettiä varten
- `lzma2/max` -kompressio: installer ~40-60% pienempi kuin paljas exe
- Suomi + englanti -kielet, Start-menu + optional desktop shortcut
- `.spec` + `.iss` poimivat `assets/dxf2ifc.ico`:n automaattisesti
- `build.yml` + `release.yml` rakentavat installerin GitHub Actionsissa
- Code-signing-hookki dokumentoitu `docs/packaging.md`:ssä — lisätään kun
  SignPath OSS Foundation -hakemus hyväksytään

**Build #35** (2026-05-04) — Solibri auto-detect + energiateho-diagnostiikka + outlier-poisto

- **Solibri auto-detect**: lisätty `Pset_Project` `Authorization=
  "Kylmäsuunnittelu"` IfcProjectille (Granlund-konventio Solibrille).
  Lisäksi customoitu IfcApplication: `ApplicationIdentifier=
  "dxf2ifc-kylmalaite"`, ja synteettinen IfcOwnerHistory leviää
  kaikille IfcRoot-entiteeteille `write_ifc`-vaiheessa.
- **Energiateho**: full diagnostics + multi-sheet xlsx + REV. alias.
  GUI:n preview-loki näyttää nyt ladatut rivit, tunnistetut headerit,
  M/K osumat, ja ohitettujen syyt. Lauri'n RefDesign-luettelot toimivat
  out-of-the-box (Pakasteet+Kylmät+Yleiset sheetit, REV.→koneikko,
  POS.→laitetunnus, Kylmäteho/Sähköteho/Vastusteho/Jännite/Jäähdyttävä
  vaikutus -kentät).
- **Outlier-feature poistettu kokonaan** (`core/outliers.py` +
  `tests/test_outliers.py`). False positiveja Lauri'n oikealla datalla;
  Solibri tekee saman tarkistuksen omalla "Mallit hajallaan"-säännöllä.
- 496/496 testiä passes (-16 outlier-testit, +13 uutta energy_specs +
  discipline-testit).

**Build #34** (2026-05-04) — suunnitteluala = Jäähdytys + Solibri auto-rooli

- IFC:n `suunnittelualat`-luokitus näyttää nyt **"Jäähdytys"**
  (ei "KYL"). Solibrin oma terminologia.
- Project-tason metatieto Solibrin roolin auto-tunnistamista varten:
  - `IfcProject.LongName = "Jäähdytys"` (kun kaikki säännöt KYL-domainissa)
  - `IfcRelAssociatesClassification` IfcProjectille (sama
    `suunnittelualat`-luokitus)
- `domain="KYL"` säilyy profiili-skeeman sisäisenä enum-arvona; vain
  IFC-output muuttui. `discipline_label()`-helper käännös KYL → Jäähdytys.
- 5 uutta testiä `test_discipline_classification.py`. 501/501 passes.

**Build #33** (2026-05-04) — energiateho-listan lukeminen (Excel/CSV)

- `core/energy_specs.py`: lukee Excel/CSV jossa Koneikko + Laitetunnus +
  tehot. Joustava sarake-mätsäys (`Jäähdytysteho [kW]` / `Q_kW` /
  `Cooling capacity` → `Jäähdytysteho`).
- POSITIO-linkityksen jälkeen orchestrator hakee jokaisen kylmälaitteen
  rivin (koneikko, laitetunnus) ja mergaa tehot **FI_Tekninen**:iin.
- GUI: kolmas tiedostonvalitsin "Energiateho-listasta" (xlsx/csv).
- CLI: `--energy-specs <path>` flag.
- 12 uutta testiä `test_energy_specs.py`. 496/496 passes.
- Lisätty `openpyxl` runtime-dep.

**Build #32** (2026-05-04) — outlier IQR + suunnitteluala KYL

- `core/outliers.py`: Tukey-IQR-pohjainen kynnys (`max(50 m, Q3+3·IQR)`)
  korvasi kiinteän 100 m raja-arvon. Sopeutuu mallin todelliseen
  hajontaan — leveä rakennus ei enää false-positive. Yksiriviset
  varoitukset preview-logiin: `KYL-TIKASHYLLY handle 118A on 731 m
  irrallaan muusta mallista`. `convert_dxf(detect_outliers=False)`
  kytkee koko skannauksen pois.
- `domain="KYL"` lisätty profiili-skeemaan; default-profiili kaikki
  kylmälaite-säännöt KYL-domainissa. `suunnittelualat`-luokitus näyttää
  nyt KYL Solibrissa Talotekniikan sijaan. RAVA-koodit toimivat
  identtisesti (KYL ja TATE jakavat RAVA-LVI/RAVA-TATE-lähteet).
- 482/482 testiä passes.

**Build #31** (2026-05-04) — itsepäivitys + SignPath code-signing -hookki

- `core/updater.py`: GitHub Releases -polling + asset-lataus +
  Windows-temppu (rename current.exe → .old, move new.exe → current.exe,
  spawn detached, quit). Pre-release-tukinen, silent failure
  verkkovirheillä. Cleanup `.old`-jäänteistä käynnistyksellä.
- GUI banner (`gui/update_banner.py`): amber call-to-action ilmestyy
  pääikkunan ylälaitaan kun uudempi versio löytyy. "Päivitä nyt" →
  modaalinen progress dialog → swap → restart.
- `release.yml`: opt-in SignPath.io OSS Foundation -allekirjoitus.
  Aktivoituu kun 4 secret/var on asetettu repon settingseissä —
  ennen sitä release shippailee allekirjoittamattomana ilman failia.
- 26 uutta testiä `test_updater.py`. 480/480 passes.

**Build #30** (2026-05-04) — geometric outlier -varoitus DXF-luennassa

- Uusi `core/outliers.py`: `find_geometric_outliers(records, threshold_mm=100_000)`
  flagaa entiteetit joiden keskipiste on yli 100 m mediaani-keskipisteestä.
  Robusti modelin ETRS-TM35FIN-koordinaateille (median, ei origo).
- `EntityRecord.handle` läpi pipelinen → varoitus näyttää AutoCAD-handlen.
- Wirattu `convert_dxf` orchestratoriin: aina stderriin, GUI:n
  progress-callbackin kautta, ja `report.warnings`:iin kun `--validate`.
- Ehkäisee Solibrin "Mallit laajasti hajallaan" -varoituksen jo
  konversiovaiheessa — käyttäjä korjaa AutoCADissa ennen IFC-uudelleenajoa.
- 14 uutta testiä `tests/test_outliers.py`. 454/454 testiä passes.

**v0.1.0-alpha** (2026-04-30) — ensimmäinen julkinen pre-release Build
#29:n pohjalta. Asennettavissa:
<https://github.com/Mcrauli/dxf2ifc/releases/tag/v0.1.0-alpha>

- Pre-release tag (näkyy "Pre-release" -merkillä Releases-sivulla)
- Asset:t: `dxf2ifc-0.1.0.exe` (102 MB) + `.sha256` + `LICENSES.md`
- release.yml smoke-step korjattu: ei enää invokoi exe:tä
  `--version`-flagilla (windowed PyInstaller exe:llä ei stdoutia),
  vain tarkistaa että artifaktin koko on > 50 MB
- build.yml + release.yml uudelleen aktivoitu (olivat disabled)

**Build #29** (2026-04-30, SHA `76A4F5CB606034E0`)

- Repo cleanup + paketointi: `ifc_writer.py` (1908 r) → 6-moduulin paketti
  (skeleton / classification / mesh / builders / orchestrator + transforms)
- Public API ennallaan re-export-fasadin kautta — testit + GUI/CLI
  pelaa identtisesti
- Vanhat / kuolleet testit poistettu (Bugfix-12-narrowed-profile-artefaktit)
- Duplikaatti `default_kylmalaite_tate_only.toml` poistettu
- `tmp/` 610 MB → 3 MB; PROGRESS-historia archived
- 440/440 testiä passes

**Build #28** (2026-04-30, SHA `E066E277F437B40A`)

- AutoCAD COM removed → accoreconsole + STLOUT for ACIS bodies
  (no recent-files pollution, no GUI window pop, no pywin32 dependency)
- INSERT block content extracted via EXPLODE+STLOUT
  (höyrystinten kotelo + tuulettimen rengas + kannakkeet)
- 6 Finnish PSets per IFC product:
  FI_Asennus / FI_Geometria / FI_Komponentti / FI_Tuote / FI_Tekninen / FI_Sijainti
- POSITIO-blokki → Koneikko + Laitetunnus -linkitys
  (15/15 höyrystintä saa JK1/JK2/JK4 + numero 1–42 automaattisesti)
- "suunnittelualat" -luokittelu (TATE / ARK) eksplisiittisesti per tuote
- FI_Geometria field labels: Pituus hyllyille/putkille (Syvyys vain laatikoille)
- FI_Komponentti renamed: Koneikko (TEKSTI) + Laitetunnus (NUMERO)

**Test status**: 24/24 finnish_psets-testit passes. Ei-GUI-testit ~460 passes
(joitain Bugfix-12-narrowed-profile-artefakteja edelleen failauksessa,
hyväksyttävät).

## Open todos

- [ ] **DXF data quality**: 1× KYL-TIKASHYLLY 3DSOLID handle `118A` outlier-paikassa
  (X=1056k, Z=828k vs muu malli X≈730k, Z≈97k). Konvertteri flagaa nyt
  Build #30:sta lähtien — Lauri voi korjata AutoCADissa kun varoitus näkyy.
- [ ] **GUI Profile Editor** ei näytä FI_*-kenttiä (TOML-edit toimii käsin)
- [ ] **POSITIO-block-pattern** laajempi kattaus jos blokin nimi
  vaihtelee (nyt `positiov2*`)
- [ ] **`builders.py` (1146 riviä)** — split into add_*.py modules
  for readability (cleanup task, plan-mode)
- [ ] **Code signing**: SmartScreen + Defender warningit asennuksessa.
  Vaihtoehdot: SignPath.io OSS-ohjelma (ilmainen), Azure Trusted Signing
  (~€9/kk), EV-cert (€300+/v).

## Roadmap (delivered)

Plans A→H valmiit, ks. `docs/PROGRESS-archive.md` per-task-SHA-historia.
Plan I (TrueNorth-rotaatio + lisä-MEP-koodit) ei kirjoitettu —
toteutetaan jos tarve syntyy.
