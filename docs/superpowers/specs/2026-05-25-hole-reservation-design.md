# Reikavaraus / IfcProvisionForVoid design

## Tavoite

Lisataan dwg2ifc-projektiin uusi reikävarauspolku, jossa:

- AutoCAD-kayttaja luo reikävarauksen omalla LISP-tyokalulla.
- Tyokalu sijoittaa objektin aina layerille `KYL-REIKAVARAUS`.
- Objekti on CADissa attribuuttiblokki, jolla on pysyva oma `GUID`.
- IFC-exportissa objekti kirjoitetaan itsenaisena `IfcProvisionForVoid`-entiteettina.
- Sama varaus pysyy samana objektina paivityksissa, kun blokkia muokataan eika poisteta ja luoda uudelleen.
- Solibrissa nakyvat kaikki olennaiset reikävarauksen tiedot ilman kasityota.

Tama ei ole `IfcOpeningElement`-tyyppinen aukko eika sido varausta suoraan rakenteeseen. Rakennesuunnittelija kayttaa varauskappaletta oman mallinsa pohjana ja paattaa itse varsinainen aukotusratkaisun.

## Lahteet ja nykytila

- YTV osa 4 sanoo, etta varausobjektista tulee ilmeta varaaja, koko, tunnisteet, oikea sijainti ja absoluuttinen korkeusasema. Objektia tulee ensisijaisesti muokata, ei korvata uudella, jotta ohjelmistot tunnistavat saman varauksen muuttuneeksi eivatka uudeksi.
- RAVA-koodisto sisaltaa nimikkeen `Reikävaraus`, koodi `T-TATE-02-01-001`, lyhenne `RV`.
- Nykyinen dwg2ifc osaa jo lukea INSERT-blokkien attribuutit, mapata `KYL-*`-layereita ja kirjoittaa FI_* PropertySetit Solibria varten.
- Reikävaraukselle ei ole viela omaa CAD-tyokalua, profile-saantoa eika IFC-builderia.
- AutoCAD-lahteet ovat tassa repossa, mutta loppukayttajan bundle, CUIX ja asennuspakkaus elavat erillisessa `autocad-lisp-ohjeet`-repossa. Muutos on siis kaksiosainen: lahde muokataan tahan repossa ja peilataan jakelurepoon.

## Hyvaksytyt paatokset

- IFC-entiteetti: `IfcProvisionForVoid`
- Geometrian ensimmainen versio: pyorea varauskappale
- Kayttoliittyma: yksi komento, jonka alussa kayttaja valitsee `Lattia` tai `Seina`
- CAD-malli: attribuuttiblokki, ei pelkka viiva/geometria
- Layer: aina `KYL-REIKAVARAUS`
- Tunniste: blokkiin tallennettu pysyva `GUID`-attribuutti
- Ensimmainen syottojoukko:
  - `Lattia`: keskipiste, halkaisija, pituus/paksuus, korko
  - `Seina`: suunnan maarittely kahdella pisteella, halkaisija, lapaisypituus

## Ratkaisun yleisrakenne

Ratkaisu jakautuu kolmeen osaan:

1. AutoCAD-tyokalu luo ja muokkaa reikävarausblokkia.
2. dwg2ifc tunnistaa `KYL-REIKAVARAUS`-blokin ja sen attribuutit.
3. IFC writer kirjoittaa blokista `IfcProvisionForVoid`-objektin pysyvalla `GlobalId`:lla ja Solibriin sopivilla FI_* tiedoilla.

## CAD-tyokalu

### Uusi komento

Lisataan `autocad-tools/`-kansioon uusi LISP-komento nimella `REIKAVARAUS`.

Komennon kulku:

1. Varmista layer `KYL-REIKAVARAUS` olemassaolevalla layer-helper-tyylilla.
2. Aseta `CLAYER` valiaikaisesti `KYL-REIKAVARAUS`-layeriin.
3. Kysy kayttajalta varauksen tyyppi:
   - `Lattia`
   - `Seina`
4. Kysy geometriset syotteet:
   - `Lattia`: keskipiste, halkaisija, pituus/paksuus, korko
   - `Seina`: ensimmainen piste, toinen piste seinasuuntaa varten, halkaisija, lapaisypituus
5. Luo tai insertoi reikävarausblokin instanssi.
6. Tayta blokin attribuutit.
7. Palauta kayttajan alkuperainen `CLAYER`, `OSMODE`, `CMDECHO` jne.

### Blokkirakenne

Reikävaraus toteutetaan omana DWG-blokkinaan. Blokin geometria on BYBLOCK/BYLAYER-yhteensopiva kuten muissakin tyokaluissa, jotta instanssin layer maarittaa lopputuloksen.

Ensimmainen versio voi olla yksi blokki, jonka orientaatio ja mitat asetetaan dynaamisten propertyjen tai insertointijalkikasittelyn avulla. Erillista lattia- ja seinablockia ei tarvita ensimmaiseen versioon.

### Pysyva GUID

Blokilla on attribuutti `GUID`.

- Jos uusi varaus luodaan, tyokalu generoi tavallisen UUID:n ja kirjoittaa sen `GUID`-attribuuttiin.
- Jos olemassaolevaa blokkia muokataan, sama `GUID`-attribuutti sailytetaan.
- IFC-exportti ei kayta suoraan satunnaista `guid.new()`-arvoa vaan johtaa `GlobalId`:n taman attribuutin pohjalta.

UUID kannattaa tallentaa tavallisessa 36 merkin muodossa, esimerkiksi `550e8400-e29b-41d4-a716-446655440000`. Writer muuntaa sen IFC:n 22-merkkiseen `GlobalId`-muotoon `ifcopenshell.guid.compress(...)`-helperilla.

### Ribbon ja ikoni

Lisataan uusi ribbon-nappi nimella `Reikävaraus`.

- Nappi ajaa komentoa `REIKAVARAUS`.
- Napille tehdaan oma ikoni.
- Ikonit ja CUIX-muutokset eivat jakaudu suoraan taman repon kautta, vaan ne pitaa peilata `autocad-lisp-ohjeet`-repon bundleen/CUIXiin.

Tassa repossa tulee dokumentoida, mika komento ja tiedostot jakelurepossa on paivitettava.

## IFC-mappaus

### Profiilisaanto

Lisataan `src/dwg2ifc/profiles/default_kylmalaite.toml`:iin uusi saanto layerille `KYL-REIKAVARAUS`.

Saannon ominaisuudet:

- `ifc_type = "IfcProvisionForVoid"`
- domain pidetaan TATE/KYL-linjan mukaisena nykyisten saantojen kanssa
- RAVA-koodiksi sidotaan `T-TATE-02-01-001`
- FI_Komponentti-tauluun asetetaan yleisnimi `Reikävaraus` ja yleistunnus `RV`

### Parseri ja attribuutit

Nykyinen INSERT-attribuuttiketju hyodynnetaan. Reikävarauksen kentat pidetaan tavallisina blokkiattribuutteina, jotta ne kulkevat olemassa olevan `block_attribs.py`-polun kautta.

Lisattavat attribuutit:

- `GUID`
- `VARAUS_TYYPPI`
- `HALKAISIJA`
- `PITUUS`
- `KORKO`
- `TUNNUS`
- `VARAAJA`
- `KOMMENTTI`

Tarvittaessa voidaan lisata myohemmin:

- `PALOLUOKKA`
- `TIIVISTYS`
- `JARJESTELMA`
- `URAKOITSIJA`

Ensimmainen versio rajataan kuitenkin niin, etta Solibriin saadaan varmasti ainakin YTV:n minimikentat: varaaja, koko, tunniste, sijainti ja absoluuttinen korkeusasema.

### Builder

Lisataan `builders.py`:hin oma builder pyorealle `IfcProvisionForVoid`-objektille.

Builderin vastuut:

- validoi, etta syotteen geometria on reikävaraukselle tuettu
- muodostaa pyorean kappaleen halkaisijasta ja pituudesta
- sijoittaa kappaleen oikein lattia- tai seinasuuntaan
- asettaa `GlobalId`:n blokin `GUID`-attribuutin pohjalta
- liittaa olemassa olevat FI_* PropertySetit

Ensimmainen versio voidaan mallintaa sylinterina extruusiona:

- `Lattia`: extruusio Z-suunnassa
- `Seina`: extruusio kayttajan valitseman seinasuunnan mukaan

Jos nykyinen helper-polku ei tue pyoreaa profiilia suoraan, builderi saa tehda oman `IfcCircleProfileDef` + `IfcExtrudedAreaSolid` -polun.

## Solibri- ja RAVA-tiedot

Reikävarauksen tulee nayttaa Solibrissa valmiina tuotteena, ei geneerisena tyhjana kappaleena.

Kenttien sijoittuminen:

- `FI_Komponentti`
  - paaryhma
  - alaryhma
  - koodi = `T-TATE-02-01-001`
  - yleisnimi = `Reikävaraus`
  - yleistunnus = `RV`
  - `Laitetunnus` tai vastaava -> `TUNNUS`
- `FI_Asennus`
  - absoluuttinen korkeusasema `KORKO`-tiedosta
  - yla/alapinta ja asennuskorko geometrian perusteella
- `FI_Geometria`
  - halkaisija ja pituus
  - kolmannen mitan nimea voidaan joutua laajentamaan tai kuvaamaan `FI_Tekninen`-puolella, jos nykyinen Korkeus/Leveys/Syvyys ei sovi hyvin pyorealle varaukselle
- `FI_Tuote`
  - `KOMMENTTI`
- `FI_Tekninen`
  - `VARAUS_TYYPPI`
  - `VARAAJA`
  - mahdolliset lisatiedot joita ei ole luontevaa pakottaa `FI_Komponentti`-kenttiin

Periaate on, etta Solibri-kayttaja nakee heti:

- mita varaus koskee
- kuka sen on varannut
- mika sen tunnus on
- mika sen koko on
- missa korkotasossa se on
- onko kyse lattia- vai seinavarauksesta

## Orientaatio

### Lattiavaraus

- Keskiakseli on maailman Z-suuntainen.
- Pituus kulkee positiiviseen Z-suuntaan tai symmetrisesti keskipisteen ymparille. Ensimmainen toteutus paattaa yhden mallin ja dokumentoi sen.
- `KORKO` tulkitaan absoluuttisena asennus-/referenssikorkona.

Suositus: kayta keskipisteen Z-arvona kayttajan antamaa korkoa ja extrudoi kappale symmetrisesti puoliksi ylos, puoliksi alas referenssipisteesta. Tama tekee visualisoinnista vakaamman kun varauskappaletta halutaan kayttaa rakenteen lapaisyn kohdalla.

### Seinavaraus

- Kayttaja antaa kaksi pistetta, joista saadaan vaakasuuntainen tai yleinen suuntavektori.
- Builder ja CAD-komento orientoivat sylinterin taman vektorin suuntaiseksi.
- `PITUUS` on lapaisypituus suuntavektorin suunnassa.

Suositus: tulkitse ensimmainen piste varauksen keskipisteeksi ja toinen piste suunnan maarittajaksi. Tama tekee seinavarauksesta nopean sijoittaa ilman erillista rotaatiokomentoa.

## GUID-strategia

Pysyvyysvaatimus tarkoittaa, etta IFC `GlobalId` ei saa perustua export-hetken satunnaisuuteen.

Strategia:

1. CAD-blokissa on attribuutti `GUID` tavallisena UUID:na.
2. Exportissa writer lukee attribuutin.
3. UUID muunnetaan IFC-muotoon `ifcopenshell.guid.compress(uuid)`.
4. Tulos asetetaan `IfcProvisionForVoid.GlobalId`:ksi.

Jos `GUID` puuttuu tai on viallinen:

- writer voi joko failata selkealla virheella tai generoida uuden UUID:n vain jos kyse on aidosti uudesta blokista
- ensimmainen toteutus kannattaa tehda mieluummin fail-fast-periaatteella, jotta GUID-ketju ei rikkoudu huomaamatta

## Tiedostot joita muutos koskee

Tassa repossa:

- `autocad-tools/reikavaraus.lsp` uusi
- `autocad-tools/README.md`
- mahdollinen uusi reikävarausblokin `.dwg`
- `autocad-tools/_loader.lsp` jos uusi komento tarvitsee eksplisiittisen latauksen
- `src/dwg2ifc/profiles/default_kylmalaite.toml`
- `src/dwg2ifc/core/block_attribs.py`
- `src/dwg2ifc/core/types.py` jos tarvitaan oma stable-id-kentta
- `src/dwg2ifc/core/ifc_writer/builders.py`
- `src/dwg2ifc/core/ifc_writer/orchestrator.py`
- testit CAD-attribuuteille, mappaukselle ja builderille
- dokumentaatio

Jakelurepossa `autocad-lisp-ohjeet`:

- `files/`-kansioon uusi `.lsp` ja mahdollinen `.dwg`
- ribbon/CUIX-maaritykset
- uusi ikoni
- bundle/zip-paketointi
- mahdolliset asennusohjeet

## Virhetilanteet

- Jos kayttaja keskeyttaa komennon, ymparistomuuttujat palautetaan aina.
- Jos blokkia ei loydy, komento raportoi puuttuvan DWG-resurssin selkeasti.
- Jos halkaisija tai pituus ei ole positiivinen, komento ei luo blokkia.
- Jos seinasuunta ei maarity kahdesta pisteesta, komento pyytää syotteen uudelleen.
- Jos IFC-exportissa `GUID` ei ole kelvollinen UUID, konversio ilmoittaa selkean virheen ja kertoo objektin layerin/handlen.

## Testaus

Vahintaan seuraavat testit:

- profiilisaanto tunnistaa `KYL-REIKAVARAUS`-layerin oikein
- blokkattribuutit reitittyvat oikeisiin FI_* kenttiin
- `GUID` muunnetaan stabiiliksi IFC `GlobalId`:ksi
- sama `GUID` tuottaa saman `GlobalId`:n kahdessa exportissa
- `IfcProvisionForVoid` syntyy oikealla RAVA-koodilla
- `Lattia`-varaus kirjoittuu pystysuuntaisena
- `Seina`-varaus kirjoittuu valitun suuntavektorin mukaisena

## Toteutusjarjestys

1. Lisaa profiilisaanto, attribuuttikentat ja writerin builder rajatusti.
2. Lisaa CAD-blokki ja `REIKAVARAUS`-LISP.
3. Lisaa GUID-muunnos ja pysyvyystestit.
4. Lisaa ribbon-komento ja ikoni jakelurepoon.
5. Paivita dokumentaatio molempiin repoihin.

## Rajaukset ensimmaiseen versioon

- Vain pyorea varaus
- Ei automaattista rakenteen tunnistusta
- Ei `IfcOpeningElement`-relaatioita
- Ei vapaan muotoisia reikävarauksia
- Ei automaattista seinanormaalin paattelya mallista

## Definition of done

Muutos on valmis kun:

- kayttaja voi luoda `REIKAVARAUS`-komennolla lattia- tai seinavarauksen
- objekti menee aina `KYL-REIKAVARAUS`-layerille
- blokissa on pysyva `GUID`
- exportti tuottaa `IfcProvisionForVoid`-objektin
- Solibrissa nakyvat sovitut tunniste-, koko-, varaaja- ja korkotiedot
- samaa blokkia muokkaamalla IFC-objekti sailyttaa saman `GlobalId`:n
- ribbonissa on oma `Reikävaraus`-nappi omalla ikonilla
- jakelurepo on paivitetty niin, etta loppukayttaja saa komennon bundleen/CUIXiin
