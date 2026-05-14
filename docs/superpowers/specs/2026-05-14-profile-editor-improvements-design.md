# Profiilieditorin parannukset — design

**Päivä:** 2026-05-14
**Tila:** hyväksytty design, odottaa toteutussuunnitelmaa

## Tausta ja ongelma

GUI:n profiilieditori (`Profile ▸ Edit profile…`) on käytössä kankea.
Käyttäjäpalaute tunnisti neljä konkreettista kipupistettä:

1. **Scrollipalkin indikaattori on epäselvä** — 49 rivin sääntötaulukosta
   ei näe yhdellä silmäyksellä ollaanko ylä- vai alapäässä.
2. **IFC-tyyppivalikko on vajaa** — `rule_dialog.py`:n `_IFC_TYPES`
   listaa vain 11 tyyppiä, vaikka IFC-writer tukee ~28:aa (jäähdytys-
   laitteet, jakelulaitteet, IfcTank, IfcFlowController puuttuvat).
3. **Oikean säännön löytäminen 49:stä on vaikeaa** — ei hakua eikä
   suodatusta.
4. **Profiili ei tallennu sovellukseen** — `Save profile…` kirjoittaa
   TOML-tiedoston minne tahansa, eikä sitä ladata automaattisesti
   käynnistyessä. Käyttäjän pitää joka kerta etsiä ja ladata profiili.

## Tavoite

Tehdä profiilieditorista sujuva: taulukko navigoitava, IFC-tyyppilista
täydellinen, ja muokattu profiili tallentuu sovelluksen omaan muistiin
ja latautuu automaattisesti.

## Rajaukset (ei tämän scopessa)

- Sääntöjen muokkaus-workflow (rivi → `Edit…` → dialogi) säilyy
  ennallaan — käyttäjä piti sitä toimivana.
- CLI:n profiilikäsittely (`--profile`, bundled default) ei muutu.
  Sovellusmuisti on vain GUI:n ominaisuus.
- Ei multi-classificationia, IFC4 säilyy — luokitusperiaatteet
  ennallaan.
- `style.qss`:n lukitut värit/fontit eivät muutu; scrollipalkki käyttää
  olemassa olevaa amber-aksenttia.
- Ei TOML-tiedostojen vienti/tuontia editorissa (käyttäjän valinta:
  yksinkertaisin malli — pelkkä sovellusmuisti).

## Osa 1 — Taulukossa navigointi (hakukenttä + selkeä scrollipalkki)

**Tiedosto:** `src/dxf2ifc/gui/profile_editor.py`, `src/dxf2ifc/gui/style.qss`

- **Hakukenttä** (`QLineEdit`) sääntötaulukon yläpuolelle.
  `_RuleTableModel` kääritään `QSortFilterProxyModel`:iin, joka asetetaan
  taulukon malliksi. Suodatus:
  - `setFilterKeyColumn(-1)` → osuma mihin tahansa sarakkeeseen
    (layer pattern, IFC type, predefined, domain, code, name, system),
  - case-insensitive,
  - päivittyy elävästi `textChanged`-signaalista.
- **Rivilaskuri** (`QLabel`) hakukentän vieressä: `"{N} / {M} riviä"`,
  missä `M = lähdemallin rowCount`, `N = proxyn rowCount`. Päivittyy
  proxyn `rowsInserted` / `rowsRemoved` / `layoutChanged` -signaaleista
  ja suodatuksen jälkeen.
- **Selkeä scrollipalkki**: `style.qss`:ään `QScrollBar:vertical` -tyyli
  — leveämpi ura ja korkeakontrastinen vedin olemassa olevalla
  amber-aksenttivärillä. Ei uusia värejä paletissa.
- **Valintamappays**: `_selected_row()` palauttaa nyt proxy-indeksin;
  Add/Edit/Remove muunnetaan lähdemallin riviksi `proxy.mapToSource(...)`
  -kutsulla, jotta muokkaus osuu oikeaan sääntöön myös suodatettuna.
  `_RuleTableModel`:n `append_rule` / `replace_rule` / `remove_row`
  toimivat lähdemallilla; proxy heijastaa muutokset.

## Osa 2 — Täysi IFC-tyyppilista

**Tiedosto:** `src/dxf2ifc/core/ifc_writer/builders.py`,
`src/dxf2ifc/gui/rule_dialog.py`

- Uusi modulitason vakio **`SUPPORTED_IFC_TYPES`** `builders.py`:hin
  (samaan paikkaan kuin `_COOLING_EQUIPMENT_CLASSES` ja
  `_DISTRIBUTION_ELEMENT_CLASSES`). Se on **yksi totuuden lähde** sille
  mitä IFC-tyyppejä writer osaa kirjoittaa:
  - perustyypit: `IfcWall`, `IfcSlab`, `IfcDoor`, `IfcWindow`,
    `IfcPipeSegment`, `IfcCableCarrierSegment`, `IfcFurniture`,
    `IfcBuildingElementProxy`
  - jäähdytyslaitteet (`_COOLING_EQUIPMENT_CLASSES`): `IfcEvaporator`,
    `IfcCondenser`, `IfcCompressor`, `IfcChiller`, `IfcUnitaryEquipment`,
    `IfcCoil`
  - `IfcTank`, `IfcFlowController`
  - jakelulaitteet (`_DISTRIBUTION_ELEMENT_CLASSES`): `IfcSensor`,
    `IfcValve`, `IfcPump`, `IfcWasteTerminal`, `IfcInterceptor`,
    `IfcElectricDistributionBoard`, `IfcController`, `IfcAlarm`,
    `IfcSwitchingDevice`, `IfcCommunicationsAppliance`, `IfcDuctSegment`,
    `IfcDuctFitting`, `IfcAirTerminal`
  Tyyppi on listalla **vain jos** orchestratorin dispatch oikeasti
  rakentaa sen — muuten sääntö ei tekisi mitään.
- Vakio määritellään ryhmiteltynä järjestyksessä: KYL-laitteet →
  putket/hyllyt → sähkö-/jakelulaitteet → ARK-perustyypit.
- `rule_dialog.py` lukee `ifc_type_combo`:n sisällön `SUPPORTED_IFC_TYPES`
  -vakiosta. Pudotusvalikkoon lisätään ryhmäerottimet
  (`QComboBox.insertSeparator`) ryhmien väliin luettavuuden vuoksi.

## Osa 3 — Tallennus sovelluksen muistiin

**Tiedosto:** uusi `src/dxf2ifc/profiles/store.py`,
`src/dxf2ifc/gui/profile_editor.py`, `src/dxf2ifc/gui/main_window.py`,
`src/dxf2ifc/gui/recent_files.py`

### Tallennuspaikka — per-käyttäjä, safe-for-all-users

Aktiivinen profiili tallentuu kiinteään per-käyttäjä-polkuun:

```
%APPDATA%\Mcrauli\dxf2ifc\active_profile.toml
```

- Jokaisella Windows-käyttäjällä on oma `%APPDATA%` → ei jaettua tai
  globaalia tilaa, toimii jokaisella käyttäjällä.
- Kirjoitettavissa ilman admin-oikeuksia; kansio luodaan tarvittaessa.
- Sama `"Mcrauli"` / `"dxf2ifc"` -tunniste kuin QSettingsissä. Polku
  rakennetaan eksplisiittisesti samoista vakioista (ei luoteta
  QApplicationin org/app-nimen asetukseen).
- Ei kosketa käyttäjän AutoCAD-profiiliin, rekisteriin (yli nykyisen
  QSettingsin) eikä prosesseihin — noudattaa projektin
  safe-for-all-users-periaatetta.

### Uusi moduuli `profiles/store.py`

- `active_profile_path() -> Path` — kiinteä polku yllä.
- `save_active_profile(profile: Profile) -> None` — luo kansion,
  kirjoittaa **atomisesti** (temp-tiedosto + `os.replace`), jotta
  kesken kaatuminen ei jätä puolikasta tiedostoa.
- `load_active_profile() -> Profile | None` — palauttaa `None` jos
  tiedostoa ei ole; nielee + lokittaa virheen ja palauttaa `None` jos
  tiedosto on korruptoitunut tai skeema ei kelpaa.
- `clear_active_profile() -> None` — poistaa tiedoston jos on.
- Uudelleenkäyttää `loader.py`:n `dump_profile` / `load_profile`.

### `profile_editor.py`

- **Poistetaan** "Load profile…" ja "Save profile…" -tiedostodialogit
  (`_on_load`, `_on_save`, `load_from_path`, `profile_loaded` /
  `profile_load_failed` -signaalit).
- Tilalle yksi **"Tallenna"**-nappi (primary): kutsuu
  `save_active_profile(...)` muokatuilla säännöillä, emittoi
  `profile_saved`-signaalin (jonka pääikkuna kuuntelee soveltaakseen
  profiilin), ja sulkee dialogin. IO-virhe → näkyvä virheilmoitus,
  dialogi jää auki.
- **"Sulje"**-nappi (secondary) hylkää muutokset (dialogi avaa
  `deepcopy`:n, joten lähde ei mutatoidu).

### `main_window.py`

- `_load_initial_profile()`: jos `load_active_profile()` palauttaa
  profiilin → käytä sitä; muuten `load_default_profile()`. Jos
  tallennettu profiili oli korruptoitunut (store palautti `None`
  lokitetun virheen jälkeen) → fallback bundled defaultiin **ja**
  näkyvä status-viesti käyttäjälle.
- `_on_edit_profile()`: kuuntelee vain `profile_saved`-signaalia
  (`profile_loaded` poistuu); päivittää `self._profile`:n ja
  layer-preview’n.
- `_on_reset_profile()`: kutsuu `clear_active_profile()` (poistaa
  `active_profile.toml`:n) + `load_default_profile()`, jotta seuraava
  käynnistys on puhdas.
- `apply_profile_from_path()` poistetaan (ei enää polkupohjaista
  latausta GUI:ssa).

### `recent_files.py`

- `last_profile_path`-property + `_LAST_PROFILE_KEY` poistetaan —
  kuollutta koodia tämän muutoksen jälkeen. DXF-MRU-lista säilyy.

## Virheidenkäsittely

- **Korruptoitunut / vanhentunut tallennettu profiili**:
  `load_active_profile` lokittaa ja palauttaa `None`;
  `_load_initial_profile` putoaa bundled defaultiin ja näyttää
  status-viestin. Sovellus ei kaadu.
- **Atominen kirjoitus**: temp + `os.replace` estää puolikkaan
  tiedoston jos sovellus kaatuu kesken tallennuksen.
- **Tallennuksen IO-virhe** (esim. levy täynnä): `save_active_profile`
  nostaa poikkeuksen, jonka editori-dialogi näyttää virheilmoituksena;
  dialogi jää auki, muutoksia ei menetetä.
- **Suodatus**: ei virhetiloja.
- **IFC-tyyppilistan eriytyminen**: estetään testillä (ks. alla).

## Testit

Uudet / laajennettavat testit:

- **Proxy-suodatus** (`tests/test_profile_editor.py`): hakukenttä
  suodattaa rivit substringilla useasta sarakkeesta; Edit ja Remove
  osuvat oikeaan **lähdemallin** sääntöön kun taulukko on suodatettuna
  (proxy → source -mappaus).
- **Rivilaskuri**: näyttää `N / M` ja päivittyy suodattaessa.
- **`SUPPORTED_IFC_TYPES` -drift-testi**: vakion sisältö täsmää tarkasti
  siihen joukkoon jonka orchestrator oikeasti dispatchaa
  (perustyypit ∪ `_COOLING_EQUIPMENT_CLASSES` ∪
  `_DISTRIBUTION_ELEMENT_CLASSES` ∪ `{IfcTank, IfcFlowController}`).
- **`store.py`** (`tests/test_profile_store.py`): `save` → `load`
  round-trip; `load_active_profile` → `None` puuttuvalle tiedostolle;
  `load_active_profile` → `None` + lokitus korruptille tiedostolle;
  `clear_active_profile` poistaa tiedoston; atominen kirjoitus ei jätä
  temp-tiedostoa.
- **`_load_initial_profile` fallback**: ei tallennettua profiilia →
  bundled default; korruptoitunut tallennettu profiili → bundled
  default + status-viesti.

GUI-testit ajetaan offscreen-Qt-alustalla projektin nykyisen käytännön
mukaan.

## Muutettavat tiedostot — yhteenveto

| Tiedosto | Muutos |
|---|---|
| `src/dxf2ifc/gui/profile_editor.py` | Proxy-malli + hakukenttä + rivilaskuri; Load/Save-dialogit pois, "Tallenna"/"Sulje" tilalle |
| `src/dxf2ifc/gui/rule_dialog.py` | IFC-tyyppilista `SUPPORTED_IFC_TYPES`:sta, ryhmäerottimin |
| `src/dxf2ifc/gui/main_window.py` | `_load_initial_profile` käyttää storea; reset tyhjentää storen; `apply_profile_from_path` pois |
| `src/dxf2ifc/gui/recent_files.py` | `last_profile_path` pois (kuollut koodi) |
| `src/dxf2ifc/gui/style.qss` | `QScrollBar:vertical` -tyyli, amber-vedin |
| `src/dxf2ifc/core/ifc_writer/builders.py` | Uusi `SUPPORTED_IFC_TYPES` -vakio |
| `src/dxf2ifc/profiles/store.py` | **Uusi** — aktiivisen profiilin per-käyttäjä-persistointi |
| `tests/test_profile_editor.py`, `tests/test_profile_store.py` | Uudet/laajennetut testit |
| `README.md`, `PROGRESS.md`, `CHANGELOG.md`, `CLAUDE.md` | Dokumentit profiilin tallennus-workflow’n osalta |

## Avoimet kysymykset

Ei avoimia — design hyväksytty.
