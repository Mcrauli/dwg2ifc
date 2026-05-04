# PROGRESS

Volatile state — current build + open todos. Aiempi Plan-historia (A–H) +
bugfixit on arkistoitu `docs/PROGRESS-archive.md`:hen.

## Latest

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
