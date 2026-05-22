# Laitetiedot AutoCAD/BricsCAD-blokin ATTRIB:eilla

dwg2ifc lukee blokki-instanssien **ATTRIB-arvot** automaattisesti ja
näyttää ne Solibrissa FI_Tekninen-, FI_Tuote- ja FI_Komponentti-
välilehdillä. Ei tarvita erillistä Exceliä — arvot kulkevat DWG:ssä
mukana ja niitä voi muokata milloin tahansa Properties-paletista.

> ATTRIB-tuki uudistettu v0.3.0-alpha9:ssä. Toimii sekä BricsCAD:ssa
> että AutoCAD:ssa — ATTRIB on DXF-standardia, ei vendor-spesifinen.

## Tärkein sääntö

**Solibrissa näkyvä kentän nimi = ATTDEFin _prompt_, sellaisenaan.**

- **Prompt** = ihmisluettava nimi. Kirjoita se juuri niin kuin haluat
  sen näkyvän Solibrissa, yksikkö mukaan lukien — esim.
  `Lauhdutusteho (kW)`. Tämä on ainoa kenttä joka ratkaisee miltä
  FI_Tekninen näyttää.
- **Tag** = lyhyt sisäinen tunniste. Sillä ei ole väliä miltä se
  näyttää, **paitsi** tuotetietokentillä (`MALLI`, `VALMISTAJA`,
  `KUVAUS`, `KOMMENTTI`, `LINKKI`) — niiden tagi ohjaa kentän
  FI_Tuote-välilehdelle — ja laitetunnustageilla (`LAITETUNNUS`,
  `LAITETUNNUS(YKSILÖLLINEN)`) — ne menevät FI_Komponentti-
  välilehdelle. Kaikki muut tagit menevät FI_Teknieen.
- **Default / arvo** = mitä Solibri näyttää arvona. Tyhjä kenttä
  näkyy tyhjänä paikkamerkkirivinä.

Ei enää alias- tai kanoninen-nimi-arvausta. Mitä kirjoitat promptiin,
sen Solibri näyttää. Jos prompt on tyhjä, näkyy raaka tag.

Pieni siistintä: jos nimi on kirjoitettu **kokonaan isoilla** (tagi tai
caps lockilla kirjoitettu prompt), Solibri-nimi muutetaan lauseasuun —
`TEHO [KW]` → `Teho [kw]`. Jos nimessä on edes yksi pieni kirjain, se
näkyy täsmälleen kirjoitetussa muodossa (esim. `Kylmäteho -8C [kW]`) —
eli halutessasi voit lukita kirjainkoon kirjoittamalla promptin
lauseasussa.

**Oikopolku jos olet kiire:**

```
1. Avaa blokin lähde-DWG (esim. Lauhdutin.dwg) BricsCAD:ssa
2. Komento _ATTDEF
   →  Tag    = TEHO              (lyhyt tunniste, vapaa)
   →  Prompt = Teho (kW)         (TÄMÄ näkyy Solibrissa)
   →  Default tyhjä, Mode → Invisible ☑
3. Klikkaa "Pick Point" ja sijoita marker block-origon viereen
4. Toista jokaiselle kentälle
5. Tallenna DWG (_QSAVE)
6. INSERT blokin piirustukseen, täytä arvot Properties-paletista
   (Ctrl+1 → Attributes-osio)
```

---

## 1. Mitä ATTRIB on

**ATTDEF** (Attribute Definition) on AutoCAD/BricsCAD-objekti jonka
sijoitat blokin **lähde-DWG:hen**. Jokainen ATTDEF muodostaa "kentän"
jonka jokainen blokki-instanssi tuottaa **ATTRIB**:nä — labeleitu
tieto (tag + prompt + arvo) joka kulkee INSERT:n mukana ja jota voi
muokata jälkikäteen ilman blokin purkamista.

| Etu | Mitä se tarkoittaa |
|---|---|
| **Data DWG:ssä mukana** | Ei erillistä Exceliä hukattavaksi |
| **Per-laite arvot** | Jokainen instanssi voi olla erilainen |
| **Editoitavissa jälkikäteen** | Properties-paletista tai tuplaklikistä |
| **dwg2ifc näyttää sen 1:1** | Prompt → FI_Tekninen-kentän nimi, arvo → arvo |

Sopii lauhduttimille, koneikoille, höyrystimille joiden laitetiedot
vaihtelevat per-laite.

---

## 2. Esimerkki — Lauhduttimen ATTDEF:t

Tavoite: lisätä `Lauhdutin.dwg`-blokkiin näkymättömät ATTRIB-kentät
jotka Lauri täyttää Properties-paletista jokaiselle lauhduttimelle.

### Vaihe 1 — Avaa blokin lähde-DWG

```
File → Open → Lauhdutin.dwg
```

ATTDEF-objektit lisätään modelspaceen blokin geometrian rinnalle.
(Jos blokki on nimettynä nykyisessä piirustuksessa, käytä `_BEDIT`
block-editoria — muuten työvaiheet ovat samat.)

### Vaihe 2 — Lisää ATTDEF

Komentoriville:

```
_ATTDEF
```

Dialogi "Define Attribute" avautuu.

#### Mode (checkbox-rivi)

| Flag | Aseta | Selitys |
|---|---|---|
| **Invisible** | ☑ päälle | Ei näy piirustuksessa, mutta tallessa + näkyy Properties:ssa |
| Constant | ☐ pois | Haluamme käyttäjän voivan muokata arvoa |
| Verify | ☐ pois | Turha tuplakysely |
| Preset | ☐ pois | Jos päällä, ei kysytä INSERT:ssä |

#### Attribute (kolme tekstikenttää)

| Kenttä | Esimerkki | Selitys |
|---|---|---|
| **Tag** | `TEHO` | Lyhyt sisäinen tunniste. Vapaa — paitsi tuotetietotagit (ks. §4). Ei välilyöntejä (CAD ei salli). |
| **Prompt** | `Teho (kW)` | **TÄMÄ näkyy Solibrissa kentän nimenä.** Kirjoita se täsmälleen halutussa muodossa, yksikkö mukaan. Ääkköset OK. |
| **Default** | (tyhjä) | Aloitusarvo. Tyhjä → käyttäjä täyttää myöhemmin. Voit laittaa oletuksen jos haluat (esim. `400` jännitteelle). |

#### Insertion Point

Klikkaa "Pick Point" ja näytä paikka block-geometrian viereen.
Invisible-modessa sijoituspisteellä ei ole väliä — yleinen tapa on
stack:ata kaikki ATTDEF:t block-origon ympärille.

Lopuksi → **OK**.

### Vaihe 3 — Toista jokaiselle kentälle

Aja `_ATTDEF` per kenttä. Lauhduttimen esimerkkisetti:

| Tag (vapaa) | Prompt (= Solibri-nimi) |
|---|---|
| `TEHO` | `Teho (kW)` |
| `SAHKOTEHO` | `Sähköteho (kW)` |
| `JANNITE` | `Jännite (V)` |
| `KYLMAAINE` | `Kylmäaine` |
| `ILMAMAARA` | `Ilmamäärä (m³/h)` |
| `RAKENNEPAINE` | `Rakennepaine (bar)` |
| `AANITEHO` | `Maksimi äänen tehotaso dB(A)` |

> Promptin saa kirjoittaa juuri niin kuin haluaa — isoilla, pienillä,
> yksiköineen. Solibri näyttää sen 1:1.

### Vaihe 4 — Tallenna

Erillinen lähde-DWG: `_QSAVE`. Block-editorissa: `_BSAVE` + `_BCLOSE`.

### Vaihe 5 — Täytä arvot Properties-paletista

1. INSERT blokki piirustukseen (`_INSERT` → valitse blokki)
2. Valitse instanssi → **Ctrl+1** → **Attributes**-osio
3. Klikkaa "Value"-saraketta ja kirjoita arvo. Tyhjät voi jättää —
   ne näkyvät Solibrissa tyhjänä rivinä.

Konvertoi piirustus dwg2ifc:llä → Solibrin FI_Tekninen-välilehdellä
näkyy täsmälleen ne kentät jotka blokissa on, promptin mukaisin nimin.

---

## 3. Muokkaaminen jälkikäteen

- **Tuplaklikkaus** block-instanssia → "Enhanced Attribute Editor".
- **Properties-paletti** (Ctrl+1) → Attributes-osio. Hyvä monelle
  blokille rinnakkain.
- **`_EATTEDIT`** komentoriviltä — sama dialogi kuin tuplaklikistä.

---

## 4. Tagikonventio

### FI_Tuote — tuotetiedot (reititys tagin mukaan)

Nämä tagit ohjaavat kentän FI_Tuote-välilehdelle. Tagilla on siis
väliä — käytä täsmälleen näitä:

| ATTRIB tag | FI_Tuote-kenttä Solibrissa |
|---|---|
| `MALLI` | Tuotetyypin nimi |
| `VALMISTAJA` | Tuotetyypin valmistaja |
| `KUVAUS` | Tuotetyypin kuvaus |
| `KOMMENTTI` | Tuotteen kommentti |
| `LINKKI` | Tuotetyypin valmistajan linkki |

Aliakset: `MALLI` ↔ `LAITE`/`NIMI`/`MODEL`/`TUOTENIMI`/`TUOTE`;
`VALMISTAJA` ↔ `MANUFACTURER`/`BRAND`; `KUVAUS` ↔ `DESCRIPTION`/`DESC`;
`KOMMENTTI` ↔ `COMMENT`/`MUISTIINPANO`; `LINKKI` ↔ `LINK`/`URL`/
`DATASHEET`. Näiden prompt-kenttää ei käytetä — kohde on kiinteä.

> **"Tuotetyypin nimi" -etusija:** `MALLI`-ATTRIB → profiilin sääntö
> (`fi_tuote.nimi`) → IFC-tyypin auto-laitenimike ("Koneikko" /
> "Lauhdutin" / "Höyrystin"). Tyhjä `MALLI` → näkyy laitetyyppi.

### FI_Komponentti — laitetunnukset (reititys tagin mukaan)

Koneikoille ja lauhduttimille voi leimata laitetunnuksen suoraan
blokkiin. Nämä tagit ohjaavat kentän **FI_Komponentti**-välilehdelle —
laiteluokittelu, ei tekninen arvo, joten ne **eivät** mene
FI_Teknieen:

| ATTRIB tag | FI_Komponentti-kenttä Solibrissa |
|---|---|
| `LAITETUNNUS` | Laitetunnus |
| `LAITETUNNUS(YKSILÖLLINEN)` | Laitetunnus, yksilöllinen |

Tunnistus on välimerkki- ja kirjainkokoriippumaton: `Laitetunnus`,
`LAITETUNNUS_YKSILOLLINEN`, `Laitetunnus, yksilöllinen` jne. osuvat
samoihin kenttiin. Promptia ei käytetä — kohde on kiinteä.

Jos piirustuksessa on POSITIO-blokkeja, ne täyttävät FI_Komponentin
`Koneikko`- ja `Laitetunnus`-kentät automaattisesti. Blokkiin täytetty
`LAITETUNNUS`-arvo voittaa POSITIO-arvon; tyhjä blokkikenttä ei pyyhi
POSITIO-arvoa.

### FI_Tekninen — kaikki muut kentät

**Jokainen tagi joka EI ole yllä oleva tuotetieto- tai laitetunnustagi
menee FI_Teknieen, nimellä = ATTDEFin prompt.** Ei kanonisia nimiä, ei
aliaksia, ei tagin sisällön arvaamista. Tag voi olla mitä vain;
prompt ratkaisee näkyvän nimen.

- Prompt tyhjä → kenttä näkyy raa'alla tagilla.
- Arvo tyhjä → kenttä näkyy tyhjänä paikkamerkkirivinä.
- Mikään tagi ei "tipu pois" — jos se on ATTDEF, se näkyy.

Jos blokilla on omat ATTDEF:t, dwg2ifc **ei** lisää tyyppikohtaista
oletuskenttäsettiä (höyrystin/lauhdutin-templatea) — blokin ATTDEF:t
ovat koko FI_Tekninen, eivät mitään muuta.

---

## 5. ATTDEF olemassaolevaan blokkiin

Jos olet jo piirtänyt instansseja ja vasta nyt lisäät/muutat
ATTDEF:eja, synkkaa vanhat instanssit:

- **BricsCAD:** `_ATTSYNC` → Name=<blokki> tai Select
- **AutoCAD:** `_BATTMAN` → valitse blokki → Sync

Ilman synkkausta vanhat instanssit eivät tiedä uusista/muuttuneista
tageista. Uudet INSERT:it saavat ne automaattisesti. dwg2ifc-puolella
koneikko/lauhdutin-LSP redefinetoi blokin uusimmasta DWG:stä joka
ajolla, joten uudet sijoitukset ovat aina ajan tasalla.

---

## 6. Vianhaku

### Sama tagi kahdesti samassa blokissa
Älä laita kahta ATTDEF:ä samalla tagilla. CAD itse menee sekaisin ja
dwg2ifc:ssä jälkimmäinen samanniminen rivi voittaa. Anna jokaiselle
oma tag (esim. `KYLMATEHO_8C` ja `KYLMATEHO_33C`).

### Kenttä näkyy Solibrissa tagina, ei haluttuna nimenä
ATTDEFin prompt on tyhjä. Avaa ATTDEF (block-editorissa, tai poista +
luo uusi) ja täytä Prompt-kenttä.

### ATTRIB ei näy Solibrissa lainkaan
- Arvo on tyhjä **ja** kenttä on tuotetietotagi (`MALLI` ym.) — tyhjä
  tuotetieto ohitetaan. FI_Tekninen-kentät näkyvät tyhjänäkin.
- Block-instanssin layer ei matchaa profiili-patterniin (esim.
  `KYL-LAUHDUTIN*` → `IfcCondenser`) → blokkia ei mapata → ei PSettiä.

### INSERT ei kysy ATTDEF-arvoa
ATTDEF on Invisible-modessa (suositeltu). Arvot täytetään
Properties-paletista.

### dwg2ifc:n virhelokit
ATTRIB-luenta ei kaada konvertointia missään tapauksessa
(try/except-suojaus `dxf_reader.py`:ssä). Konvertoi `_validate`-flagilla
nähdäksesi varoitukset.
