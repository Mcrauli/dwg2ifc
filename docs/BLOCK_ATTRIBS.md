# Tehotiedot AutoCAD/BricsCAD-blokin ATTRIB:eilla

dwg2ifc lukee blokki-instanssien **ATTRIB-arvot** automaattisesti ja
ohjaa ne suoraan FI_Tekninen-kenttiin Solibrissa. Ei tarvita erillistä
Exceliä lauhduttimille / koneikoille / muille per-laitteille speksattaville
kohteille — arvot kulkevat DWG:ssä mukana ja niitä voi muokata milloin
tahansa Properties-paletista.

> Tuettu v0.3.0-alpha5:stä lähtien. Toimii sekä BricsCAD:ssa että
> AutoCAD:ssa — ATTRIB on DXF-standardia, ei vendor-spesifinen.

## 1. Tag-konventio

dwg2ifc tunnistaa ATTRIB-tagin samalla alias-systeemillä kuin
energy-Excel-headerit. Tagi on **iso kirjain, ei välilyöntejä, ei
ääkkösiä, ei yksikköjä**. Yksikkö lisätään automaattisesti
kanoniseen nimeen.

| ATTRIB tag         | FI_Tekninen-kenttä Solibrissa  |
|--------------------|-------------------------------|
| `JAAHDYTYSTEHO`    | Jäähdytysteho (kW)            |
| `LAUHDUTUSTEHO`    | Lauhdutusteho (kW)            |
| `SAHKOTEHO`        | Sähköteho (kW)                |
| `VASTUSTEHO`       | Vastusteho (kW)               |
| `JANNITE`          | Jännite (V)                   |
| `ILMAVIRTA`        | Ilmavirta (m³/h)              |
| `AANITEHO`         | Ääniteho (dB(A))              |
| `KAYTTOLAMPOTILA`  | Käyttölämpötila (°C)          |
| `HOYRYSTYMISLAMPOTILA` | Höyrystymislämpötila (°C) |
| `LAUHTUMISLAMPOTILA`   | Lauhtumislämpötila (°C)   |
| `JAAHDYTTAVAVAIKUTUS`  | Jäähdyttävä vaikutus (kW) |
| `KYLMAAINE`        | Kylmäaine                     |

Englanninkieliset aliakset toimivat myös (`VOLTAGE` → Jännite,
`REFRIGERANT` → Kylmäaine, jne. — sama lista kuin
`core/energy_specs.py:_FIELD_ALIASES`).

**Tuntematon tagi ohitetaan** — ei tipu PSetiin junkkina.

## 2. Lisää ATTDEF:t blokin lähde-DWG:hen (kerran per blokki)

Esim. `Lauhdutin.dwg`:

1. Avaa `Lauhdutin.dwg` (tai vastaava block-lähde) BricsCAD:ssa
2. **Aktivoi** blokin sisältö — modelspace ON blokin määritelmä jos
   lataat sen `(command "_.-INSERT" "BLOCK=POLKU" ...)`-tyyliin
   (klhylly/kotelo-konventio). Jos blokki on jo nimeltä määritelty
   omassa DWG:ssä, avaa BEDIT:llä: `_BEDIT` → valitse blokki
3. Aja **`_ATTDEF`** (lyhyt: `_ATT`)
4. Dialogin kentät:
   - **Tag**: `LAUHDUTUSTEHO` (iso, ei välilyöntiä, ei ääkköstä, ei yksikköä)
   - **Prompt**: `Lauhdutusteho (kW):` (mitä AutoCAD kysyy INSERT:n yhteydessä)
   - **Default**: jätä tyhjäksi (käyttäjä täyttää myöhemmin)
   - **Mode → Invisible (I)**: ✅ päälle (ei sotke piirustusta;
     attribuutti on silti queryable Properties:sta + dwg2ifc:lle)
   - Tekstin koko ja sijoituspiste eivät käytännössä haittaa
     invisible-modessa — voit klikata jonnekin block-origon viereen
5. **Toista** jokaiselle haluamallesi spec-kentälle (taulukon mukaan)
6. Tallenna DWG: `_BSAVE` (jos olit BEDIT:ssä) tai `_QSAVE` (jos
   suoraan lähde-DWG:ssä)

> AutoCAD-vastaavuus: sama `_ATTDEF` toimii AutoCAD:ssa identtisesti.
> BricsCAD:n ja AutoCAD:n DXF-tasolla ATTDEF on samaa formaattia
> (group code 100 = `AcDbAttributeDefinition`).

## 3. Sijoita blokki (INSERT) ja täytä arvot

Kun käytät `_INSERT`- tai oman LISP:n kautta (`KYL-LAUHDUTIN.lsp`
tms.):

- AutoCAD/BricsCAD prompttaa jokaisen näkyvän ATTDEF:in Prompt-teksti
  (esim. "Lauhdutusteho (kW):"). Painaa Enter → tyhjä arvo, täytä
  myöhemmin.
- Invisible-attribuutit eivät prompttaa, vaan saavat oletusarvon
  (yleensä tyhjä). Käyttäjä täyttää ne Properties-paletista.

## 4. Muokkaa arvoja jälkikäteen

Kolme vaihtoehtoa, valitse mikä mukavin:

### A) Properties-paletti (helpoin yhdelle blokille)

1. Valitse block-instanssi (klikkaa)
2. Avaa Properties (`_PROPERTIES` tai `Ctrl+1`)
3. Vieritä alas — Attributes-osiossa jokainen tag omana rivinä
4. Klikkaa arvo, kirjoita, paina Enter

### B) Tuplaklikkaus → Enhanced Attribute Editor (kerralla useat tagit)

1. **Tuplaklikkaa** block-instanssia
2. Avautuu "Enhanced Attribute Editor" -dialogi (tab: Attributes)
3. Klikkaa tag → muokkaa Value-kenttää → OK

### C) `_EATTEDIT` / `_DDATTE` -komennot

Komentoriville `_EATTEDIT` → valitse block → sama dialogi kuin
tuplaklikistä.

> Jos käytät `BATTMAN`-komennolla (Block Attribute Manager) **lisäät
> uusia ATTDEF:eja** olemassa olevaan blokkiin, BricsCAD/AutoCAD
> kysyy haluatko soveltaa muutokset olemassa oleviin instansseihin.
> Vastaa **Yes** niin uudet kentät ilmestyvät kaikkiin Properties-
> näkymiin.

## 5. Mitä Solibri näkee

Sinun täyttämät ATTRIB-arvot päätyvät jokaiselle laitteelle
FI_Tekninen-PSet:iin:

- Tyhjät tai pelkkä whitespace → ohitetaan (ei korvaa Excel-arvoa
  jos sellainen on olemassa samalle kentälle)
- Täytetyt → **ohittavat** Excel-arvot (per-laite > per-projekti)
- Tuntemattomat tagit → ei tipu PSetiin

## 6. Suosittu spec-setti per laitetyyppi

Sama kuin Excel-version `_FI_TEKNINEN_DEFAULTS`:ssa. Jos haluat
PSet näyttävän kaikki kentät vaikka useimmat olisivat tyhjiä, lisää
kaikki tagit ATTDEF:nä.

**Lauhdutin (IfcCondenser)**:
- `LAUHDUTUSTEHO`, `SAHKOTEHO`, `VASTUSTEHO`, `JANNITE`,
  `KYLMAAINE`, `ILMAVIRTA`, `AANITEHO`, `KAYTTOLAMPOTILA`

**Koneikko / kompressori (IfcCompressor)**:
- `JAAHDYTYSTEHO`, `SAHKOTEHO`, `KYLMAAINE`,
  `HOYRYSTYMISLAMPOTILA`, `LAUHTUMISLAMPOTILA`, `AANITEHO`

**Höyrystin (IfcEvaporator)**:
- `JAAHDYTYSTEHO`, `SAHKOTEHO`, `VASTUSTEHO`, `JANNITE`,
  `KYLMAAINE`, `ILMAVIRTA`, `AANITEHO`, `KAYTTOLAMPOTILA`,
  `JAAHDYTTAVAVAIKUTUS`
- Tämä toimii Excel-kierron rinnalla; ATTRIB voittaa jos sama kenttä
  on molemmissa.

## 7. Vianhaku

**ATTRIB ei näy Solibrissa**:
- Tarkista että tag on **isolla kirjaimella ja ilman ääkkösiä**
  (Properties näyttää sen) — `Jäähdytysteho` ei matchaa, `JAAHDYTYSTEHO`
  matchaa.
- Tarkista että value ei ole tyhjä tai pelkkä whitespace.
- Tarkista että block-instanssin layer matchaa
  `default_kylmalaite.toml`:ssa määriteltyyn KYL-pattern:iin (muuten
  blokki ei tule mappatuksi mihinkään IFC-tyyppiin → ei PSet:iä).

**INSERT ei kysy ATTDEF-arvoa**:
- ATTDEF on Invisible-modessa (ei prompttaa, vain tarjoaa
  Properties-kentän). Tämä on suositeltu konventio. Jos haluat
  promptin, ATTDEF Mode pois Invisible-flagista.

**Kaikki ATTRIB:t kerralla**:
- BricsCAD: komento `_ATTSYNC` synkkaa olemassa olevat instanssit
  blokin uusittuun ATTDEF-määritelmään (jos lisäät uusia tageja
  jälkikäteen).
- AutoCAD: `BATTMAN` → Sync.
