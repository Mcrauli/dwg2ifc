# dxf2ifc — projektimuistio Claudelle

Lue tämä aina kun jatkat tätä projektia. Pääset nopeasti kiinni kontekstiin ja vältyt käymästä samoja päätöksiä uudelleen.

## Mikä tämä on

DXF → IFC -konvertteri suomalaisille kylmälaite- ja LVI-suunnittelijoille. Muuntaa AutoCAD-pohjassa piirretyn DXF:n IFC 4 -tiedostoksi, jossa on **Talo2000-luokittelu** (pakollinen YTV 2012:n mukaan) ja oikeat IFC-tyyppitiedot. Desktop-appi GUI:lla + CLI.

- **Tekijä:** Lauri Rekola (Radika Oy, kylmälaitesuunnittelija)
- **Kohderyhmä:** muut kylmä-/LVI-suunnittelijat jotka piirtävät AutoCADilla mutta tarvitsevat IFC-luovutuksen Talo2000-koodeilla
- **Greenfield:** uusi projekti, ei liity olemassa olevaan `~/work/autocad-lisp-ohjeet`-repoon (LISP-työkalusivusto)

## Status

- ✅ Design-spec valmis: `docs/superpowers/specs/2026-04-24-dxf2ifc-design.md`
- ✅ Plan A kirjoitettu: `docs/superpowers/plans/2026-04-24-plan-a-core-cli-wall-pipeline.md` (21 tehtävää)
- 🟢 Plan A **13/21 valmis** — seuraava tehtävä ja SHA-historia: **`PROGRESS.md`** (autoritatiivinen volatile state)
- ✅ Plan B kirjoitettu (`2026-04-27-plan-b-full-element-set.md`, 50 tehtävää). Plans C–F edelleen kirjoittamatta.
- ✅ Remote: `https://github.com/Mcrauli/dxf2ifc` (PRIVATE, default branch `master`)
- 🔁 Routine-agentti `trig_014mxffDUvDZkafKftutpgwo` pyörii 3× päivässä (08/14/20 Helsinki), ohje: `docs/routines/next-task.md`

## Päätetyt valinnat (brainstormauksen jälkeen)

| Päätös | Valinta |
|--------|---------|
| Scope | Kylmäsäilytystila + LVI/putket: seinät, laatat, ovet, hyllyt, putket, kaapelihyllyt, kylmälaitteet |
| Jakelumuoto | Desktop-appi GUI:lla (+ CLI rinnalla) |
| Tech stack | **Python 3.12 + PySide6** (ifcopenshell ja ezdxf ovat Python-natiivia) |
| IFC-skeema | **IFC 4 ainoa tavoite** — moderni skeema, oikeat MEP-entiteetit (`IfcEvaporator` / `IfcCondenser` / `IfcCompressor`), parempi Talo2000-integraatio. YTV sallii 2x3-minimin, mutta me tähtäämme korkeammalle. |
| Layer-mappaus | Hybridi: sisäänrakennettu "Kylmälaite Talo2000" -oletusprofiili + käyttäjän TOML-ylikirjoitukset |
| Geometria | Hybridi: 3D-solidit käytetään suoraan, 2D-viivat ekstrudoidaan layer-default-korkeuksiin |

## Verifioidut Talo2000-koodit

Lähteet: Solibri `Talo2000.classification` (Java-serialisoitu binääri) + RT 10-10962 Talo 2000 Hankenimikkeistö + YTV 2012 osat 1, 3, 4.

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

- **Yksiköt:** millimetri pakollinen (osa 3 ARK, rivi 204)
- **Talo2000-luokittelu:** pakollinen rakennusosille (osa 3 ARK, rivi 847)
- **IFC-skeema:** vähintään IFC 2x3 julkisissa hankkeissa (osa 1 rivi 203). Me tuotamme **IFC 4:n** — se täyttää YTV-minimin ja tuo oikeat MEP-entiteetit kylmälaitteille.
- **Kerrosmallinnus:** per-kerros-eristetty, monitasoiset seinät pilkotaan kerroskorkuisiin siivuihin
- **Seinätyypit:** US, VK, VS / horizontal: AP, VP, YP (Talo2000-lyhenteet suoraan)

## Projektirakenne (aiottu, ei vielä luotu)

```
dxf2ifc/
├── pyproject.toml           # uv + ezdxf, ifcopenshell, pydantic, PySide6, pytest
├── README.md
├── .gitignore
├── src/dxf2ifc/
│   ├── __init__.py
│   ├── __main__.py          # python -m dxf2ifc → CLI
│   ├── cli.py               # argparse-based entry
│   ├── core/
│   │   ├── types.py         # Point3D, LineGeometry, EntityRecord, MappedEntity
│   │   ├── dxf_reader.py    # ezdxf → EntityRecord list
│   │   ├── mapper.py        # apply_profile(entities, profile)
│   │   ├── geometry.py      # 2D→3D extrude, 3D direct
│   │   └── ifc_writer.py    # ifcopenshell → IFC file
│   └── profiles/
│       ├── schema.py        # pydantic Profile + Rule
│       ├── loader.py        # load_profile / load_default_profile
│       └── default_kylmalaite_talo2000.toml
├── tests/
│   ├── conftest.py
│   ├── test_types.py / test_mapper.py / test_dxf_reader.py / ...
│   ├── test_integration.py
│   └── fixtures/
│       └── simple_wall.dxf
└── docs/
    ├── superpowers/
    │   ├── specs/2026-04-24-dxf2ifc-design.md
    │   └── plans/2026-04-24-plan-a-core-cli-wall-pipeline.md
    └── user-guide.md (tulossa Phase 2)
```

## Plan A — mitä pitää rakentaa seuraavaksi

Plan A pilkkoo end-to-end-putken 21 tehtävään. Tavoite: toimiva CLI joka muuntaa DXF:n (yksi `KYL-ULKOSEINA`-viiva) validiksi IFC 4 -tiedostoksi jossa on `IfcWall` + Talo2000-luokittelureferenssi (1241 Ulkoseinät).

Vaiheet tiivistettynä:

1. Asenna Python 3.12 + uv
2. `pyproject.toml` + dependencies (ezdxf, ifcopenshell, pydantic, pytest, ruff)
3. Package-runko + tests/-kansio
4. `Point3D`, `LineGeometry`, `EntityRecord`, `MappedEntity` dataclassit
5. Pydantic `Profile` + `Rule` -skeemat
6. Minimaalinen default TOML (vain ulkoseinä-sääntö)
7. Profile-loader (`importlib.resources` shipped-defaultin lataukseen)
8. Testifixtuuri `simple_wall.dxf` (generoidaan ezdxf:llä)
9. `dxf_reader` lukee LINE-entiteettejä
10. `mapper.layer_matches` + `apply_profile`
11. `geometry.line_to_wall_extrusion`
12. `ifc_writer.build_ifc_project_skeleton` (millimetri-units)
13. `add_wall` + `add_talo2000_classification`
14. `convert_dxf` orchestrator
15. CLI `argparse` + `__main__.py`
16. Integraatio-testi (`ifcopenshell.validate`)
17. Lint + coverage -portti

**TDD-kurina:** jokainen tehtävä alkaa failing-testillä, päätyy commit:iin. Ks. plan-tiedosto täydet askeleet + koodit.

## Plans B–F (kirjoitetaan myöhemmin)

- **Plan B:** ✅ kirjoitettu `docs/superpowers/plans/2026-04-27-plan-b-full-element-set.md` (50 tehtävää, 12 sectionia). Laajentaa Plan A:n pipelinen kattamaan kaikki 10 jäljellä olevaa Talo2000-elementtityyppiä (slabs, doors, windows, putket, hyllyt, kaapelihyllyt, proxies, laitteet). Toteutus kesken — ks. `PROGRESS.md`.
- **Plan C:** `IfcSystem`-ryhmittely kylmäjärjestelmille (putket, laitteet, kaapelihyllyt samaan järjestelmään)
- **Plan D:** PySide6 GUI joka wrappaa CLI-corea (MainWindow, Preview, layer-listaus). Sis. **TOML-profiilin editori UI:ssa**: oletusprofiili (Kylmälaite Talo2000) ship-attuna, mutta UI tukee custom-rules joilla käyttäjä voi lisätä omia layer→IFC-mappauksia ilman tiedoston muokkaamista käsin.
- **Plan E:** Packaging — PyInstaller .exe Windowsille + GitHub Releases
- **Plan F:** Spec verifiointi-taskit (avaa Solibri, vahvista tai päivitä profiili per spec § "Verification")


## Visuaalinen design (Plan D GUI)

dxf2ifc-sovelluksen GUI seuraa **autocad-lisp-ohjeet-verkkosivuston design-kieltä** yhtäläisen brändi-ilmeen takaamiseksi sovelluksen ja sivuston välillä. Sivuston repo: `https://github.com/Mcrauli/autocad-lisp-ohjeet`. Toteutus dxf2ifc:ssä: PySide6 + QSS (Qt Style Sheets — CSS-mainen syntaksi).

### Värit (käytä QSS:ssä, älä keksi uusia)

| Rooli | Hex |
|---|---|
| Tausta gradient | `#0f172a` (top) → `#020617` (bottom), Qt: `QLinearGradient` |
| Aksentti primääri (amber) | `#f59e0b` — napit, focus, korostus, brand-icon |
| Aksentti sekundääri (blue) | `#60a5fa` — info-tilat, koodi-tagit, badge, version |
| Brand white | `#f8fafc` |
| Body text | `#e2e8f0` / `#cbd5f5` |
| Heikko teksti | `#94a3b8` / `#64748b` |
| Border subtle | `rgba(255,255,255,0.05)` |
| Code text | `#f1f5f9` |
| Toast border-left | `#f59e0b` (3px) |

### Fontit (lataa QFontDatabase:lla appin käynnistyksessä, bundlea resursseihin)

- **Inter** 400/500/600/700 — leipäteksti, napit
- **Space Grotesk** 500/600/700 — kaikki otsikot, brand
- **JetBrains Mono** 500 — koodi, versiot, numerot, labels (esim. layer-listaus, IFC-tyyppi-merkinnät)

### Typografia

- H1: Space Grotesk 700, letter-spacing -0.02em, line-height 1.15
- H2: Space Grotesk 600, letter-spacing -0.01em, line-height 1.3
- Paragraph line-height 1.75
- Brand: Space Grotesk 700, font-size 15px

### Toistuvat patternit

- **Tumma tausta gradientilla** (slate radial) main-windowin taustana
- **Mahdollisuus: blueprint-grid** 40×40px, 4% opacity (CAD-viittaus, kevyt aksentti) main-windowin tai preview-areean taustalla
- **Mahdollisuus: corner-crosshairit** (amber `+` neljässä nurkassa) — pieni CAD-aksentti, harkinnanvarainen
- **Amber-painikkeet** primäärisille toimille (Convert, Save, Run); sininen sekundäärisille (Browse, Settings)
- **Border-left 3px amber** toast-/notification-viesteille
- **Hover-states** amber-tinted backgrounds (`rgba(245,158,11,0.12)`)

### PySide6 / QSS toteutus-ohje

- Keskitä tyylit yhteen QSS-tiedostoon tai Qt-resurssiin (analogia `style.css`:lle), älä injektoi widget-kohtaisesti
- Käytä `QFontDatabase.addApplicationFont` Inter/SpaceGrotesk/JetBrainsMono lataamiseen ennen kuin pääikkuna avataan
- QSS tukee `font-feature-settings` ei suoraan, mutta `QFont.setFeatures` tai stylistic alternates ei välttämättä tarvita — body-tekstin näkymä riittää ilman cv11/ss01/ss03

### Mitä EI saa muuttaa

- **Värit eivät saa lisääntyä** — käytä yllä lueteltuja
- **Fontit eivät saa lisääntyä** — kolme riittää
- **Cyan (`#22d3ee`) ja deep-blue (`#3b82f6`) ovat varattu vain LISP-sivuston putki-animaatioihin**, ei käytössä dxf2ifc-GUI:ssa
- Älä lisää tracking-scriptejä, analytics, telemetria — sama linja kuin sivustolla
## Avoimet kysymykset

1. **MEP Talo2000 -alakoodit** (21xx putket, 25xx laitteet) — ei löydy Hankenimikkeistöstä eikä Solibri-filesta yksityiskohtaisesti. Tarvitaan RT-kortisto tai NotebookLM-kysely YTV:stä.
2. **YTV-pakolliset PropertySetit** per IFC-entiteetti — YTV osa 5 RAK + TATE-liitteet käymättä läpi. NotebookLM voisi vastata täsmällisesti.
3. **Varastointihyllyt** (KLHYLLY LEVY/TIKAS) IFC-tyyppi — Lauri aikoo tsekata Solibri-referenssistä onko `IfcFurniture` vai jotain muuta. Granlundin mallissa oli kaapelihyllyt `IfcFlowSegment`+`IfcCableCarrierSegmentType` — mutta ne eivät ole sama asia kuin varastointihyllyt.
4. **Kylmälaitteet** (höyrystin / lauhdutin / kompressori) — Granlund ei sisällyttänyt niitä omiin IFC-luovutuksiinsa. MVP voi skipata tai jättää profiilin aspirationalina kunnes referenssiä löytyy.

## Työtavat jotka on käytössä

- **Superpowers-skillit**: `brainstorming` (käytetty), `writing-plans` (käytetty), `subagent-driven-development` (suunniteltu Plan A:n toteutukseen), `writing-skills` tarvittaessa
- **Plan mode**: käytetään kun kyseessä on isompi muutos → `EnterPlanMode`
- **TDD-kuri**: failing-test → minimal-impl → pass → commit. Spec:in mukaan jokainen Plan-tehtävä noudattaa tätä.
- **Auto mode**: Lauri preferoi "execute > plan" — toteuta heti jos tehtävä on pieni ja turvallinen
- **Kieli**: Suomi chatissa (sinuttelu, informaali), englanti commit-viesteissä ja koodikommenteissa, englanti spec/plan-dokumenteissa (tekninen yleisö)
- **Git**: suora push mainiin (henkilökohtaiset repot) — ei PR-flowta. Commit-viestissä `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>` trailer.
- **Commit-viestin muoto**: imperatiivi, ei emojeita, mieluiten useampi rivi josta ensimmäinen on ~72 merkin tiivistelmä

## Työkalut joita Laurilla on konfiguroituna

- **Claude Code** (päätyökalu)
- **Codex CLI** (openai/codex, asennettu, kirjautunut ChatGPT Go:lla) — toinen näkökulma koodiin, hyvä scaffoldingiin ja reviewiin
- **ChatGPT Go + NotebookLM** (YTV 2012 kokonaan sisällä) — suomalaisten standardien nopea haku. Kysymykset voidaan ohjata Laurille jotka liittää vastauksen chatiin.
- **Solibri** (BIM validointi) — `Talo2000.classification`-tiedosto saatavilla, referenssiprojektit Granlund/Sweco-malleista
- **AutoCAD** (Laurin pääpiirtotyökalu) — tuottaa DXF:ät joita konvertteri lukee
- **GitHub CLI** (`gh.exe`, polku `C:\Program Files\GitHub CLI\`), tili **Mcrauli**
- **Poppler** (asennettu `winget install oschwartz10612.Poppler`) — `pdftotext` PDF-extraktioon. Binäärit: `C:\Users\LauriRekola\AppData\Local\Microsoft\WinGet\Packages\oschwartz10612.Poppler_*\poppler-*\Library\bin\`

## Yhteydet muihin projekteihin

- **`~/work/autocad-lisp-ohjeet`** (erillinen, jo julkaistu GitHub Pagesissa) — Laurin LISP-työkalusivusto. Sieltä tulevat layer-nimet / block-nimet joita tämä konvertteri tunnistaa:
  - `LT IMU`, `MT IMU`, `MT NESTE` (Putkityökalu 3PTK)
  - `KYL-LEVYHYLLY`, `KYL-TIKASHYLLY` (KLHYLLY-blokit → IfcFurniture / Talo2000 1331)
  - `KYL-TIKASHYLLY` vertikaalinen (KLHYLLYV)
  - `POSITIO`-blokki (numerointi — ei suoranaisesti IFC-merkitystä)
- **`~/CAD_LISP/sireeni.lsp`** (paikallinen, ei repo) — Lauri aikoo piirtää oman sireeniblokin itse. Jätetty käytännössä kehityshyllyltä pois.
- **Tuleva viemäri-LISP** — käyttää layer `KYL-VIEMARI*`, profiili valmis mappaamaan `IfcPipeSegment` DRAINPIPE.

## Seuraava askel

**Plan A jatkoa** — Current task ja completed-SHA:t: **`PROGRESS.md`** (autoritatiivinen). Lyhyt status `README.md`:n yläosassa.

**Scheduled-ajoon:** `docs/routines/next-task.md` ohjaa routine-agenttia: pull-rebase → read PROGRESS.md:n "Current task" → TDD plan:n mukaan → commit → päivitä PROGRESS.md + README:n header → push.

**Manuaaliseen ajoon:** lue PROGRESS.md → avaa plan A:n vastaava Task-sektio → käytä **subagent-driven-development**-skilliä tai tee itse.

## Kun Plan A on ylhäällä

Kirjoita Plan B. Se kopioi saman pipeline-kaavan kaikille 10 muulle elementtityypille (slabs, doors, windows, putket, hyllyt, proxies, kaapelihyllyt, kylmälaitteet). Arvio: ~30-40 tehtävää.

Sitten Plan C (IFC 2x3 output + IfcSystem), Plan D (GUI), Plan E (packaging), Plan F (spec verification).
