# Changelog

All notable user-facing changes to dxf2ifc are documented here. The format
loosely follows [Keep a Changelog](https://keepachangelog.com/), and the
project uses semantic versioning.

## Unreleased

## v0.2.0-alpha11 — 2026-05-08 (kattava kylmälaitesuunnittelun tuki)

**Lisätty — out-of-the-box mappaus kaikelle kylmälaitesuunnitteluun**:

Default-profiili kasvoi 17:stä 49:ään sääntöön. Käyttäjä saa valmiin
mappauksen yleisimmille KYL-* layereille; oma profile voi karsia /
muokata layer-patterneja kun AutoCAD-konventiot eroavat.

**Builders-laajennus**:

- **`_COOLING_EQUIPMENT_CLASSES`** kattaa nyt myös `IfcChiller`,
  `IfcUnitaryEquipment`, `IfcCoil` — `add_cooling_equipment` rakentaa
  niille mesh-Brep-tuotteen kuten höyrystimille / lauhduttimille.
- **Uusi `add_distribution_element(ifc, m, *, ifc_class, parent_storey)`**
  — geneerinen rakentaja `IfcSensor`/`IfcValve`/`IfcPump`/
  `IfcWasteTerminal`/`IfcInterceptor`/`IfcDistributionBoard`/
  `IfcDuctSegment`/`IfcDuctFitting`/`IfcAirTerminal`-luokille.
  Funnel:oi `_add_mesh_product`-kautta samalla pattern:lla kuin
  `add_flow_controller`.
- Orchestrator-dispatchiin uusi haaroitus jokaisen
  `_DISTRIBUTION_ELEMENT_CLASSES`-luokan käsittelyyn.

**Profile-säännöt — Section 7 (uutta sisältöä)**:

| Kategoria | Layer-pattern -prefix | RAVA-koodit |
|---|---|---|
| **7a Kylmäkoneikkojen loput osat** | `KYL-CHILLER*` `KYL-VEDENJAAHDY*` `KYL-KYLMAVESIAS*` `KYL-KONEIKKO*` `KYL-VALIJAAHD*` `KYL-KOMPLAUH*` `KYL-KAASUNJAA*` `KYL-NESTEJAAHD*` `KYL-VARAAJA*` | T-LVI-01-01-003/004/005/016/019/024/027 + T-LVI-03-07-012 |
| **7b Kylmäkalusteet** | `KYL-PAKASTEKAAPPI*` `KYL-KYLMAKAAPPI*` `KYL-PAKASTEALLAS*` `KYL-PAKASTEARKKU*` `KYL-KYLMAALLAS*` `KYL-MARJAALLAS*` `KYL-PIKAJAA*` `KYL-OMAKONEELLI*` | T-LVI-01-01-999 (MUU) + ObjectType FI_Komponenttiin |
| **7c Kondenssiviemäri** | `KYL-KONDENSSI*` `KYL-LATTIAKAIV*` `KYL-VESILUKKO*` `KYL-PADOTUS*` | T-LVI-04-01-001 + T-LVI-05-01-001 + T-LVI-04-02-002/005, J-LVI-04-04 |
| **7d Säätö ja anturit** | `KYL-TERMO*` `KYL-LAMPOTILA*` `KYL-PAINEMITT*` `KYL-PINTAANT*` `KYL-MAGNV*` `KYL-PAISUNTAVENT*` `KYL-SULATUSVAST*` | T-TATE-01-01-099 / T-LVI-02 / T-LVI-01-01-999 |
| **7e Sähkökeskukset** | `KYL-KK-*` `KYL-RK-*` | T-TATE-01-01-099 |
| **7f Putkivarusteet** | `KYL-VENTTIILI*` `KYL-PUMPPU*` `KYL-PAISUNTASAILIO*` | T-LVI-02 |

**RAVA-LVI-TUOTEOSA-cache laajennettu**: 9 uutta T-LVI-01-01-koodia
(002, 006, 015, 016, 020, 021, 022, 026, 027, 999) jotta tarkka
luokitus on käytettävissä custom-profileissa.

**Tärkeä huomio käyttäjälle**: nämä ovat oletus-layer-patternit, eivät
pakottavia. Tee oma profile jos AutoCAD-konventiot eroavat — profile-
TOML on selkeä ja kommentoitu.

## v0.2.0-alpha10 — 2026-05-08 (DWG-tuki + toggle-checkboxit pois)

**Poistettu — pelkistetty käyttöliittymä ja core-pipeline**:

Lauri:n päätös: koska `--magicad-ifc`-merge on käytössä ja toimii,
DWG-input + sen toggle-checkboxit ovat tarpeettomia. Poistetaan
kokonaan ettei käyttäjä eksy hauraihin AutoCAD COM -reitteihin.

- **DWG-input poistettu**: `core/dwg_preconvert.py` (768 r) deletoitu,
  `tests/test_dwg_preconvert.py` deletoitu. Orchestratorin DWG-haara
  + `last_explode_meshes`-merge poistettu. Vain `.dxf` hyväksytään
  syötteenä.
- **`pywin32`-dependency poistettu** `pyproject.toml`:sta — ei enää
  Windows-only-vaadetta, asennettavissa myös macOS/Linux-Pythonille
  (vaikka käyttötapaus on edelleen Windows-keskeinen `accoreconsole`-
  riippuvuuden takia).
- **CLI `--no-preprocess-proxies`-argumentti poistettu**.
- **GUI:n "Pikakonversio (ohita 3D-tessellaatio)"-checkbox poistettu**
  — accoreconsole 3DSOLID-tessellaatio aina päällä.
- **GUI:n "MagiCAD/proxy-objektien geometria"-checkbox poistettu** —
  DXF-puolen MAGI*-luokat skipataan automaattisesti kun MagiCAD-IFC
  on annettu, muutoin niitä luetaan oletuksena.
- **`recent_files.quick_convert` + `recent_files.preprocess_proxies`
  -kentät poistettu** — vanhat asetukset pysyvät QSettings-rekisterissä
  mutta eivät enää vaikuta pipelineen.
- `convert_dxf`-funktion `preprocess_proxies`-kwargi poistettu;
  `convert_worker.run` -metodista `quick_convert` + `preprocess_proxies`
  -parametrit poistettu; `FilePanel.convert_requested`-signaali
  pelkistetty 7 → 5 parametriin.
- Dokumentaatio päivitetty: README, CLAUDE.md, PROGRESS.md,
  ARCHITECTURE.md, CLAUDE_TASKS.md, DWG_MAGICAD_PREPROCESSING.md
  (jälkimmäinen historic-näkökulmaan: mitä ei toimi ja miksi).

**Ei toiminnallisia muutoksia DXF-pipelineen** — kaikki KYL-LISP-osat,
3DFACE-aggregaatio, energiateho-Excel-merge ja MagiCAD-IFC-merge
toimivat identtisesti.

## v0.2.0-alpha9 — 2026-05-08 (RAVA viemäri-koodit valmiina cache:hen)

**Lisätty — RAVA-LVI viemärikoodit koodisto-cache:hen**:

Lauri:n pyynnöstä haettiin valmiiksi viemäri-puolen RAVA3Pro-luokitukset
jotta niille on tuki valmiina kun layer-mappausta laajennetaan. Itse
mappauspatterneja ei vielä lisätty — Lauri päättää myöhemmin mitkä
DXF-layerit ovat KYL-puolen kondenssiviemäri ja mitkä LVI-puolen
jv/sv/tuuletus.

- **`profiles/rava/lvi_tuoteosa.json`** laajennettu: kaikki T-LVI-04-*
  (viemäriputket + varusteet + eristeet) + T-LVI-05-01-* (kaivot) +
  T-LVI-01-03-* (pumppaamot).
- **`profiles/rava/lvi_jarjestelma.json`** laajennettu: kaikki
  J-LVI-04-* viemärijärjestelmät (jätevesi/sadevesi/tuuletus/kondenssi/
  rasva/öljy/erikois/salaoja/perusvesi/sekavesi/dialyysi + paineviemärit).
- **`docs/RAVA_DRAINAGE_CODES.md`** uusi pikamuisti — IFC-tyyppi-mappaus-
  ehdotukset + esimerkki profile-säännöstä + mitä tehdä seuraavaksi.

**Erityishuomio kylmälaitepuolelle**: höyrystinten sulatusvedet ja
muut kylmälaitepuolen kondenssit kuuluvat järjestelmäkoodiin
`J-LVI-04-04 Viemäri - kondenssi`. Tuoteosa-koodi runkoputkille on
edelleen `T-LVI-04-01-001 Viemäriputki`.

## v0.2.0-alpha8 — 2026-05-08 (hyllyjen FI_Tekninen siivous)

**Muutettu — `IfcCableCarrierSegment` (KYL-TIKASHYLLY / KYL-LEVYHYLLY)
FI_Tekninen-defaultit minimoitu**:

Lauri:n päätös 2026-05-08: hyllyille riittää matsku + pinnoite. Aiemmat
laajat tekniset kentät (paloluokka, paino, kuormitus, levypaksuus,
korroosioluokka, värit, valmistajan linkki) jäävät pois oletuksena.

- **`_FI_TEKNINEN_DEFAULTS["IfcCableCarrierSegment"]`** sisältää nyt
  vain `Materiaali` + `Pinnoite`.
- **`default_kylmalaite.toml`** -hyllysäännöt päivitetty:
  - Tikashylly: `Materiaali = "Teräs"`, `Pinnoite = "Kuumasinkitty"`
  - Levyhylly: `Materiaali = "Teräs"`, `Pinnoite = "Polyesterimaalattu"`
    (poistettu "Valkoinen RAL 9010" -värimerkintä)
- **`fi_tuote.valmistajan_linkki`** poistettu hyllyiltä — ei tartte
  laittaa linkkiä tuotteeseen oletuksena.

Käyttäjä voi lisätä mitä tahansa kenttää takaisin custom profile:n
kautta jos joku projekti vaatii esim. paloluokan tai kuormitustiedon.

## v0.2.0-alpha7 — 2026-05-07 (Excel-luenta: yhdistetyt otsikot + sektiot)

**Lisätty — RefDesign Teholuettelo-pohjien tuki**:

- **Slash-yhdistetyt otsikot**: ``KYLMÄ-/SÄHKÖ-/VASTUSTEHO [kW]`` -tyyppinen
  yhdistetty Excel-otsikko jaetaan kolmeksi sarakkeeksi ja jokainen
  token mätsätään erikseen kanonisiin kenttiin
  (Jäähdytysteho/Sähköteho/Vastusteho). Auto-teho-suffix kun yksikkö on
  ``[kW]`` / ``[W]``.
- **Sektio-otsikko-tunnistus**: rivi jossa yksi solu sisältää
  ``JK1``/``KK2``/``RK10``/``LA1`` -koodin (esim. ``"PAKASTEET JK1"``)
  asettaa koneikon kaikkiin seuraaviin riveihin. RefDesign-konvention
  mukaisesti yksi sektio yhdellä koneikolla, monta sektiota sheetissä.
- **Forward-fill**: kun rivin ``REV.``-sarake on tyhjä, koneikko
  periytyy edellisestä sektio-otsikosta. Ennen tätä useimmat data-
  rivit jäivät pois koska niiden REV. oli blank.
- **Robusti koneikko-validointi**: vapaa teksti REV.-sarakkeessa
  (``"Sähköurakoitsija tuo syötöt…"``) EI enää nouse koneikoksi —
  vain JKx/KKx/RKx/LAx-pattern hyväksytään, muutoin forward-fill.

**Testattu**: Lauri:n ``teholuettelo 2.xlsx`` (KM Kolari) — 39 spec
luetaan kahdesta koneikosta (JK1 + JK2), 3 tehoa per laite + jännite
+ jäähdyttävä vaikutus.

## v0.2.0-alpha6 — 2026-05-07 (levyhyllyn kyljet + peilatut INSERT:t)

**Korjattu — kaksi alpha5:n jäljelle jäänyttä bugia**:

1. **Levyhyllyn kyljet puuttuivat**: ohuet etu/takareunan LWPOLYLINE:t
   (1.2 mm leveät) extrudoituivat alpha5:ssä vain pohjalaatan paksuuteen
   (1.2 mm) eivätkä koko hyllyn korkeuteen. Heuristiikka: jos closed
   LWPOLYLINE:n lyhempi sivu ≤ 5 mm (= "ohut sivurima"), extrudoidaan
   block:n korkeimpaan top:iin sen sijaan että matchattaisiin lähimpään
   3DFACE:hen. Tämä saa levyhyllyn 4 kyljen kiertämään hyllyn pohjasta
   yläreunaan.

2. **Peilattu INSERT (yscale=-1) tuotti negative-Z-meshin**: LWPOLYLINE
   on 2D-entity OCS-tasolla; kun parent-INSERT:llä on yscale=-1 ezdxf
   palauttaa virtual-LWPOLYLINE:n extrusion=(0,0,-1):lla mutta jättää
   elevation:n ennalleen. Read elevation suoraan → block-level elev=10
   landed at world Z=-10. Korjaus: muunnetaan LWPOLYLINE:n vertex:t
   ja elevation OCS→WCS `entity.ocs().to_wcs(...)`-kutsulla — flip
   hoidetaan transparenttisesti.

**Lopputulos**: 8 hyllyä Lauri:n `Drawing2.dxf`:stä — 3 levyhyllyä
Z=0..67.8mm (kyljet, pohja, päätypalkit), 5 tikashyllyä Z=0..60mm
(sivupalkit + tikkapuut), kaikki yhdenmukaisesti world-koordinaatistossa
ilman peilaus-artefakteja.

## v0.2.0-alpha5 — 2026-05-07 (LWPOLYLINE-extrusio = oikeat solidit)

**Korjattu — alpha4:n hyllyt olivat pelkkiä yläpintoja, ei volyymiä**:

Alpha4 luki vain block:n 3DFACE:t → yksittäiset litteät pinnat
Solibrissa, ei oikeaa 3D-laatikkoa (vrt. Lauri:n AutoCAD-näkymä jossa
sivupalkit + tikkapuut + levyt ovat oikeita box:eja).

`_aggregate_3dface_from_insert` extrudoi nyt myös block:n closed
LWPOLYLINE:t niiden `elevation`:ista → vastaavaan 3DFACE:n Z-arvoon.
Top-Z päätellään: pienin 3DFACE jonka XY-bbox kattaa LWPOLYLINE:n
bbox:n ja jonka Z on LWPOLYLINE-elevation:n yläpuolella. Fallback
`base_z + 9 mm` jos pari ei löydy.

Tikashyllyn rakenne IFC:ssä alpha5:ssä:
- 2 sivupalkkia (closed LWPOLYLINE elev=0 → solid Z=0..60)
- N tikkapuuta (closed LWPOLYLINE elev=10 → solid Z=10..25)
- 3DFACE:t yläpinnat säilyvät (sileä yläpinta)

Levyhyllyn rakenne:
- Pohjalaatta + ohuet etu/takareunat (closed LWPOLYLINE elev=0)
- Päätypalkit (closed LWPOLYLINE elev=58.75)
- 3DFACE:t yläpinnat

**Testattu**: Lauri:n `Drawing2.dxf` → 8 IfcCableCarrierSegment, joiden
mesh sisältää nyt vertex/face-määrät 32-352 / 49-396 (vrt. alpha4:n
1-44 face:n yläpinta-only). Z-range 0..60mm tikashyllyille ja
0..67.8mm levyhyllyille — vastaa AutoCAD-näkymän mittoja.

## v0.2.0-alpha4 — 2026-05-07 (dynamic block hyllyt: 3DFACE-aggregaatio)

**Korjattu — KYL-LISP-hyllyjen uusi dynamic-block-formaatti**:

- Lauri:n hylly-LISP tuottaa nyt blockreferenssejä joiden anonyymi
  `*U*`-block-määritelmä sisältää 3DFACE-pintoja (aiemmin natiiveja
  3DSOLID-bodyja). Pipeline ei aiemmin lukenut näitä → hyllyt eivät
  tulleet IFC:hen.
- `dxf_reader._aggregate_3dface_from_insert(insert)` käyttää
  `INSERT.virtual_entities()`:tä joka soveltaa INSERT:in transformaation
  (insertion + rotation + scale) automaattisesti, jolloin block-tason
  3DFACE:t saadaan suoraan world space:hen ilman accoreconsole+STLOUT-
  tessellaatio-vaihetta.
- Vertex-deduplikointi 4-desimaalin tarkkuudella → adjacent face:t
  jakavat vertex:t (Solibrissa pinta yhtenäinen).
- **Ei AutoCAD COM:ia, ei accoreconsole:a, ei STLOUT:ia** — puhdas
  ezdxf:n natiivi luenta.
- Fallback BlockInstance:hin säilyy block:eille joissa ei ole 3DFACE:ja
  (POSITIO-numerointiblokit, label-blokit jne).

**Testattu**: 8 hyllyä Lauri:n `Drawing2.dxf`:stä (5 tikashyllyä +
3 levyhyllyä) tulevat IFC:hen mesh-pohjaisesti, oikeilla
`IfcCableCarrierSegment` / `CABLELADDERSEGMENT` / `CABLETRAYSEGMENT`-
luokituksilla. 4 uutta yksikkötestiä syntetisoidulla DXF:llä.

## v0.2.0-alpha3 — 2026-05-07 (MagiCAD-IFC merge)

**Lisätty — MAGIIFCEXPORT-tuotetun IFC:n yhdistäminen master-IFC:hen**:

- **Uusi GUI-filepicker "MagiCAD-IFC"** (valinnainen). Kun annettu, dxf2ifc
  yhdistää sen tuotteet master-IFC:hen ensimmäisen `IfcBuildingStorey`:n alle.
- **Uusi CLI-argumentti `--magicad-ifc PATH`** vastaavalla logiikalla.
- **Uusi `dxf2ifc.core.ifc_merger`-moduuli** käyttää
  `ifcopenshell.api.project.append_asset`:ia kopioimaan `IfcProduct`-johdannaiset
  MagiCAD-IFC:stä master-IFC:hen yhdessä geometric context:ien, materiaalien,
  styles:ien ja propertyset:ien kanssa. `IfcSite` / `IfcBuilding` / `IfcBuildingStorey`
  / `IfcSpace` ohitetaan — master-IFC:n hierarkia pysyy kanonisena.
- **Spatial container linkitys**: jokainen yhdistetty tuote sidotaan master-IFC:n
  ensimmäiseen `IfcBuildingStorey`:hen `IfcRelContainedInSpatialStructure`:llä.
- **DXF-puolen MagiCAD-skip kun MagiCAD-IFC annettu**: `read_dxf` saa
  `skip_magicad`-lipun joka ohittaa `MAGI*`-natiivit luokat ja
  `ACAD_PROXY_ENTITY`-tietueet jotta DXF-pohjainen mesh-tessellaatio ei
  duplikoitu MagiCAD-IFC:n semanttisten tuotteiden kanssa.

**Käyttötapaus**: kollegan FULL-MagiCAD-lisensoidun koneen `-MAGIIFCCD`-komento
(command-line / dialog-vapaa variantti `MAGIIFCEXPORT`-perheestä) tuottaa
korkeatasoisen MagiCAD-IFC:n (oikeat `IfcDuctSegment` / `IfcAirTerminal` /
MagiCAD-PSet:t). Sen ja Lauri:n KYL-LISP-DXF:n yhdistäminen yhdeksi
master-IFC:ksi onnistuu nyt yhdellä konversio-ajolla — DXF-syötteellä
pipeline ei tarvitse AutoCAD COM:ia eikä `acad.exe`:tä lainkaan,
ainoastaan `accoreconsole.exe`:n 3DSOLID-tessellaatioon.

**Testit**: 7 uutta merger-testiä + 2 uutta GUI file_panel -testiä.
Yhteensä 530 testiä passes (1 skipped, 3 pre-existing failures että master:in
puolella).

## v0.2.0-alpha2 — 2026-05-07 (POC v4 -saagan tulos)

**Muutettu — automaattinen MAGIEXPLODE+EXPLODE-keystroke**:

- **DWG-pipeline lähettää MagiCAD-räjäytyksen** Python-puolen `SendCommand`-
  tekstillä (`MAGIEXPLODE\nALL\n\n` + `EXPLODE\nALL\n\n`) AutoCAD:in
  command-lineen — sama tapa kuin oikea näppäimistö. Tämä toimii
  render-only Object Enabler -tilassa silloin kun aiempi LISP-tason
  `(command "MAGIEXPLODE" …)` rejekoitiin "Invalid selection":lla.
- **AutoCAD näkyy konversion ajan** (Visible=True, ei enää piilossa) jotta
  käyttäjä näkee MagiCAD-popup:t ja voi klikata OK. Yksi-kaksi popup:ia
  per ajo, ei estoa.
- **DXFOUT käyttää SendCommand-keystrokeja** (`FILEDIA 0 / DXFOUT path /
  Enter / 8 / FILEDIA 1`) — luotettavampi kuin `vla-saveas` tai
  `doc.SaveAs(path, fmt)` jotka palauttivat `Invalid argument` AutoCAD
  2025:ssä.
- **DWG-kopio temp-polkuun** `shutil.copy2`:lla ennen avaamista —
  alkuperäinen DWG ei mutaatu vaikka MAGIEXPLODE+EXPLODE ajetaan.
- **Sysvar SAVE+RESTORE** (FILEDIA, CMDDIA, FACETRES, EXPERT) — käyttäjän
  AutoCAD-asetukset palautuvat aina, myös crash-tilanteessa.
- **AutoCAD-ikkunan koon säätö POISTETTU** — POC v3.x:n
  `WindowState/WindowLeft/Top/Width/Height` -mutaatiot mutaroivat
  Lauri:n AutoCAD-profile:in command bar -kokoa. v0.2.0-alpha2 ei kosketa
  ikkunaa. Aiemmin tallentunut profile-tila pitää resetoida käsin
  AutoCAD:ssa: `OPTIONS` → Profiles → Reset.

**Lisätty — diagnostiikka**:

- Progress-loki näyttää: `DXF-luettu: N polyface/3DFACE/MESH + M ACIS`,
  `Mesh-layerit (top 5)`, `Profile-mappaus: K mesh-pohjaisia`,
  `Mesh→IFC-tyypit (top 5)` — diagnoosin nopeampi tunnistus.
- LISP-loki:ssa: `MAGI_BEFORE/AFTER`, `INSERTS_REMAINING`,
  `FINAL_3DSOLIDS`, `POLYFACE_AFTER`.

**Korjattu — orchestrator**:

- `BlockInstance` skipataan `IfcBuildingElementProxy`,
  `IfcCooler/Condenser/Compressor`, `IfcTank`, `IfcFlowController`,
  `IfcPipeSegment`, `IfcFurniture`-haaroissa — ei enää
  `TypeError: expects MeshGeometry, got BlockInstance` -kaatumista.
- `IfcPipeSegment` MeshGeometry-tapauksessa kirjoitetaan
  `IfcTriangulatedFaceSet`-mesh:nä `_add_mesh_product`-helperin kautta —
  MagiCAD-pipet eivät enää droppaudu pipelineesta.

**Tunnetut rajoitukset**:

- **Render-only Object Enabler** (Lauri:n kone) ei tuota 3D-pintoja
  MagiCAD-objekteille edes manuaalisella MAGIEXPLODE+EXPLODE:lla.
  Tupla-räjäytys tuottaa 2D-polylineja jotka eivät käännyksellä saada
  3DSOLID:eiksi. **Vain Lauri:n KYL-LISP-osat tulevat IFC:hen**.
- **FULL MagiCAD-lisenssin** koneella (esim. kollegan kone) sama
  pipeline tuottaa todennäköisesti oikeat MagiCAD-pinnat IFC:hen ilman
  koodimuutoksia — MagiCAD-ARX käsittelee EXPLODE:n eri tavalla.
- Polyline-extrusion-strategia (POC v5) jatkossa render-only-tilassa.

## v0.2.0-alpha1 — 2026-05-06

**Lisätty — DWG-input + MagiCAD-tuki**:

- **`.dwg`-tiedostot hyväksytään input:ina** — `dxf2ifc convert input.dwg
  output.ifc` toimii samalla tavalla kuin DXF. GUI Browse-dialog filter
  laajennettu `*.dxf;*.dwg`.
- **MagiCAD-objektien EXPLODE FULL-MagiCAD-koneella**: DWG-input:lle
  käynnistetään AutoCAD piilotettuna (`acad.exe` Visible=False
  pywin32-COM:lla). MagiCAD ARX latautuu autoload-rekisteristä, ja
  `(command "_.EXPLODE" ent)` tuottaa 3DSOLID-lapsia jotka STLOUT
  tessellöi STL:ksi. Välitilanne-DXF kirjoitetaan DXFOUT:lla, jonka
  jälkeen normaali pipeline (ezdxf + accoreconsole + IFC-tuotanto)
  jatkaa siitä.
- **Adaptiivinen käyttäytyminen**: Render-only Object Enabler -koneella
  EXPLODE epäonnistuu hiljaa → MagiCAD-osat jäävät pois IFC:stä mutta
  Lauri:n omat KYL-LISP-piirrokset toimivat ennallaan. FULL-MagiCAD-
  koneella sama koodi tuottaa täydellisen 3D-geometrian.
- **Singleton hidden AutoCAD**: COM-instanssi pidetään muistissa
  konversioiden välillä. Cold-start ~14 s ekan kerran, seuraavat
  ~3 s/konversio. Spike v3 vahvisti: ikkuna ei näy missään vaiheessa.
- **Throwaway profile** `dxf2ifc_headless`: estää RECENTFILES-, FILEDIA-,
  CMDDIA-, SDI-sysvar-saastumisen käyttäjän omasta AutoCAD-profiilista.

**Riippuvuudet**:

- `pywin32>=305` (Windows-only, sys_platform=='win32'). DWG-input vaatii
  AutoCAD:in asennetuksi. DXF-input ei vaadi pywin32-tukea.

**Sisäinen**:

- Uusi moduuli `core/dwg_preconvert.py` (~270 riviä) — singleton COM
  session, AutoLISP-pohjainen EXPLODE+STLOUT+DXFOUT, atexit-cleanup.
- Poistettu `core/proxy_preprocessing.py` (v0.1.19-yritys
  accoreconsole-EXPLODE-polulle, todistettu mahdottomaksi: accoreconsole
  ei lataa ARX-moduuleja Autodesk-rajoitteen vuoksi).
- Orchestrator detect:taa `.dwg`-suffix:in ja kutsuu DWG-pre-conversion:in
  ennen muuta pipelineä.
- Ei regressiota DXF-input:lle: 4001_1krs.dxf tuottaa täsmälleen
  v0.1.18-baseline:n product-counts (9 + 12 + 15).
- 512/512 pytest passes (+3 uutta `test_dwg_preconvert.py`-testiä).

**Rajoitteet**:

- MagiCAD-osien täysi 3D-geometria vaatii FULL MagiCAD-lisenssin
  asennetuksi konversiokoneella. Render-only Object Enabler ei riitä —
  Object Enabler ei tarjoa Explode-toiminnallisuutta MAGI*-luokille.
  Empiirisesti vahvistettu 4 spike-iteraatiossa.
- Rekisteröidyt accoreconsole-asetukset säilyvät (RECENTFILES jne.) vain
  oman profiilin ulkopuolella `dxf2ifc_headless`-profiilissa.

## v0.1.19-alpha1 — 2026-05-06

**Lisätty — MagiCAD/proxy-objektien geometria**:

- **Avoimet polyline:t** (LWPOLYLINE/POLYLINE ilman ``closed``-flagia)
  hyväksytään ``dxf_reader``-tasolla LineGeometry-segmentteinä — yksi
  per peräkkäinen vertex-pari. Ratkaisee MagiCAD ACAD_PROXY_ENTITY-
  putkien (KYL-JV1) + detail-viivojen näkyvyyden, jotka v0.1.18:ssa
  putosivat hiljaa pois ``is_closed=True``-tarkistuksessa.
- **Uusi moduuli** ``core/proxy_preprocessing.py``: jokaiselle
  ACAD_PROXY_ENTITYlle joko bbox-cuboid-fallback (kun ezdxf:n
  proxy_graphic-parser ei pysty purkamaan eikä Object Enableria ole)
  tai täydellinen accoreconsole-EXPLODE+STLOUT (kun MagiCAD:in ilmainen
  Object Enabler on asennettu).
- **Object Enabler -tunnistus**: Windowsin rekisterihakemisto
  ``HKLM\\SOFTWARE\\Autodesk\\ObjectDBX`` etsitään tunnetuille MagiCAD-
  luokille. Jos puuttuu, progress-logiin tulee tarkka asennusohje:
  https://www.magicad.com/object-enabler/
- **Profile-säännöt** ``default_kylmalaite.toml``:
  - KYL-JV1 → IfcPipeSegment (CHILLEDWATER)
  - KYL-JV1-LAITE → IfcFlowController (USERDEFINED)
  - KYL-KONDENSSIASTIAT → IfcTank (BASIN)
- **Uudet builders**: ``add_tank``, ``add_flow_controller`` (mesh-
  pohjaisia, hyödyntävät ``_add_mesh_product``-helperä).
- **CLI flag** ``--no-preprocess-proxies`` opt-out:in tueksi.
- **GUI checkbox** "MagiCAD/proxy-objektien geometria" oletus päällä,
  persistoituu ``QSettings:Mcrauli/dxf2ifc/preprocess_proxies``.
  Pikakonversio-tila kytkee sen pois automaattisesti.

**Verifioitu**:

- ``4001_1krs.dxf`` (ei MagiCAD:ia): ei regressiota (9 + 12 + 15 entityä
  kuten v0.1.18:ssa).
- ``magicad_1krs.dxf`` (145 ACAD_PROXY_ENTITYä): 39 IfcPipeSegment
  (KYL-JV1) + 13 IfcBuildingElementProxy (MUUT_OSAT) + 3
  IfcCableCarrierSegment näkyy IFC:ssä. KYL-JV1-LAITE (36) ja
  KYL-KONDENSSIASTIAT (18) tulevat näkyviin sen jälkeen kun Object
  Enabler on asennettu.

**Sisäinen**:

- ``_record_from_entity`` palauttaa nyt ``list[EntityRecord]`` (0/1/N)
  yksittäisen ``EntityRecord | None`` sijaan — yksinkertaistaa
  segment-fan-out-logiikkaa proxy-graphics:eille.
- ``add_building_element_proxy`` hyväksyy nyt sekä PolygonGeometryn
  (suljettu paneeli) että MeshGeometryn (faceted Brep proxy-cuboid-
  fallbackista).
- Open-polyline-segmentit IfcBuildingElementProxy / IfcTank /
  IfcFlowController -säännöille hylätään hiljaa orchestrator-
  dispatchissä — ne ovat MagiCAD:in 2D-detail-renderiä, ei pää-
  geometriaa.
- 516 / 516 pytest passes (+10 uutta v0.1.18:n 502:sta).

## v0.1.18-alpha1 — 2026-05-06

**Lisätty**:

- **Checkbox "Lisää 1.krs absoluuttinen korko"** ennen korko-kenttää.
  Päällä (default): nykyinen offset-käyttäytyminen — DXF:n Z=0 tulkitaan
  1.krs lattiaksi ja annettu korko lisätään jokaiseen
  IfcBuildingStorey.Elevation- ja elementti-Z-arvoon. Pois: DXF:n
  Z-koordinaatit menevät IFC:hen sellaisinaan, ei mitään offsettia.
  Tila persistoituu QSettings:iin (``Mcrauli/dxf2ifc/
  floor_elevation_enabled``), eli kerran valittu työtapa pysyy
  käynnistyskerrasta toiseen. Sopii suunnittelijalle joka piirtää
  AutoCADissa suoraan absoluuttisilla koordinaateilla — ei tarvitse
  muistaa nollata kenttää joka konversiolla.

## v0.1.17-alpha1 — 2026-05-06

**Korjattu (KRIITTINEN)**:

- **Tikashyllyt, levyhyllyt ja höyrystimet eivät enää puutu IFC:stä.**
  v0.1.14:n LWPOLYLINE→CONVTOSOLID-laajennus puski LISP-bodyn 1818 → 1868
  merkkiin, joka tempdir-polkujen substituution jälkeen ylitti
  ``accoreconsole.exe``:n hard-cap 2048-merkin .scr-rivipuskurin (~2065
  merkkiä). Form katkesi kesken Phase 1:n, parser jäi ``((_>``
  multi-paren-prompt:iin ikuisesti, **0 STL-tiedostoa kirjoitettiin** ja
  3DSOLID-bodyt tippuivat hiljaa pois. Korjaus: `_LISP_BODY` jaettu
  neljäksi top-level-formiksi (SETUP / PHASE1 / PHASE2 / CLEANUP),
  jokainen oma rivi ``.scr``:ssä, setq-globaalit pysyvät yli rivien.
  Verifioitu Lauri:n ``4001_1krs.dxf``:llä: 9 KYL-TIKASHYLLY +
  12 KYL-LEVYHYLLY + 15 KYL-HÖYRYSTIMET → IFC:hen täysillä
  IfcFacetedBrep-meshillä. Bisektio: 2048 OK, 2092 jumissa.

## v0.1.16-alpha1 — 2026-05-05

**Korjattu**:

- **MAGIFLOORORIGO + muut MagiCAD:in non-graphical proxyt** eivät enää
  kaatu konversiota. Aiemmin yritys lukea ``entity.dxf.layer`` tällaisesta
  control-objektista raise-asi ``Invalid DXF attribute``-virheen ja koko
  read-vaihe pysähtyi. Nyt lukijassa on defensive try/except jokaisen
  entity:n attribuutti-luvun ympärillä — ei-graafisten entityjen kanssa
  silent skip, todelliset geometria-entityt käsitellään normaalisti.

**Lisätty**:

- **GUI-checkbox "Pikakonversio (ohita 3D-tessellaatio)"** Convert-napin
  yläpuolelle. Kun valittu, accoreconsole-vaihe (joka tessellöi
  3DSOLID-bodyt) ohitetaan kokonaan. Käytännössä **5–10× nopeampi**
  raskaalle DXF:lle — käytä kun haluat nopean tarkistuksen että
  layer-mappaus + 2D-geometria mappautuu oikein. Valinta persistoituu
  QSettings:iin (``Mcrauli/dxf2ifc/quick_convert``) ja täyttyy
  automaattisesti seuraavalla käynnistyksellä.

**Sisäinen**:

- 496 passed, 1 skipped, 1 deselected.

## v0.1.15-alpha1 — 2026-05-05

**Lisätty**:

- **MagiCAD-proxy-objektien luku DXF:stä**: ``ACAD_PROXY_ENTITY``-tyyppiset
  entityt (AutoCADin tapa tallentaa MagiCAD-objektien näytettävä geometria)
  räjähtävät nyt ezdxf:n ``__virtual_entities__()``-API:n kautta
  primitiiveiksi (LINE, LWPOLYLINE, POLYLINE, MESH) jotka prosessoidaan
  saman dispatch:n läpi kuin natiivit DXF-entityt. Aiemmin MagiCAD-piirretyt
  putket / venttiilit / laitteet katosivat hiljaa konversiossa. Layer:n
  perii proxyn alkuperäinen authored layer kun virtual-entity ei sitä
  itse kantaa, joten profile-mappaus toimii tutuilla layer-pattern:eillä.
- **POLYLINE (closed)** -tuki, jota MagiCAD-proxy graphics tyypillisesti
  käyttää LWPOLYLINE:n sijaan vanhemmissa DXF-formaateissa.

**Sisäinen**:

- ``dxf_reader.py``: dispatch-loop refaktoroitu ``_record_from_entity``
  -helperiksi joka tukee ``layer_override`` + ``handle_override`` -optoreja
  proxy-rekursiota varten.
- 496 passed, 1 skipped, 1 deselected (test_extract_acis_meshes_round_trip
  on edelleen Lauri:n DXF + accoreconsole -ympäristötesti).

## v0.1.14-alpha1 — 2026-05-05

**Lisätty**:

- **MagiCAD-yhteensopivuus laajennettu**: höyrystimet, lauhduttimet ja
  kompressorit (``IfcEvaporator`` / ``IfcCondenser`` / ``IfcCompressor``)
  saavat nyt Type-objektit + ``Pset_*TypeCommon``-PSetin, joten MagiCAD:n
  "Convert to MagiCAD object" tunnistaa myös koneikot. Aiemmin tämä toimi
  vain hyllyille ja putkille.
- **MUUT_OSAT-layer** lisätty default-profiiliin: yleiset kylmälaitteen
  osat (kannakkeet, tukirakenteet, venttiilit, anturit) joilla ei ole
  spesifiä IFC-tyyppiä. Mappaus → ``IfcBuildingElementProxy`` +
  ``USERDEFINED`` + ``ElementType="MUUT_OSAT"`` +
  ``Pset_BuildingElementProxyTypeCommon`` Reference="MUUT_OSAT".

**Sisäinen**:

- 490 passed, 1 skipped, 1 deselected (test_extract_acis_meshes_round_trip
  on lokaali ympäristötesti joka tarvitsee Lauri'n DXF + accoreconsole;
  ei regression v0.1.14-koodin lisäyksistä).

## v0.1.13-alpha1 — 2026-05-05

**Lisätty**:
- **IFC-värit**: kaikki konvertoidut elementit saavat AutoCAD ACI 175
  -värin (slate-purppura) jaetun ``IfcSurfaceStyle`` + ``IfcStyledItem``
  -ketjun kautta. Refrigeration-malli lukeutuu visuaalisesti yhtenäisenä
  Solibrissä ja MagiCAD:ssä.
- **MagiCAD-yhteensopivuus**: ``IfcCableCarrierSegmentType`` ja
  ``IfcPipeSegmentType`` saavat nyt ``Pset_*TypeCommon``-PSetin
  Reference-kentällä — ilman tätä MagiCAD:n "Convert to MagiCAD object"
  -komento ei tunnistanut LEVYHYLLY-elementtejä.
- **DOMAIN-valikkoon KYL** Profile Editorin Edit-dialogissa
  (oli vain ARK + TATE), KYL on uusi default kun "Add rule".
- **RAVA-koodien vapaateksti**: Edit-dialogin LVI / TALOTEKNIIKKA-combot
  ovat nyt editable — voit kirjoittaa oman koodin jota ei ole
  bundlatussa codesetissä.

**Korjattu**:
- **Layer-tableisiin selvempi otsikko**: "Domain" → **"Luokitus"**
  (sarake näyttää codeset-nimen kuten RAVA-LVI, ei domain-arvoa).
- **Installer luo työpöytäkuvakkeen** oletuksena (oli opt-in).
  Käyttäjä voi yhä disabloida asennuksen aikana.
- **Sovelluksen värit pysyvät tummina** myös light-themalla Windows
  -koneilla. Style.qss kattaa nyt QTextEdit, QComboBox-popup, QSpinBox,
  QDialog, QGroupBox, QToolTip ja scrollbar-elementit, jotka aiemmin
  fallbackasivat OS-defaulttiin (valkoinen pohja).

**Sisäinen**:
- 491 passed, 1 skipped (4 olemassa olevaa rule_dialog-testiä päivitetty
  uuteen KYL-default-tilaan).

## v0.1.12-alpha1 — 2026-05-05

**Fixed**:

- **1.krs korko vaikuttaa nyt myös elementtien Z-koordinaattiin**: v0.1.11
  siirsi vain ``IfcBuildingStorey.Elevation``-arvoa, mutta itse hyllyt /
  putket / höyrystimet jäivät DXF:n Z-tasolle. Syy: builders kirjoittavat
  ``IfcLocalPlacement``-matriisin elementin omasta anchor-Z:stä, eikä
  storey-tason siirto kaskadoidu ``edit_object_placement``-API:n kautta.
  Korjaus: orchestrator siirtää nyt jokaisen ``MappedEntity.geometry``
  Z-komponentteja ``floor_elevation_mm``-verran ENNEN builders-vaihetta.
  Nyt 1.krs korolla 12000 mm hylly Z=3000 → IFC absoluuttinen Z=15000
  (storey 12000 + storey-relative 3000), kuten oletettua.

## v0.1.11-alpha1 — 2026-05-05

**Added**:
- **1.krs korko -input** GUI:hin Excel-rivin alle ja CLI:lle
  ``--floor-elevation MM``. AutoCAD piirretään 1.krs Z=0:lla; tämä arvo
  lisätään jokaiseen ``IfcBuildingStorey.Elevation``-arvoon, jotta
  rakennus tulee absoluuttiseen korkoon koko projektin
  koordinaatistossa (esim. 1.krs korko 12000 mm + hylly Z=3000 mm
  → IFC:ssä Z=15000 mm). Arvo persistoituu QSettings:iin (``Mcrauli/
  dxf2ifc/floor_elevation_mm``) ja täyttyy automaattisesti seuraavalla
  käynnistyksellä.
- **Versionumero status-rivin oikeassa reunassa**: ohjelman versio
  näkyy jatkuvasti ilman About-dialogin avaamista.

**Removed**:
- **CRS / ETRS-TM35FIN georeferensointi** kokonaisuudessaan: pois
  Profile-skeemasta, GUI:n "Set CRS…" -dialogi, CLI:n
  ``--eastings`` / ``--northings`` / ``--orthogonal-height``
  -argumentit, ``IfcProjectedCRS`` + ``IfcMapConversion``
  -kirjoitus, ``--validate`` ``expect_crs``-kytkin sekä
  Solibri-rule-set:n CRS-coverage-rule. Käyttäjäkohtainen palaute:
  feature ei tuonut työnkulkuun lisäarvoa, ja 1.krs korko-input
  vastaa todelliseen tarpeeseen rakennuksen sijoittamisesta
  absoluuttiseen koordinaatistoon ilman GIS-monimutkaisuutta.

## v0.1.10-alpha1 — 2026-05-04

**Fixed**:
- **Itsepäivityksen "Failed to start embedded python interpreter" -virhe**:
  uusi exe käynnistetään nyt **3 sekunnin viiveellä** piilotetun
  PowerShell-launcherin kautta. Antaa vanhan prosessin vapauttaa
  ``.old``-exen handle ja Windows Defenderin viimeistellä reaaliaikaskannauksen
  ennen kuin uuden exen PyInstaller-bootloader yrittää purkaa tiedostoja
  ``%TEMP%``:iin. Aiemmin OLD ``os._exit(0)`` ja NEW spawn osuivat
  millisekuntien päähän toisistaan ja törmäsivät satunnaisesti.
- **SHA-256-verifiointi ladattuun assettiin**: päivittäjä hakee nyt
  GitHub Releases ``.sha256``-sidecarin ja vertaa downloadatun exen
  hashin streamatessa. Mismatch → ``.part``-tiedosto poistetaan ja
  vaihto keskeytetään ennen swapia. Estää korruptoituneen / katkenneen
  latauksen pääsyn käynnistettäväksi, mikä on yksi mahdollinen
  bootloader-virheen syy.

**Removed**:
- **Help-menun "Käyttöohjeet (selain)" -action**: About-dialogissa on
  nyt linkki samaan käyttöohjeeseen, joten erillinen menu-action oli
  duplikaatti.

## v0.1.9-alpha1 — 2026-05-04

**Changed**:
- **About-dialogi**: poistettu "MIT-licensed." -rivi (LICENSE-tiedosto
  repon juuressa pysyy lain mukaan ennallaan). Tilalle linkki
  käyttöohjeisiin osoitteessa
  <https://mcrauli.github.io/autocad-lisp-ohjeet/dxf2ifc.html>.
- **Help → Käyttöohjeet (selain)**: uusi menu-action joka avaa
  käyttöohjeet selaimessa (F1-pikanäppäin). About siirtyi separatorin
  alapuolelle.
- **Binary copyright -metatieto** lyhennetty: `(c) 2026 Lauri Rekola`
  (poistettu ". MIT licence." -loppu installerin VersionInfoCopyright-
  ja exe:n LegalCopyright-kentistä).

## v0.1.8-alpha1 — 2026-05-04

**Changed**:
- **Brand metadata**: poistettu "Radika Oy" -maininta installerista, exe:n
  Win32-resource-blokista ja LICENSE-tiedostosta. Publisher / CompanyName
  / LegalCopyright / Copyright on nyt **"Lauri Rekola"** ilman
  yritysmainintaa — dxf2ifc on Lauri'n henkilökohtainen projekti, ei
  työnantaja-integroitu.
- **Sisäiset Windows-tunnisteet** vaihdettu `Mcrauli`-namespaceen:
  - AppUserModelID `Radika.dxf2ifc.kylmalaite.1` → `Mcrauli.dxf2ifc.kylmalaite.1`
  - QSettings-organisaatio `Radika` → `Mcrauli` (recent-files-rekisteri
    siirtyy `HKCU\Software\Mcrauli\dxf2ifc`-polkuun, vanhat
    recent-files-listaukset eivät säily yli päivityksen).

Toiminnallisuus identtinen v0.1.7-alpha1:n kanssa.

## v0.1.7-alpha1 — 2026-05-04

**Added**:
- **MEKA-spec FI_Tekninen + FI_Tuote KYL-TIKASHYLLY ja KYL-LEVYHYLLY -säännöille**.
  Default-profiili kirjoittaa nyt nämä Solibrin Asennushyllyjärjestelmälle:
  - **Tikashylly** (KS20-500 K L=6000 PG): Materiaali Teräs, Pinnoite
    Kuumasinkitty (EN 10346), Korroosioluokka C1-C2,
    Paloturvallisuusluokka E90, Levypaksuus 0,75 mm, Paino 10,68 kg/6 m.
    FI_Tuote: Valmistaja MEKA + linkki tuotesivulle.
  - **Levyhylly** (KRA-60-500 L=3000 M): Materiaali Teräs, Pinnoite
    Valkoinen RAL 9010 polyesterimaali, Korroosioluokka C1-C2,
    Paloturvallisuusluokka E90, Levypaksuus 1,25 mm, Paino 19,09 kg/3 m.
    FI_Tuote: Valmistaja MEKA + linkki tuotesivulle.
- **`_FI_TEKNINEN_DEFAULTS["IfcCableCarrierSegment"]`** laajennettu:
  Materiaali, Pinnoite, Korroosioluokka, Paloturvallisuusluokka,
  Levypaksuus, Kuormitus, Paino. (Nimi `Korroosiosuojaus` →
  `Korroosioluokka` RAVA-konvention mukaan.)

Käyttäjä voi ylikirjoittaa fi_tekninen / fi_tuote oman profiilin TOML:n
kautta jos käytössä on eri valmistaja tai mitoitus.

## v0.1.6-alpha1 — 2026-05-04

**Added**:
- **Inno Setup -installeri** (`dxf2ifc-Setup-0.1.6a1.exe`): oikea Windows-
  asennusohjelma jonka kautta sovellus saa Start-menu -merkinnän, Apps &
  Features -uninstallerin ja version-info-resurssit. Asennus per-user
  `%LOCALAPPDATA%\Programs\dxf2ifc`:iin, ei UAC-promptia. SmartScreen-
  kitka pienempi kuin paljaalla `.exe`:llä koska installer näyttää
  oikealta Windows-asennusohjelmalta.
- Stable AppId GUID upgrade/uninstall-identiteettiä varten — sama GUID
  läpi versioiden, joten installer päivittää aiemman dxf2ifc-asennuksen
  oikein.
- Suomi + englanti -kielet wizardissa.
- `lzma2/max` -kompressio: installer ~40-60% pienempi kuin paljas exe.

Raw exe (`dxf2ifc-0.1.6a1.exe`) toimitetaan edelleen rinnalla — sitä
käyttävä auto-update-banneri jatkaa toimintaansa.

## v0.1.5-alpha1 — 2026-05-04

**Fixed (CRITICAL — v0.1.4 was broken)**:
- v0.1.4-alpha1:n `cleanup_stale_meipass_dirs`-funktio poisti vahingossa
  ajossa olevan exen oman `_MEI***`-temp-kansion → seuraava käynnistys
  failasi `[Errno 2] No such file or directory: ...\_MEI*\base_library.zip`
  -virheellä. Vika oli Windows-polkujen short-form (`LAURIR~1`) vs
  long-form (`LauriRekola`) -vertailussa: `os.path.normcase` ei
  yhdenmukaista niitä, joten oma _MEI tunnistettiin "vanhentuneeksi"
  ja siivottiin pois.
- Korjaus: cleanup-funktio poistettu kokonaan. Windows siivoaa %TEMP%:n
  ajan myötä — meidän omasta riskinotosta ei ole hyötyä joka oikeuttaisi
  bugin riskin.

> Jos sun nykyinen exe on rikki (ei käynnisty), lataa **v0.1.5-alpha1
> manuaalisesti** GitHubista ja korvaa nykyinen — itsepäivitys ei
> luonnollisesti toimi rikkinäisestä prosessista.

## v0.1.4-alpha1 — 2026-05-04

**Fixed**:
- GUI:n alaotsikko luki "AutoCAD DXF → IFC 4 with Talo2000 classification"
  vaikka projekti on alusta asti ollut RAVA3Pro-pohjainen kylmäsuunnittelu.
  Korjattu sekä GUI-kuvateksti, About-dialogi, CLI `--help`-kuvaus ja
  pyproject.toml description-kenttä mainitsemaan **RAVA3Pro** ja
  **kylmäsuunnittelu**. Talo2000 säilyy tekstissä paikoissa joissa se on
  teknisesti oikein (ARK-domain-validointisäännöt, profiili-skeeman
  `talo2000_code`-kenttä).

## v0.1.3-alpha1 — 2026-05-04

**Fixed**:
- **"Failed to remove temporary directory" -popup itsepäivityksen jälkeen**.
  PyInstaller-bootloader yrittää siivota `_MEI***`-temp-kansion vanhasta
  exestä swap-hetkellä mutta tiedostot ovat lukittuna kunnes Windows on
  ehtinyt vapauttaa ne. Itsepäivitysflow käyttää nyt `os._exit(0)`:ia
  joka skippaa bootloaderin siivouksen kokonaan; uusi exe sweeppaa
  vanhentuneet `_MEI*`-kansiot käynnistyessään.
- **Custom-ikoni näkyy nyt taskbarissa, Alt+Tab:ssä ja desktop-pikakuvakkeessa**.
  Lisätty Windows AppUserModelID (`Radika.dxf2ifc.kylmalaite.1`) ennen
  QApplicationia — ilman tätä Windows ryhmittelee sovelluksen
  PyInstaller-bootloaderin yleiseksi exeksi ja taskbar käytti
  generic-ikonia.
- EXE-icon-polku spec-tiedostossa muutettu absoluuttiseksi
  (`ROOT/assets/dxf2ifc.ico` SPECPATH-relatiivisen sijaan) — varmistaa
  että PyInstaller löytää ikonin.

## v0.1.2-alpha1 — 2026-05-04

**Added**:
- **Brand-ikoni**: Lauri'n suunnittelema kuvake (DXF-viiva → 3D-render)
  exe-tiedostolle, GUI-ikkunan title-baariin, taskbar-näkymälle ja
  Alt+Tab-vaihtajalle. Multi-resolution `.ico` (16/32/48/64/128/256 px)
  generoitu lähde-PNG:stä. Asetettu sekä PyInstallerin EXE-iconiksi
  että Qt:n WindowIcon-asetuksena.

## v0.1.1-alpha1 — 2026-05-04

Toinen alpha — ensimmäinen release jossa GUI:n itsepäivitys-banneri
voi tarjota latausta automaattisesti seuraavissa versioissa. Lataa
tämä manuaalisesti kerran, sen jälkeen päivitykset hoituvat itsestään.

**Removed**:
- **Pre-conversion geometric outlier scan** (`core/outliers.py`,
  `convert_dxf(detect_outliers=...)` kwargs). The scan produced false
  positives on real refrigeration models with multi-storey equipment
  spread; Solibri's own "Mallit hajallaan" rule covers the same check
  natively when the file is opened. Removing the feature drops one
  false-warning source and ~150 lines of code.

**Added**:
- **Solibri discipline auto-detect via `Pset_Project`**: every IFC
  project now carries `Pset_Project.Authorization = "Kylmäsuunnittelu"`,
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
  and `Kylmät` sheets — both flow through. Sheets without a
  recognisable Koneikko + Laitetunnus header are skipped.
- **Excel column aliases**: `"REV."` is now recognised as a koneikko
  column (RefDesign convention where the "Revision" column actually
  carries the koneikkotunnus). New canonical FI_Tekninen fields
  `Vastusteho`, `Jännite`, and `Jäähdyttävä vaikutus` with their
  Finnish/English aliases.
- New helper `load_energy_specs_with_headers(path)` returns
  `(specs, {sheet_name: [header strings]})` so callers can quote the
  parsed headers back to the user when no rows matched.
- IfcEvaporator + IfcCondenser FI_Tekninen default templates now
  include Vastusteho + Jännite (+ Jäähdyttävä vaikutus on Evaporator)
  so Solibri shows those rows even when an Excel hasn't been picked.

**Changed**:
- Excel field-alias matching now requires an exact match for tokens
  ≤3 characters long. `"Te"` (an evaporation-temperature shorthand)
  no longer false-matches inside `"Vastusteho"`, `"u_v"` no longer
  leaks into voltage-adjacent headers, etc.

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
