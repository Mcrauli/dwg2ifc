# Tehotiedot AutoCAD/BricsCAD-blokin ATTRIB:eilla

dwg2ifc lukee blokki-instanssien **ATTRIB-arvot** automaattisesti ja
ohjaa ne suoraan FI_Tekninen-kenttiin Solibrissa. Ei tarvita erillistä
Exceliä lauhduttimille / koneikoille / muille per-laitteille speksattaville
kohteille — arvot kulkevat DWG:ssä mukana ja niitä voi muokata milloin
tahansa Properties-paletista.

> Tuettu v0.3.0-alpha5:stä lähtien. Toimii sekä BricsCAD:ssa että
> AutoCAD:ssa — ATTRIB on DXF-standardia, ei vendor-spesifinen.

**Oikopolku jos olet kiire:**

```
1. Avaa blokin lähde-DWG (esim. Lauhdutin.dwg) BricsCAD:ssa
2. Komento _BEDIT  →  valitse blokki  →  Open
3. Komento _ATTDEF →  Tag = LAUHDUTUSTEHO, Prompt = "Lauhdutusteho (kW):",
                       Default tyhjä, Mode → Invisible ☑
4. Klikkaa "Pick Point" ja sijoita näkymätön marker block-origon viereen
5. Toista jokaiselle spec-kentälle (taulukko alla)
6. _BSAVE + _BCLOSE
7. INSERT blokin piirustukseen, täytä arvot Properties-paletista
   (Ctrl+1 → Attributes-osio)
```

Lisätietoa, esimerkit ja vianhaku jatkossa.

---

## 1. Mitä ATTRIB on ja miksi se on hyvä

**ATTDEF** (Attribute Definition) on AutoCAD/BricsCAD-objekti jonka
sijoitat blokin **lähde-DWG:hen** kun määrittelet blokkia. Jokainen
ATTDEF muodostaa "kentän" jonka jokainen blokki-instanssi tuottaa
**ATTRIB**:nä — se on labeleitu tieto (tag + arvo) joka kulkee
INSERT:n mukana ja jota voi muokata jälkikäteen ilman, että blokkia
joutuu purkamaan / piirtämään uudelleen.

| Etu | Mitä se tarkoittaa |
|---|---|
| **Data DWG:ssä mukana** | Ei erillistä Exceliä eikä projektikohtaista tiedostoa hukattavaksi |
| **Per-laite arvot** | Jokainen blokki-instanssi voi olla erilainen, vaikka ne käyttäisivät samaa blokin määritelmää |
| **Editoitavissa jälkikäteen** | Properties-palettista tai tuplaklikistä, ilman block edit -tilaa |
| **dwg2ifc lukee automaattisesti** | ATTRIB-tag mappautuu kanoniseksi FI_Tekninen-kentäksi → Solibri näkee sen |

Sopii erinomaisesti **lauhduttimille, koneikoille, höyrystimille**
joiden tehotiedot vaihtelevat per-laite. Excel-pohjainen energy_specs
toimii yhä rinnalla höyrystimille (samat kentät, kollegan teholuettelo
elää) — jos sama kenttä on sekä Excelissä että ATTRIB:ssä, **ATTRIB
voittaa** (per-laite > per-projekti).

---

## 2. Esimerkki — Lauhduttimen ATTDEF:t alusta loppuun

Käytetään esimerkkinä `Lauhdutin.dwg`-blokin lähde-DWG:tä.
Tavoite: lisätä kuusi näkymätöntä ATTRIB-kenttää (Lauhdutusteho,
Sähköteho, Jännite, Ilmavirta, Ääniteho, Käyttölämpötila), jotka
Lauri voi täyttää Properties-paletista jokaiselle sijoitetulle
lauhduttimelle.

### Vaihe 1 — Avaa blokin lähde-DWG

Lauhdutin-blokin pitää olla **olemassa**. Kaksi vaihtoehtoa:

**A) Blokki on määritelty omassa DWG-tiedostossa** (esim.
`files/Lauhdutin.dwg` kotelo/klhylly-konvention mukaan):

```
File → Open → Lauhdutin.dwg
```

ATTDEF-objektit lisätään modelspaceen blokin geometrian rinnalle.

**B) Blokki on osa nykyistä piirustustasi** (sisäisesti nimetty):

Pysy nykyisessä piirustuksessa, käytä `_BEDIT` block-editor.

### Vaihe 2 — Käynnistä Block Editor (jos käytät vaihtoehtoa B)

Komentoriville:

```
_BEDIT
```

Dialogi "Edit Block Definition" avautuu. Listassa kaikki nimetyt
blokit. Valitse `LAUHDUTIN` (tai oma nimesi) → **OK**.

Block-editor avaa erillisen näkymän (tausta on vaalea, statusbarissa
"Block Editor" -merkki). Voit nyt muokata blokin sisältöä — sekä
geometriaa että ATTDEF-määrityksiä.

### Vaihe 3 — Lisää ensimmäinen ATTDEF

Komentoriville:

```
_ATTDEF
```

(Tai BricsCAD-valikossa: Insert → Define Attributes.)

Dialogi "Define Attribute" avautuu. Täytä **vain alla mainitut kentät**
— muut voivat olla oletuksia:

#### Mode (vasen yläkulma — checkbox-rivi)

| Flag | Aseta | Mitä se tekee |
|---|---|---|
| **Invisible** | ☑ **päälle** | Attribuutti ei näy piirustuksessa mutta on tallessa + queryable Properties:sta |
| Constant | ☐ | Pidä pois — me haluamme käyttäjän voivan muokata arvoa |
| Verify | ☐ | Pidä pois — turha tuplakysely |
| Preset | ☐ | Pidä pois — jos päällä, ei kysytä lainkaan INSERT:ssä |

#### Attribute (oikea puoli — kolme tekstikenttää)

| Kenttä | Arvo | Selitys |
|---|---|---|
| **Tag** | `LAUHDUTUSTEHO` | ISO kirjain, EI ääkkösiä, EI yksikköjä, EI välilyöntejä. Tämä tagi mappaa dwg2ifc:ssä kanoniseksi nimeksi "Lauhdutusteho (kW)". Tagi on **avain**, ei käyttäjälle näkyvä. |
| **Prompt** | `Lauhdutusteho (kW):` | Mitä BricsCAD kysyy INSERT:n yhteydessä jos attribuutti ei ole Invisible-modessa. Invisible-tapauksessa ei nähdä, mutta hyvä silti täyttää (näkyy Properties-paletissa kenttänimenä joissain CAD-versioissa). |
| **Default** | (jätä tyhjäksi) | Aloitusarvo. Tyhjä → käyttäjä täyttää myöhemmin Properties:sta. Jos haluat oletuksen ("400" jännitteelle) niin laita se. |

#### Insertion Point (vasen alakulma)

```
Pick Point ✓  (klikkaa nappia ja näytä paikka piirustuksessa)
```

Klikkaa nappia ja **klikkaa paikka block-geometrian viereen** (esim.
0,0 -tienoot). Sijoituspiste ei haittaa kun Invisible on päällä —
mihin tahansa kohtaan käy. Yleinen tapa on stack:ata kaikki ATTDEF:t
päällekkäin block-origon ympärille jotta ne löytyvät myöhemmin
helposti edit-tilassa.

#### Text Settings (oikea alakulma)

Pidä oletukset:
- Height: 2.5 mm (näkyy edit-tilassa, ei häiritse Invisible-modessa)
- Rotation: 0°

Lopuksi → **OK**.

Näet block-editorissa pienen tekstipätkän "LAUHDUTUSTEHO"
(itse tag-nimi näkyy editori-tilassa block-geometrian rinnalla).
Tämä on pelkkä paikkamerkki sinulle — käyttäjä ei näe sitä
INSERT-tilassa kun Invisible on päällä.

### Vaihe 4 — Toista jokaiselle spec-kentälle

Aja `_ATTDEF` uudestaan kuhunkin tag:iin alla (Mode → Invisible
☑ joka kerta). Lauhduttimen kokonaissetti (taulukko 4. luvussa):

| Tag (kirjoita exactly) | Prompt (oma valinta) |
|---|---|
| `LAUHDUTUSTEHO` | `Lauhdutusteho (kW):` |
| `SAHKOTEHO` | `Sähköteho (kW):` |
| `VASTUSTEHO` | `Vastusteho — sulatusvastus (kW):` |
| `JANNITE` | `Jännite (V):` |
| `KYLMAAINE` | `Kylmäaine:` |
| `ILMAVIRTA` | `Ilmavirta (m³/h):` |
| `AANITEHO` | `Ääniteho (dB(A)):` |
| `KAYTTOLAMPOTILA` | `Käyttölämpötila (°C):` |

Sijoituspisteet — klikkaa eri kohtiin tai stack:aa samaan paikkaan.

### Vaihe 5 — Tallenna blokin uusi määritelmä

Block-editor-tilassa:

```
_BSAVE     (tallenna nykyinen blokki)
_BCLOSE    (sulje block-editor)
```

BricsCAD palauttaa modelspaceen. Tai jos käytit vaihtoehtoa A
(erillinen Lauhdutin.dwg), tallenna tavallisella `_QSAVE`.

### Vaihe 6 — Testaa: INSERT uusi instanssi

Avaa testipiirustus, aja `_INSERT` → valitse `LAUHDUTIN`-blokki.

- Jos jätit ATTDEF:t Invisible-modeen → BricsCAD ei prompttaa
  arvoista. Blokki sijoittuu ja näyttää siltä kuin sillä ei olisi
  attribuutteja.
- Jos olisit jättänyt Invisible-flagin pois, BricsCAD prompttaisi
  jokaista Prompt-tekstiä — paina Enter ohittaaksesi.

### Vaihe 7 — Täytä arvot Properties-paletista

1. Valitse äsken sijoittamasi block (klikkaa kerran)
2. Aktivoi Properties-paletti: **Ctrl+1** (tai komento `_PROPERTIES`)
3. Vieritä alas — **Attributes**-osio listaa jokaisen ATTDEF-tagisi
4. Klikkaa "Value"-saraketta sen tagin riviltä → kirjoita arvo →
   Enter
5. Toista jokaiselle täytettävälle kentälle. Tyhjät voi jättää.

### Vaihe 8 — Vahvista että arvo tallentui

Aja `_LIST` ja klikkaa block-instanssia. Output sisältää:

```
INSERT Layer: "KYL-LAUHDUTIN"
...
Attribute: "LAUHDUTUSTEHO" = "30.5"
Attribute: "JANNITE"       = "400"
...
```

Jos näet arvosi, blokki kantaa ne. Konvertoi piirustus dwg2ifc:llä —
Solibrissa lauhduttimen FI_Tekninen-PSet:ssä on `Lauhdutusteho (kW):
30.5` + `Jännite (V): 400`.

---

## 3. Muokkaaminen jälkikäteen — kolme tapaa

### A) Tuplaklikkaus (helpoin yksittäiselle blokille)

Tuplaklikkaa block-instanssia → "Enhanced Attribute Editor" -dialogi
avautuu. Listaa kaikki ATTRIB-tagit. Klikkaa tagia, muokkaa
Value-kenttää, OK. Nopea kun haluat muokata samaa blokkia useamman
kerran.

### B) Properties-paletti (helpoin kun monta blokkia rinnakkain)

Valitse useita block-instansseja kerralla → **Ctrl+1** → Attributes-
osiossa muokkaa arvot. Hyvä kun haluat yhdellä silmäyksellä nähdä
millä arvoja on, millä ei.

### C) `_EATTEDIT` / `_DDATTE` -komennot

Komentoriviltä jos haluat command-line-oriented työnkulun. Sama
dialogi kuin tuplaklikistä.

---

## 4. Tag-konventio — kanoniset nimet

dwg2ifc tunnistaa ATTRIB-tagin tag-nimen perusteella ja ohjaa sen
oikeaan PSet:iin. Tagi on **iso kirjain, ei välilyöntejä, ei
ääkkösiä, ei yksikköjä**.

### FI_Tuote — tuotetiedot (valmistaja, malli, kuvaus)

| ATTRIB tag    | FI_Tuote-kenttä Solibrissa        |
|---------------|-----------------------------------|
| `MALLI`       | Tuotetyypin nimi                  |
| `VALMISTAJA`  | Tuotetyypin valmistaja            |
| `KUVAUS`      | Tuotetyypin kuvaus                |
| `KOMMENTTI`   | Tuotteen kommentti                |
| `LINKKI`      | Tuotetyypin valmistajan linkki    |

`MALLI`-aliakset: `LAITE`, `NIMI`, `MODEL`, `TUOTENIMI`, `TUOTE`.
Englanniksi myös `MANUFACTURER`/`BRAND`, `DESCRIPTION`/`DESC`,
`COMMENT`, `LINK`/`URL`/`DATASHEET`.

> **"Tuotetyypin nimi" -kentän etusijajärjestys:** `MALLI`-ATTRIB →
> profiilin sääntö (`fi_tuote.nimi`) → IFC-tyypin auto-laitenimike
> ("Koneikko" / "Lauhdutin" / "Höyrystin"). Eli jos jätät `MALLI`:n
> tyhjäksi, näkyy yhä laitetyyppi; jos täytät sen, näkyy malli.
> Laitetyyppi löytyy joka tapauksessa FI_Komponentti → yleisnimi
> -kentästä.

### FI_Tekninen — tekniset arvot (tehot, jännite, kylmäaine)

dwg2ifc käyttää samaa alias-systeemiä kuin energy-Excel-headerit.
Yksikkö lisätään automaattisesti kanoniseen nimeen.

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

**Tuntematon tagi ohitetaan** — ei tipu PSetiin junkkina. Eli
voit lisätä omiakin "kommentti"-tageja blokkiin ilman että ne
sotkevat IFC-vientiä.

### Suositellut spec-setit per laitetyyppi

Lisää jokaiseen laite-blokkiin sekä **tuotetiedot** (`MALLI`,
`VALMISTAJA`) että laitetyypin **tekniset arvot**. Jos haluat PSet:n
näyttävän kaikki kentät vaikka useimmat olisivat tyhjiä, lisää
kaikki tagit ATTDEF:nä.

**Kaikille laitteille (FI_Tuote)**:
- `MALLI`, `VALMISTAJA` — minimisetti. Halutessa myös `KUVAUS`,
  `KOMMENTTI`, `LINKKI`.

**Lauhdutin (IfcCondenser) — FI_Tekninen**:
- `LAUHDUTUSTEHO`, `SAHKOTEHO`, `VASTUSTEHO`, `JANNITE`,
  `KYLMAAINE`, `ILMAVIRTA`, `AANITEHO`, `KAYTTOLAMPOTILA`

**Koneikko (IfcUnitaryEquipment) / kompressori (IfcCompressor) — FI_Tekninen**:
- `JAAHDYTYSTEHO`, `SAHKOTEHO`, `KYLMAAINE`,
  `HOYRYSTYMISLAMPOTILA`, `LAUHTUMISLAMPOTILA`, `AANITEHO`

**Höyrystin (IfcEvaporator) — FI_Tekninen**:
- `JAAHDYTYSTEHO`, `SAHKOTEHO`, `VASTUSTEHO`, `JANNITE`,
  `KYLMAAINE`, `ILMAVIRTA`, `AANITEHO`, `KAYTTOLAMPOTILA`,
  `JAAHDYTTAVAVAIKUTUS`
- Tämä toimii Excel-kierron rinnalla; ATTRIB voittaa jos sama kenttä
  on molemmissa.

---

## 5. ATTDEF olemassaolevaan blokkiin (jonka instansseja on jo piirustuksessa)

Tämä on yleinen tilanne: olet jo piirtänyt 12 lauhdutinta, ja vasta
nyt päätit lisätä ATTRIB-kenttiä blokkiin. Steppi:

1. **Lisää ATTDEF:t blokin määritelmään** (Vaiheet 1–5 yllä —
   `_BEDIT` → `_ATTDEF` per kenttä → `_BSAVE` + `_BCLOSE`)
2. **Synkkaa olemassa olevat instanssit** uusiin tageihin:

   **BricsCAD:**
   ```
   _ATTSYNC      (kysyy "Name/Select", anna joko Name=LAUHDUTIN tai
                   Select → klikkaa block-instanssia)
   ```

   **AutoCAD:**
   ```
   _BATTMAN      (avaa Block Attribute Manager)
   → valitse blokki → Sync
   ```

3. Tarkista että uudet kentät näkyvät Properties:ssa kun valitset
   olemassa olevan blokin.

Jos et tee `_ATTSYNC`:ä, **vanhat instanssit eivät tiedä uusista
tageista** ja Properties näyttää vain alkuperäisen settin. Uudet
INSERT:it saavat uudet kentät automaattisesti.

---

## 6. Mitä Solibri näkee

Sinun täyttämät ATTRIB-arvot päätyvät jokaiselle laitteelle
FI_Tekninen-PSet:iin:

- **Tyhjät tai pelkkä whitespace** → ohitetaan (ei korvaa Excel-arvoa
  jos sellainen on olemassa samalle kentälle)
- **Täytetyt** → **ohittavat** Excel-arvot (per-laite > per-projekti)
- **Tuntemattomat tagit** → ei tipu PSetiin

Konvertoi DWG dwg2ifc:llä → avaa IFC Solibrissa → valitse
lauhdutin/koneikko → tuoteosa-näkymä → FI_Tekninen-välilehti näyttää
arvot kanonisilla nimillä yksiköiden kanssa.

---

## 7. Vianhaku

### ATTRIB ei näy Solibrissa
- **Tagi pieni tai ääkkösellä**: Properties näyttää tagin sellaisenaan.
  Jos siellä on "Jäähdytysteho" tai "jaahdytysteho", se ei matchaa —
  pitää olla `JAAHDYTYSTEHO`.
- **Arvo on tyhjä**: pelkkä whitespace ei riitä. Kirjoita oikea numero
  tai teksti.
- **Block-instanssin layer ei matchaa profile-pattern:iin**: ilman
  layer-mappausta (esim. `KYL-LAUHDUTIN*` →`IfcCondenser`) blokki ei
  tule mappatuksi → ei FI_Tekninen-PSettiä.

### INSERT ei kysy ATTDEF-arvoa
- ATTDEF on Invisible-modessa (suositeltu konventio). Properties-
  palettin kautta täytetään arvot. Jos haluat promptin, ATTDEF Mode
  pois Invisible-flagista (mutta tekstit näkyvät piirustuksessa).

### Olen lisännyt uusia ATTDEF:eja mutta vanhat instanssit eivät kuule
- Aja `_ATTSYNC` (BricsCAD) tai `_BATTMAN` → Sync (AutoCAD) — ks. §5.

### ATTDEF-marker näkyy edit-tilassa mutta haittaa
- Sijoita ne block-origon päälle (samaan pisteeseen) tai jonnekin
  block-geometrian taakse. Edit-tilassa ne ovat aina näkyvissä, mutta
  käyttäjälle Invisible-modessa eivät häiritse INSERT:n jälkeen.

### Pelkään että rikon olemassaolevat instanssit
- ATTSYNC kysyy vahvistuksen ennen kuin koskee. Voit testata yhdellä
  block-instanssilla `_ATTSYNC` → Select-vaihtoehdolla — vaikuttaa
  vain valittuun.

### Voinko poistaa ATTDEF:n jälkikäteen?
- Block-editorissa valitse ATTDEF-objekti → `_ERASE`. Tallenna
  blokki. Olemassa olevat instanssit säilyttävät edelleen vanhan
  ATTRIB:n datassaan kunnes ajat `_ATTSYNC`:n joka strippaa
  ylimääräiset.

### dwg2ifc:n virhelokit
- Konvertoi `_validate`-flagilla niin näkee mahd. varoitukset.
  ATTRIB-luenta ei kaada konvertointia missään tapauksessa
  (try/except-suojaus dxf_reader.py:ssä).
