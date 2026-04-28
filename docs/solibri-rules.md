# Solibri-säännöt — dxf2ifc.bcfzip

Tämä dokumentti kuvaa suomeksi jokaisen säännön, joka kuljetetaan tiedostossa
`tools/solibri/dxf2ifc.bcfzip`. Sääntölistaus on tarkoitettu luettavaksi ilman
Solibrin avaamista, jotta dxf2ifc:n laatuporttia voi auditoida ja testata
manuaalisesti.

BCF 2.1 -arkisto sisältää viisi `TopicType="Rule"`-tyyppistä topicia, yksi
sääntö per topic. Jokainen sääntö sisältää viittauksen YTV 2012- tai
RT-kortistoon. Säännöt on järjestetty samaan järjestykseen kuin
`tools/solibri/build_bcfzip.py:RULES`-vakio.

## 1. Units are millimetres

- **GUID:** `11111111-aaaa-4aaa-aaaa-111111111111`
- **Mitä validoi:** `IfcUnitAssignment` sisältää SI-yksikön
  `LENGTHUNIT` jonka prefix on `MILLI` ja name on `METRE`. Toisin sanoen
  IFC-mallin pituusyksikkö on millimetri.
- **Miksi:** YTV 2012 osa 3 (Arkkitehtisuunnittelu) edellyttää että
  rakennustietomallin geometriayksikkö on millimetri.
- **Viite:** YTV 2012 osa 3, kohta 4.1.2.
- **Solibri-säännön tyyppi:** "Quantity Takeoff / Units" -kategorian
  _Length unit must be millimetres_.

## 2. Talo2000 classification coverage

- **GUID:** `22222222-bbbb-4bbb-bbbb-222222222222`
- **Mitä validoi:** Jokainen `IfcWall`, `IfcSlab`, `IfcDoor` ja
  `IfcWindow` on linkitetty `IfcRelAssociatesClassification`-relaatiolla
  Talo2000-codesetiin. Sääntö hylkää myös tyhjän `Identification`-arvon
  ja luokitukset jotka eivät ole RT 10-10962 -mukaisia Talo2000-koodeja.
- **Miksi:** YTV 2012 osa 3 + osa 4 vaatii Talo2000-luokittelun
  rakennusosista, jotta tietomalli on luovutuskelpoinen tilaajalle.
- **Viite:** RT 10-10962 + YTV 2012 osa 3 (RAK) ja osa 4 (TATE).
- **Solibri-säännön tyyppi:** "Information takeoff / Classification"
  _Required classification reference present_.
- **dxf2ifc:n vastaava automaattinen tarkistus:**
  `dxf2ifc.core.quality.validate_ifc` emittaa
  `"missing Talo2000 classification"` -warningin jos linkki puuttuu.

## 3. IfcSystem grouping for refrigeration networks

- **GUID:** `33333333-cccc-4ccc-cccc-333333333333`
- **Mitä validoi:** Kylmäaineputket (LT IMU, MT IMU, MT NESTE),
  viemäriputket (KYL-VIEMARI*), kaapelihyllyt sekä kylmälaitteet
  (höyrystin / lauhdutin / kompressori) on ryhmitelty
  `IfcSystem`-objektien alle `IfcRelAssignsToGroup`-relaatiolla.
  Jokaisella `IfcSystem`-objektilla pitää olla vähintään yksi jäsen.
- **Miksi:** YTV 2012 osa 4 (TATE) edellyttää järjestelmäryhmittelyä
  kylmä- ja LVI-järjestelmille, jotta määrälaskenta ja
  järjestelmätason raportointi on mahdollista.
- **Viite:** YTV 2012 osa 4 + Plan C ryhmittelypäätös
  (`Refrigeration LT`, `Refrigeration MT`, `Drainage`, `Cable carriers`,
  `Refrigeration plant`).
- **Solibri-säännön tyyppi:** "MEP / System" _Required IfcSystem
  grouping_.

## 4. Cold-room panels emit IfcBuildingElementProxy 1352

- **GUID:** `44444444-dddd-4ddd-dddd-444444444444`
- **Mitä validoi:** Kylmähuone-elementit (KYL-LEVY\*, KYL-NURKKA\*) on
  esitetty `IfcBuildingElementProxy`-entiteettinä ja luokiteltu
  Talo2000-koodilla `1352`. Sääntö hälyttää, jos sama paneeli on
  jätetty `IfcWall`-tyyppiseksi.
- **Miksi:** Talo2000-koodi 1352 (Kylmähuone-elementit) erottelee
  esivalmistetut paneelit kantavista seinistä, joka on kriittistä
  kustannuslaskennassa ja luovutusaineistossa.
- **Viite:** RT 10-10962 koodi 1352 + YTV 2012 osa 3.
- **Solibri-säännön tyyppi:** "Architecture / Walls" _Cold-room panels
  must be Proxy 1352, not Wall_.
- **dxf2ifc:n vastaava automaattinen tarkistus:** Default-profiilin
  KYL-LEVY*-säännöt mappaavat suoraan `IfcBuildingElementProxy`:lle.

## 5. Cooling equipment uses MEP entity types

- **GUID:** `55555555-eeee-4eee-eeee-555555555555`
- **Mitä validoi:** HOYRYSTIN-blokit on kartoitettu `IfcEvaporator`-,
  LAUHDUTIN-blokit `IfcCondenser`- ja KOMPRESSORI-blokit
  `IfcCompressor`-tyyppisiksi. `IfcFlowFitting` tai
  `IfcBuildingElementProxy` ei kelpaa kylmälaitteelle.
- **Miksi:** IFC 4 -skeeman MEP-entiteetit kuvaavat kylmälaitteet
  semanttisesti oikein, joka on edellytys Solibri-tarkistuksille,
  törmäystarkasteluille ja LVI-määrälaskennalle. IFC 2x3:n yleisemmät
  entiteetit eivät tarjoa samaa tarkkuutta.
- **Viite:** IFC 4 MEP -skeema + Plan B Section 11.
- **Solibri-säännön tyyppi:** "MEP / Cooling" _Cooling equipment must
  use MEP types_.

## Manuaalinen ajaminen

```bash
# 1. Avaa Solibri Anywhere ja lataa baseline-IFC
solibri_anywhere tests/fixtures/solibri_reference_full.ifc

# 2. Tuo dxf2ifc.bcfzip ruleset:ksi (File → Open BCF…)
solibri_anywhere/import tools/solibri/dxf2ifc.bcfzip

# 3. Aja ruleset (Checking → Run all rules)
# 4. Vie raportti BCF:nä ja tallenna tests/snapshots/solibri/<malli>.json
```

Plan F Section 3–4 kuvaavat tämän workflown automaation
(`tools/solibri/verify.py`, `tools/solibri/parse_report.py` ja
snapshot-diff). Kunnes nämä on toteutettu, käytä yllä olevaa
manuaalista prosessia.
