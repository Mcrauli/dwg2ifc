# RAVA-luokitus dxf2ifc:ssä

dxf2ifc tukee Plan H:sta lähtien kahta erillistä **suunnitteluala-domainia**
(`Rule.domain`):

| domain | Codeset                                | IfcClassification.Name | Käyttötarkoitus                             |
| ------ | -------------------------------------- | ---------------------- | ------------------------------------------- |
| `ARK`  | Talo 2000 -hankenimikkeistö            | `Talo2000`             | Rakennusosat (seinät, laatat, ovet, ikkunat, kalusteet, paneelit) |
| `TATE` | RAVA Pro3 — LVI-TUOTEOSA               | `RAVA-LVI`             | Kylmälaitteet, kylmäaineputket, viemäriputket |
| `TATE` | RAVA Pro3 — TALOTEKNIIKKA-TUOTEOSA     | `RAVA-TATE`            | Kaapelihyllyt, asennuskanavat                |

Yksi `Rule` saa kantaa **vain yhden** domainin koodin. Pydantic-validaattori
(`profiles/schema.py:_validate_domain_codes`) hylkää profiilit jotka:

- merkitsevät `domain="ARK"` mutta jättävät `talo2000_code`-kentän tyhjäksi,
- merkitsevät `domain="TATE"` mutta sisältävät `talo2000_code`-arvon,
- merkitsevät `domain="TATE"` mutta täyttävät sekä `lvi_code`:n että
  `talotekniikka_code`:n yhtä aikaa (tasan yksi sallittu).

Tämä takaa että jokainen IFC-tuoteosa saa täsmälleen yhden
`IfcRelAssociatesClassification`-relaation.

## Codeset-lähde

RAVA-koodit ladataan virallisesta JSON-API:sta osoitteessa
`https://koodistot.suomi.fi/codelist-api/api/v1/coderegistries/rytj/codeschemes/<scheme>_Versio_1_0/codes`.
Neljä codeset:iä on cache:ttu repo:on tiedostoiksi `src/dxf2ifc/profiles/rava/`:

- `lvi_tuoteosa.json`
- `lvi_jarjestelma.json`
- `talotekniikka_tuoteosa.json`
- `talotekniikka_jarjestelma.json`

Cache:n päivitys: `python -m tools.rava.sync_codes` (Plan H Task 5).
`dxf2ifc.profiles.rava.loader.load_rava_codes()` palauttaa dictin
`code → RAVACode(code, name, codeset)` ja sallii koodien validoinnin
profiili-editorissa.

## Vahvistetut RAVA-koodit (Plan H)

LVI-TUOTEOSA:

- `T-LVI-01-01-003` — Vedenjäähdytyskone
- `T-LVI-01-01-004` — Kylmävesiasema
- `T-LVI-01-01-005` — Jäähdytyskompressorikoneikko
- `T-LVI-01-01-017` — Kompressori
- `T-LVI-01-01-018` — Lauhdutin
- `T-LVI-01-01-019` — Kompressorilauhdutin
- `T-LVI-01-01-023` — Höyrystin
- `T-LVI-01-01-024` — Välijäähdytin
- `T-LVI-02` — Kylmäainejärjestelmän putki (yleinen kategoria; LT/MT IMU/NESTE
  erotellaan `system_name` + `pset_overrides.NominalDiameter`)
- `T-LVI-03-07-012` — Kylmäainevaraajasäiliö
- `T-LVI-04-01-001` — Viemäriputki (käytetään höyrystimen sulatusvalumalle)

TALOTEKNIIKKA-TUOTEOSA:

- `T-TATE-01-01-001` — Kaapelihylly

## Default-profiilin vaikutus

`src/dxf2ifc/profiles/default_kylmalaite.toml` ohjaa:

- ARK-säännöt (KYL-ULKOSEINA, KYL-VALISEINA, KYL-OVET-*, KYL-IKKUNA, KYL-LEVY,
  KYL-LEVYHYLLY, KYL-TIKASHYLLY*, AR12xx-prefix-säännöt, K-prefix-säännöt) →
  emittaavat IfcClassification "Talo2000".
- TATE-säännöt (KYL-HOYRYSTIN, KYL-LAUHDUTIN, KYL-KOMPRESSORI, LT IMU, MT IMU,
  MT NESTE, KYL-VIEMARI*) → emittaavat IfcClassification "RAVA-LVI" oikealla
  T-LVI-… koodillaan.
- KAAPELIHYLLY → emittaa IfcClassification "RAVA-TATE" koodilla
  `T-TATE-01-01-001`.

## Quality gate (validate_ifc)

`dxf2ifc.core.quality.validate_ifc` tarkistaa kaksi rinnakkaista warning-
sääntöä:

- `_check_talo2000_classification` — IfcWall / IfcSlab / IfcDoor / IfcWindow
  ilman Talo2000-linkkiä.
- `_check_rava_classification` — IfcPipeSegment / IfcCableCarrierSegment /
  IfcEvaporator / IfcCondenser / IfcCompressor ilman RAVA-LVI / RAVA-TATE-
  linkkiä.

Solibri-puolella vastaavat säännöt toimitetaan
`tools/solibri/dxf2ifc.bcfzip`:n topiceina **2** ("Talo2000 classification
coverage") ja **3** ("RAVA classification coverage") — ks. `docs/solibri-rules.md`.

Yleinen laatuporttiarkkitehtuuri (auto + manuaali) on kuvattu
[`docs/quality-gates.md`](quality-gates.md):ssä.
