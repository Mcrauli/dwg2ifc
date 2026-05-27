# Changelog

All notable user-facing changes to dwg2ifc are documented here. The format
loosely follows [Keep a Changelog](https://keepachangelog.com/), and the
project uses semantic versioning.

## Unreleased

## v0.3.0-alpha26 — 2026-05-27 (versiopumppu: a25-fixit mukaan banneriin)

- Versiopumppu jotta GUI-banneri triggeröityy: a25-release buildattiin ennen
  yleistunnus-korjausta, joten a26 tuo sen käyttäjille automaattisesti.
- Sisältö identtinen a25:n kanssa (yleistunnus RAVA-arvo + TOML auto-numerointi-avain).

## v0.3.0-alpha25 — 2026-05-27 (Tunnistaminen 100% takaisin: yleistunnus RAVA-arvo, auto-numerointi TOML-avaimella)

- **Korjattu: a24 rikkoi tunnistamisen 88 elementille.** a24:ssä TOML fi_komponentti.yleistunnus
  ohitti RAVA:n arvon, mutta validaattori tarkistaa "05 Komponentin yleistunnus" -kentän
  RAVA:n virallista shortNameä vasten. T-LVI-02-01-001 / T-LVI-04-01-001 / T-LVI-01-01-999
  koodien shortName on "ei tunnusta" — TOML:n "KP" / "CO2A" / "CO2S" yms. aiheuttivat
  "Tuoteosakoodistojen arvoissa puutteita" -virheen 88 elementille.
- **FI_Komponentti yleistunnus käyttää aina RAVA:n kanonista arvoa** (tai TOML:a kun
  RAVA-koodia ei ole). Tunnistaminen palaa 100%:iin.
- **Laitetunnus auto-numerointi käyttää silti TOML-yleistunnusta avaimena** kun RAVA sanoo
  "ei tunnusta": CO2-anturi → "CO2A-01", CO2-sireeni → "CO2S-01", KP-putket → "KP-01" jne.

## v0.3.0-alpha24 — 2026-05-27 (CO2A/CO2S-tunnukset + Jakelujärjestelmä-luokka + hylly-sarjanimet)

- **Korjattu: CO2-anturin ja CO2-sirreenin yleistunnus ja Laitetunnus auto-numerointi.**
  RAVA-koodi T-LVI-01-01-999 palauttaa shortName = "ei tunnusta", jolloin auto-numerointi
  käytti fallbackina `mapped.ifc_type` → Laitetunnus oli "IfcSensor-01" / "IfcAlarm-01".
  Korjattu: kun RAVA sanoo "ei tunnusta", käytetään TOML fi_komponentti.yleistunnus-arvoa.
  CO2-anturi → laitetunnus "CO2A-01", CO2-sireeni → "CO2S-01".
- **Korjattu: Jakelujärjestelmä Järjestelmäluokka ja Järjestelmätyypin yleistunnus
  puuttuivat.** J-LVI on RAVA:n ylin taso (hierarchyLevel=1) — shortName tyhjä eikä
  J-LVI-09/J-LVI-04-haaroja ollut käsitelty. Korjattu: level-1 J-LVI saa
  `jarjestelmaluokka = "LVI-JÄRJESTELMÄT"` ja `yleistunnus = "J-LVI"`.
- **Korjattu: IfcSystem-luokitusviite (IfcClassificationReference) ilman Name-kenttää.**
  `add_system_classification` lisää nyt RAVA:n prefLabel:n Name-kentäksi
  (esim. "Kylmä - suorahöyrysteinen" Kylmäjärjestelmälle).
- **FI_Tuote: Sarjan nimi lisätty MEKA-hyllysäännöille.** KYL-TIKASHYLLY* → `sarjan_nimi = "KS20"`,
  KYL-LEVYHYLLY* → `sarjan_nimi = "KRA-60"`.

## v0.3.0-alpha23 — 2026-05-27 (Laitetunnus auto-numerointi + Jakelujärjestelmä-koodi)

- **Uusi: Laitetunnus auto-numerointi.** Kaikki laitteet joilla ei ole POSITIO- tai
  ATTDEF-pohjaista laitetunnusta saavat automaattisen tunnuksen muodossa
  `<yleistunnus>-01`, `<yleistunnus>-02` jne. per konversioajo. Numero kasvaa
  yleistunnus-kohtaisesti (esim. CO2A-01/CO2A-02 ja CO2S-01 erikseen).
  Laskuri jaetaan kaikille tuotteille saman IFC-tiedoston sisällä. POSITIOsta
  tai ATTDEFistä tuleva tunnus ohittaa auto-numeroinnin aina.
- **Korjattu: Jakelujärjestelmä FI_Järjestelmä tyhjät kentät.** `add_system()`
  kutsuttiin ilman `system_code`-parametria → kaikki kentät olivat tyhjiä.
  Korjattu: `system_code="J-LVI"` (RAVA LVI-JÄRJESTELMÄT, ylin taso).

## v0.3.0-alpha22 — 2026-05-27 (FI_Geometria Koko (DN) + Uponor HTP viemäriputkille)

- **Korjattu: FI_Geometria puuttui kokonaan `IfcPipeSegment`-tuotteilta.** Koodi yritti
  lukea `mapped.pset_overrides`-attribuuttia jota `MappedEntity`-luokassa ei ole;
  AttributeError nieltiin hiljaa ja kaikki FI_*-PSetit FI_Asennuksen jälkeen jäivät
  kirjoittamatta. Korjattu käyttämään `extras["default_diameter_mm"]`:ää, jonne
  mapper kopioi NominalDiameter:n profiilisäännöstä.
- **FI_Geometria: Koko (DN) johdetaan automaattisesti.** Kun putken TOML-säännössä on
  `Pset_PipeSegmentOccurrence.NominalDiameter`, kenttä `Koko (DN)` kirjoitetaan
  muodossa "DN\<pyöristetty arvo\>" (esim. `DN32`). `Ulkohalkaisija` asetetaan
  NominalDiameter-arvoon.
- **FI_Tuote: Uponor HTP -tuotedata KYL-VIEMARI-säännöille.** Lisätty profiiliin
  `fi_tuote = { valmistaja = "Uponor", sarjan_nimi = "Uponor HTP", materiaalin_nimi = "PP" }`
  kaikille KYL-VIEMARI-putkisäännöille (32 / 50 / 75 / yleinen).
- **Skeema: `FiTuoteOverrides` lisäkentät.** `sarjan_nimi`, `materiaalin_nimi`,
  `materiaalin_tunnus`, `eristesarja` lisätty Pydantic-malliin — TOML-profiili voi
  nyt asettaa nämä ilman validointivirhettä.

## v0.3.0-alpha21 — 2026-05-27 (FI_Geometria viemäriputket + FI_Järjestelmä IfcText-bugi)

- **Korjattu: KYL-VIEMARI FI_Geometria Sisähalkaisija/Ulkohalkaisija/Eristeen paksuus
  puuttui kokonaan.** Solibri laski nämä 64 putkea "tietorakenteet-puutteeksi" (❌).
  Pipe-kontekstissa (koko_dn asetettu) kentät kirjoitetaan nyt aina `IfcLengthMeasure`
  0.0-oletuksella kun todellista arvoa ei ole — property on läsnä.
- **Korjattu: FI_Järjestelmä-kentät käyttivät `IFCLABEL`-tyyppiä `IfcText`:n sijaan.**
  `pset.edit_pset` wrappasi plain stringit automaattisesti IfcLabel:iksi. Korjattu
  eksplisiittisillä `ifc.create_entity("IfcText", ...)` -kutsuilla.

## v0.3.0-alpha20 — 2026-05-26 (FI_* PSet-kentät tietorakenteet-tarkistukseen)

- **Korjattu: Solibri tietorakenteet ja -sisällöt -tarkistus 17 % → parannettu.**
  Lisätty puuttuvat kentät kaikkiin kuuteen FI_*-PropertySetiin:
- **FI_Asennus**: Lisätty eristeen pinta-korkoarvot (01 Eristeen yläpinnan
  korko abs., 05 Eristeen alapinnan korko abs., 11/15 kerroskorosta). Oletuksella
  `insulation_mm=0` arvot samat kuin komponentin pinnat — kenttä on aina läsnä.
- **FI_Geometria**: Lisätty `Koko` (kaapelikourut), `Koko (DN)` (putket),
  `Sisähalkaisija`, `Ulkohalkaisija`, `Eristeen paksuus`.
- **FI_Komponentti**: `always_emit=True` — kaikki tekstikentät (Koneikko,
  Laitetunnus jne.) kirjoitetaan aina, tyhjinä tarvittaessa.
- **FI_Tuote**: Lisätty `Sarjan nimi`, `Materiaalin nimi`, `Materiaalin tunnus`,
  `Eristesarja`. `always_emit=True`. `kuvaus` saa oletuksena RAVA-yleisnimenä.
- **FI_Tekninen**: `IfcPipeSegment`-oletuksiin lisätty `Normivirtaamien summa`.
- **`add_fi_geometria`**: `koko_dn=""` (tyhjä string) laukaisee `always_emit=True`
  oikein (ei enää `bool("")=False`-bugi).

## v0.3.0-alpha19 — 2026-05-26 (FI_Komponentti-kentät automaattisesti RAVA-hierarkiasta)

- **Korjattu: Solibri tunnistaminen -tarkistus läpäisi 0 % tuotteista.**
  FI_Komponentti-pääryhmä, alaryhmä, yleisnimi ja yleistunnus oli
  kovakoodattu TOML-profiiliin omatekoisten arvojen kanssa, eivät
  täsmänneet RAVA3Pro:n kanonisiin arvoihin joita Solibri vertaa koodin
  perusteella.
- **`profiles/rava/loader.py`**: Uusi `load_tuoteosa_hierarchy()`-funktio
  lukee `lvi_tuoteosa.json` ja `talotekniikka_tuoteosa.json`:n, navigoi
  `broaderCode`-ketjun tasolta 3 → 2 → 1 ja palauttaa kanonisen
  pääryhmä/alaryhmä/yleisnimi/yleistunnus per RAVA-koodi. Tulos on
  moduulitason välimuistissa.
- **`core/finnish_psets.py`**: `build_fi_psets_for_product()` hakee
  FI_Komponentti-kentät automaattisesti RAVA-hierarkiasta kunkin
  säännön koodin perusteella; profiilissa ei enää tarvita käsin
  asetettuja arvoja.
- **`profiles/default_kylmalaite.toml`**: Korjattu 15+ väärää tai
  olemattomaan koodiin viittaavaa RAVA-koodia:
  - `T-LVI-02` (ryhmätason koodi) → `T-LVI-02-01-001` (Putki)
  - `T-TATE-01-01-099` (ei olemassa) → oikeat koodit kullekin laitteelle
  - CO2-anturi/sireeni/huolto-PC/hätäseis: `T-TATE-02-01-003` →
    `T-LVI-01-01-999` (MUU - Lämmitys- ja jäähdytyslaitteistot)
  - Magneettiventtiili → `T-LVI-03-02-002`, paisuntaventtiili →
    `T-LVI-03-03-012`, sulkuventtiili → `T-LVI-03-03-001`,
    pumppu → `T-LVI-03-06-001`, paisunta-astia → `T-LVI-03-07-002`,
    mittarit → `T-LVI-03-05-999`, muut osat → `T-TATE-02-01-003`

## v0.3.0-alpha14 - 2026-05-25 (levyhyllyn umpikylki käyttää LWPOLYLINE thickness -arvoa)

- **Korjattu: uuden `KYL-LEVYHYLLY`-blokin umpinainen kylkilevy jäi pois
  IFC:stä.** Ongelma ei ollut pelkkä rim-tunnistus, vaan uusi levyhylly
  koodaa kyljen korkeuden `LWPOLYLINE.dxf.thickness`-arvoon (`60 mm`).
  Parseri jätti tämän arvon huomiotta ja päätteli korkeutta vain
  3DFACE-kansista. Tässä blokkimuodossa ainoa 3DFACE oli pohjalevyn top
  (`z=1.25`), joten kylki typistyi pohjalevyn paksuiseksi ja näytti
  puuttuvan Solibrissa.
- `core/dxf_reader.py` käyttää nyt asetettua `LWPOLYLINE`-thickness-arvoa
  ensisijaisena extrusion-korkeutena 3DFACE-parituksen sijaan. Tämä palauttaa
  levyhyllyn yhtenäiset umpikyljet ja säilyttää tikashyllyjen toimivan
  geometrian.
- Lisätty regressiotesti `test_insert_levyhylly_sidewall_uses_lwpolyline_thickness`
  (`tests/test_dxf_reader_insert_3dface.py`) uudelle hyllymuodolle.

## v0.3.0-alpha13 - 2026-05-25 (levyhyllyn kyljet näkyviin myös muokatulla blokkigeometrialla)

- **Korjattu: `KYL-LEVYHYLLY` / `KYL-KOTELO` -blokkeihin tehdyn geometriamuokkauksen jälkeen hyllyn kyljet saattoivat kadota tai jäädä mataliksi IFC:ssä.** 3DFACE+LWPOLYLINE-aggregoinnin rim-tunnistus nojaasi aiemmin käytännössä vain absoluuttiseen `<=5 mm` strip-paksuuteen. Kun kylkipeltiä paksunnettiin blokissa, strip ei enää mennyt rim-haaraan ja extrudoitui väärään korkeuteen.
- Uusi logiikka (`core/dxf_reader.py`) käyttää absoluuttisen kynnyksen lisäksi **blokkiin suhteutettua perimeter-tunnistusta**: jos strip osuu blokin reunaan ja sen lyhyempi sivu on pieni suhteessa blokin kokoon, se käsitellään kylkenä ja nostetaan 3DFACE-määritettyyn block-top-korkoon.
- Lisätty regressiotesti `test_insert_kotelo_thicker_rim_still_extrudes_to_block_top` (`tests/test_dxf_reader_insert_3dface.py`) varmistamaan, että myös paksummat kylkistripit näkyvät oikein.

## v0.3.0-alpha12 â€” 2026-05-22 (Laitetunnus-attribuutit FI_Komponentti-vÃ¤lilehdelle)

- **Blokin `LAITETUNNUS`- ja `LAITETUNNUS(YKSILÃ–LLINEN)`-attribuutit
  nÃ¤kyvÃ¤t Solibrissa nyt FI_Komponentti-vÃ¤lilehdellÃ¤ â€” eivÃ¤t enÃ¤Ã¤
  FI_TeknisessÃ¤.** Aiemmin jokainen ei-tuotetietotagi reititettiin
  FI_Teknieen; koneikon ja lauhduttimen laitetunnukset ovat
  laiteluokittelua, eivÃ¤t teknisiÃ¤ arvoja, joten ne kuuluvat
  FI_Komponentti-tabille `Koneikko`-kentÃ¤n viereen.
- **Uusi FI_Komponentti-kenttÃ¤ `Laitetunnus, yksilÃ¶llinen`** per-laite-
  kohtaiselle yksilÃ¶lliselle tunnukselle.
- Tagintunnistus on vÃ¤limerkki- ja kirjainkokoriippumaton
  (`core/block_attribs.py`, `resolve_fi_komponentti_field`):
  `LAITETUNNUS`, `Laitetunnus`, `LAITETUNNUS(YKSILÃ–LLINEN)`,
  `LAITETUNNUS_YKSILOLLINEN` jne. osuvat samoihin kenttiin.
- Laitetunnus-arvot kulkevat `extra_props`-kanavan kautta (sama kuin
  POSITIO-blokkien parituksessa): blokin tÃ¤ytetty arvo voittaa
  POSITIO-johdetun arvon, tyhjÃ¤ arvo ei pyyhi sitÃ¤.

## v0.3.0-alpha11 â€” 2026-05-22 (anonyymiblokit STLOUT-polulle)

- **Korjattu: BEDITissÃ¤ muokattu tai kopioitu laite (esim. koneikko)
  jÃ¤i ilman 3D-geometriaa ja putosi bbox-placeholder-laatikoksi.**
  Kun blokkia muokataan BEDITissÃ¤ tai se kopioituu, AutoCAD tekee siitÃ¤
  anonyymin blokin (`*U`-alkuinen nimi). Phase 2:n STLOUT-suodatin
  (worthlist) rakennetaan ezdxf:n nÃ¤kemillÃ¤ blokkinimillÃ¤, mutta
  AutoCAD **uudelleennumeroi anonyymit blokit** DXF:Ã¤Ã¤ ladatessaan â€”
  ezdxf:n `*U8` palaa accoreconsolessa nimellÃ¤ `*U7`, jolloin
  worthlist-jÃ¤senyystesti ei osu ja laite ohitettiin STLOUT-polulta.
- Korjaus (`core/preprocessing.py`, `_LISP_PHASE2`): `*`-alkuiset
  anonyymit blokit rÃ¤jÃ¤ytetÃ¤Ã¤n ja STLOUTataan nyt aina, ohi
  worthlist-tarkistuksen â€” samaan tapaan kuin ei-ASCII-nimiset jo
  aiemmin. Worthlist ei voi taata nimeÃ¤ joka ei ole stabiili
  ezdxfâ†”accoreconsole-rajan yli. Koskee sekÃ¤ ylÃ¤tason INSERT-silmukkaa
  ettÃ¤ sisÃ¤kkÃ¤istÃ¤ rekursiota.
- Vahvistettu testitiedostolla: anonyymiksi muuttunut koneikko tuottaa
  nyt tÃ¤yden meshin (4140 verteksiÃ¤) bbox-laatikon sijaan.

## v0.3.0-alpha10 â€” 2026-05-21 (FI_Tekninen-kenttÃ¤nimet lauseasuun)

- **Kokonaan isoilla kirjoitettu FI_Tekninen-kentÃ¤n nimi siistitÃ¤Ã¤n
  lauseasuun.** ATTDEF-prompt tai -tagi joka on kirjoitettu CAPS
  LOCKilla (esim. lauhduttimen `TEHO [KW]`, koneikon tagi `KYLMAAINE`)
  nÃ¤kyy Solibrissa nyt muodossa `Teho [kw]` / `Kylmaaine` â€” ei enÃ¤Ã¤
  huutavana versaalina.
- Jos nimessÃ¤ on **edes yksi pieni kirjain**, se nÃ¤ytetÃ¤Ã¤n tÃ¤smÃ¤lleen
  kirjoitetussa muodossa (esim. `KylmÃ¤teho -8C [kW]`). NÃ¤in blokin
  tekijÃ¤ voi lukita kirjainkoon kirjoittamalla promptin lauseasussa.
- Koskee vain FI_Tekninen-kenttien **nimiÃ¤**; arvot ja FI_Tuote
  sÃ¤ilyvÃ¤t ennallaan.

## v0.3.0-alpha9 â€” 2026-05-21 (ATTRIB â†’ FI_Tekninen verbatim, ei aliasarvausta)

- **ATTRIB-kentÃ¤t nÃ¤kyvÃ¤t Solibrissa nyt tÃ¤smÃ¤lleen siinÃ¤ muodossa kuin
  ne on blokin ATTDEF:eissÃ¤.** Aiempi reititys ajoi jokaisen tagin
  energy-Excelille tarkoitetun alias-systeemin lÃ¤pi, mikÃ¤ koneikon ja
  lauhduttimen oikeilla blokeilla **pudotti puolet kentistÃ¤ ja mappasi
  toisen puolen vÃ¤Ã¤rin** â€” esim. `RAKENNEPAINE` ja Ã¤Ã¤nenpainetaso
  nÃ¤kyivÃ¤t Solibrissa nimellÃ¤ "KylmÃ¤aine" (osajono "aine" osui
  KylmÃ¤aine-aliakseen).
- **Uusi reititys** ([`core/block_attribs.py`](src/dwg2ifc/core/block_attribs.py)):
  - Tuotetietotagit (`MALLI`/`VALMISTAJA`/`KUVAUS`/`KOMMENTTI`/`LINKKI`)
    â†’ FI_Tuote, kuten ennen.
  - **Kaikki muut ATTDEF:t â†’ FI_Tekninen sellaisenaan.** Solibrissa
    nÃ¤kyvÃ¤ kentÃ¤n nimi = ATTDEFin **prompt** (tai raaka tag jos prompt
    on tyhjÃ¤). Ei alias- eikÃ¤ kanonista-nimi-arvausta â€” blokki on speksi.
  - TyhjÃ¤ arvo sÃ¤ilyy tyhjÃ¤nÃ¤ paikkamerkkirivinÃ¤ (tekninen vÃ¤lilehti
    toimii tÃ¤ytettÃ¤vÃ¤nÃ¤ speksilomakkeena) muttei ylikirjoita aiempaa
    arvoa (esim. energy-Excel-mergeÃ¤).
- **ATTDEF-blokit eivÃ¤t enÃ¤Ã¤ saa tyyppikohtaista oletuskenttÃ¤settiÃ¤.**
  Jos blokilla on omat ATTDEF:t, ne ovat koko FI_Tekninen â€” ei
  `_FI_TEKNINEN_DEFAULTS`-templatea pÃ¤Ã¤lle ([`finnish_psets.py`](src/dwg2ifc/core/finnish_psets.py)).
- ATTDEFin **prompt** luetaan nyt blokin mÃ¤Ã¤rityksestÃ¤ ja kuljetetaan
  mukana: `EntityRecord.block_attribs` on `dict[str,str]`:n sijaan
  jÃ¤rjestyksen sÃ¤ilyttÃ¤vÃ¤ `list[BlockAttrib]` (tag, prompt, value).
- Energy-spec Excel -tuonti kÃ¤yttÃ¤Ã¤ yhÃ¤ omaa alias-systeemiÃ¤Ã¤n
  (`energy_specs._FIELD_ALIASES`) â€” se on erillinen syÃ¶tepolku eikÃ¤
  muuttunut.
- Ohje [`docs/BLOCK_ATTRIBS.md`](docs/BLOCK_ATTRIBS.md) kirjoitettu
  uusiksi: prompt = Solibri-nimi, tag = vapaa tunniste.

## v0.3.0-alpha8 â€” 2026-05-21 (FI_Tuote valmistaja + malli ATTRIB:eilla)

- **Block-ATTRIB:t ohjautuvat nyt myÃ¶s FI_Tuotteeseen**, eivÃ¤t vain
  FI_Tekniseen. Koneikoille ja lauhduttimille voi merkitÃ¤ per-laite
  valmistajan ja mallin suoraan blokin ATTRIB:eihin â†’ Solibrin
  tuoteosa-nÃ¤kymÃ¤ tÃ¤yttyy ilman erillistÃ¤ ExceliÃ¤ tai profile-sÃ¤Ã¤ntÃ¶Ã¤:
  - `MALLI` (aliakset `LAITE`/`NIMI`/`MODEL`/`TUOTENIMI`/`TUOTE`) â†’
    "Tuotetyypin nimi"
  - `VALMISTAJA` (`MANUFACTURER`/`BRAND`) â†’ "Tuotetyypin valmistaja"
  - `KUVAUS` (`DESCRIPTION`) â†’ "Tuotetyypin kuvaus"
  - `KOMMENTTI` (`COMMENT`) â†’ "Tuotteen kommentti"
  - `LINKKI` (`LINK`/`URL`/`DATASHEET`) â†’ "Tuotetyypin valmistajan linkki"
- **"Tuotetyypin nimi" -etusijajÃ¤rjestys**: `MALLI`-ATTRIB â†’ profiilin
  `fi_tuote.nimi` â†’ alpha7:n IFC-tyyppi-auto-laitenimike. Eli tyhjÃ¤
  `MALLI` jÃ¤ttÃ¤Ã¤ nÃ¤kyviin "Koneikko"/"Lauhdutin", tÃ¤ytetty `MALLI`
  korvaa sen oikealla mallinimellÃ¤. Laitetyyppi sÃ¤ilyy joka tapauksessa
  FI_Komponentti â†’ yleisnimi -kentÃ¤ssÃ¤.
- `block_attribs.py` reitittÃ¤Ã¤ tagin ensin FI_Tuote-alias-systeemin
  lÃ¤pi, sitten FI_Tekninen-systeemin (energy_specs); tuntematon tagi
  ohitetaan. Ohje [`docs/BLOCK_ATTRIBS.md`](docs/BLOCK_ATTRIBS.md)
  pÃ¤ivitetty FI_Tuote-tagitaulukolla.

## v0.3.0-alpha7 â€” 2026-05-19 (FI_Tuote.Tuotetyypin nimi auto-tÃ¤yttyy)

- **"Tuotetyypin nimi" -kenttÃ¤ on aina tÃ¤ytetty** Solibrin tuoteosa-
  nÃ¤kymÃ¤ssÃ¤: tyhjÃ¤n placeholderin tilalla on suomenkielinen
  laitenimike per IFC-tyyppi, kun profiili tai ATTRIB ei aseta omaa
  arvoa. KÃ¤yttÃ¤jÃ¤ nÃ¤kee yhdellÃ¤ silmÃ¤yksellÃ¤ mistÃ¤ laitteesta on kyse.
  Auto-mappaus:
  - IfcEvaporator â†’ "HÃ¶yrystin"
  - IfcCondenser â†’ "Lauhdutin"
  - IfcCompressor â†’ "Kompressori"
  - IfcUnitaryEquipment â†’ "Koneikko"
  - IfcChiller â†’ "VesijÃ¤Ã¤hdytin"
  - IfcTank â†’ "SÃ¤iliÃ¶", IfcFlowController â†’ "SÃ¤Ã¤din"
  - IfcSensor â†’ "Anturi", IfcAlarm â†’ "HÃ¤lytin",
    IfcElectricDistributionBoard â†’ "SÃ¤hkÃ¶keskus", IfcController â†’
    "Ohjain", IfcSwitchingDevice â†’ "Kytkin"
  - IfcCableCarrierSegment â†’ "Asennushylly" (yleinen â€” KYL-LEVYHYLLY*
    / KYL-TIKASHYLLY* / KYL-KOTELO* -sÃ¤Ã¤nnÃ¶t ohittavat tÃ¤mÃ¤n omilla
    nimillÃ¤ "Levyhylly" / "Tikashylly" / "Kotelo")
  - IfcWall â†’ "SeinÃ¤", IfcSlab â†’ "Laatta", IfcDoor â†’ "Ovi",
    IfcWindow â†’ "Ikkuna", IfcPipeSegment â†’ "Putki",
    IfcBuildingElementProxy â†’ "SÃ¤hkÃ¶laite", IfcFurniture â†’ "Kaluste"
- **Per-laite ATTRIB-tagit FI_Tuotteeseen** (LAITE / VALMISTAJA / â€¦)
  jÃ¤tetty myÃ¶hemmin â€” tÃ¤mÃ¤ release vain tÃ¤yttÃ¤Ã¤ automaattisesti
  laitetyypin nimen, kÃ¤yttÃ¤jÃ¤n per-instanssi-override tulee toisessa
  releasessa kun tarve vahvistuu.

## v0.3.0-alpha6 â€” 2026-05-19 (KORJAUS â€” mapper menetti ATTRIB-tiedot)

- **KORJAUS â€” alpha5:n block-ATTRIB-tuki ei toiminut**: `apply_profile`
  rakensi uuden `MappedEntity`:n EntityRecord:istÃ¤ mutta unohti
  kopioida `block_attribs`-kentÃ¤n. Kaikki muut (layer, attributes,
  block_name, handle, jne.) propagoituvat, vain ATTRIB tagâ†’value -kartta
  jÃ¤i default-tyhjÃ¤ksi. `apply_block_attribs` nÃ¤ki siten tyhjÃ¤n dictin
  eikÃ¤ tehnyt mitÃ¤Ã¤n â†’ Solibrin FI_Tekninen-PSet nÃ¤ytti pelkÃ¤t tyhjÃ¤t
  default-kentÃ¤t vaikka kÃ¤yttÃ¤jÃ¤ oli tÃ¤yttÃ¤nyt Properties-paletissa
  arvot blokille.
- **Vahvistettu Laurin testitiedostoilla** (Lauhdutin atttest.dwg +
  Koneikko atttest.dwg): kaikki 8 ATTRIB-kenttÃ¤Ã¤ (Lauhdutusteho,
  SÃ¤hkÃ¶teho, Vastusteho, JÃ¤nnite, KylmÃ¤aine, Ilmavirta, Ã„Ã¤niteho,
  KÃ¤yttÃ¶lÃ¤mpÃ¶tila) pÃ¤Ã¤tyvÃ¤t nyt FI_Tekniseen oikeilla yksikÃ¶illÃ¤
  sekÃ¤ IfcCondenser- ettÃ¤ IfcUnitaryEquipment-tuotteille.
- **Regressiotesti** `test_mapper.py::test_apply_profile_propagates_block_attribs_to_mapped_entity`
  estÃ¤Ã¤ saman bugin uudelleenilmaantumisen.

## v0.3.0-alpha5 â€” 2026-05-19 (block-ATTRIB:t â†’ FI_Tekninen per-laite)

- **AutoCAD/BricsCAD-blokkien ATTRIB-arvot mergetÃ¤Ã¤n suoraan
  FI_Tekninen-PSettiin** per-laite-pohjaisesti. Lauhduttimille +
  koneikoille ei tarvita enÃ¤Ã¤ erillistÃ¤ Excel-tiedostoa: lisÃ¤Ã¤
  ATTDEF-mÃ¤Ã¤ritykset blokin lÃ¤hde-DWG:hen, kÃ¤yttÃ¤jÃ¤ tÃ¤yttÃ¤Ã¤ arvot
  Properties-paletista (tai tuplaklikistÃ¤), dwg2ifc lukee ne
  `INSERT.attribs`:sta ja mappaa kanonisiksi FI_Tekninen-kentiksi
  saman alias-systeemin kautta kuin Excel-headerit.
- **Tag-konventio**: tagi on iso kirjain, ei Ã¤Ã¤kkÃ¶siÃ¤, ei vÃ¤lilyÃ¶ntejÃ¤,
  ei yksikkÃ¶jÃ¤ â€” esim. `LAUHDUTUSTEHO` â†’ kanoninen "Lauhdutusteho (kW)".
  Englanninkielisetkin aliakset toimivat (`VOLTAGE`, `REFRIGERANT`).
  Tuntemattomat tagit ohitetaan (ei tipu junkkina PSetiin).
- **Konflikti-politiikka**: per-laite ATTRIB voittaa projektin-laajuisen
  Excel-arvon â€” instanssi-spesifinen tieto on aina tarkempaa. TyhjÃ¤ /
  whitespace-only ATTRIB ohitetaan eikÃ¤ korvaa olemassaolevaa arvoa.
- **Step-by-step-ohje BricsCAD/AutoCAD:lle**: ks.
  [`docs/BLOCK_ATTRIBS.md`](docs/BLOCK_ATTRIBS.md). Sama `_ATTDEF` toimii
  molemmissa CAD-ohjelmissa identtisesti, DXF-tasolla on standardia.
- **Tekninen**: uusi `core/block_attribs.py`-moduli + 11 testiÃ¤.
  `EntityRecord.block_attribs` kantaa tagâ†’value-mappauksen kun
  `dxf_reader` lukee INSERT:n; `orchestrator._process_one_file` kutsuu
  `apply_block_attribs(mapped)` heti energy-spec-luvun jÃ¤lkeen, joten
  Excel + ATTRIB toimivat saumattomasti yhdessÃ¤.

## v0.3.0-alpha4 â€” 2026-05-19 (FI_Tekninen-kenttien nimiin yksikÃ¶t suluissa)

- **Numeerisilla FI_Tekninen-kentillÃ¤ yksikkÃ¶ nimen perÃ¤ssÃ¤ suluissa.**
  Solibrin tuoteosa-nÃ¤kymÃ¤ esitti ennen "JÃ¤Ã¤hdytysteho: 12.5" â€” yksikkÃ¶
  jÃ¤i kenttÃ¤nimestÃ¤ uupumaan ja kÃ¤yttÃ¤jÃ¤ joutui arvaamaan onko luku
  W vai kW. Nyt avaimena "JÃ¤Ã¤hdytysteho (kW)" ja arvona pelkkÃ¤ numero
  "12.5". PÃ¤ivitetyt kentÃ¤t:
  - JÃ¤Ã¤hdytysteho (kW), Lauhdutusteho (kW), SÃ¤hkÃ¶teho (kW), Vastusteho (kW)
  - JÃ¤nnite (V), Ilmavirta (mÂ³/h), Ã„Ã¤niteho (dB(A))
  - KÃ¤yttÃ¶lÃ¤mpÃ¶tila (Â°C), HÃ¶yrystymislÃ¤mpÃ¶tila (Â°C), LauhtumislÃ¤mpÃ¶tila (Â°C)
  - JÃ¤Ã¤hdyttÃ¤vÃ¤ vaikutus (kW), Eristyspaksuus (mm), PainekestÃ¤vyys (bar)
- **TekstikentÃ¤t** (KylmÃ¤aine, Materiaali, Pinnoite, Eristys) jÃ¤tetÃ¤Ã¤n
  ilman yksikkÃ¶Ã¤ â€” eivÃ¤t ole numeerisia.
- **Excel-luku** toimii muuttumatta: `_normalise_header` strippaa
  yksikkÃ¶-suluet ennen alias-matchausta, joten "JÃ¤Ã¤hdytysteho [kW]"
  -niminen sarake mappautuu yhÃ¤ oikein uuteen kanoniseen nimeen
  "JÃ¤Ã¤hdytysteho (kW)".
- **Vanhat IFC-tiedostot** sÃ¤ilyttÃ¤vÃ¤t vanhat kenttÃ¤nimet (Solibrissa
  rinnakkain uusien kanssa); ei kosketa olemassaolevia tiedostoja.

## v0.3.0-alpha3 â€” 2026-05-18 (itsepÃ¤ivitys ei enÃ¤Ã¤ yritÃ¤ kÃ¤ynnistÃ¤Ã¤ itseÃ¤Ã¤n)

- **Auto-restart pois itsepÃ¤ivityksestÃ¤.** alpha37:n cmd-launcher
  korjasi "ei kÃ¤ynnisty ollenkaan" -ongelman, mutta unsigned
  PyInstaller-onefile-buildin bootloader-race Windows Defenderin
  reaaliaikatarkistuksen kanssa tuotti yhÃ¤ `Failed to load Python DLL`
  -virheen launcher-spawnatussa restartissa. SignPath ei toteudu, joten
  cleaner ratkaisu on luopua koko auto-restartista: pÃ¤ivitys lataa +
  vaihtaa exen + nÃ¤yttÃ¤Ã¤ "PÃ¤ivitys asennettu. Avaa dwg2ifc uudelleen
  tyÃ¶pÃ¶ydÃ¤ltÃ¤ tai KÃ¤ynnistÃ¤-valikosta." -dialogin + sulkee appin.
  KÃ¤yttÃ¤jÃ¤n manuaalinen klikkaus tyÃ¶pÃ¶ytÃ¤pikakuvaketta antaa Defenderille
  riittÃ¤vÃ¤n skannausajan â†’ DLL-race ei laukea.
- **Tekninen**: `schedule_replace_and_restart` sÃ¤ilyy backward-compat-
  aliaksena joka kutsuu uutta `replace_exe`:Ã¤ â€” `extra_args` ja
  `delay_seconds` -parametrit hyvÃ¤ksytÃ¤Ã¤n mutta ohitetaan. cmd-launcher-
  koodi (`_spawn_delayed_launcher` + batch-builderit) jÃ¤Ã¤ lÃ¤hdekoodiin
  jos joskus tulee allekirjoitettu build jolloin auto-restart toimisi.

## v0.3.0-alpha2 â€” 2026-05-18 (nÃ¤kyvÃ¤t DXF-jÃ¤Ã¤nteet + launcher-ikkuna piiloon)

- **KORJAUS â€” itse-pÃ¤ivitys vilkutti hetken cmd-ikkunaa.** v0.3.0a1:n
  `DETACHED_PROCESS | CREATE_NO_WINDOW`-kombo on Microsoftin
  dokumentaation mukaan toisensa poissulkeva: `CREATE_NO_WINDOW`
  jÃ¤tetÃ¤Ã¤n huomiotta kun `DETACHED_PROCESS` on asetettu, ja cmd.exe
  saa silti konsoli-ikkunan. Tilalle canonical hidden-console-child-
  resepti: `STARTUPINFO.dwFlags |= STARTF_USESHOWWINDOW` +
  `wShowWindow = SW_HIDE` + `CREATE_NO_WINDOW`. Cmd-child elÃ¤Ã¤
  edelleen vanhemman `os._exit`-kutsun yli (Windows ei kasvattele
  prosessikuolemia ilman job objectia).
- **GUI-stringit DXF â†’ DWG/DXF**: alpha1 jÃ¤tti kolme nÃ¤kyvÃ¤Ã¤
  jÃ¤Ã¤nnettÃ¤ â€” About-dialogin teksti ("AutoCAD DXF â†’ IFC 4 â€¦"),
  pÃ¤Ã¤ikkunan caption ja CLI:n `--help`-description sanoivat vielÃ¤
  pelkkÃ¤Ã¤ "DXF". Nyt "DWG/DXF" kuvaa todellista syÃ¶tetukea.
  `style.qss`:n kommentti `/* dxf2ifc brand stylesheet */` siistitty.
- **Itse-pÃ¤ivityksen viive 3 s â†’ 5 s**: mitigoi unsigned PyInstaller-
  onefile-buildin + Windows Defenderin reaaliaikatarkistuksen vÃ¤listÃ¤
  race-conditionia (`Failed to load Python DLL`-virhe). Ei lopullinen
  korjaus â€” kÃ¤yttÃ¤jÃ¤lle suositeltava polku jos virhe toistuu: tuplaklikkaa
  exe uudestaan, Defender on ehtinyt skannata ja toinen yritys onnistuu.

## v0.3.0-alpha1 â€” 2026-05-18 (rebrand `dxf2ifc` â†’ `dwg2ifc`)

- **Projekti uudelleennimetty.** DWG on alpha21:stÃ¤ lÃ¤htien ollut
  ensisijainen syÃ¶te (preconvertataan headless `accoreconsole + DXFOUT`
  -reitillÃ¤), joten nimi `dxf2ifc` ei enÃ¤Ã¤ kuvannut todellista kÃ¤yttÃ¶Ã¤.
  Major bump v0.2.0 â†’ v0.3.0 merkkaa identiteetin vaihdon.
- **MitÃ¤ muuttui:** Python-paketti `src/dxf2ifc/` â†’ `src/dwg2ifc/`, CLI
  `dxf2ifc` â†’ `dwg2ifc`, GUI-launcher `dxf2ifc-gui` â†’ `dwg2ifc-gui`,
  exe + installer + asset-tiedostot (`dwg2ifc.ico`, `dwg2ifc.png`),
  PyInstaller-spec + Inno Setup `.iss`, GitHub Actions workflow:t,
  README/CLAUDE.md/PROGRESS.md ajantasalle. Inno Setup AppId uusittu
  niin ettÃ¤ dwg2ifc on erillinen ohjelma (vanha dxf2ifc-asennus jÃ¤Ã¤
  rinnalle, kÃ¤yttÃ¤jÃ¤ voi poistaa sen kÃ¤sin).
- **GitHub-repo `Mcrauli/dxf2ifc` â†’ `Mcrauli/dwg2ifc`.** Vanhat URL:t
  redirectoituvat automaattisesti; alpha37-asennusten autoupdater
  toimii redirectin yli ja tarjoaa v0.3.0a1:n normaalisti. Olemassa
  olevassa filesysteemissÃ¤ exe jÃ¤Ã¤ `dxf2ifc.exe`-nimiseksi mutta sisÃ¤ltÃ¶
  on dwg2ifc â€” siisti migraatio on ajaa uusi `dwg2ifc-Setup-0.3.0a1.exe`
  kÃ¤sin ja poistaa vanha dxf2ifc-asennus.
- **MitÃ¤ JÃ„I koskemattomaksi:** docs/* (ARCHITECTURE.md, CLAUDE_TASKS.md,
  DWG_MAGICAD_PREPROCESSING.md, plans/, superpowers/) viittaavat
  tarkoituksellisesti `dxf2ifc`-nimeen historiana, ja tmp/-arkisto +
  vanhat CHANGELOG-entriet sÃ¤ilyttÃ¤vÃ¤t alkuperÃ¤isen nimen. Vanhat
  git-tagit v0.1.xâ€“v0.2.0a37 elÃ¤vÃ¤t GitHubilla muuttumattomina.
- Funktiot kuten `convert_dxf()` ja `_aggregate_3dface_from_insert`
  pidettiin nimeltÃ¤Ã¤n ennallaan â€” niiden nimet kuvaavat sisÃ¤istÃ¤
  toimintaa (DXF-luenta) eivÃ¤tkÃ¤ tuotenimeÃ¤.

## v0.2.0-alpha37 â€” 2026-05-18 (itsepÃ¤ivityksen uudelleenkÃ¤ynnistys toimii)

- **KORJAUS â€” GUI:n itsepÃ¤ivitys sulki appin mutta ei kÃ¤ynnistÃ¤nyt sitÃ¤
  uudestaan.** Vanha viivÃ¤stetty launcher kÃ¤ytti hidden powershell.exe:tÃ¤ +
  ``Start-Process``-cmdlet:iÃ¤; jollain Windows-asennuksilla (execution-
  policy ``Restricted`` / ``AllSigned`` tai ``-NonInteractive``-yhteensopivuus-
  ongelma) launcher kuoli hiljaisesti eikÃ¤ uutta exeÃ¤ koskaan startannut.
  Tilalle cmd-pohjainen launcher: ``cmd.exe /c restart.cmd`` jossa
  ``timeout /t 3 /nobreak`` + ``start "" "<exe>"`` (canonical Windowsin
  detached-spawn) + itsensÃ¤ poistava .cmd. Ei execution policya, ei
  profile-latausta, ei interaktiivisuus-quirkeja.
- **NÃ¤kyvÃ¤ status pÃ¤ivityksen lopussa**: latauksen valmistuttua dialogi
  vaihtaa tekstiin "Asennetaan pÃ¤ivitys ja kÃ¤ynnistetÃ¤Ã¤n uudelleenâ€¦" +
  indeterminate-progress + Peruuta-nappi pois. KÃ¤yttÃ¤jÃ¤ nÃ¤kee ettei
  appin sulkeutuminen ole kaatuminen, vaan tarkoituksellinen viive.
- **Breadcrumb-log silent failure -tapauksiin**: launcher kirjoittaa
  jokaisesta vaiheesta ``%TEMP%\\dxf2ifc_restart.log``:iin (sleep,
  launch, errorlevel) jotta myÃ¶hempiÃ¤ silent-failures voi
  diagnosoida ilman patchatun build:n lÃ¤hettÃ¤mistÃ¤ takaisin.

## v0.2.0-alpha36 â€” 2026-05-18 (KYL-KOTELO geometria + FI_*-PSetit tÃ¤ydennetty)

- **KORJAUS â€” kotelon leveÃ¤ ylÃ¤seinÃ¤mÃ¤ nÃ¤ytti vajoavan sisÃ¤Ã¤npÃ¤in
  sivuseinÃ¤mien yli.** `_aggregate_3dface_from_insert` laski
  `block_max_top`:n kaavalla `max(3DFACE_z, max(polyline_elev) +
  DEFAULT_TOP_OFFSET_MM)`. KYL-KOTELO-blokin ylÃ¤slab on LWPOLYLINE
  elevaatiossa 118.2 â†’ fallback 118.2 + 9 = **127.2** voitti todellisen
  3DFACE-katon z=120. Ohuet sivuseinÃ¤mÃ¤-LWPOLYLINEt (leveys â‰¤ 5 mm,
  "thin rim") ekstrudoituivat tÃ¤hÃ¤n inflatoituun kattoon, joten ne
  tÃ¶rrÃ¶ttivÃ¤t 7.2 mm yli kotelon todellisesta ylÃ¤pinnasta ja ylÃ¤seinÃ¤mÃ¤
  jÃ¤i visuaalisesti niiden alle "sisÃ¤Ã¤npÃ¤in". Korjaus: kun blokissa
  on 3DFACEt, niitÃ¤ pidetÃ¤Ã¤n autoritaarisina; +9-fallback kÃ¤ytetÃ¤Ã¤n
  vain blokeille joissa ei ole yhtÃ¤Ã¤n 3DFACEa (legacy outline-blokit,
  KLHYLLY ei regressoi koska sen kaikki polylinet ovat pohjassa z=0).
- **KYL-KOTELO-sÃ¤Ã¤nnÃ¶lle tÃ¤ydet FI_*-PSetit** (alpha35:n minimaalinen
  versio jÃ¤i vaillinaiseksi): nyt levyhyllyn kaavan mukaisesti
  `fi_tekninen` (Materiaali=TerÃ¤s, Pinnoite=Polyesterimaalattu) +
  `fi_tuote` (nimi=Kotelo, valmistaja=MEKA). KÃ¤yttÃ¤jÃ¤ voi yliajaa
  valmistaja-kohtaiset speksit custom profile:n kautta.

## v0.2.0-alpha35 â€” 2026-05-18 (negatiivisen Z:n STLOUT-korjaus + KYL-KOTELO-mappaus)

- **KORJAUS â€” negatiivisessa Z:ssÃ¤ olevat 3DSOLID-laitteet litistyivÃ¤t
  kerroskorkoon.** AutoCAD:n `STLOUT` kieltÃ¤ytyy kirjoittamasta
  geometriaa datumin (Z=0) alapuolelle: se siirtÃ¤Ã¤ koko kappaleen +Z:ssÃ¤
  ylÃ¶s niin ettÃ¤ viety STL alkaa tismalleen Z=0:sta (X ja Y sÃ¤ilyvÃ¤t).
  NiinpÃ¤ Z=-5000:een piirretty koneikko palautui tessellÃ¶itynÃ¤ Z=0:aan,
  ja kerroskorko-offsetin jÃ¤lkeen *jokainen* datumin alapuolinen laite
  romahti kerroskorkoon (esim. objekti -5000 + kerros 1000 â†’ 1000, ei
  -4000). Korjaus: `preprocessing.py` lukee jokaisen ACIS-bodyn todellisen
  maailmankoordinaatti-min-Z:n DXF:stÃ¤ (ezdxf:n ACIS-purku, SAT + SAB) jo
  ennen accoreconsole-ajoa ja kumoaa STLOUT:n siirron meshikohtaisesti.
  Vain selvÃ¤sti siirretyt kappaleet korjataan (STL ~Z=0 + lÃ¤hdegeometria
  aidosti negatiivinen) â€” datumin ylÃ¤puolinen geometria ei regressoi.
- **Uusi layer-mappaus: `KYL-KOTELO*`** â†’ `IfcCableCarrierSegment` /
  `CABLETRUNKINGSEGMENT`. Kotelo on koteloitu (suljettu) kaapelireitti;
  `CABLETRUNKINGSEGMENT` erottaa sen avoimista tikas-/levyhyllyistÃ¤
  (`CABLELADDERSEGMENT` / `CABLETRAYSEGMENT`). RAVA-koodi
  `T-TATE-01-01-001`, KYL-domain. Kotelot piirretÃ¤Ã¤n
  `autocad-lisp-ohjeet/files/kotelo.lsp`-tyÃ¶kalulla (sama
  polyline+thickness-dynamic-block-rakenne kuin KLHYLLY-hyllyillÃ¤, joten
  preprocessing/geometry-polku toimii sellaisenaan).

## v0.2.0-alpha34 â€” 2026-05-14 (profiilieditori: haku, tÃ¤ysi IFC-lista, tallennus sovellukseen)

**Profiilieditori kÃ¤yttÃ¶kelpoisemmaksi** â€” kolme kÃ¤yttÃ¤jÃ¤palautteen
kipupistettÃ¤ korjattu:

- **HakukenttÃ¤ + selkeÃ¤ scrollipalkki**: sÃ¤Ã¤ntÃ¶taulukon ylÃ¤puolella
  hakukenttÃ¤ joka suodattaa rivit elÃ¤vÃ¤sti (layer pattern / IFC-tyyppi /
  domain / koodi). VieressÃ¤ laskuri joka kertoo montako sÃ¤Ã¤ntÃ¶Ã¤ nÃ¤kyy / yhteensÃ¤. Pystyscrollipalkki
  leveÃ¤mpi ja korkeakontrastinen amber-vetimellÃ¤ â€” nÃ¤kee yhdellÃ¤
  silmÃ¤yksellÃ¤ missÃ¤ kohtaa listaa ollaan. Add/Edit/Remove osuvat oikeaan
  sÃ¤Ã¤ntÃ¶Ã¶n myÃ¶s suodatettuna.
- **TÃ¤ysi IFC-tyyppivalikko**: pudotusvalikossa oli vain 11 tyyppiÃ¤,
  vaikka writer tukee ~29:Ã¤Ã¤. Nyt kaikki â€” jÃ¤Ã¤hdytyslaitteet, sÃ¤iliÃ¶t,
  sÃ¤hkÃ¶- ja jakelulaitteet â€” ryhmiteltynÃ¤ erottimin. Lista tulee yhdestÃ¤
  `SUPPORTED_IFC_TYPES`-vakiosta jota testi pitÃ¤Ã¤ synkassa orchestratorin
  kanssa.
- **Tallennus sovelluksen muistiin**: "Tallenna" kirjoittaa profiilin
  per-kÃ¤yttÃ¤jÃ¤-tiedostoon (`%APPDATA%\Mcrauli\dxf2ifc\active_profile.toml`)
  ja se latautuu automaattisesti kÃ¤ynnistyessÃ¤ â€” ei enÃ¤Ã¤ TOML-tiedoston
  etsimistÃ¤ ja lataamista joka kerta. Atominen kirjoitus; vioittunut
  tiedosto putoaa siististi oletusprofiiliin. "Reset to bundled default"
  poistaa tallennetun profiilin. Editorin Load/Save-tiedostodialogit
  poistettu. CLI:n `--profile` toimii ennallaan.

## v0.2.0-alpha33 â€” 2026-05-14 (KORJAUS: hÃ¶yrystimet jÃ¤ivÃ¤t tessellÃ¶imÃ¤ttÃ¤)

**Juurisyy-fix alpha32:n regressiolle â€” hÃ¶yrystimet tulivat vÃ¤Ã¤rin**:

alpha32:n `worthlist`-optimointi kirjoitti accoreconsolen `.scr`-skriptiin
listan blockeista jotka kannattaa rÃ¤jÃ¤yttÃ¤Ã¤. Lista sisÃ¤lsi myÃ¶s
Ã¤/Ã¶-kirjaimellisia nimiÃ¤ (`HÃ¶yrystin 1-puh`, `SÃ¤Ã¤dinkeskus`) sellaisinaan.
Kaksi asiaa rikkoi nÃ¤iden tÃ¤smÃ¤yksen:

1. `.scr` kirjoitetaan UTF-8:na, mutta accoreconsole lukee sen
   jÃ¤rjestelmÃ¤n ANSI-koodisivulla â†’ ei-ASCII-tavut menivÃ¤t sekaisin.
2. AutoLISPin `strcase` **ei** muunna `Ã¶ â†’ Ã–` kuten Python `str.upper()`
   tekee â†’ `(member (strcase bname) worthlist)` ei osunut vaikka tavut
   olisivat sÃ¤ilyneetkin.

Tulos: Phase 2 ohitti **jokaisen** hÃ¶yrystin-INSERTin EXPLODE-vaiheen
â†’ ei STLOUT-meshiÃ¤ â†’ hÃ¶yrystimet jÃ¤ivÃ¤t ilman tessellÃ¶ityÃ¤ geometriaa.
TIKASHYLLY / KONEIKKO / CO2-anturi yms. ovat puhdasta ASCII:ta, joten
ne toimivat normaalisti â€” vika osui vain Ã¤/Ã¶-nimisiin blockeihin.

Korjaus:

- **Worthlist-literaaliin vain ASCII-nimet** (`_worthlist_literal`).
  Ei-ASCII-nimiset blockit jÃ¤tetÃ¤Ã¤n pois listalta tarkoituksella.
- **Phase 2 rÃ¤jÃ¤yttÃ¤Ã¤ ei-ASCII-nimiset blockit aina** uuden LISP
  `asciip`-escapen kautta (`(not (asciip bname))`). Sama suoja sekÃ¤
  ylÃ¤tason ettÃ¤ sisÃ¤kkÃ¤isen INSERTin kohdalla.

Nopeutus sÃ¤ilyy ASCII-nimisille blockeille (dynamic-block-hyllyt,
2D-symbolit) â€” vain Ã¤/Ã¶-nimiset laitteet kulkevat nyt aina "rÃ¤jÃ¤ytÃ¤"-
polun. 564 testiÃ¤ lÃ¤pi (6 uutta worthlist-testiÃ¤; 2 pre-existing
fail ei liity tÃ¤hÃ¤n).

## v0.2.0-alpha32 â€” 2026-05-14 (Phase 2 ohittaa turhat EXPLODE-kutsut)

**Nopeutus â€” vain ACIS-sisÃ¤ltÃ¶iset blockit rÃ¤jÃ¤ytetÃ¤Ã¤n**:

Phase 2 rÃ¤jÃ¤ytti aiemmin JOKAISEN INSERTin nÃ¤hdÃ¤kseen onko sisÃ¤llÃ¤
3DSOLIDeja. RÃ¤jÃ¤ytys-raskaissa kuvissa suurin osa INSERTeistÃ¤ on
dynamic-block-hyllyjÃ¤ ja 2D-symboleita joissa ei ole yhtÃ¤Ã¤n ACIS-bodya
â€” ezdxf lukee ne suoraan, accoreconsolea ei tarvita. (Testitiedostossa
131 INSERTistÃ¤ vain 53:ssa oli 3DSOLIDeja â†’ 78 turhaa EXPLODE-kutsua.)

Nyt Python skannaa blockimÃ¤Ã¤rittelyt **transitiivisesti** (myÃ¶s
sisÃ¤kkÃ¤isten INSERTtien lÃ¤pi â€” tÃ¤mÃ¤ hoitaa layer-0-kontit oikein) ja
vÃ¤littÃ¤Ã¤ accoreconsolelle listan blockeista jotka oikeasti sisÃ¤ltÃ¤vÃ¤t
ACIS-bodyja. Phase 2 rÃ¤jÃ¤yttÃ¤Ã¤ vain ne. TyhjÃ¤ lista / liian pitkÃ¤
literaali / epÃ¤varma blockinimi â†’ "rÃ¤jÃ¤ytÃ¤ kaikki" (turvallinen
fallback).

Mitattu: 2krs.dwg 10.6s â†’ 8.5s, testitiedosto 36s â†’ 22.6s.

## v0.2.0-alpha31 â€” 2026-05-14 (accoreconsole-tessellointi ~3Ã— nopeampi)

**Nopeutus â€” yksi STLOUT per INSERT, ei per body**:

Phase 2 teki aiemmin yhden erillisen `STLOUT`-kutsun (+ komento-
round-trip + tiedostokirjoitus) JOKAISELLE rÃ¤jÃ¤ytetylle 3DSOLIDille â€”
65-solidinen koneikko-block tarkoitti 65 kutsua. Nyt koko rÃ¤jÃ¤ytetty
body-valintajoukko kerÃ¤tÃ¤Ã¤n yhteen `ssadd`-settiin ja STLOUTataan
**yhdellÃ¤ kutsulla** per INSERT (`insert_out/<ih>.stl`). STLOUT
ketjuttaa kaikkien valittujen solidien kolmiot yhteen STL-tiedostoon,
mikÃ¤ on tismalleen se per-INSERT-mesh jonka Python-puoli muutenkin
haluaa â€” joten kymmenet kutsut korvautuvat yhdellÃ¤. Mitattu
testitiedostolla: STLOUT-vaihe ~78 s â†’ ~25 s.

ACIS-tyyppitarkistus siirretty SETUP-formin `acis?`-helperiksi (pitÃ¤Ã¤
PHASE2:n 2048-merkin .scr-rivirajan alla). Python-puolen per-INSERT-
mesh-merge poistettu â€” tarpeeton kun STLOUT tuottaa jo yhden tiedoston.

**Peruttu â€” alpha29:n layer-filter**:

alpha29 johti ssget-layer-suodattimen profiilista rajatakseen
tessellointia. Se osoittautui hauraaksi: laite-INSERTit ovat usein
layer "0":lla olevien kontti-blockien sisÃ¤llÃ¤, jolloin
`KYL-*`-suodatin Phase 2:n INSERT-valinnassa pudotti koko
laitehaaran. Suodatin peruttu â€” tessellÃ¶idÃ¤Ã¤n taas kaikki, mapperi
pudottaa mappaamattoman geometrian joka tapauksessa. STLOUT-batching
hoitaa nopeutuksen turvallisesti ilman korrektisuusriskiÃ¤.

## v0.2.0-alpha30 â€” 2026-05-14 (kerros-korko siirtÃ¤Ã¤ geometriaa taas)

**Palautettu â€” kerros-korko siirtÃ¤Ã¤ geometriaa**:

alpha29 poisti geometrian siirron (kerros-korko vain
`IfcBuildingStorey.Elevation`-metadataksi). Se oli vÃ¤Ã¤rÃ¤ tulkinta â€”
kerros-koron KUULUU liikuttaa objekteja. Palautettu vanha logiikka,
sama joka oli vanhassa "LisÃ¤Ã¤ 1.krs absoluuttinen korko" -checkboxissa,
mutta ilman valintanappia â€” aina pÃ¤Ã¤llÃ¤:

`world_Z = kerros_korko + dxf_Z`

Eli kunkin tiedoston geometria nostetaan sen rivin Z-arvon verran, ja
`IfcBuildingStorey` asetetaan samalle korolle. Korko 0 â†’ CAD-koordinaatit
sellaisinaan (no-op). TÃ¤mÃ¤ on kÃ¤ytÃ¤nnÃ¶ssÃ¤ alpha28-kÃ¤yttÃ¤ytyminen ilman
alpha29:n vÃ¤livaihetta.

ACIS-tesselloinnin layer-filter-nopeutus (alpha29) sÃ¤ilyy ennallaan.

## v0.2.0-alpha29 â€” 2026-05-14 (ACIS-tessellointi nopeampi)

> Huom: alpha29 sisÃ¤lsi myÃ¶s kerros-koron geometriasiirron poiston, joka
> osoittautui vÃ¤Ã¤rÃ¤ksi tulkinnaksi ja palautettiin alpha30:ssÃ¤. Vain
> alla kuvattu nopeutus jÃ¤i voimaan.

**Nopeutus â€” ACIS-tessellointi rajataan profiilin layereihin**:

`accoreconsole.exe` STLOUT-tessellÃ¶i aiemmin JOKA 3DSOLIDin JOKA
layerilla (`layer_filter="*"`) â€” myÃ¶s arkkitehti/rakenne-XREF:ien
bodyt jotka mapperi joka tapauksessa pudottaa. Nyt orchestrator johtaa
ssget-layer-suodattimen aktiivisen profiilin layer-patterneista (esim.
oletusprofiili â†’ `KYL-*,KAAPELIHYLLY*,LT *,MT *,MUUT_OSAT*`) ja
vÃ¤littÃ¤Ã¤ sen `extract_acis_meshes`:lle. Suodatin elÃ¤Ã¤ SETUP-formin
`lyrfilter`-muuttujassa (PHASE1/PHASE2 lukevat `(cons 8 lyrfilter)`),
koska inline-substituutio rikkoisi 2048-merkin .scr-rivirajan.
SisÃ¤kkÃ¤iset block-3DSOLIDit (usein layer "0") tessellÃ¶ityvÃ¤t yhÃ¤ â€”
suodatin koskee vain ylÃ¤tason valintaa. Profiili ilman sÃ¤Ã¤ntÃ¶jÃ¤ tai
`*`-pattern â†’ `"*"` (kaikki).

## v0.2.0-alpha28 â€” 2026-05-14 (ROOT CAUSE: TILEMODE â€” modelspace forced)

**Juurisyy lÃ¶ytyi ja korjattiin.** 2krs.dwg:n kaltaiset tiedostot
(tallennettu paper-space-layout-vÃ¤lilehti aktiivisena) saivat
accoreconsolen STLOUT-Phase-1:n hylkÃ¤Ã¤mÃ¤Ã¤n JOKA ikisen modelspace-
3DSOLIDin virheellÃ¤ "1 was not in current space". STLOUT operoi vain
aktiivisessa tilassa, ja accoreconsole avaa DWG:n siihen vÃ¤lilehteen
joka oli aktiivisena tallennettaessa. HylÃ¤tyt valinnat jÃ¤ivÃ¤t
roikkumaan STLOUT-promptiin, seuraavan loopin token syÃ¶tiin
selektioksi, komentopino korruptoitui â†’ STATUS_STACK_BUFFER_OVERRUN.

Korjaukset (kaikki preprocessing.py:n LISP-skriptissÃ¤):

1. **`(setvar "TILEMODE" 1)`** SETUP-formissa â€” pakottaa Model-tabin
   aktiiviseksi heti. TÃ¤mÃ¤ on varsinainen juurisyy-fix: nyt
   modelspace-bodyt ovat valittavissa STLOUTille.
2. **`flushcmd`-helper + `(fc)`-kutsut** jokaisen STLOUT/EXPLODE/
   CONVTOSOLID-kutsun jÃ¤lkeen â€” peruu mahdollisen roikkuvan komennon
   (`(command)` ilman argumentteja = ESC). Defence-in-depth: vaikka
   joku body olisi aidosti viallinen, se ei enÃ¤Ã¤ kaada koko prosessia
   eikÃ¤ syÃ¶ seuraavia komentoja.
3. **Workdir sÃ¤ilyy levyllÃ¤ kun accoreconsole exitoi != 0** â€” aiempi
   `finally: shutil.rmtree(workdir)` poisti diagnostiikan AINA, vaikka
   "diagnostics preserved" -viesti lupasi muuta. Nyt extract.log +
   accoreconsole.log + extract.scr jÃ¤Ã¤vÃ¤t talteen crash-analyysiÃ¤
   varten.

Tulos: 2krs.dwg:n koneikot (block "4+3") ja lauhduttimet (block
"kaasunjaahdytin") + raaka-3DSOLIDit tessellÃ¶ityvÃ¤t nyt OIKEINA
IfcFacetedBrep-kappaleina â€” ei placeholder-laatikoita, ei
CER-popuppia, ei crashia.

## v0.2.0-alpha27 â€” 2026-05-13 (SAB-bbox fallback + handle propagation)

Sukellettiin 4002_2krs.dwg:n kaltaisten tiedostojen kohdalle. NiissÃ¤
KYL-KONEIKKO / KYL-LAUHDUTIN -blokit (block "4+3" 65 3DSOLIDilla, block
"kaasunjaahdytin" 31:llÃ¤) kaatavat accoreconsole STLOUT:in
stack-buffer-overrun-virheeseen (0xC0000409) ennen kuin yhtÃ¤kÃ¤Ã¤n
meshia ehtii valmistua. Alpha25:n bbox-fallback ei aktivoitunut nÃ¤ille
kahdesta syystÃ¤ jotka nyt korjattu:

1. **mapper unohti propagatoida `handle`-kentÃ¤n** EntityRecord â†’
   MappedEntity, joten bbox-fallback ei pystynyt lÃ¶ytÃ¤mÃ¤Ã¤n alkuperÃ¤istÃ¤
   INSERTia uudelleen DXF:stÃ¤ handle-lookupilla. Yhden rivin korjaus
   `core/mapper.py`:hin.

2. **ezdxf:n `bbox.extents([INSERT])` palauttaa tyhjÃ¤n** kun blokin
   sisÃ¤llÃ¤ on vain 3DSOLIDeja (ACIS SAB v4 binÃ¤Ã¤rimuoto, jonka
   strukturoitu parseri ei vielÃ¤ lue). LisÃ¤tty rinnakkais-fallback joka
   skannaa SAB-binÃ¤Ã¤rin raakatavuista `0x14`-position-opcodet ja niitÃ¤
   seuraavat IEEE-754-doublet (x,y,z), yhdistÃ¤Ã¤ bodyjen vertex-pilvet
   yhdeksi laatikoksi, ja transformoi INSERT-asettelun (insertion +
   rotation + scale) mukaan world-koordinaatteihin.

Tuloksena 2krs.dwg:n koneikot ja lauhduttimet nÃ¤kyvÃ¤t nyt IFC:ssÃ¤
laatikko-placeholdereina vaikka itse accoreconsole-crash on yhÃ¤
olemassa â€” kÃ¤yttÃ¤jÃ¤ saa visuaalisen vahvistuksen ettÃ¤ equipment on
oikealla paikalla, eikÃ¤ mitÃ¤Ã¤n tipu hiljaa.

## v0.2.0-alpha26 â€” 2026-05-13 (suppress AutoCAD CER popup)

Vaiennetaan AutoCAD-Customer Error Report -popup joka muuten aukeaa
joka kerta kun accoreconsolen STLOUT kaatuu jonkun spesifin 3DSOLIDin
kohdalla. Korjaus lisÃ¤Ã¤ LISP SETUP-formiin `(setvar "REPORTERROR" 0)` +
`(setvar "SENDREPORTINFO" 0)` jolloin AutoCAD ei nosta CER-dialogia
prosessin kaatuessa. Konversio etenee normaalisti â€” alpha25:n
bbox-fallback hoitaa puuttuvat meshit edes laatikoiksi.

Itse kaatuminen ei ole ratkaistu (tarvitsee DWG-spesifisen 3DSOLID-
analyysin), mutta kÃ¤yttÃ¤jÃ¤lle vaikutus on nyt nÃ¤kymÃ¤tÃ¶n.

## v0.2.0-alpha25 â€” 2026-05-13 (accoreconsole-kestÃ¤vyys + bbox-fallback + diagnostics)

Kolmen yhdistelmÃ¤korjaus jotka adressoivat 2.krs-tyyppisiÃ¤ DWG:itÃ¤
jotka kaatavat accoreconsole STLOUT:in:

- **Bbox-fallback** â€” kun acis-mesh puuttuu (accoreconsole crashasi tai
  ei ajettu), cooling-equipment / proxy / distribution-element /
  furniture / tank -INSERT:in geometria korvataan ezdxf:n laskemalla
  block-bbox-cuboidilla. Tulos: koneikot, lauhduttimet jne. nÃ¤kyvÃ¤t
  edes laatikko-placeholderina IFC:ssÃ¤ oikealla XY-paikalla, eivÃ¤t
  enÃ¤Ã¤ tipu kokonaan kuvasta.
- **Per-body diagnostics-loggaus** â€” Phase 1 ja Phase 2 kirjaavat
  kÃ¤siteltÃ¤vÃ¤n handle:n / block-nimen `extract.log`-tiedostoon ENNEN
  STLOUT/EXPLODE-kutsua. Kun accoreconsole crashaa, log-tiedosto
  paljastaa MIKÃ„ body / blokki laukaisi kaatumisen â€” toistaiseksi
  sokean tyÃ¶n ja arvailun sijaan.
- **Robusti .scr-kirjoitus** â€” `Path.write_text` korvattu
  `write_bytes`:llÃ¤ jotta Windows-tekstimoodi ei kahdenna `\\r\\n` â‡’
  `\\r\\r\\n` (mikÃ¤ on havaittu sotkevan accoreconsolen .scr-parserin
  joillain DWG:illÃ¤). ItsestÃ¤Ã¤nselvÃ¤, mutta defensiivinen.

## v0.2.0-alpha24 â€” 2026-05-13 (always skip MagiCAD blocks in accoreconsole Phase 2)

**Korjattu â€” AutoCAD CER 2.krs:n koneikoilla/lauhduttimilla**:

Accoreconsolen Phase 2 INSERT-EXPLODE laukaisi CER-popupin sellaisilla
DWG:illÃ¤ joissa on MagiCAD-blokkeja, vaikka `--magicad-ifc`-flagia ei
oltu annettu (alpha18:n fix oli ehdollinen siihen flagiin). Tuloksena
3DSOLIDit, jotka olivat samassa tyÃ¶passissa, jÃ¤ivÃ¤t tessellÃ¶imÃ¤ttÃ¤ ja
koneikko/lauhdutin-objektit eivÃ¤t tulleet IFC:hen.

TÃ¤stÃ¤ versiosta MagiCAD-blokit (`MAGI*` / `*MAGICAD*` / `MAG_*`)
ohitetaan AINA accoreconsolen Phase 2:ssa. `.arx`-moduulit eivÃ¤t
lataudu accoreconsoleen muutenkaan, joten nÃ¤iden EXPLODE ei tuottanut
hyÃ¶dyllistÃ¤ geometriaa edes silloin kun se ei kaatunut.

## v0.2.0-alpha23 â€” 2026-05-13 (multi-floor merge â€” N DWG â†’ 1 IFC)

**Uusi â€” Multi-floor DWG â†’ yksi IFC**:

dxf2ifc hyvÃ¤ksyy nyt useita DXF/DWG-tiedostoja yhteen IFC:hen. Jokainen
tiedosto = yksi `IfcBuildingStorey`. GUI:ssÃ¤ monirivinen taulukko
(tiedosto / kerros / Z mm), CLI:ssÃ¤ `--floor PATH[:LABEL[:ELEV_MM]]`
toistettavasti. Labeli kirjoitetaan `IfcBuildingStorey.Name`-kenttÃ¤Ã¤n
sellaisenaan ("1.krs", "2.krs", "kellari", â€¦). Maailma-Z =
`kerroksen korko + DXF-objektin Z`, joten kaikki kerrokset @ 0 mm
pÃ¤Ã¤stÃ¤Ã¤ AutoCADin absoluuttiset Z:t lÃ¤pi sellaisinaan.

**Breaking changes**:

- Profiilin `storey_z_levels_mm`-kenttÃ¤ poistettu. Vanhat custom-TOML:t
  jotka kÃ¤yttÃ¤vÃ¤t sitÃ¤ eivÃ¤t enÃ¤Ã¤ validoidu â€” poista rivi.
- GUI:n "LisÃ¤Ã¤ 1.krs absoluuttinen korko" -valintaruutu ja yksittÃ¤inen
  korko-spinbox poistettu. Korko asetetaan per kerros taulukon
  Z-sarakkeessa.
- `RecentFilesStore`:sta poistettu `floor_elevation_mm` ja
  `floor_elevation_enabled` â€” globaalia tilaa ei enÃ¤Ã¤ tarvita.

**SisÃ¤istÃ¤**:

- `orchestrator.convert(files: list[FileEntry], â€¦)` on uusi
  pÃ¤Ã¤entrypoint. `convert_dxf(...)` sÃ¤ilytetty yhden tiedoston shim:nÃ¤
  takaisinpÃ¤in yhteensopivuuden vuoksi.
- `MappedEntity.storey_index` kuljettaa jokaisen entiteetin
  omistaja-storeyn writerille; orchestrator ei enÃ¤Ã¤ kutsu
  `skeleton.resolve_storey`:ta.

## v0.2.0-alpha22 â€” 2026-05-13 (3D-rotaatio-fixi LWPOLYLINE-ekstrudointiin)

**Korjattu â€” KLHV (pystytetty TIKAS-hylly) ei enÃ¤Ã¤ romahda yhdeksi pystypalkiksi**:

**Korjattu â€” KLHV (pystytetty TIKAS-hylly) ei enÃ¤Ã¤ romahda yhdeksi pystypalkiksi**:

KLHYLLY-TIKAS-blockin INSERT-rÃ¤jÃ¤ytys kÃ¤ytti aikaisemmin block-sisÃ¤isen
LWPOLYLINEn vain XY-osaa ja extrudoi paksuuden aina WCS-Z-akselin
suuntaan. Kun KLHV pystyttÃ¤Ã¤ saman blockin asettamalla INSERT.extrusion
= (0, -1, 0), block-lokaalin Z-akseli osoittaa WCS:n -Y-suuntaan ja
askelmien LWPOLYLINEt ovat eri Z-arvoilla. Edellinen logiikka:

1. luki ainoastaan (x, y) pisteistÃ¤ ja hukkasi Z:n,
2. kÃ¤ytti yhden vertikseksen Z:tÃ¤ `base_z`-arvona,
3. extrudoi `(p[0], p[1], top_z)` â€” eli pystysuoraan WCS:n Z:n suuntaan.

Tuloksena kaikki askelmat romahtivat samaan tasoon ja muodostivat
yhden pitkÃ¤n pystypalkin oikean ladder-rakenteen sijaan.

Uusi logiikka aggregoi koko blockin Object Coordinate SystemissÃ¤
(OCS) jonka Z-akseli on LWPOLYLINEn extrusion-vektori. 3DFACEt
muunnetaan WCSâ†’OCS, LWPOLYLINEt ovat jo OCS:ssÃ¤, pairing ja
ekstrudointi tehdÃ¤Ã¤n OCS-tasossa ja lopullinen mesh muunnetaan
OCSâ†’WCS. Axis-aligned INSERT (extrusion=(0,0,1)) on identtinen
vanhan kÃ¤ytÃ¶ksen kanssa, joten KLH ja muut horisontaaliset hyllyt
eivÃ¤t muutu.

Tiedostot:

- `src/dxf2ifc/core/dxf_reader.py` â€” `_aggregate_3dface_from_insert`
  kÃ¤yttÃ¤Ã¤ nyt yhteistÃ¤ `block_ocs`-objektia kaikkien block-sisÃ¤isten
  entiteettien aggregaatioon
- **UUSI** `tests/test_dxf_reader_insert_3dface.py::test_insert_3d_rotated_polyline_extrudes_along_block_local_z`
  â€” todistaa ettÃ¤ INSERT.extrusion=(0,-1,0) extrudoi block-Z-suuntaan
  ja askelmat sÃ¤ilyvÃ¤t WCS-Z:ssÃ¤ erillisinÃ¤

Vaikuttaa: KLHV (kylmÃ¤laite-LISP:n pystytetty tikashylly) muuntuu nyt
oikeaksi ladder-meshiksi Solibrissa. Muut LISP-hyllyt (vaaka KLH,
KLHV ilman 3D-rotaatiota) pysyvÃ¤t identtisinÃ¤.

## v0.2.0-alpha21 â€” 2026-05-13 (DWG-syÃ¶te takaisin â€” accoreconsole + DXFOUT)

**LisÃ¤tty â€” DWG-tiedostot kÃ¤yvÃ¤t jÃ¤lleen syÃ¶tteeksi**:

`.dwg`-tiedostoa voi syÃ¶ttÃ¤Ã¤ suoraan sekÃ¤ CLI:lle ettÃ¤ GUI:lle.
Konversiopipeline preconvertaa DWG:n DXF:ksi headless-AutoCAD:in
(`accoreconsole.exe`) ja `DXFOUT`-komennon avulla, jonka jÃ¤lkeen
DXF-parsing-putki jatkaa muuttumattomana. Yksi yhteinen koodipolku
ja yksi GUI-virheilmoitus jos AutoCAD puuttuu (vain AutoCAD-omistajille
suunnattu).

TÃ¤rkeÃ¤ ero alpha10:ssÃ¤ poistettuun reittiin: uusi polku kÃ¤yttÃ¤Ã¤
**samaa headless-tekniikkaa** jolla 3DSOLID-tessellaatio jo toimii
(ei COM:ia, ei sendkeys:iÃ¤, ei nÃ¤kyvÃ¤Ã¤ AutoCADia, ei FILEDIA-toggle:a,
ei kÃ¤yttÃ¤jÃ¤n AutoCAD-profiilin pollutiota). Hauras `acad.exe`-COM-
keystroke-pipeline ei palaa.

KÃ¤yttÃ¶:

```bash
# CLI
python -m dxf2ifc convert piirustus.dwg out.ifc

# GUI: pudota .dwg tiedostopolku-kenttÃ¤Ã¤n, paina Convert.
```

Rajoitukset:
- Vaatii AutoCAD-asennuksen (LT EI tue accoreconsole.exe:tÃ¤ â€” paitsi
  jos LT-installissa on AutoCAD-LT-Cargo-laajennus, mitÃ¤ emme tue)
- MagiCAD-DWG-syÃ¶te EI ole tuettu â€” proxy-objektit tulisivat 2D-
  fragmentteina (sama syy kuin alpha2:n POC:ssa). MagiCAD-osat:
  kollegan `-MAGIIFCCD` + `--magicad-ifc`-merge

Tiedostot:
- **UUSI** `src/dxf2ifc/core/dwg_preconvert.py` â€” `convert_dwg_to_dxf()`
- `src/dxf2ifc/core/ifc_writer/orchestrator.py` â€” `.dwg`-syÃ¶tteen
  haarautuminen `convert_dxf`-funktion etupÃ¤Ã¤hÃ¤n
- `src/dxf2ifc/cli.py` + `src/dxf2ifc/gui/file_panel.py` +
  `src/dxf2ifc/gui/main_window.py` â€” UI hyvÃ¤ksyy `.dwg`:n
- **UUSI** `tests/test_dwg_preconvert.py` â€” 5 unit-testiÃ¤ + 1 end-to-
  end -testi joka skip:Ã¤Ã¤ ilman AutoCAD-asennusta

## v0.2.0-alpha20 â€” 2026-05-12 (poistettu skip-ACIS-toggle GUI:sta ja CLI:stÃ¤)

**Poistettu â€” kÃ¤yttÃ¤jÃ¤lle nÃ¤kyvÃ¤ accoreconsole-ohitusvalinta**:

`FilePanel`-checkbox **"Ohita 3DSOLID-triangulaatio (accoreconsole)"**
ja CLI-flagi **`--skip-acis`** (alpha17) on poistettu. Toggle oli
hÃ¤tÃ¤korjaus alpha17:n aikaiseen oletettuun crash-tilanteeseen joka
ratkesi alpha18:n MagiCAD-blokkien LISP-Phase-2-skipillÃ¤; toggle ei
jÃ¤Ã¤ kÃ¤yttÃ¶Ã¶n tarpeellisena vaan toimii lÃ¤hinnÃ¤ jalkaalaukauksena
(kÃ¤yttÃ¤jÃ¤ saattaa unohtaa sen pÃ¤Ã¤lle ja sitten ihmetellÃ¤ miksi
ACIS-pohjaiset osat puuttuvat IFC:stÃ¤).

SisÃ¤inen `convert_dxf(preprocess_acis=False)`-parametri sÃ¤ilyy â€”
testit kÃ¤yttÃ¤vÃ¤t sitÃ¤ hermeettisiin ajoihin ilman accoreconsolea.
PelkÃ¤n kÃ¤yttÃ¤jÃ¤lle nÃ¤kyvÃ¤n pintansa poistettiin.

QSettings:n `skip_acis`-avain ei enÃ¤Ã¤ luotaisi/luettaisi. Jos avain
on jonkun kÃ¤yttÃ¤jÃ¤n asetuksissa alpha17â€“alpha19:n ajoilta, se
ignoroidaan harmittomasti.

## v0.2.0-alpha19 â€” 2026-05-12 (kylmÃ¤koneikon sÃ¤hkÃ¶varusteet â€” 6 uutta layer-mappausta)

**LisÃ¤tty â€” VARUSTEET-LISP:n 6:n uuden laitteen tuki**:

Autocad-lisp-ohjeet/Laitteet/-kansion uudet 3DSOLID-blokit
(CO2-anturi, CO2-sireeni, Huolto-PC, RK-JK10, SÃ¤Ã¤dinkeskus, kylmÃ¤koneikon
hÃ¤tÃ¤seispainike) tunnistetaan nyt automaattisesti default-profiilista
ja mapataan IFC4-tyypeiksi RAVA3Pro-tilavarauskoodeilla:

| Layer | IFC4-tyyppi | PredefinedType | RAVA |
|---|---|---|---|
| `KYL-CO2-ANTURI*` | `IfcSensor` | `CO2SENSOR` | `T-TATE-02-01-003` |
| `KYL-CO2-SIREENI*` | `IfcAlarm` | `SIREN` | `T-TATE-02-01-003` |
| `KYL-HUOLTO-PC*` | `IfcCommunicationsAppliance` | `COMPUTER` | `T-TATE-02-01-003` |
| `KYL-RK-*` (myÃ¶s JK10) | `IfcElectricDistributionBoard` | `DISTRIBUTIONBOARD` | `T-TATE-02-01-004` |
| `KYL-SAADINKESKUS-*` | `IfcController` | `PROGRAMMABLE` | `T-TATE-02-01-004` |
| `KYL-HATASEIS*` | `IfcSwitchingDevice` | `EMERGENCYSTOP` | `T-TATE-02-01-003` |

RAVA-konventio: kylmÃ¤suunnittelijan sÃ¤hkÃ¶laitteet ovat **tilavarauksia**
(`T-TATE-02-01-003` Tilavaraus - laitteisto / `T-TATE-02-01-004`
Tilavaraus - keskus) joita sÃ¤hkÃ¶suunnittelija korvaa lopullisilla
osilla. TATE-TUOTEOSA-katalogissa ei ole erillisiÃ¤ sÃ¤hkÃ¶laite-koodeja
yksittÃ¤isille antureille / sireeneille / kytkimille.

**Korjattu â€” IFC4-yhteensopivuus**:

- Aiempi `IfcDistributionBoard` (vain IFC4.3) â†’ `IfcElectricDistributionBoard`
  (toimii sekÃ¤ IFC4:ssÃ¤ ettÃ¤ IFC4.3:ssa). Olemassaolevat sÃ¤Ã¤nnÃ¶t
  `KYL-KK-*` ja `KYL-RK-*` kÃ¤yttivÃ¤t tyyppiÃ¤ joka EI ole IFC4-skeemassa
  ja olisi kaatanut konversion jos nÃ¤itÃ¤ layereja olisi DXF:ssÃ¤ ollut.
- SÃ¤Ã¤dinkeskus-sÃ¤Ã¤nnÃ¶n `predefined_type` korjattu: `PROGRAMMABLECONTROLLER`
  â†’ `PROGRAMMABLE` (IFC4 `IfcControllerTypeEnum`).

**Korjattu â€” RAVA-koodien oikaisu**:

`KYL-KK-*` ja `KYL-RK-*` kÃ¤yttivÃ¤t placeholder-koodia `T-TATE-01-01-099`
("MUU - Asennushyllyt") joka ei vastaa keskusten luonnetta. Nyt
`T-TATE-02-01-004` (Tilavaraus - keskus) â€” Solibri nÃ¤yttÃ¤Ã¤ nÃ¤mÃ¤
oikeassa RAVA-kategoriassa.

**SisÃ¤istÃ¤**:

- `_DISTRIBUTION_ELEMENT_CLASSES` laajeni 4 uudella tyypillÃ¤ (IfcAlarm,
  IfcController, IfcSwitchingDevice, IfcCommunicationsAppliance) +
  IfcDistributionBoard â†’ IfcElectricDistributionBoard.
- `src/dxf2ifc/profiles/rava/` paikalliset koodisto-cachet ajettiin
  ajan tasalle `python -m tools.rava.sync_codes`-komennolla
  koodistot.suomi.fi/RYTJ-API:sta. TATE-TUOTEOSA stub (2 koodia) â†’
  tÃ¤ysi katalogi (90 koodia) sis. tilavaraus-osion.

## v0.2.0-alpha18 â€” 2026-05-11 (skip MagiCAD-blokit accoreconsolen LISP-puolelta)

**Korjattu â€” MagiCAD-osat eivÃ¤t enÃ¤Ã¤ aja `_.EXPLODE`-kutsuun**:

Kun `--magicad-ifc`-merge on kÃ¤ytÃ¶ssÃ¤, accoreconsolen LISP-puoli ohittaa
nyt myÃ¶s MagiCAD-blokit (`MAGI*`, `*MAGICAD*`, `MAG_*`) Phase 2:n
INSERT-rÃ¤jÃ¤ytys-silmukassa â€” aiemmin vain `*POSITIO*`-blokit ohitettiin.
TÃ¤mÃ¤ korjaa AutoCAD-crash-raportin joka voi tulla **kollegan koneella
jossa FULL-MagiCAD-ARX on ladattuna**: `_.EXPLODE` MagiCAD-entityyn voi
kaataa MagiCAD-ARX:in jonka nÃ¤kyvÃ¤nÃ¤ lopputuloksena on Customer Error
Reporting -dialogi. Koska MagiCAD-osat tulevat IFC:hen kuitenkin
`-MAGIIFCCD`-mergen kautta, niiden rÃ¤jÃ¤ytys oli vain hukkatyÃ¶ +
crash-riski.

LisÃ¤ksi: jos accoreconsole pÃ¤Ã¤ttyy ei-nollalla exit-koodilla,
preview-loki nÃ¤yttÃ¤Ã¤ nyt sen koodin sekÃ¤ `%TEMP%\dxf2ifc_acis_*`-
tyÃ¶hakemiston polun jossa `accoreconsole.log` + `extract.log` +
`extract.scr` ovat diagnostiikkaa varten.

KÃ¤yttÃ¤jÃ¤lle nÃ¤kyvÃ¤ muutos:
- Default-konversiossa (ei `--magicad-ifc`-flagia) ei muutosta.
- `--magicad-ifc`-konversiossa MagiCAD-blokit ohitetaan accoreconsolen
  LISP-puolelta, mikÃ¤ estÃ¤Ã¤ CER-popupin kollegan koneella.

## v0.2.0-alpha17 â€” 2026-05-11 (skip-ACIS-toggle GUI:hin + CLI:hen)

**LisÃ¤tty â€” accoreconsole-ohitusvalinta kÃ¤yttÃ¤jÃ¤lle**:

- GUI:n FilePaneliin uusi checkbox **"Ohita 3DSOLID-triangulaatio
  (accoreconsole)"**. PÃ¤Ã¤llÃ¤-tilassa konvertteri ei kÃ¤ynnistÃ¤
  `accoreconsole.exe`-prosessia DXF:n 3DSOLID/SURFACE/REGION-bodien
  triangulointiin. Valinta persistoituu QSettings-kautta
  (`skip_acis`-avain).
- CLI:hen uusi flagi **`--skip-acis`** samalla semantiikalla:
  `dxf2ifc convert in.dxf out.ifc --skip-acis`.
- Default-tila on yhÃ¤ **kÃ¤ytÃ¤ accoreconsolea** koska useimmat KYL-DXF:t
  sisÃ¤ltÃ¤vÃ¤t 3DSOLID-pohjaisia tikashyllyjÃ¤ / putkia jotka tarvitsevat
  triangulointia. Ohitusvalinta on tarkoitettu tilanteisiin jossa
  accoreconsole heittÃ¤Ã¤ AutoCAD-crash-reportin tai DXF sisÃ¤ltÃ¤Ã¤ vain
  dynamic-block / INSERT-pohjaista geometriaa.

SisÃ¤isesti `convert_dxf(preprocess_acis=False)` oli jo olemassa â€”
tÃ¤mÃ¤ release vain altistaa lipun loppukÃ¤yttÃ¤jÃ¤lle.

## v0.2.0-alpha16 â€” 2026-05-11 (suunnitteluala-label "JÃ¤Ã¤hdytys" â†’ "KYL")

**Muutettu â€” discipline-classification:n label vastaa nyt AutoCAD-puolta**:

`DISCIPLINE_LABELS["KYL"]` `"JÃ¤Ã¤hdytys"` â†’ `"KYL"`. TÃ¤mÃ¤ vaikuttaa:

- `IfcProject.LongName` = `KYL` (oli `JÃ¤Ã¤hdytys`)
- `IfcClassification "suunnittelualat"` â†’ reference `Identification` ja
  `Name` = `KYL` (oli `JÃ¤Ã¤hdytys`) sekÃ¤ projektitasolla ettÃ¤ jokaisella
  KYL-domain-tuotteella
- `Pset_Discipline.Discipline` = `KYL` (oli `JÃ¤Ã¤hdytys`)

`Pset_Project.Authorization` jÃ¤Ã¤ edelleen `"KylmÃ¤suunnittelu"`:ksi
(Granlund/RAVA3Pro-konventio). Tuotteiden surface-vÃ¤ri pysyy AutoCAD
ACI 175:ssÃ¤ (RGB 76,76,153).

Solibrin role-auto-detect ei toiminut "JÃ¤Ã¤hdytys"-labelillakaan
(testit alpha15:ssÃ¤), joten siirrytÃ¤Ã¤n yhdenÂ­mukaiseen lyhenteeseen
joka nÃ¤kyy AutoCAD-layereissa (KYL-*). Manuaalinen rooliÂ­valinta
SolibrissÃ¤ avatessa pysyy hyvÃ¤ksyttynÃ¤.

## v0.2.0-alpha15 â€” 2026-05-11 (Pset_Discipline IfcProject-tasolle)

**LisÃ¤tty â€” Solibri-role-auto-detect saa yhden lisÃ¤signaalin**:

Kun konversio tuottaa yksisuunnitteluala-mallin (kaikki rivit
`domain="KYL"`), `IfcProject`-entiteettiin liitetÃ¤Ã¤n nyt
`Pset_Discipline` -PropertySet, jossa `Discipline = "JÃ¤Ã¤hdytys"`.

Aiemmin emittoituja Solibri-roolin signaaleja (`IfcProject.LongName`,
`Pset_Project.Authorization`, `suunnittelualat`-luokitus,
STEP-header `KylmÃ¤suunnittelu`, `IfcApplication`) ei muutettu â€” tÃ¤mÃ¤ on
defence-in-depth-lisÃ¤ys jonka jotkin Solibri-konfiguraatiot lukevat
suoraan Pset_DisciplinestÃ¤ Pset_Projectin sijaan. Jos Solibri ohittaa
sen, kustannus on yksi PSet IfcProjectin alla, ei mitÃ¤Ã¤n muuta.

PÃ¤ivitÃ¤ alpha15 â†’ avaa IFC SolibrissÃ¤ â†’ katso tuleeko "JÃ¤Ã¤hdytys"-rooli
automaattisesti ilman dialogia. Jos ei, Solibri ei lue tÃ¤tÃ¤ mekanismia
ja jÃ¤Ã¤ manuaalinen valinta kÃ¤yttÃ¶Ã¶n.

## v0.2.0-alpha14 â€” 2026-05-11 (POSITIO-linkki anonyymeille blokeille)

**Korjattu â€” POSITIO matchaa kaikki hÃ¶yrystimet/lauhduttimet/kompressorit
modifioiduilla blokeilla**:

Kaksi vikaa POSITIO-linkkauksessa kun kÃ¤ytetÃ¤Ã¤n muokattua positio-blokkia
(dynamic-block-variantti jonka AutoCAD nimeÃ¤Ã¤ anonyymisti `*U12` jne):

1. **`index_positio_markers` matchasi vain block-nimen perusteella**
   patternilla `positiov2*`. Anonyymi `*U12` ei matchannut, vaikka
   sisÃ¤ltÃ¶ (NUMERO + TEKSTI -ATTRIBit) on sama. Nyt tunnistus on
   ATTRIBUUTTIVETOINEN: kun INSERTilla on sekÃ¤ NUMERO ettÃ¤ TEKSTI -
   attribuutit, se on positio riippumatta blokin nimestÃ¤.

2. **Orchestrator kÃ¤ytti mesh-bbox-keskipistettÃ¤ target-XY:nÃ¤** kun
   mapped-entity on MeshGeometry-pohjainen (kaikki accoreconsole-
   pipelinen lÃ¤pimenneet hÃ¶yrystimet). HÃ¶yrystimen mesh ulottuu
   etupuolelle ~250 mm INSERT-pisteestÃ¤ â†’ bbox-keskipiste on sivussa
   INSERTistÃ¤, mikÃ¤ saattaa heittÃ¤Ã¤ 3 m POSITIO-radiuksen vahingossa
   ulottumattomiin. Nyt kÃ¤ytetÃ¤Ã¤n INSERT.xy:tÃ¤ handle-haulla.

Verifioitu 4001_1krs.dxf:llÃ¤: 16/16 IfcEvaporator saa nyt
Koneikko (JK1/JK2/JK3/JK4) + Laitetunnus (NUMERO) FI_Komponentti-PSettiin.

## v0.2.0-alpha13 â€” 2026-05-08 (block-sisÃ¤iset 3DSOLIDit huomataan)

**Korjattu â€” koneikko-blokit triggerÃ¶ivÃ¤t nyt accoreconsole-pipelinen**:

`dxf_contains_acis_bodies` skannasi vain modelspacea â€” koneikko ja muut
laite-blokit joiden 3DSOLID-sisÃ¤ltÃ¶ asuu **block definitionin sisÃ¤llÃ¤**
(MEKA / Solibri / valmistajien kirjastoista tuodut kokoonpanot ovat
tyypillisesti tÃ¤llaisia) eivÃ¤t triggerÃ¶ineet accoreconsole-Stage 1+2 -
pipelinea lainkaan. Tarkistus kÃ¤y nyt lÃ¤pi jokaisen block-definition.

YhdessÃ¤ alpha12:n Phase 2 -laajennuksen kanssa: koneikko-INSERTit
layer KYL-KONEIKKO* rÃ¤jÃ¤ytetÃ¤Ã¤n â†’ block-sisÃ¤iset 62 Ã— 3DSOLID
STLOUTataan â†’ mesh aggregoidaan â†’ IfcUnitaryEquipment + IfcFacetedBrep
syntyy IFC:hen.

## v0.2.0-alpha12 â€” 2026-05-08 (STLOUT kaikille INSERT-blokeille)

**Korjattu â€” koneikko ja muut equipment-blokit saavat nyt geometrian**:

Phase 2:n LISP-filter rajasi STLOUTin vain block-name-patterneilla
`*yrystin*,*ahdutin*,*pressori*,KLHYLLY-*,VPUTKI-*` â€” alpha11:n
laajennuksen tuomat uudet KYL-laitteet (KONEIKKO, CHILLER, KOMPLAUH,
KAASUNJAA, NESTEJAAHD, VARAAJA, PAKASTEKAAPPI, KYLMAKAAPPI jne)
jÃ¤ivÃ¤t ilman meshiÃ¤, putosivat orchestratorin BlockInstance-skipiin
ja eivÃ¤t pÃ¤Ã¤tyneet IFC:hen.

**`preprocessing.py` Phase 2** kÃ¤yttÃ¤Ã¤ nyt **layer-filteriÃ¤** (sama kuin
Phase 1, oletus `*`) block-name-filterin sijaan. Kaikki INSERTit
layer-filterillÃ¤ rÃ¤jÃ¤ytetÃ¤Ã¤n ja STLOUTataan. LisÃ¤ksi:

- POSITIO-annotaatioblokit suljetaan pois `wcmatch ... "*POSITIO*"`
- Nested INSERTit rÃ¤jÃ¤ytetÃ¤Ã¤n rekursiivisesti queue-pohjaisella loopilla
  (iter_cap 1000) â€” compound-blokit joiden mÃ¤Ã¤rittelyssÃ¤ on alablokkeja
  (esim. koneikko = kompressori-sub + lauhdutin-sub) saavat lehti-
  tason 3DSOLIDinsÃ¤ esiin
- Kaikki ACIS-tyypit STLOUTataan: `3DSOLID` + `SURFACE` + `REGION` +
  `BODY` + `PLANESURFACE`/`EXTRUDEDSURFACE`/`REVOLVEDSURFACE`/
  `SWEPTSURFACE`/`LOFTEDSURFACE`/`NURBSURFACE`
- LWPOLYLINE+thickness â†’ CONVTOSOLID â†’ STLOUT (KLHYLLY-pattern sÃ¤ilyy)

**`dxf_reader.py` `_aggregate_3dface_from_insert`** flatten:Ã¤Ã¤ nested
INSERTit virtual_entities-rekursiolla. ezdxf:n `virtual_entities()` ei
itse descend:aa sub-blokkeihin â€” ilman tÃ¤tÃ¤ accoreconsoleton fallback
(KYL-LISP-hyllyt) jÃ¤isi sokeaksi nested 3DFACE/closed LWPOLYLINE
-sisÃ¤llÃ¶lle.

EI bbox-arvauksia. Jokainen geometriareitti tuottaa aitoa mesh-dataa.

## v0.2.0-alpha11 â€” 2026-05-08 (kattava kylmÃ¤laitesuunnittelun tuki)

**LisÃ¤tty â€” out-of-the-box mappaus kaikelle kylmÃ¤laitesuunnitteluun**:

Default-profiili kasvoi 17:stÃ¤ 49:Ã¤Ã¤n sÃ¤Ã¤ntÃ¶Ã¶n. KÃ¤yttÃ¤jÃ¤ saa valmiin
mappauksen yleisimmille KYL-* layereille; oma profile voi karsia /
muokata layer-patterneja kun AutoCAD-konventiot eroavat.

**Builders-laajennus**:

- **`_COOLING_EQUIPMENT_CLASSES`** kattaa nyt myÃ¶s `IfcChiller`,
  `IfcUnitaryEquipment`, `IfcCoil` â€” `add_cooling_equipment` rakentaa
  niille mesh-Brep-tuotteen kuten hÃ¶yrystimille / lauhduttimille.
- **Uusi `add_distribution_element(ifc, m, *, ifc_class, parent_storey)`**
  â€” geneerinen rakentaja `IfcSensor`/`IfcValve`/`IfcPump`/
  `IfcWasteTerminal`/`IfcInterceptor`/`IfcDistributionBoard`/
  `IfcDuctSegment`/`IfcDuctFitting`/`IfcAirTerminal`-luokille.
  Funnel:oi `_add_mesh_product`-kautta samalla pattern:lla kuin
  `add_flow_controller`.
- Orchestrator-dispatchiin uusi haaroitus jokaisen
  `_DISTRIBUTION_ELEMENT_CLASSES`-luokan kÃ¤sittelyyn.

**Profile-sÃ¤Ã¤nnÃ¶t â€” Section 7 (uutta sisÃ¤ltÃ¶Ã¤)**:

| Kategoria | Layer-pattern -prefix | RAVA-koodit |
|---|---|---|
| **7a KylmÃ¤koneikkojen loput osat** | `KYL-CHILLER*` `KYL-VEDENJAAHDY*` `KYL-KYLMAVESIAS*` `KYL-KONEIKKO*` `KYL-VALIJAAHD*` `KYL-KOMPLAUH*` `KYL-KAASUNJAA*` `KYL-NESTEJAAHD*` `KYL-VARAAJA*` | T-LVI-01-01-003/004/005/016/019/024/027 + T-LVI-03-07-012 |
| **7b KylmÃ¤kalusteet** | `KYL-PAKASTEKAAPPI*` `KYL-KYLMAKAAPPI*` `KYL-PAKASTEALLAS*` `KYL-PAKASTEARKKU*` `KYL-KYLMAALLAS*` `KYL-MARJAALLAS*` `KYL-PIKAJAA*` `KYL-OMAKONEELLI*` | T-LVI-01-01-999 (MUU) + ObjectType FI_Komponenttiin |
| **7c KondenssiviemÃ¤ri** | `KYL-KONDENSSI*` `KYL-LATTIAKAIV*` `KYL-VESILUKKO*` `KYL-PADOTUS*` | T-LVI-04-01-001 + T-LVI-05-01-001 + T-LVI-04-02-002/005, J-LVI-04-04 |
| **7d SÃ¤Ã¤tÃ¶ ja anturit** | `KYL-TERMO*` `KYL-LAMPOTILA*` `KYL-PAINEMITT*` `KYL-PINTAANT*` `KYL-MAGNV*` `KYL-PAISUNTAVENT*` `KYL-SULATUSVAST*` | T-TATE-01-01-099 / T-LVI-02 / T-LVI-01-01-999 |
| **7e SÃ¤hkÃ¶keskukset** | `KYL-KK-*` `KYL-RK-*` | T-TATE-01-01-099 |
| **7f Putkivarusteet** | `KYL-VENTTIILI*` `KYL-PUMPPU*` `KYL-PAISUNTASAILIO*` | T-LVI-02 |

**RAVA-LVI-TUOTEOSA-cache laajennettu**: 9 uutta T-LVI-01-01-koodia
(002, 006, 015, 016, 020, 021, 022, 026, 027, 999) jotta tarkka
luokitus on kÃ¤ytettÃ¤vissÃ¤ custom-profileissa.

**TÃ¤rkeÃ¤ huomio kÃ¤yttÃ¤jÃ¤lle**: nÃ¤mÃ¤ ovat oletus-layer-patternit, eivÃ¤t
pakottavia. Tee oma profile jos AutoCAD-konventiot eroavat â€” profile-
TOML on selkeÃ¤ ja kommentoitu.

## v0.2.0-alpha10 â€” 2026-05-08 (DWG-tuki + toggle-checkboxit pois)

**Poistettu â€” pelkistetty kÃ¤yttÃ¶liittymÃ¤ ja core-pipeline**:

Lauri:n pÃ¤Ã¤tÃ¶s: koska `--magicad-ifc`-merge on kÃ¤ytÃ¶ssÃ¤ ja toimii,
DWG-input + sen toggle-checkboxit ovat tarpeettomia. Poistetaan
kokonaan ettei kÃ¤yttÃ¤jÃ¤ eksy hauraihin AutoCAD COM -reitteihin.

- **DWG-input poistettu**: `core/dwg_preconvert.py` (768 r) deletoitu,
  `tests/test_dwg_preconvert.py` deletoitu. Orchestratorin DWG-haara
  + `last_explode_meshes`-merge poistettu. Vain `.dxf` hyvÃ¤ksytÃ¤Ã¤n
  syÃ¶tteenÃ¤.
- **`pywin32`-dependency poistettu** `pyproject.toml`:sta â€” ei enÃ¤Ã¤
  Windows-only-vaadetta, asennettavissa myÃ¶s macOS/Linux-Pythonille
  (vaikka kÃ¤yttÃ¶tapaus on edelleen Windows-keskeinen `accoreconsole`-
  riippuvuuden takia).
- **CLI `--no-preprocess-proxies`-argumentti poistettu**.
- **GUI:n "Pikakonversio (ohita 3D-tessellaatio)"-checkbox poistettu**
  â€” accoreconsole 3DSOLID-tessellaatio aina pÃ¤Ã¤llÃ¤.
- **GUI:n "MagiCAD/proxy-objektien geometria"-checkbox poistettu** â€”
  DXF-puolen MAGI*-luokat skipataan automaattisesti kun MagiCAD-IFC
  on annettu, muutoin niitÃ¤ luetaan oletuksena.
- **`recent_files.quick_convert` + `recent_files.preprocess_proxies`
  -kentÃ¤t poistettu** â€” vanhat asetukset pysyvÃ¤t QSettings-rekisterissÃ¤
  mutta eivÃ¤t enÃ¤Ã¤ vaikuta pipelineen.
- `convert_dxf`-funktion `preprocess_proxies`-kwargi poistettu;
  `convert_worker.run` -metodista `quick_convert` + `preprocess_proxies`
  -parametrit poistettu; `FilePanel.convert_requested`-signaali
  pelkistetty 7 â†’ 5 parametriin.
- Dokumentaatio pÃ¤ivitetty: README, CLAUDE.md, PROGRESS.md,
  ARCHITECTURE.md, CLAUDE_TASKS.md, DWG_MAGICAD_PREPROCESSING.md
  (jÃ¤lkimmÃ¤inen historic-nÃ¤kÃ¶kulmaan: mitÃ¤ ei toimi ja miksi).

**Ei toiminnallisia muutoksia DXF-pipelineen** â€” kaikki KYL-LISP-osat,
3DFACE-aggregaatio, energiateho-Excel-merge ja MagiCAD-IFC-merge
toimivat identtisesti.

## v0.2.0-alpha9 â€” 2026-05-08 (RAVA viemÃ¤ri-koodit valmiina cache:hen)

**LisÃ¤tty â€” RAVA-LVI viemÃ¤rikoodit koodisto-cache:hen**:

Lauri:n pyynnÃ¶stÃ¤ haettiin valmiiksi viemÃ¤ri-puolen RAVA3Pro-luokitukset
jotta niille on tuki valmiina kun layer-mappausta laajennetaan. Itse
mappauspatterneja ei vielÃ¤ lisÃ¤tty â€” Lauri pÃ¤Ã¤ttÃ¤Ã¤ myÃ¶hemmin mitkÃ¤
DXF-layerit ovat KYL-puolen kondenssiviemÃ¤ri ja mitkÃ¤ LVI-puolen
jv/sv/tuuletus.

- **`profiles/rava/lvi_tuoteosa.json`** laajennettu: kaikki T-LVI-04-*
  (viemÃ¤riputket + varusteet + eristeet) + T-LVI-05-01-* (kaivot) +
  T-LVI-01-03-* (pumppaamot).
- **`profiles/rava/lvi_jarjestelma.json`** laajennettu: kaikki
  J-LVI-04-* viemÃ¤rijÃ¤rjestelmÃ¤t (jÃ¤tevesi/sadevesi/tuuletus/kondenssi/
  rasva/Ã¶ljy/erikois/salaoja/perusvesi/sekavesi/dialyysi + paineviemÃ¤rit).
- **`docs/RAVA_DRAINAGE_CODES.md`** uusi pikamuisti â€” IFC-tyyppi-mappaus-
  ehdotukset + esimerkki profile-sÃ¤Ã¤nnÃ¶stÃ¤ + mitÃ¤ tehdÃ¤ seuraavaksi.

**Erityishuomio kylmÃ¤laitepuolelle**: hÃ¶yrystinten sulatusvedet ja
muut kylmÃ¤laitepuolen kondenssit kuuluvat jÃ¤rjestelmÃ¤koodiin
`J-LVI-04-04 ViemÃ¤ri - kondenssi`. Tuoteosa-koodi runkoputkille on
edelleen `T-LVI-04-01-001 ViemÃ¤riputki`.

## v0.2.0-alpha8 â€” 2026-05-08 (hyllyjen FI_Tekninen siivous)

**Muutettu â€” `IfcCableCarrierSegment` (KYL-TIKASHYLLY / KYL-LEVYHYLLY)
FI_Tekninen-defaultit minimoitu**:

Lauri:n pÃ¤Ã¤tÃ¶s 2026-05-08: hyllyille riittÃ¤Ã¤ matsku + pinnoite. Aiemmat
laajat tekniset kentÃ¤t (paloluokka, paino, kuormitus, levypaksuus,
korroosioluokka, vÃ¤rit, valmistajan linkki) jÃ¤Ã¤vÃ¤t pois oletuksena.

- **`_FI_TEKNINEN_DEFAULTS["IfcCableCarrierSegment"]`** sisÃ¤ltÃ¤Ã¤ nyt
  vain `Materiaali` + `Pinnoite`.
- **`default_kylmalaite.toml`** -hyllysÃ¤Ã¤nnÃ¶t pÃ¤ivitetty:
  - Tikashylly: `Materiaali = "TerÃ¤s"`, `Pinnoite = "Kuumasinkitty"`
  - Levyhylly: `Materiaali = "TerÃ¤s"`, `Pinnoite = "Polyesterimaalattu"`
    (poistettu "Valkoinen RAL 9010" -vÃ¤rimerkintÃ¤)
- **`fi_tuote.valmistajan_linkki`** poistettu hyllyiltÃ¤ â€” ei tartte
  laittaa linkkiÃ¤ tuotteeseen oletuksena.

KÃ¤yttÃ¤jÃ¤ voi lisÃ¤tÃ¤ mitÃ¤ tahansa kenttÃ¤Ã¤ takaisin custom profile:n
kautta jos joku projekti vaatii esim. paloluokan tai kuormitustiedon.

## v0.2.0-alpha7 â€” 2026-05-07 (Excel-luenta: yhdistetyt otsikot + sektiot)

**LisÃ¤tty â€” RefDesign Teholuettelo-pohjien tuki**:

- **Slash-yhdistetyt otsikot**: ``KYLMÃ„-/SÃ„HKÃ–-/VASTUSTEHO [kW]`` -tyyppinen
  yhdistetty Excel-otsikko jaetaan kolmeksi sarakkeeksi ja jokainen
  token mÃ¤tsÃ¤tÃ¤Ã¤n erikseen kanonisiin kenttiin
  (JÃ¤Ã¤hdytysteho/SÃ¤hkÃ¶teho/Vastusteho). Auto-teho-suffix kun yksikkÃ¶ on
  ``[kW]`` / ``[W]``.
- **Sektio-otsikko-tunnistus**: rivi jossa yksi solu sisÃ¤ltÃ¤Ã¤
  ``JK1``/``KK2``/``RK10``/``LA1`` -koodin (esim. ``"PAKASTEET JK1"``)
  asettaa koneikon kaikkiin seuraaviin riveihin. RefDesign-konvention
  mukaisesti yksi sektio yhdellÃ¤ koneikolla, monta sektiota sheetissÃ¤.
- **Forward-fill**: kun rivin ``REV.``-sarake on tyhjÃ¤, koneikko
  periytyy edellisestÃ¤ sektio-otsikosta. Ennen tÃ¤tÃ¤ useimmat data-
  rivit jÃ¤ivÃ¤t pois koska niiden REV. oli blank.
- **Robusti koneikko-validointi**: vapaa teksti REV.-sarakkeessa
  (``"SÃ¤hkÃ¶urakoitsija tuo syÃ¶tÃ¶tâ€¦"``) EI enÃ¤Ã¤ nouse koneikoksi â€”
  vain JKx/KKx/RKx/LAx-pattern hyvÃ¤ksytÃ¤Ã¤n, muutoin forward-fill.

**Testattu**: Lauri:n ``teholuettelo 2.xlsx`` (KM Kolari) â€” 39 spec
luetaan kahdesta koneikosta (JK1 + JK2), 3 tehoa per laite + jÃ¤nnite
+ jÃ¤Ã¤hdyttÃ¤vÃ¤ vaikutus.

## v0.2.0-alpha6 â€” 2026-05-07 (levyhyllyn kyljet + peilatut INSERT:t)

**Korjattu â€” kaksi alpha5:n jÃ¤ljelle jÃ¤Ã¤nyttÃ¤ bugia**:

1. **Levyhyllyn kyljet puuttuivat**: ohuet etu/takareunan LWPOLYLINE:t
   (1.2 mm leveÃ¤t) extrudoituivat alpha5:ssÃ¤ vain pohjalaatan paksuuteen
   (1.2 mm) eivÃ¤tkÃ¤ koko hyllyn korkeuteen. Heuristiikka: jos closed
   LWPOLYLINE:n lyhempi sivu â‰¤ 5 mm (= "ohut sivurima"), extrudoidaan
   block:n korkeimpaan top:iin sen sijaan ettÃ¤ matchattaisiin lÃ¤himpÃ¤Ã¤n
   3DFACE:hen. TÃ¤mÃ¤ saa levyhyllyn 4 kyljen kiertÃ¤mÃ¤Ã¤n hyllyn pohjasta
   ylÃ¤reunaan.

2. **Peilattu INSERT (yscale=-1) tuotti negative-Z-meshin**: LWPOLYLINE
   on 2D-entity OCS-tasolla; kun parent-INSERT:llÃ¤ on yscale=-1 ezdxf
   palauttaa virtual-LWPOLYLINE:n extrusion=(0,0,-1):lla mutta jÃ¤ttÃ¤Ã¤
   elevation:n ennalleen. Read elevation suoraan â†’ block-level elev=10
   landed at world Z=-10. Korjaus: muunnetaan LWPOLYLINE:n vertex:t
   ja elevation OCSâ†’WCS `entity.ocs().to_wcs(...)`-kutsulla â€” flip
   hoidetaan transparenttisesti.

**Lopputulos**: 8 hyllyÃ¤ Lauri:n `Drawing2.dxf`:stÃ¤ â€” 3 levyhyllyÃ¤
Z=0..67.8mm (kyljet, pohja, pÃ¤Ã¤typalkit), 5 tikashyllyÃ¤ Z=0..60mm
(sivupalkit + tikkapuut), kaikki yhdenmukaisesti world-koordinaatistossa
ilman peilaus-artefakteja.

## v0.2.0-alpha5 â€” 2026-05-07 (LWPOLYLINE-extrusio = oikeat solidit)

**Korjattu â€” alpha4:n hyllyt olivat pelkkiÃ¤ ylÃ¤pintoja, ei volyymiÃ¤**:

Alpha4 luki vain block:n 3DFACE:t â†’ yksittÃ¤iset litteÃ¤t pinnat
Solibrissa, ei oikeaa 3D-laatikkoa (vrt. Lauri:n AutoCAD-nÃ¤kymÃ¤ jossa
sivupalkit + tikkapuut + levyt ovat oikeita box:eja).

`_aggregate_3dface_from_insert` extrudoi nyt myÃ¶s block:n closed
LWPOLYLINE:t niiden `elevation`:ista â†’ vastaavaan 3DFACE:n Z-arvoon.
Top-Z pÃ¤Ã¤tellÃ¤Ã¤n: pienin 3DFACE jonka XY-bbox kattaa LWPOLYLINE:n
bbox:n ja jonka Z on LWPOLYLINE-elevation:n ylÃ¤puolella. Fallback
`base_z + 9 mm` jos pari ei lÃ¶ydy.

Tikashyllyn rakenne IFC:ssÃ¤ alpha5:ssÃ¤:
- 2 sivupalkkia (closed LWPOLYLINE elev=0 â†’ solid Z=0..60)
- N tikkapuuta (closed LWPOLYLINE elev=10 â†’ solid Z=10..25)
- 3DFACE:t ylÃ¤pinnat sÃ¤ilyvÃ¤t (sileÃ¤ ylÃ¤pinta)

Levyhyllyn rakenne:
- Pohjalaatta + ohuet etu/takareunat (closed LWPOLYLINE elev=0)
- PÃ¤Ã¤typalkit (closed LWPOLYLINE elev=58.75)
- 3DFACE:t ylÃ¤pinnat

**Testattu**: Lauri:n `Drawing2.dxf` â†’ 8 IfcCableCarrierSegment, joiden
mesh sisÃ¤ltÃ¤Ã¤ nyt vertex/face-mÃ¤Ã¤rÃ¤t 32-352 / 49-396 (vrt. alpha4:n
1-44 face:n ylÃ¤pinta-only). Z-range 0..60mm tikashyllyille ja
0..67.8mm levyhyllyille â€” vastaa AutoCAD-nÃ¤kymÃ¤n mittoja.

## v0.2.0-alpha4 â€” 2026-05-07 (dynamic block hyllyt: 3DFACE-aggregaatio)

**Korjattu â€” KYL-LISP-hyllyjen uusi dynamic-block-formaatti**:

- Lauri:n hylly-LISP tuottaa nyt blockreferenssejÃ¤ joiden anonyymi
  `*U*`-block-mÃ¤Ã¤ritelmÃ¤ sisÃ¤ltÃ¤Ã¤ 3DFACE-pintoja (aiemmin natiiveja
  3DSOLID-bodyja). Pipeline ei aiemmin lukenut nÃ¤itÃ¤ â†’ hyllyt eivÃ¤t
  tulleet IFC:hen.
- `dxf_reader._aggregate_3dface_from_insert(insert)` kÃ¤yttÃ¤Ã¤
  `INSERT.virtual_entities()`:tÃ¤ joka soveltaa INSERT:in transformaation
  (insertion + rotation + scale) automaattisesti, jolloin block-tason
  3DFACE:t saadaan suoraan world space:hen ilman accoreconsole+STLOUT-
  tessellaatio-vaihetta.
- Vertex-deduplikointi 4-desimaalin tarkkuudella â†’ adjacent face:t
  jakavat vertex:t (Solibrissa pinta yhtenÃ¤inen).
- **Ei AutoCAD COM:ia, ei accoreconsole:a, ei STLOUT:ia** â€” puhdas
  ezdxf:n natiivi luenta.
- Fallback BlockInstance:hin sÃ¤ilyy block:eille joissa ei ole 3DFACE:ja
  (POSITIO-numerointiblokit, label-blokit jne).

**Testattu**: 8 hyllyÃ¤ Lauri:n `Drawing2.dxf`:stÃ¤ (5 tikashyllyÃ¤ +
3 levyhyllyÃ¤) tulevat IFC:hen mesh-pohjaisesti, oikeilla
`IfcCableCarrierSegment` / `CABLELADDERSEGMENT` / `CABLETRAYSEGMENT`-
luokituksilla. 4 uutta yksikkÃ¶testiÃ¤ syntetisoidulla DXF:llÃ¤.

## v0.2.0-alpha3 â€” 2026-05-07 (MagiCAD-IFC merge)

**LisÃ¤tty â€” MAGIIFCEXPORT-tuotetun IFC:n yhdistÃ¤minen master-IFC:hen**:

- **Uusi GUI-filepicker "MagiCAD-IFC"** (valinnainen). Kun annettu, dxf2ifc
  yhdistÃ¤Ã¤ sen tuotteet master-IFC:hen ensimmÃ¤isen `IfcBuildingStorey`:n alle.
- **Uusi CLI-argumentti `--magicad-ifc PATH`** vastaavalla logiikalla.
- **Uusi `dxf2ifc.core.ifc_merger`-moduuli** kÃ¤yttÃ¤Ã¤
  `ifcopenshell.api.project.append_asset`:ia kopioimaan `IfcProduct`-johdannaiset
  MagiCAD-IFC:stÃ¤ master-IFC:hen yhdessÃ¤ geometric context:ien, materiaalien,
  styles:ien ja propertyset:ien kanssa. `IfcSite` / `IfcBuilding` / `IfcBuildingStorey`
  / `IfcSpace` ohitetaan â€” master-IFC:n hierarkia pysyy kanonisena.
- **Spatial container linkitys**: jokainen yhdistetty tuote sidotaan master-IFC:n
  ensimmÃ¤iseen `IfcBuildingStorey`:hen `IfcRelContainedInSpatialStructure`:llÃ¤.
- **DXF-puolen MagiCAD-skip kun MagiCAD-IFC annettu**: `read_dxf` saa
  `skip_magicad`-lipun joka ohittaa `MAGI*`-natiivit luokat ja
  `ACAD_PROXY_ENTITY`-tietueet jotta DXF-pohjainen mesh-tessellaatio ei
  duplikoitu MagiCAD-IFC:n semanttisten tuotteiden kanssa.

**KÃ¤yttÃ¶tapaus**: kollegan FULL-MagiCAD-lisensoidun koneen `-MAGIIFCCD`-komento
(command-line / dialog-vapaa variantti `MAGIIFCEXPORT`-perheestÃ¤) tuottaa
korkeatasoisen MagiCAD-IFC:n (oikeat `IfcDuctSegment` / `IfcAirTerminal` /
MagiCAD-PSet:t). Sen ja Lauri:n KYL-LISP-DXF:n yhdistÃ¤minen yhdeksi
master-IFC:ksi onnistuu nyt yhdellÃ¤ konversio-ajolla â€” DXF-syÃ¶tteellÃ¤
pipeline ei tarvitse AutoCAD COM:ia eikÃ¤ `acad.exe`:tÃ¤ lainkaan,
ainoastaan `accoreconsole.exe`:n 3DSOLID-tessellaatioon.

**Testit**: 7 uutta merger-testiÃ¤ + 2 uutta GUI file_panel -testiÃ¤.
YhteensÃ¤ 530 testiÃ¤ passes (1 skipped, 3 pre-existing failures ettÃ¤ master:in
puolella).

## v0.2.0-alpha2 â€” 2026-05-07 (POC v4 -saagan tulos)

**Muutettu â€” automaattinen MAGIEXPLODE+EXPLODE-keystroke**:

- **DWG-pipeline lÃ¤hettÃ¤Ã¤ MagiCAD-rÃ¤jÃ¤ytyksen** Python-puolen `SendCommand`-
  tekstillÃ¤ (`MAGIEXPLODE\nALL\n\n` + `EXPLODE\nALL\n\n`) AutoCAD:in
  command-lineen â€” sama tapa kuin oikea nÃ¤ppÃ¤imistÃ¶. TÃ¤mÃ¤ toimii
  render-only Object Enabler -tilassa silloin kun aiempi LISP-tason
  `(command "MAGIEXPLODE" â€¦)` rejekoitiin "Invalid selection":lla.
- **AutoCAD nÃ¤kyy konversion ajan** (Visible=True, ei enÃ¤Ã¤ piilossa) jotta
  kÃ¤yttÃ¤jÃ¤ nÃ¤kee MagiCAD-popup:t ja voi klikata OK. Yksi-kaksi popup:ia
  per ajo, ei estoa.
- **DXFOUT kÃ¤yttÃ¤Ã¤ SendCommand-keystrokeja** (`FILEDIA 0 / DXFOUT path /
  Enter / 8 / FILEDIA 1`) â€” luotettavampi kuin `vla-saveas` tai
  `doc.SaveAs(path, fmt)` jotka palauttivat `Invalid argument` AutoCAD
  2025:ssÃ¤.
- **DWG-kopio temp-polkuun** `shutil.copy2`:lla ennen avaamista â€”
  alkuperÃ¤inen DWG ei mutaatu vaikka MAGIEXPLODE+EXPLODE ajetaan.
- **Sysvar SAVE+RESTORE** (FILEDIA, CMDDIA, FACETRES, EXPERT) â€” kÃ¤yttÃ¤jÃ¤n
  AutoCAD-asetukset palautuvat aina, myÃ¶s crash-tilanteessa.
- **AutoCAD-ikkunan koon sÃ¤Ã¤tÃ¶ POISTETTU** â€” POC v3.x:n
  `WindowState/WindowLeft/Top/Width/Height` -mutaatiot mutaroivat
  Lauri:n AutoCAD-profile:in command bar -kokoa. v0.2.0-alpha2 ei kosketa
  ikkunaa. Aiemmin tallentunut profile-tila pitÃ¤Ã¤ resetoida kÃ¤sin
  AutoCAD:ssa: `OPTIONS` â†’ Profiles â†’ Reset.

**LisÃ¤tty â€” diagnostiikka**:

- Progress-loki nÃ¤yttÃ¤Ã¤: `DXF-luettu: N polyface/3DFACE/MESH + M ACIS`,
  `Mesh-layerit (top 5)`, `Profile-mappaus: K mesh-pohjaisia`,
  `Meshâ†’IFC-tyypit (top 5)` â€” diagnoosin nopeampi tunnistus.
- LISP-loki:ssa: `MAGI_BEFORE/AFTER`, `INSERTS_REMAINING`,
  `FINAL_3DSOLIDS`, `POLYFACE_AFTER`.

**Korjattu â€” orchestrator**:

- `BlockInstance` skipataan `IfcBuildingElementProxy`,
  `IfcCooler/Condenser/Compressor`, `IfcTank`, `IfcFlowController`,
  `IfcPipeSegment`, `IfcFurniture`-haaroissa â€” ei enÃ¤Ã¤
  `TypeError: expects MeshGeometry, got BlockInstance` -kaatumista.
- `IfcPipeSegment` MeshGeometry-tapauksessa kirjoitetaan
  `IfcTriangulatedFaceSet`-mesh:nÃ¤ `_add_mesh_product`-helperin kautta â€”
  MagiCAD-pipet eivÃ¤t enÃ¤Ã¤ droppaudu pipelineesta.

**Tunnetut rajoitukset**:

- **Render-only Object Enabler** (Lauri:n kone) ei tuota 3D-pintoja
  MagiCAD-objekteille edes manuaalisella MAGIEXPLODE+EXPLODE:lla.
  Tupla-rÃ¤jÃ¤ytys tuottaa 2D-polylineja jotka eivÃ¤t kÃ¤Ã¤nnyksellÃ¤ saada
  3DSOLID:eiksi. **Vain Lauri:n KYL-LISP-osat tulevat IFC:hen**.
- **FULL MagiCAD-lisenssin** koneella (esim. kollegan kone) sama
  pipeline tuottaa todennÃ¤kÃ¶isesti oikeat MagiCAD-pinnat IFC:hen ilman
  koodimuutoksia â€” MagiCAD-ARX kÃ¤sittelee EXPLODE:n eri tavalla.
- Polyline-extrusion-strategia (POC v5) jatkossa render-only-tilassa.

## v0.2.0-alpha1 â€” 2026-05-06

**LisÃ¤tty â€” DWG-input + MagiCAD-tuki**:

- **`.dwg`-tiedostot hyvÃ¤ksytÃ¤Ã¤n input:ina** â€” `dxf2ifc convert input.dwg
  output.ifc` toimii samalla tavalla kuin DXF. GUI Browse-dialog filter
  laajennettu `*.dxf;*.dwg`.
- **MagiCAD-objektien EXPLODE FULL-MagiCAD-koneella**: DWG-input:lle
  kÃ¤ynnistetÃ¤Ã¤n AutoCAD piilotettuna (`acad.exe` Visible=False
  pywin32-COM:lla). MagiCAD ARX latautuu autoload-rekisteristÃ¤, ja
  `(command "_.EXPLODE" ent)` tuottaa 3DSOLID-lapsia jotka STLOUT
  tessellÃ¶i STL:ksi. VÃ¤litilanne-DXF kirjoitetaan DXFOUT:lla, jonka
  jÃ¤lkeen normaali pipeline (ezdxf + accoreconsole + IFC-tuotanto)
  jatkaa siitÃ¤.
- **Adaptiivinen kÃ¤yttÃ¤ytyminen**: Render-only Object Enabler -koneella
  EXPLODE epÃ¤onnistuu hiljaa â†’ MagiCAD-osat jÃ¤Ã¤vÃ¤t pois IFC:stÃ¤ mutta
  Lauri:n omat KYL-LISP-piirrokset toimivat ennallaan. FULL-MagiCAD-
  koneella sama koodi tuottaa tÃ¤ydellisen 3D-geometrian.
- **Singleton hidden AutoCAD**: COM-instanssi pidetÃ¤Ã¤n muistissa
  konversioiden vÃ¤lillÃ¤. Cold-start ~14 s ekan kerran, seuraavat
  ~3 s/konversio. Spike v3 vahvisti: ikkuna ei nÃ¤y missÃ¤Ã¤n vaiheessa.
- **Throwaway profile** `dxf2ifc_headless`: estÃ¤Ã¤ RECENTFILES-, FILEDIA-,
  CMDDIA-, SDI-sysvar-saastumisen kÃ¤yttÃ¤jÃ¤n omasta AutoCAD-profiilista.

**Riippuvuudet**:

- `pywin32>=305` (Windows-only, sys_platform=='win32'). DWG-input vaatii
  AutoCAD:in asennetuksi. DXF-input ei vaadi pywin32-tukea.

**SisÃ¤inen**:

- Uusi moduuli `core/dwg_preconvert.py` (~270 riviÃ¤) â€” singleton COM
  session, AutoLISP-pohjainen EXPLODE+STLOUT+DXFOUT, atexit-cleanup.
- Poistettu `core/proxy_preprocessing.py` (v0.1.19-yritys
  accoreconsole-EXPLODE-polulle, todistettu mahdottomaksi: accoreconsole
  ei lataa ARX-moduuleja Autodesk-rajoitteen vuoksi).
- Orchestrator detect:taa `.dwg`-suffix:in ja kutsuu DWG-pre-conversion:in
  ennen muuta pipelineÃ¤.
- Ei regressiota DXF-input:lle: 4001_1krs.dxf tuottaa tÃ¤smÃ¤lleen
  v0.1.18-baseline:n product-counts (9 + 12 + 15).
- 512/512 pytest passes (+3 uutta `test_dwg_preconvert.py`-testiÃ¤).

**Rajoitteet**:

- MagiCAD-osien tÃ¤ysi 3D-geometria vaatii FULL MagiCAD-lisenssin
  asennetuksi konversiokoneella. Render-only Object Enabler ei riitÃ¤ â€”
  Object Enabler ei tarjoa Explode-toiminnallisuutta MAGI*-luokille.
  Empiirisesti vahvistettu 4 spike-iteraatiossa.
- RekisterÃ¶idyt accoreconsole-asetukset sÃ¤ilyvÃ¤t (RECENTFILES jne.) vain
  oman profiilin ulkopuolella `dxf2ifc_headless`-profiilissa.

## v0.1.19-alpha1 â€” 2026-05-06

**LisÃ¤tty â€” MagiCAD/proxy-objektien geometria**:

- **Avoimet polyline:t** (LWPOLYLINE/POLYLINE ilman ``closed``-flagia)
  hyvÃ¤ksytÃ¤Ã¤n ``dxf_reader``-tasolla LineGeometry-segmentteinÃ¤ â€” yksi
  per perÃ¤kkÃ¤inen vertex-pari. Ratkaisee MagiCAD ACAD_PROXY_ENTITY-
  putkien (KYL-JV1) + detail-viivojen nÃ¤kyvyyden, jotka v0.1.18:ssa
  putosivat hiljaa pois ``is_closed=True``-tarkistuksessa.
- **Uusi moduuli** ``core/proxy_preprocessing.py``: jokaiselle
  ACAD_PROXY_ENTITYlle joko bbox-cuboid-fallback (kun ezdxf:n
  proxy_graphic-parser ei pysty purkamaan eikÃ¤ Object Enableria ole)
  tai tÃ¤ydellinen accoreconsole-EXPLODE+STLOUT (kun MagiCAD:in ilmainen
  Object Enabler on asennettu).
- **Object Enabler -tunnistus**: Windowsin rekisterihakemisto
  ``HKLM\\SOFTWARE\\Autodesk\\ObjectDBX`` etsitÃ¤Ã¤n tunnetuille MagiCAD-
  luokille. Jos puuttuu, progress-logiin tulee tarkka asennusohje:
  https://www.magicad.com/object-enabler/
- **Profile-sÃ¤Ã¤nnÃ¶t** ``default_kylmalaite.toml``:
  - KYL-JV1 â†’ IfcPipeSegment (CHILLEDWATER)
  - KYL-JV1-LAITE â†’ IfcFlowController (USERDEFINED)
  - KYL-KONDENSSIASTIAT â†’ IfcTank (BASIN)
- **Uudet builders**: ``add_tank``, ``add_flow_controller`` (mesh-
  pohjaisia, hyÃ¶dyntÃ¤vÃ¤t ``_add_mesh_product``-helperÃ¤).
- **CLI flag** ``--no-preprocess-proxies`` opt-out:in tueksi.
- **GUI checkbox** "MagiCAD/proxy-objektien geometria" oletus pÃ¤Ã¤llÃ¤,
  persistoituu ``QSettings:Mcrauli/dxf2ifc/preprocess_proxies``.
  Pikakonversio-tila kytkee sen pois automaattisesti.

**Verifioitu**:

- ``4001_1krs.dxf`` (ei MagiCAD:ia): ei regressiota (9 + 12 + 15 entityÃ¤
  kuten v0.1.18:ssa).
- ``magicad_1krs.dxf`` (145 ACAD_PROXY_ENTITYÃ¤): 39 IfcPipeSegment
  (KYL-JV1) + 13 IfcBuildingElementProxy (MUUT_OSAT) + 3
  IfcCableCarrierSegment nÃ¤kyy IFC:ssÃ¤. KYL-JV1-LAITE (36) ja
  KYL-KONDENSSIASTIAT (18) tulevat nÃ¤kyviin sen jÃ¤lkeen kun Object
  Enabler on asennettu.

**SisÃ¤inen**:

- ``_record_from_entity`` palauttaa nyt ``list[EntityRecord]`` (0/1/N)
  yksittÃ¤isen ``EntityRecord | None`` sijaan â€” yksinkertaistaa
  segment-fan-out-logiikkaa proxy-graphics:eille.
- ``add_building_element_proxy`` hyvÃ¤ksyy nyt sekÃ¤ PolygonGeometryn
  (suljettu paneeli) ettÃ¤ MeshGeometryn (faceted Brep proxy-cuboid-
  fallbackista).
- Open-polyline-segmentit IfcBuildingElementProxy / IfcTank /
  IfcFlowController -sÃ¤Ã¤nnÃ¶ille hylÃ¤tÃ¤Ã¤n hiljaa orchestrator-
  dispatchissÃ¤ â€” ne ovat MagiCAD:in 2D-detail-renderiÃ¤, ei pÃ¤Ã¤-
  geometriaa.
- 516 / 516 pytest passes (+10 uutta v0.1.18:n 502:sta).

## v0.1.18-alpha1 â€” 2026-05-06

**LisÃ¤tty**:

- **Checkbox "LisÃ¤Ã¤ 1.krs absoluuttinen korko"** ennen korko-kenttÃ¤Ã¤.
  PÃ¤Ã¤llÃ¤ (default): nykyinen offset-kÃ¤yttÃ¤ytyminen â€” DXF:n Z=0 tulkitaan
  1.krs lattiaksi ja annettu korko lisÃ¤tÃ¤Ã¤n jokaiseen
  IfcBuildingStorey.Elevation- ja elementti-Z-arvoon. Pois: DXF:n
  Z-koordinaatit menevÃ¤t IFC:hen sellaisinaan, ei mitÃ¤Ã¤n offsettia.
  Tila persistoituu QSettings:iin (``Mcrauli/dxf2ifc/
  floor_elevation_enabled``), eli kerran valittu tyÃ¶tapa pysyy
  kÃ¤ynnistyskerrasta toiseen. Sopii suunnittelijalle joka piirtÃ¤Ã¤
  AutoCADissa suoraan absoluuttisilla koordinaateilla â€” ei tarvitse
  muistaa nollata kenttÃ¤Ã¤ joka konversiolla.

## v0.1.17-alpha1 â€” 2026-05-06

**Korjattu (KRIITTINEN)**:

- **Tikashyllyt, levyhyllyt ja hÃ¶yrystimet eivÃ¤t enÃ¤Ã¤ puutu IFC:stÃ¤.**
  v0.1.14:n LWPOLYLINEâ†’CONVTOSOLID-laajennus puski LISP-bodyn 1818 â†’ 1868
  merkkiin, joka tempdir-polkujen substituution jÃ¤lkeen ylitti
  ``accoreconsole.exe``:n hard-cap 2048-merkin .scr-rivipuskurin (~2065
  merkkiÃ¤). Form katkesi kesken Phase 1:n, parser jÃ¤i ``((_>``
  multi-paren-prompt:iin ikuisesti, **0 STL-tiedostoa kirjoitettiin** ja
  3DSOLID-bodyt tippuivat hiljaa pois. Korjaus: `_LISP_BODY` jaettu
  neljÃ¤ksi top-level-formiksi (SETUP / PHASE1 / PHASE2 / CLEANUP),
  jokainen oma rivi ``.scr``:ssÃ¤, setq-globaalit pysyvÃ¤t yli rivien.
  Verifioitu Lauri:n ``4001_1krs.dxf``:llÃ¤: 9 KYL-TIKASHYLLY +
  12 KYL-LEVYHYLLY + 15 KYL-HÃ–YRYSTIMET â†’ IFC:hen tÃ¤ysillÃ¤
  IfcFacetedBrep-meshillÃ¤. Bisektio: 2048 OK, 2092 jumissa.

## v0.1.16-alpha1 â€” 2026-05-05

**Korjattu**:

- **MAGIFLOORORIGO + muut MagiCAD:in non-graphical proxyt** eivÃ¤t enÃ¤Ã¤
  kaatu konversiota. Aiemmin yritys lukea ``entity.dxf.layer`` tÃ¤llaisesta
  control-objektista raise-asi ``Invalid DXF attribute``-virheen ja koko
  read-vaihe pysÃ¤htyi. Nyt lukijassa on defensive try/except jokaisen
  entity:n attribuutti-luvun ympÃ¤rillÃ¤ â€” ei-graafisten entityjen kanssa
  silent skip, todelliset geometria-entityt kÃ¤sitellÃ¤Ã¤n normaalisti.

**LisÃ¤tty**:

- **GUI-checkbox "Pikakonversio (ohita 3D-tessellaatio)"** Convert-napin
  ylÃ¤puolelle. Kun valittu, accoreconsole-vaihe (joka tessellÃ¶i
  3DSOLID-bodyt) ohitetaan kokonaan. KÃ¤ytÃ¤nnÃ¶ssÃ¤ **5â€“10Ã— nopeampi**
  raskaalle DXF:lle â€” kÃ¤ytÃ¤ kun haluat nopean tarkistuksen ettÃ¤
  layer-mappaus + 2D-geometria mappautuu oikein. Valinta persistoituu
  QSettings:iin (``Mcrauli/dxf2ifc/quick_convert``) ja tÃ¤yttyy
  automaattisesti seuraavalla kÃ¤ynnistyksellÃ¤.

**SisÃ¤inen**:

- 496 passed, 1 skipped, 1 deselected.

## v0.1.15-alpha1 â€” 2026-05-05

**LisÃ¤tty**:

- **MagiCAD-proxy-objektien luku DXF:stÃ¤**: ``ACAD_PROXY_ENTITY``-tyyppiset
  entityt (AutoCADin tapa tallentaa MagiCAD-objektien nÃ¤ytettÃ¤vÃ¤ geometria)
  rÃ¤jÃ¤htÃ¤vÃ¤t nyt ezdxf:n ``__virtual_entities__()``-API:n kautta
  primitiiveiksi (LINE, LWPOLYLINE, POLYLINE, MESH) jotka prosessoidaan
  saman dispatch:n lÃ¤pi kuin natiivit DXF-entityt. Aiemmin MagiCAD-piirretyt
  putket / venttiilit / laitteet katosivat hiljaa konversiossa. Layer:n
  perii proxyn alkuperÃ¤inen authored layer kun virtual-entity ei sitÃ¤
  itse kantaa, joten profile-mappaus toimii tutuilla layer-pattern:eillÃ¤.
- **POLYLINE (closed)** -tuki, jota MagiCAD-proxy graphics tyypillisesti
  kÃ¤yttÃ¤Ã¤ LWPOLYLINE:n sijaan vanhemmissa DXF-formaateissa.

**SisÃ¤inen**:

- ``dxf_reader.py``: dispatch-loop refaktoroitu ``_record_from_entity``
  -helperiksi joka tukee ``layer_override`` + ``handle_override`` -optoreja
  proxy-rekursiota varten.
- 496 passed, 1 skipped, 1 deselected (test_extract_acis_meshes_round_trip
  on edelleen Lauri:n DXF + accoreconsole -ympÃ¤ristÃ¶testi).

## v0.1.14-alpha1 â€” 2026-05-05

**LisÃ¤tty**:

- **MagiCAD-yhteensopivuus laajennettu**: hÃ¶yrystimet, lauhduttimet ja
  kompressorit (``IfcEvaporator`` / ``IfcCondenser`` / ``IfcCompressor``)
  saavat nyt Type-objektit + ``Pset_*TypeCommon``-PSetin, joten MagiCAD:n
  "Convert to MagiCAD object" tunnistaa myÃ¶s koneikot. Aiemmin tÃ¤mÃ¤ toimi
  vain hyllyille ja putkille.
- **MUUT_OSAT-layer** lisÃ¤tty default-profiiliin: yleiset kylmÃ¤laitteen
  osat (kannakkeet, tukirakenteet, venttiilit, anturit) joilla ei ole
  spesifiÃ¤ IFC-tyyppiÃ¤. Mappaus â†’ ``IfcBuildingElementProxy`` +
  ``USERDEFINED`` + ``ElementType="MUUT_OSAT"`` +
  ``Pset_BuildingElementProxyTypeCommon`` Reference="MUUT_OSAT".

**SisÃ¤inen**:

- 490 passed, 1 skipped, 1 deselected (test_extract_acis_meshes_round_trip
  on lokaali ympÃ¤ristÃ¶testi joka tarvitsee Lauri'n DXF + accoreconsole;
  ei regression v0.1.14-koodin lisÃ¤yksistÃ¤).

## v0.1.13-alpha1 â€” 2026-05-05

**LisÃ¤tty**:
- **IFC-vÃ¤rit**: kaikki konvertoidut elementit saavat AutoCAD ACI 175
  -vÃ¤rin (slate-purppura) jaetun ``IfcSurfaceStyle`` + ``IfcStyledItem``
  -ketjun kautta. Refrigeration-malli lukeutuu visuaalisesti yhtenÃ¤isenÃ¤
  SolibrissÃ¤ ja MagiCAD:ssÃ¤.
- **MagiCAD-yhteensopivuus**: ``IfcCableCarrierSegmentType`` ja
  ``IfcPipeSegmentType`` saavat nyt ``Pset_*TypeCommon``-PSetin
  Reference-kentÃ¤llÃ¤ â€” ilman tÃ¤tÃ¤ MagiCAD:n "Convert to MagiCAD object"
  -komento ei tunnistanut LEVYHYLLY-elementtejÃ¤.
- **DOMAIN-valikkoon KYL** Profile Editorin Edit-dialogissa
  (oli vain ARK + TATE), KYL on uusi default kun "Add rule".
- **RAVA-koodien vapaateksti**: Edit-dialogin LVI / TALOTEKNIIKKA-combot
  ovat nyt editable â€” voit kirjoittaa oman koodin jota ei ole
  bundlatussa codesetissÃ¤.

**Korjattu**:
- **Layer-tableisiin selvempi otsikko**: "Domain" â†’ **"Luokitus"**
  (sarake nÃ¤yttÃ¤Ã¤ codeset-nimen kuten RAVA-LVI, ei domain-arvoa).
- **Installer luo tyÃ¶pÃ¶ytÃ¤kuvakkeen** oletuksena (oli opt-in).
  KÃ¤yttÃ¤jÃ¤ voi yhÃ¤ disabloida asennuksen aikana.
- **Sovelluksen vÃ¤rit pysyvÃ¤t tummina** myÃ¶s light-themalla Windows
  -koneilla. Style.qss kattaa nyt QTextEdit, QComboBox-popup, QSpinBox,
  QDialog, QGroupBox, QToolTip ja scrollbar-elementit, jotka aiemmin
  fallbackasivat OS-defaulttiin (valkoinen pohja).

**SisÃ¤inen**:
- 491 passed, 1 skipped (4 olemassa olevaa rule_dialog-testiÃ¤ pÃ¤ivitetty
  uuteen KYL-default-tilaan).

## v0.1.12-alpha1 â€” 2026-05-05

**Fixed**:

- **1.krs korko vaikuttaa nyt myÃ¶s elementtien Z-koordinaattiin**: v0.1.11
  siirsi vain ``IfcBuildingStorey.Elevation``-arvoa, mutta itse hyllyt /
  putket / hÃ¶yrystimet jÃ¤ivÃ¤t DXF:n Z-tasolle. Syy: builders kirjoittavat
  ``IfcLocalPlacement``-matriisin elementin omasta anchor-Z:stÃ¤, eikÃ¤
  storey-tason siirto kaskadoidu ``edit_object_placement``-API:n kautta.
  Korjaus: orchestrator siirtÃ¤Ã¤ nyt jokaisen ``MappedEntity.geometry``
  Z-komponentteja ``floor_elevation_mm``-verran ENNEN builders-vaihetta.
  Nyt 1.krs korolla 12000 mm hylly Z=3000 â†’ IFC absoluuttinen Z=15000
  (storey 12000 + storey-relative 3000), kuten oletettua.

## v0.1.11-alpha1 â€” 2026-05-05

**Added**:
- **1.krs korko -input** GUI:hin Excel-rivin alle ja CLI:lle
  ``--floor-elevation MM``. AutoCAD piirretÃ¤Ã¤n 1.krs Z=0:lla; tÃ¤mÃ¤ arvo
  lisÃ¤tÃ¤Ã¤n jokaiseen ``IfcBuildingStorey.Elevation``-arvoon, jotta
  rakennus tulee absoluuttiseen korkoon koko projektin
  koordinaatistossa (esim. 1.krs korko 12000 mm + hylly Z=3000 mm
  â†’ IFC:ssÃ¤ Z=15000 mm). Arvo persistoituu QSettings:iin (``Mcrauli/
  dxf2ifc/floor_elevation_mm``) ja tÃ¤yttyy automaattisesti seuraavalla
  kÃ¤ynnistyksellÃ¤.
- **Versionumero status-rivin oikeassa reunassa**: ohjelman versio
  nÃ¤kyy jatkuvasti ilman About-dialogin avaamista.

**Removed**:
- **CRS / ETRS-TM35FIN georeferensointi** kokonaisuudessaan: pois
  Profile-skeemasta, GUI:n "Set CRSâ€¦" -dialogi, CLI:n
  ``--eastings`` / ``--northings`` / ``--orthogonal-height``
  -argumentit, ``IfcProjectedCRS`` + ``IfcMapConversion``
  -kirjoitus, ``--validate`` ``expect_crs``-kytkin sekÃ¤
  Solibri-rule-set:n CRS-coverage-rule. KÃ¤yttÃ¤jÃ¤kohtainen palaute:
  feature ei tuonut tyÃ¶nkulkuun lisÃ¤arvoa, ja 1.krs korko-input
  vastaa todelliseen tarpeeseen rakennuksen sijoittamisesta
  absoluuttiseen koordinaatistoon ilman GIS-monimutkaisuutta.

## v0.1.10-alpha1 â€” 2026-05-04

**Fixed**:
- **ItsepÃ¤ivityksen "Failed to start embedded python interpreter" -virhe**:
  uusi exe kÃ¤ynnistetÃ¤Ã¤n nyt **3 sekunnin viiveellÃ¤** piilotetun
  PowerShell-launcherin kautta. Antaa vanhan prosessin vapauttaa
  ``.old``-exen handle ja Windows Defenderin viimeistellÃ¤ reaaliaikaskannauksen
  ennen kuin uuden exen PyInstaller-bootloader yrittÃ¤Ã¤ purkaa tiedostoja
  ``%TEMP%``:iin. Aiemmin OLD ``os._exit(0)`` ja NEW spawn osuivat
  millisekuntien pÃ¤Ã¤hÃ¤n toisistaan ja tÃ¶rmÃ¤sivÃ¤t satunnaisesti.
- **SHA-256-verifiointi ladattuun assettiin**: pÃ¤ivittÃ¤jÃ¤ hakee nyt
  GitHub Releases ``.sha256``-sidecarin ja vertaa downloadatun exen
  hashin streamatessa. Mismatch â†’ ``.part``-tiedosto poistetaan ja
  vaihto keskeytetÃ¤Ã¤n ennen swapia. EstÃ¤Ã¤ korruptoituneen / katkenneen
  latauksen pÃ¤Ã¤syn kÃ¤ynnistettÃ¤vÃ¤ksi, mikÃ¤ on yksi mahdollinen
  bootloader-virheen syy.

**Removed**:
- **Help-menun "KÃ¤yttÃ¶ohjeet (selain)" -action**: About-dialogissa on
  nyt linkki samaan kÃ¤yttÃ¶ohjeeseen, joten erillinen menu-action oli
  duplikaatti.

## v0.1.9-alpha1 â€” 2026-05-04

**Changed**:
- **About-dialogi**: poistettu "MIT-licensed." -rivi (LICENSE-tiedosto
  repon juuressa pysyy lain mukaan ennallaan). Tilalle linkki
  kÃ¤yttÃ¶ohjeisiin osoitteessa
  <https://mcrauli.github.io/autocad-lisp-ohjeet/dxf2ifc.html>.
- **Help â†’ KÃ¤yttÃ¶ohjeet (selain)**: uusi menu-action joka avaa
  kÃ¤yttÃ¶ohjeet selaimessa (F1-pikanÃ¤ppÃ¤in). About siirtyi separatorin
  alapuolelle.
- **Binary copyright -metatieto** lyhennetty: `(c) 2026 Lauri Rekola`
  (poistettu ". MIT licence." -loppu installerin VersionInfoCopyright-
  ja exe:n LegalCopyright-kentistÃ¤).

## v0.1.8-alpha1 â€” 2026-05-04

**Changed**:
- **Brand metadata**: poistettu "Radika Oy" -maininta installerista, exe:n
  Win32-resource-blokista ja LICENSE-tiedostosta. Publisher / CompanyName
  / LegalCopyright / Copyright on nyt **"Lauri Rekola"** ilman
  yritysmainintaa â€” dxf2ifc on Lauri'n henkilÃ¶kohtainen projekti, ei
  tyÃ¶nantaja-integroitu.
- **SisÃ¤iset Windows-tunnisteet** vaihdettu `Mcrauli`-namespaceen:
  - AppUserModelID `Radika.dxf2ifc.kylmalaite.1` â†’ `Mcrauli.dxf2ifc.kylmalaite.1`
  - QSettings-organisaatio `Radika` â†’ `Mcrauli` (recent-files-rekisteri
    siirtyy `HKCU\Software\Mcrauli\dxf2ifc`-polkuun, vanhat
    recent-files-listaukset eivÃ¤t sÃ¤ily yli pÃ¤ivityksen).

Toiminnallisuus identtinen v0.1.7-alpha1:n kanssa.

## v0.1.7-alpha1 â€” 2026-05-04

**Added**:
- **MEKA-spec FI_Tekninen + FI_Tuote KYL-TIKASHYLLY ja KYL-LEVYHYLLY -sÃ¤Ã¤nnÃ¶ille**.
  Default-profiili kirjoittaa nyt nÃ¤mÃ¤ Solibrin AsennushyllyjÃ¤rjestelmÃ¤lle:
  - **Tikashylly** (KS20-500 K L=6000 PG): Materiaali TerÃ¤s, Pinnoite
    Kuumasinkitty (EN 10346), Korroosioluokka C1-C2,
    Paloturvallisuusluokka E90, Levypaksuus 0,75 mm, Paino 10,68 kg/6 m.
    FI_Tuote: Valmistaja MEKA + linkki tuotesivulle.
  - **Levyhylly** (KRA-60-500 L=3000 M): Materiaali TerÃ¤s, Pinnoite
    Valkoinen RAL 9010 polyesterimaali, Korroosioluokka C1-C2,
    Paloturvallisuusluokka E90, Levypaksuus 1,25 mm, Paino 19,09 kg/3 m.
    FI_Tuote: Valmistaja MEKA + linkki tuotesivulle.
- **`_FI_TEKNINEN_DEFAULTS["IfcCableCarrierSegment"]`** laajennettu:
  Materiaali, Pinnoite, Korroosioluokka, Paloturvallisuusluokka,
  Levypaksuus, Kuormitus, Paino. (Nimi `Korroosiosuojaus` â†’
  `Korroosioluokka` RAVA-konvention mukaan.)

KÃ¤yttÃ¤jÃ¤ voi ylikirjoittaa fi_tekninen / fi_tuote oman profiilin TOML:n
kautta jos kÃ¤ytÃ¶ssÃ¤ on eri valmistaja tai mitoitus.

## v0.1.6-alpha1 â€” 2026-05-04

**Added**:
- **Inno Setup -installeri** (`dxf2ifc-Setup-0.1.6a1.exe`): oikea Windows-
  asennusohjelma jonka kautta sovellus saa Start-menu -merkinnÃ¤n, Apps &
  Features -uninstallerin ja version-info-resurssit. Asennus per-user
  `%LOCALAPPDATA%\Programs\dxf2ifc`:iin, ei UAC-promptia. SmartScreen-
  kitka pienempi kuin paljaalla `.exe`:llÃ¤ koska installer nÃ¤yttÃ¤Ã¤
  oikealta Windows-asennusohjelmalta.
- Stable AppId GUID upgrade/uninstall-identiteettiÃ¤ varten â€” sama GUID
  lÃ¤pi versioiden, joten installer pÃ¤ivittÃ¤Ã¤ aiemman dxf2ifc-asennuksen
  oikein.
- Suomi + englanti -kielet wizardissa.
- `lzma2/max` -kompressio: installer ~40-60% pienempi kuin paljas exe.

Raw exe (`dxf2ifc-0.1.6a1.exe`) toimitetaan edelleen rinnalla â€” sitÃ¤
kÃ¤yttÃ¤vÃ¤ auto-update-banneri jatkaa toimintaansa.

## v0.1.5-alpha1 â€” 2026-05-04

**Fixed (CRITICAL â€” v0.1.4 was broken)**:
- v0.1.4-alpha1:n `cleanup_stale_meipass_dirs`-funktio poisti vahingossa
  ajossa olevan exen oman `_MEI***`-temp-kansion â†’ seuraava kÃ¤ynnistys
  failasi `[Errno 2] No such file or directory: ...\_MEI*\base_library.zip`
  -virheellÃ¤. Vika oli Windows-polkujen short-form (`LAURIR~1`) vs
  long-form (`LauriRekola`) -vertailussa: `os.path.normcase` ei
  yhdenmukaista niitÃ¤, joten oma _MEI tunnistettiin "vanhentuneeksi"
  ja siivottiin pois.
- Korjaus: cleanup-funktio poistettu kokonaan. Windows siivoaa %TEMP%:n
  ajan myÃ¶tÃ¤ â€” meidÃ¤n omasta riskinotosta ei ole hyÃ¶tyÃ¤ joka oikeuttaisi
  bugin riskin.

> Jos sun nykyinen exe on rikki (ei kÃ¤ynnisty), lataa **v0.1.5-alpha1
> manuaalisesti** GitHubista ja korvaa nykyinen â€” itsepÃ¤ivitys ei
> luonnollisesti toimi rikkinÃ¤isestÃ¤ prosessista.

## v0.1.4-alpha1 â€” 2026-05-04

**Fixed**:
- GUI:n alaotsikko luki "AutoCAD DXF â†’ IFC 4 with Talo2000 classification"
  vaikka projekti on alusta asti ollut RAVA3Pro-pohjainen kylmÃ¤suunnittelu.
  Korjattu sekÃ¤ GUI-kuvateksti, About-dialogi, CLI `--help`-kuvaus ja
  pyproject.toml description-kenttÃ¤ mainitsemaan **RAVA3Pro** ja
  **kylmÃ¤suunnittelu**. Talo2000 sÃ¤ilyy tekstissÃ¤ paikoissa joissa se on
  teknisesti oikein (ARK-domain-validointisÃ¤Ã¤nnÃ¶t, profiili-skeeman
  `talo2000_code`-kenttÃ¤).

## v0.1.3-alpha1 â€” 2026-05-04

**Fixed**:
- **"Failed to remove temporary directory" -popup itsepÃ¤ivityksen jÃ¤lkeen**.
  PyInstaller-bootloader yrittÃ¤Ã¤ siivota `_MEI***`-temp-kansion vanhasta
  exestÃ¤ swap-hetkellÃ¤ mutta tiedostot ovat lukittuna kunnes Windows on
  ehtinyt vapauttaa ne. ItsepÃ¤ivitysflow kÃ¤yttÃ¤Ã¤ nyt `os._exit(0)`:ia
  joka skippaa bootloaderin siivouksen kokonaan; uusi exe sweeppaa
  vanhentuneet `_MEI*`-kansiot kÃ¤ynnistyessÃ¤Ã¤n.
- **Custom-ikoni nÃ¤kyy nyt taskbarissa, Alt+Tab:ssÃ¤ ja desktop-pikakuvakkeessa**.
  LisÃ¤tty Windows AppUserModelID (`Radika.dxf2ifc.kylmalaite.1`) ennen
  QApplicationia â€” ilman tÃ¤tÃ¤ Windows ryhmittelee sovelluksen
  PyInstaller-bootloaderin yleiseksi exeksi ja taskbar kÃ¤ytti
  generic-ikonia.
- EXE-icon-polku spec-tiedostossa muutettu absoluuttiseksi
  (`ROOT/assets/dxf2ifc.ico` SPECPATH-relatiivisen sijaan) â€” varmistaa
  ettÃ¤ PyInstaller lÃ¶ytÃ¤Ã¤ ikonin.

## v0.1.2-alpha1 â€” 2026-05-04

**Added**:
- **Brand-ikoni**: Lauri'n suunnittelema kuvake (DXF-viiva â†’ 3D-render)
  exe-tiedostolle, GUI-ikkunan title-baariin, taskbar-nÃ¤kymÃ¤lle ja
  Alt+Tab-vaihtajalle. Multi-resolution `.ico` (16/32/48/64/128/256 px)
  generoitu lÃ¤hde-PNG:stÃ¤. Asetettu sekÃ¤ PyInstallerin EXE-iconiksi
  ettÃ¤ Qt:n WindowIcon-asetuksena.

## v0.1.1-alpha1 â€” 2026-05-04

Toinen alpha â€” ensimmÃ¤inen release jossa GUI:n itsepÃ¤ivitys-banneri
voi tarjota latausta automaattisesti seuraavissa versioissa. Lataa
tÃ¤mÃ¤ manuaalisesti kerran, sen jÃ¤lkeen pÃ¤ivitykset hoituvat itsestÃ¤Ã¤n.

**Removed**:
- **Pre-conversion geometric outlier scan** (`core/outliers.py`,
  `convert_dxf(detect_outliers=...)` kwargs). The scan produced false
  positives on real refrigeration models with multi-storey equipment
  spread; Solibri's own "Mallit hajallaan" rule covers the same check
  natively when the file is opened. Removing the feature drops one
  false-warning source and ~150 lines of code.

**Added**:
- **Solibri discipline auto-detect via `Pset_Project`**: every IFC
  project now carries `Pset_Project.Authorization = "KylmÃ¤suunnittelu"`,
  matching the Granlund/RAVA3Pro reference convention Solibri reads
  for role auto-selection. Plus the producing IfcApplication is now
  tagged `ApplicationIdentifier = "dxf2ifc-kylmalaite"` (was generic
  IfcOpenShell). A synthetic IfcOwnerHistory is propagated to every
  IfcRoot in the file at write-time so consumers can branch on the
  producing tool reliably.
- **Energy-spec diagnostics**: when `convert_dxf` runs with an
  `energy_specs_path`, the GUI preview-log / stderr now reports
  loaded row count, parsed headers per sheet, matched/total
  refrigeration devices, and the first 10 skip reasons (POSITIO
  missing or row not in spreadsheet). Earlier the lookup failed
  silently and the user could not tell why FI_Tekninen stayed empty.
- **Multi-sheet Excel support**: `load_energy_specs` now reads every
  sheet of an `.xlsx` workbook (was: active sheet only). Lauri's
  RefDesign teholuettelo splits frozen + chilled across `Pakasteet`
  and `KylmÃ¤t` sheets â€” both flow through. Sheets without a
  recognisable Koneikko + Laitetunnus header are skipped.
- **Excel column aliases**: `"REV."` is now recognised as a koneikko
  column (RefDesign convention where the "Revision" column actually
  carries the koneikkotunnus). New canonical FI_Tekninen fields
  `Vastusteho`, `JÃ¤nnite`, and `JÃ¤Ã¤hdyttÃ¤vÃ¤ vaikutus` with their
  Finnish/English aliases.
- New helper `load_energy_specs_with_headers(path)` returns
  `(specs, {sheet_name: [header strings]})` so callers can quote the
  parsed headers back to the user when no rows matched.
- IfcEvaporator + IfcCondenser FI_Tekninen default templates now
  include Vastusteho + JÃ¤nnite (+ JÃ¤Ã¤hdyttÃ¤vÃ¤ vaikutus on Evaporator)
  so Solibri shows those rows even when an Excel hasn't been picked.

**Changed**:
- Excel field-alias matching now requires an exact match for tokens
  â‰¤3 characters long. `"Te"` (an evaporation-temperature shorthand)
  no longer false-matches inside `"Vastusteho"`, `"u_v"` no longer
  leaks into voltage-adjacent headers, etc.

**Changed**:
- **Discipline name in the IFC is now "JÃ¤Ã¤hdytys" (was "KYL")** â€” Solibri
  uses "JÃ¤Ã¤hdytys" as the canonical refrigeration discipline label, so
  the IFC matches the role names Solibri's UI presents. The internal
  `domain="KYL"` value in the profile schema is unchanged; only the
  string emitted in the `suunnittelualat` IfcClassificationReference
  was renamed.
- **Project-level discipline metadata for Solibri auto-role detection**:
  when every rule in the active profile shares one domain, the IFC now
  embeds the discipline label in `IfcProject.LongName` plus an
  `IfcRelAssociatesClassification` linking the project to the
  `suunnittelualat` classification. Solibri picks the JÃ¤Ã¤hdytys role
  automatically on file open, no prompt.

**Added**:
- **Energy-spec Excel/CSV import** â€” convert_dxf accepts an optional
  energy-spec file path (CLI `--energy-specs`, GUI third file picker)
  with rows keyed by Koneikko + Laitetunnus. After POSITIO linkage
  every refrigeration device's row is looked up and the JÃ¤Ã¤hdytysteho /
  SÃ¤hkÃ¶teho / KylmÃ¤aine / Ilmavirta / Ã„Ã¤niteho / KÃ¤yttÃ¶lÃ¤mpÃ¶tila fields
  flow into FI_Tekninen automatically â€” no more hand-typing the energy
  list into the IFC. Column header matching is forgiving (`Q_kW`,
  `Cooling capacity [kW]`, `JÃ¤Ã¤hdytysteho [kW]` all map to the same
  canonical FI_Tekninen field). Adds openpyxl as runtime dep for .xlsx
  reading; .csv reading uses the stdlib.

**Changed**:
- **Outlier detection now adaptive (Tukey IQR)** â€” replaces the fixed
  100 m threshold that flagged whole models in wide buildings. Threshold
  becomes `max(50 m, Q3 + 3Â·IQR)` of the per-entity distance distribution,
  and the warning message is one-line short: `KYL-TIKASHYLLY handle 118A
  on 731 m irrallaan muusta mallista`. Detection can be disabled per-call
  via `convert_dxf(detect_outliers=False)`.
- **Refrigeration discipline is now `KYL` instead of `TATE`** in the
  default profile. The IFC `suunnittelualat` classification reference
  now reads `KYL` for kylmÃ¤laite/cooling items so Solibri's discipline
  view shows kylmÃ¤laitesuunnittelu, not generic Talotekniikka. Schema
  still accepts `TATE` for general LVI/HVAC mappings; only refrigeration
  rules switched.

**Added**:
- **In-app self-update**: GUI shows an amber banner at the top of the
  main window when a newer dxf2ifc release is on GitHub. "PÃ¤ivitÃ¤ nyt"
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
  `convert_dxf(outlier_threshold_mm=â€¦)`. Warnings include layer + DXF
  handle so the user can find the offending entity in AutoCAD.
- `EntityRecord.handle` field carries the DXF entity handle through the
  pipeline for diagnostics.

## v0.1.0-alpha â€” 2026-04-30

EnsimmÃ¤inen julkinen alpha-release. Build #29 (SHA `76A4F5CB606034E0`) â€”
sopiva demoamiseen / asiakaspilotteihin.

**MitÃ¤ toimii**:
- Suomalainen Talo2000 + RAVA-LVI / RAVA-TATE -luokitus, IFC 4 default
  (`--schema=ifc4x3` saatavilla)
- 6 RAVA3Pro-PSetia per IFC-tuote: `FI_Asennus` / `FI_Geometria` /
  `FI_Komponentti` / `FI_Tuote` / `FI_Tekninen` / `FI_Sijainti`
- POSITIO-blokin (`positiov2`) lukeminen â†’ automaattinen Koneikko + Laitetunnus
  -linkitys kylmÃ¤laitteille (â‰¤ 3 m sÃ¤de)
- ACIS-bodyjen tessellaatio headlessisti `accoreconsole.exe`:lla â€” ei
  AutoCAD-ikkuna-pop-uppia, ei recent-files-saastutusta, ei pywin32:ta
- Suunnittelualat-luokittelu (TATE/ARK) eksplisiittisesti â€” Solibri ei enÃ¤Ã¤
  pÃ¤Ã¤ttele ARK:ksi
- IfcSystem-ryhmittely (Refrigeration LT/MT, Drainage, Cable carriers,
  Refrigeration plant)
- ETRS-TM35FIN georeferensointi (`EPSG:3067`), geometria pysyy LOCAL
- PySide6-GUI: layer-preview, profiili-editori, taustasÃ¤ikeen konversio,
  CRS-dialogi
- `ifcopenshell.validate` + YTV/RAVA-sÃ¤Ã¤nnÃ¶t + Solibri-snapshot-verifiointi
- Windows-bundlattu `.exe` (PyInstaller, ~95 MB)

**Tunnetut rajoitukset**:
- `accoreconsole.exe` vaaditaan AutoCAD 2018+ -asennuksesta ACIS-bodyjen
  tessellaatioon. Jos puuttuu, 3DSOLID-pohjaiset elementit dropataan.
- GUI Profile Editor ei vielÃ¤ nÃ¤ytÃ¤ FI_*-kenttiÃ¤ (TOML-edit toimii kÃ¤sin).
- Curved 3DSOLID-bodyt (kaarevat pinnat) tessellataan FACETRES 0.1:llÃ¤ â€”
  silhuetti voi olla karkea, mut IFC pysyy hallittavan kokoisena.

## v0.1.0 â€” 2026-04-XX (TBD)

First public release. The MVP covers the full Talo2000 element set for
Finnish refrigeration / HVAC design, an IfcSystem-aware orchestrator and a
PySide6 desktop GUI with a profile editor.

### Added

- **CLI core** â€” `dxf2ifc convert input.dxf output.ifc` writes IFC 4 with
  millimetre units, a default Site â†’ Building â†’ Storey hierarchy and a
  per-rule Talo2000 classification reference (Plan A).
- **All 11 Talo2000 element types** â€” exterior / partition / glass walls
  (`IfcWall` STANDARD/PARTITIONING, codes 1241/1311/1312), floor / mezzanine /
  roof slabs (`IfcSlab` FLOOR/ROOF, codes 1221/1235/1236), exterior /
  interior / special doors (`IfcDoor`, codes 1243/1315/1316), windows
  (`IfcWindow` 1242), refrigeration & drain pipes (`IfcPipeSegment`
  REFRIGERATION/DRAINPIPE, codes 21xx), storage shelves (`IfcFurniture`
  1331), cable trays (`IfcCableCarrierSegment` CABLETRUNKINGSEGMENT, code
  2380), cold-room panels (`IfcBuildingElementProxy`, code 1352) and cooling
  equipment (`IfcEvaporator` / `IfcCondenser` / `IfcCompressor`, codes
  2510/2520/2530) (Plan B).
- **IfcSystem grouping** â€” refrigeration LT, refrigeration MT, drainage,
  cable carriers and refrigeration plant systems are auto-created from the
  active profile and members are wired through `IfcRelAssignsToGroup`
  (Plan C).
- **PySide6 GUI** (`dxf2ifc-gui`) â€” Inter / Space Grotesk / JetBrains Mono
  brand fonts, layered slate / amber / blue palette, file panel with Convert
  worker on a background thread, layer table preview, profile editor with
  Add/Edit/Remove/Save and a recent-files store backed by QSettings
  (Plan D).
- **Profile load/persist** â€” Profile editor's Load button reads any TOML
  profile, MainWindow remembers the last-used profile path between sessions.
- **Preview & log panel** â€” Right pane shows DXF entity counts per layer on
  open, then logs Convert progress (start, success, errors) with
  colour-coded JetBrains Mono lines.
- **Default profile** â€” TOML-based "KylmÃ¤laite Talo2000" profile with the
  layer / block conventions used by the AutoCAD LISP toolkit
  (`KYL-ULKOSEINA`, `KYL-VALISEINA`, `LT IMU`, `MT IMU`, `MT NESTE`,
  `KYL-VIEMARI*`, `KAAPELIHYLLY*`, `KYL-LEVYHYLLY`, `KYL-TIKASHYLLY`,
  `HOYRYSTIN`, `LAUHDUTIN`, `KOMPRESSORI`).
- **Windows .exe distribution** â€” PyInstaller bundle with full asset bundling
  (TOML profile, QSS, fonts, LICENSES), version resource, hidden imports
  for ifcopenshell + ezdxf + PySide6.QtSvg, and Win/Linux build workflows
  on GitHub Actions (Plan E in progress).

