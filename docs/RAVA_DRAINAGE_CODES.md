# RAVA-LVI viemärikoodit — pikamuisti

Lauri:n layer-mappausta varten kerätty kartta. Lähde:
<https://koodistot.suomi.fi/codelist-api/api/v1/coderegistries/rytj/codeschemes/LVI-TUOTEOSA_Versio_1_0/codes>
+ `LVI-JARJESTELMA_Versio_1_0`. Cache:t päivitetty alpha9:ssä.

> **Konventio**: tuoteosa-koodi (`T-LVI-*`) menee `rule.lvi_code`-
> kenttään, järjestelmäkoodi (`J-LVI-*`) menee
> `rule.fi_sijainti.jarjestelmien_tunnukset`-kenttään. Molemmat
> kirjoitetaan IFC:hen omiin classification reference -entiteetteihinsä.

## Tuoteosa (T-LVI) — fyysinen osa, IFC-tyyppi-mappaus

### T-LVI-04-01 Viemäriputket ja -putkiosat

| Koodi | Suomeksi | Suositeltu IFC-tyyppi | PredefinedType |
|---|---|---|---|
| `T-LVI-04-01-001` | Viemäriputki | `IfcPipeSegment` | `RIGIDSEGMENT` |
| `T-LVI-04-01-002` | Viemäriputken kulmayhde | `IfcPipeFitting` | `BEND` |
| `T-LVI-04-01-003` | Viemäriputken T-yhde | `IfcPipeFitting` | `JUNCTION` |
| `T-LVI-04-01-004` | Viemäriputken muuntoyhde | `IfcPipeFitting` | `TRANSITION` |
| `T-LVI-04-01-005` | Viemäriputken liitinyhde | `IfcPipeFitting` | `CONNECTOR` |
| `T-LVI-04-01-006` | Viemäriputken X-yhde | `IfcPipeFitting` | `JUNCTION` |
| `T-LVI-04-01-007` | Viemäriputken tulppa | `IfcPipeFitting` | `OBSTRUCTION` |
| `T-LVI-04-01-008` | Viemäriputken uraliitin | `IfcPipeFitting` | `CONNECTOR` |
| `T-LVI-04-01-009` | Viemäriputken kauluslaippa | `IfcPipeFitting` | `CONNECTOR` |

### T-LVI-04-02 Viemäriputkistovarusteet

| Koodi | Suomeksi | Suositeltu IFC-tyyppi | PredefinedType |
|---|---|---|---|
| `T-LVI-04-02-001` | Viemäriputken joustava liitinyhde | `IfcPipeFitting` | `CONNECTOR` |
| `T-LVI-04-02-002` | Vesilukko (hajulukko) | `IfcWasteTerminal` | `WASTETRAP` |
| `T-LVI-04-02-003` | Puhdistusyhde - viemäriputki | `IfcPipeFitting` | `JUNCTION` |
| `T-LVI-04-02-004` | Alipaineventtiili | `IfcValve` | `AIRRELEASE` |
| `T-LVI-04-02-005` | Padotusventtiili | `IfcValve` | `CHECKVALVE` |
| `T-LVI-04-02-006` | Jäätymissuoja - tuuletusviemäri | `IfcPipeFitting` | `OBSTRUCTION` |
| `T-LVI-04-02-007` | Harmaan jäteveden suodatin | `IfcInterceptor` | `USERDEFINED` |
| `T-LVI-04-02-008` | Viemäriputken pohjakulma | `IfcPipeFitting` | `BEND` |
| `T-LVI-04-02-009` | Viemäröintiliitin | `IfcPipeFitting` | `CONNECTOR` |

### T-LVI-04-03 Viemäriputkistoeristeet

| Koodi | Suomeksi | Käsittely |
|---|---|---|
| `T-LVI-04-03-001` | Viemäriputkieriste | `IfcCovering` (CLADDING) tai PSet putkelle |

### T-LVI-05-01 Kaivot

| Koodi | Suomeksi | Suositeltu IFC-tyyppi | PredefinedType |
|---|---|---|---|
| `T-LVI-05-01-001` | Lattiakaivo | `IfcWasteTerminal` | `FLOORTRAP` |
| `T-LVI-05-01-002` | Kuivakaivo | `IfcWasteTerminal` | `WASTEDISPOSALUNIT` |
| `T-LVI-05-01-003` | Sadevesikattokaivo | `IfcWasteTerminal` | `ROOFDRAIN` |
| `T-LVI-05-01-004` | Parvekekaivo | `IfcWasteTerminal` | `FLOORTRAP` |
| `T-LVI-05-01-005` | Kurakaivo | `IfcWasteTerminal` | `FLOORTRAP` |
| `T-LVI-05-01-006` | Jätevesikaivo | `IfcWasteTerminal` | `GULLYTRAP` |
| `T-LVI-05-01-007` | Jäteveden tarkastuskaivo | `IfcWasteTerminal` | `USERDEFINED` |
| `T-LVI-05-01-008` | Tarkastusputki | `IfcPipeFitting` | `OBSTRUCTION` |

### T-LVI-01-03 Pumppaamot (kuuluvat aluepumppausjärjestelmiin, eivät putkistoon)

| Koodi | Suomeksi | Suositeltu IFC-tyyppi |
|---|---|---|
| `T-LVI-01-03-001` | Jätevesipumppaamo | `IfcPump` (SUMPPUMP) |
| `T-LVI-01-03-002` | Sadevesipumppaamo | `IfcPump` (SUMPPUMP) |
| `T-LVI-01-03-003` | Perusvesipumppaamo | `IfcPump` (SUMPPUMP) |

## Järjestelmä (J-LVI-04) — mihin viemärilinjaan kuuluu

Asetetaan `rule.fi_sijainti.jarjestelmien_tunnukset`-kenttänä +
`system_name`-grouppauksena.

| Koodi | Suomeksi | Käyttötarkoitus |
|---|---|---|
| `J-LVI-04-01` | Viemäri - jätevesi | WC, pesualtaat, talousjätevesi |
| `J-LVI-04-02` | Viemäri - sadevesi | Kattokaivot, sadevesijärjestelmä |
| `J-LVI-04-03` | Viemäri - tuuletus | Viemärin tuuletusputket katolle |
| **`J-LVI-04-04`** | **Viemäri - kondenssi** | **Kylmälaitteilta — Lauri:n KYL-laitteet** |
| `J-LVI-04-05` | Viemäri - rasva | Keittiön rasvanerotin-järjestelmä |
| `J-LVI-04-06` | Viemäri - öljy | Korjaamon öljynerotin-järjestelmä |
| `J-LVI-04-07` | Viemäri - erikois | Erikoisjäteveden järjestelmä |
| `J-LVI-04-08` | Viemäri - salaoja | Perustusten kuivatus |
| `J-LVI-04-09` | Viemäri - perusvesi | Pohjaveden pumppaus |
| `J-LVI-04-10` | Viemäri - sekavesi | Sekajätevesi (jv + sv yhdessä) |
| `J-LVI-04-11` | Viemäri - dialyysi | Sairaala-dialyysi |
| `J-LVI-04-12` | Paineviemäri - jätevesi | Painekiertoinen jv |
| `J-LVI-04-13` | Paineviemäri - sadevesi | Painekiertoinen sv |
| `J-LVI-04-14` | Paineviemäri - perusvesi | Painekiertoinen pv |
| `J-LVI-04-15` | Paineviemäri - sekavesi | Painekiertoinen sv |
| `J-LVI-04-99` | MUU - Viemärijärjestelmät | Fallback |

## Esimerkki profile-säännöstä (kun layer-pattern päätetty)

```toml
[[rules]]
layer_pattern = "KYL-KONDENSSI*"
ifc_type = "IfcPipeSegment"
predefined_type = "RIGIDSEGMENT"
domain = "KYL"
lvi_code = "T-LVI-04-01-001"
system_name = "Refrigeration drainage"
fi_komponentti = { paaryhma = "TUOTEOSAT - LVI", alaryhma = "VIEMÄRIPUTKISTOT", yleisnimi = "Kondenssiviemäri", yleistunnus = "VEM.LVI" }
fi_sijainti = { jarjestelmien_nimet = "Viemäri - kondenssi", jarjestelmien_tunnukset = "J-LVI-04-04" }
fi_tekninen = { Materiaali = "Muovi (PP)" }

[[rules]]
layer_pattern = "LVI-LATTIAKAIVO*"
ifc_type = "IfcWasteTerminal"
predefined_type = "FLOORTRAP"
domain = "TATE"
lvi_code = "T-LVI-05-01-001"
system_name = "Drainage"
fi_sijainti = { jarjestelmien_nimet = "Viemäri - jätevesi", jarjestelmien_tunnukset = "J-LVI-04-01" }
fi_tekninen = { Materiaali = "Valurauta", Pinnoite = "Kromi" }
```

## Mitä Lauri tekee seuraavaksi

1. Päättää KYL-LISP-puolen layer-patternit (esim. `KYL-KONDENSSI*` /
   `KYL-VIEMÄRI*`) ja LVI-puolen (esim. `LVI-VIEM-JV*` / `LVI-SV*`)
2. Lisää säännöt `default_kylmalaite.toml`:hen yllä olevan mallin
   mukaan
3. Validoi `--validate`:lla että koodit löytyvät cache:sta — virheilmoitus
   kertoo jos tyyppivirhe

Koodit ovat nyt valmiit cachessa (`profiles/rava/lvi_tuoteosa.json`,
`profiles/rava/lvi_jarjestelma.json`).
