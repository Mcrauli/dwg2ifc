# VARUSTEET — kylmäkoneikon sähkölaite-blokit + dxf2ifc-mappaus

**Status**: hyväksytty 2026-05-12, valmis toteutettavaksi.

## Tarkoitus

Lauri on tuottanut 6 uutta DWG-blokkia kylmäkoneikon sähkö-/automaatio-
varustelua varten (`Laitteet/`-kansiossa autocad-lisp-ohjeet-repossa).
Tarvitaan:

1. **LISP-komento** (`VARUSTEET`) joka tarjoaa nuolinäppäimin
   navigoitavan valikon 6:sta blokista ja insertoi valitun
   layeriinsä.
2. **dxf2ifc-mappaus** joka tunnistaa nämä layerit DXF:stä ja
   tuottaa oikeat IFC4-tyypit + RAVA3Pro-tilavarauskoodit Solibri:in.

## Blokit, layerit, IFC-tyypit, RAVA-koodit

| Block-nimi (DWG) | Layer | IFC4-tyyppi | PredefinedType | RAVA-koodi |
|---|---|---|---|---|
| `CO2-anturi` | `KYL-CO2-ANTURI` | `IfcSensor` | `CO2SENSOR` | `T-TATE-02-01-003` |
| `CO2-sireeni` | `KYL-CO2-SIREENI` | `IfcAlarm` | `SIREN` | `T-TATE-02-01-003` |
| `Huolto-PC` | `KYL-HUOLTO-PC` | `IfcCommunicationsAppliance` | `COMPUTER` | `T-TATE-02-01-003` |
| `RK-JK10` | `KYL-RK-JK10` | `IfcDistributionBoard` | `DISTRIBUTIONBOARD` | `T-TATE-02-01-004` |
| `Säädinkeskus (KU)` | `KYL-SAADINKESKUS-KU` | `IfcController` | `PROGRAMMABLE` | `T-TATE-02-01-004` |
| `kylmäkoneikon hätäseispainike` | `KYL-HATASEIS` | `IfcSwitchingDevice` | `EMERGENCYSTOP` | `T-TATE-02-01-003` |

RAVA-perustelu: TATE-TUOTEOSA-katalogissa (90 koodia) ei ole erillisiä
sähkölaite-koodeja. Konventio: kylmäsuunnittelijan sähköpuolen elementit
ovat tilavarauksia (`T-TATE-02-01-003` Tilavaraus - laitteisto / `T-TATE-02-01-004`
Tilavaraus - keskus), jotka sähkösuunnittelija korvaa lopullisilla osilla.

Domain = `KYL` kaikille (kylmäsuunnittelijan vastuulla piirrettäessä;
suunnittelualat-luokitus = "KYL" säilyy yhdenmukaisena muiden
KYL-tuotteiden kanssa).

## LISP-puoli (`files/varusteet.lsp`)

`(defun c:VARUSTEET ...)` joka:

1. Tallentaa CLAYER/CMDECHO/OSMODE → palauttaa lopussa.
2. `(initget "CO2anturi CO2sireeni HuoltoPC RKJK10 Saadinkeskus Hataseis")`
   + `(getkword)`-prompt: `Valitse varuste [CO2anturi/CO2sireeni/HuoltoPC/RKJK10/Saadinkeskus/Hataseis] <CO2anturi>:`
   Modern AutoCAD näyttää keywordit nuolinäppäimin navigoitavana valikkona.
3. Mappaa keyword → (block-DWG-nimi, target-layer-nimi).
4. `varusteet-ensure-layer` luo target-layerin uniikilla ACI-värillä jos
   puuttuu (klhylly-ensure-layer-helperin malliin).
5. `varusteet-find-block-file` etsii block-DWG:n samalla locator-pattern:lla
   kuin positio.lsp / klhylly.lsp: support path → samasta kansiosta josta
   LSP ladattiin (APPLOAD MRU rekisteristä) → `%USERPROFILE%/suunnittelutyokalut/`
   → `%USERPROFILE%/AutoCADLisp/` → `C:\AutoCADLisp/`. Tämä toimii
   automaattisesti kun käyttäjä purkaa sivuilta ladatun
   `suunnittelutyokalut.zip`:n yhteen kansioon ja `APPLOAD`-laataa
   `varusteet.lsp`:n — kaikki 6 DWG ovat samassa kansiossa.
6. `-INSERT block=path` → user pickaa insertion-pisteen → kysyy rotation.
7. Asettaa CLAYER target-layerille ennen INSERT:iä, palauttaa lopussa.

### Layer-värit (ACI)

| Layer | ACI |
|---|---|
| `KYL-CO2-ANTURI` | 5 (sininen) |
| `KYL-CO2-SIREENI` | 1 (punainen) |
| `KYL-HUOLTO-PC` | 250 (harmaa) |
| `KYL-RK-JK10` | 6 (magenta) |
| `KYL-SAADINKESKUS-KU` | 2 (keltainen) |
| `KYL-HATASEIS` | 1 (punainen) |

## dxf2ifc-puoli (`src/dxf2ifc/profiles/default_kylmalaite.toml`)

6 uutta `[[rules]]`-osiota, yksi per layer. Kaava per sääntö:

```toml
[[rules]]
layer_pattern = "KYL-CO2-ANTURI"
ifc_type = "IfcSensor"
predefined_type = "CO2SENSOR"
domain = "KYL"
talotekniikka_code = "T-TATE-02-01-003"
system_name = "Refrigeration sähkövarusteet"
fi_komponentti = { paaryhma = "TALOTEKNIIKAN VARUSTEET", alaryhma = "SÄHKÖLAITTEET", yleisnimi = "CO2-anturi", yleistunnus = "CO2A" }
```

### Parserissa ei muutoksia

`accoreconsole+STLOUT` Phase 2:n yleinen `KYL-*` layer-filter poimii
uudet 3DSOLID-INSERT:t automaattisesti — `mapper.py`:n
ensimmäinen-mätsäys-voittaa-logiikka hoitaa loput.

## Test plan

### Profiili (`tests/test_profile_varusteet.py`)

- 6 sääntöä parsiutuvat schema-validation läpi (`Rule`-pydantic OK).
- Layer-pattern-mätsäys: `KYL-CO2-ANTURI` mätsää 1:1, ei matchaa
  yleisemmälle `KYL-*`-säännölle (varmistaa että uudet säännöt menevät
  ENNEN yleisempiä KYL-* fallbackeja).

### End-to-end (`tests/test_varusteet_integration.py`)

Synteettinen DXF jossa 6 layeria + yksi yksinkertainen INSERT/3DSOLID
per layer → `convert_dxf` → IFC4 → tarkista:

- 6 IfcXxx-instanssia luotu (oikeat tyypit + PredefinedType:t)
- Suunnittelualat-luokitus "KYL" jokaisella
- IfcClassificationReference RAVA-koodilla
  (T-TATE-02-01-003 tai T-TATE-02-01-004)

Mocataan `extract_acis_meshes`-paluu (käyttää valmiita placeholder-mesh:eja),
ei tarvita accoreconsolea testirungissa.

## Out-of-scope tällä kierroksella

- POSITIO-tunnisteet (Koneikko + Laitetunnus) näille laitteille
- FI_Tekninen-arvot per laite (jännite/IP-luokka/valmistaja)
- GUI Profile Editor:in UI-päivitys (TOML-edit toimii käsin)
- Erillisten varusteet-osioiden lisääminen autocad-lisp-ohjeet-
  sivuston `ohjeet.html`:iin

## ZIP-jakelu (autocad-lisp-ohjeet)

1. Siirretään 6 DWG `Laitteet/` → `files/` (sama kansio kuin muut LSP+DWG:t).
   `Laitteet/`-kansio voidaan poistaa tai jättää tyhjäksi rinnalle —
   jakelussa käytetään vain `files/`.
2. `varusteet.lsp` ladataan `files/`-kansioon.
3. `make-bundle.ps1` ajetaan → `files/suunnittelutyokalut.zip` rebuildaa
   sisältäen nyt 5 LSP + (positio.dwg + klhylly-levy.dwg + klhylly-tikas.dwg + 6
   varuste-DWG) = 9 DWG.
4. `lataukset.html`-sivun ZIP-kortin meta päivitetään (sisältö "5 LSP + 9 DWG",
   uusi tiedostokoko).

## Versiointi & julkaisu

- dxf2ifc: bump → `v0.2.0a19`, CHANGELOG-osio, tag → release-workflow → itsepäivitys.
- autocad-lisp-ohjeet: suora push mainiin + `make-bundle.ps1` rebuild + ZIP
  publish. Per [autocad-lisp-ohjeet CLAUDE.md](../../../OneDrive%20-%20RADIKA%20OY/Työpöytä/work/autocad-lisp-ohjeet/CLAUDE.md):n
  ohjetta GitHub Pages deployaa automaattisesti mainista ~1 min kuluttua.
