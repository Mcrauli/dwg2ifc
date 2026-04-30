---
plan: H
title: IFC 4.3 migration + RAVA classification (domain-based)
status: draft
date: 2026-04-28
depends_on: F
---

# Plan H: IFC 4.3 -migraatio + RAVA-luokitus (domain-pohjainen)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps käyttävät `- [ ]`-syntaksia. Tämä plan vaihtaa skeeman IFC4 → IFC4X3 ja siirtää TATE/kylmälaitteet pois Talo2000:sta RAVA-koodien (LVI-TUOTEOSA / TALOTEKNIIKKA-TUOTEOSA) alle. ARK-puolella (seinät/laatat/ovet/ikkunat/paneelit) Talo2000 säilyy. Multi-classification on KIELLETTY: jokainen elementti saa täsmälleen yhden codesetin domainin mukaan. RAVA-koodit ladataan virallisesta `koodistot.suomi.fi`-JSON-API:sta tooling-skriptillä; codesetit cachetetaan `src/dxf2ifc/profiles/rava/`-kansioon committoituna JSON:nä.

**Goal:** Tuottaa IFC 4.3 -tiedostot RAVA Pro3 -yhteensopivina, jolloin TATE-luokittelu (LVI- ja talotekniikka-tuoteosat sekä -järjestelmät) tulee suoraan RAVA-koodistosta. Lauri:n kylmälaiteasiakkaiden BIM-luovutus on tällöin Suomen valtion tuoteosa-koodiston (RAVA) -yhteensopiva, mikä on edellytys julkisen sektorin urakoissa ja täydentää Talo2000:n ARK-luovutuksen.

**Architecture:** Vaihe A on puhtaasti skeeman vaihto + regressio (kaikki nykyiset 314 testiä passaa IFC4X3:lla). Vaihe B muuttaa profiili-skeeman: `Rule.domain` on uusi pakollinen `Literal["ARK", "TATE"]`, ja yksi kolmesta koodi-kentästä täytetään (`talo2000_code` / `lvi_code` / `talotekniikka_code`). Mapper + ifc_writer kunnioittavat domainia: ARK-elementeille emitoidaan IfcRelAssociatesClassification Talo2000:een, TATE-elementeille RAVAan. Default-profiilin nimi vaihtuu `default_kylmalaite_talo2000.toml` → `default_kylmalaite.toml`, ja kylmälaitteet siirtyvät RAVA-koodien alle.

**Tech stack:** ifcopenshell ≥ 0.8.5 (IFC4X3 tuettu), ezdxf, pydantic, requests (RAVA-koodien lataaminen), tomli-w. Ei uusia juuri-deps:eja.

---

## Repository state before this plan

Plan A 21/21 + Plan B 50/50 + Plan C 12/12 + Plan D 25/25 + Plan E 23/23 + Plan F 16/16 valmis. Bugfix kierros 2 valmis (placement 1000× -bugi `2f827ea`, xref-prefix mapper `230f327`, ARK layer-säännöt `b1df8c3`). Master `b1df8c3`. 314 testiä passed + 1 skipped (Solibri-marker). Coverage 91 %.

---

## Section 1: IFC4X3-skeema-migraatio

- [ ] Task 1: lisää `build_ifc_project_skeleton(schema: Literal["IFC4", "IFC4X3"] = "IFC4")`-parametri ja päivitä `IfcStore.create()`/`ifcopenshell.api.run("project.create_file", schema=schema)` kutsuvalle skeemalle. Failing-testi: skeleton schema="IFC4X3" → `ifc.schema == "IFC4X3"`.
- [ ] Task 2: regressio koko `convert_dxf`-pipeline IFC4X3-skeemalla — full_kylmaelement_dxf-fixture läpi konversion, varmista että jokainen 11 IFC-luokkaa (Wall/Slab/Door/Window/PipeSegment/Furniture/CableCarrierSegment/BuildingElementProxy/Evaporator/Condenser/Compressor) syntyy IFC4X3:ssa ja `ifcopenshell.validate` palauttaa 0 errors.
- [ ] Task 3: laajenna `convert_dxf` ja CLI:n `dxf2ifc convert ... --schema=ifc4x3`-flag (default `ifc4`); GUI:ssa toistaiseksi defaultaa `ifc4`. Failing-testi: CLI-mock `--schema=ifc4x3` → IFC:n schema-attribuutti vastaa.
- [ ] Task 4: päivitä `validate_ifc.summary` näyttämään dynaamisesti `ifc.schema` (jo tekee — varmista test joka antaa molemmat skeemat ja odottaa "IFC4X3"-stringin summarystä).

## Section 2: RAVA-koodien lataaminen (4 codesetin sync)

- [ ] Task 5: lisää `tools/rava/sync_codes.py` joka lataa neljästä `koodistot.suomi.fi`-codesetistä (LVI-TUOTEOSA, LVI-JARJESTELMA, TALOTEKNIIKKA-TUOTEOSA, TALOTEKNIIKKA-JARJESTELMA) JSON:n ja persistoi `src/dxf2ifc/profiles/rava/<scheme>.json`-tiedostoiksi. Käytä virallista API:a `https://koodistot.suomi.fi/codelist-api/api/v1/coderegistries/rytj/codeschemes/<scheme>_Versio_1_0/codes`. Failing-testi: monkeypatchattu requests.get → 4 JSON:n kirjoitus tarkistettu.
- [ ] Task 6: commitoi 4 RAVA-codeset-JSON:ää (`lvi_tuoteosa.json`, `lvi_jarjestelma.json`, `talotekniikka_tuoteosa.json`, `talotekniikka_jarjestelma.json`) `src/dxf2ifc/profiles/rava/`:hen Lauri:n kautta tehtävän sync-ajon jälkeen. Failing-testi: kaikki 4 JSON:ää eksistoi + `RAVA_CODES["T-LVI-01-01-023"]["name"]` (höyrystin) on suomenkielinen string.
- [ ] Task 7: kirjoita `dxf2ifc.profiles.rava.loader.load_rava_codes()` joka palauttaa dict[code → RAVACode-dataclass] (code, name, codeset). Failing-testi: höyrystin = `T-LVI-01-01-023`, kompressori = `T-LVI-01-01-017`, lauhdutin = `T-LVI-01-01-018` löytyvät loadatusta dictistä.

## Section 3: Profile-skeeman domain-laajennus

- [ ] Task 8: laajenna `Rule`-pydantic-malli kentillä `domain: Literal["ARK", "TATE"]` (pakollinen) ja `lvi_code: str | None`, `talotekniikka_code: str | None`. Lisää `model_validator` joka tarkistaa: domain="ARK" → talo2000_code pakollinen, lvi/talotekniikka tyhjät; domain="TATE" → tasan yksi lvi_code TAI talotekniikka_code, talo2000_code tyhjä. Failing-testit: 4 validation-skenaariota.
- [ ] Task 9: päivitä `loader.dump_profile` ja `load_profile` kirjoittamaan ja lukemaan uudet kentät (TOML round-trip). Failing-testi: TOML jossa domain="TATE" + lvi_code → loader säilyttää, dumper kirjoittaa ne takaisin.
- [ ] Task 10: lisää `MappedEntity`-dataclassiin `domain: str`, `lvi_code: str | None`, `talotekniikka_code: str | None`. Failing-testi: `apply_profile`:ssa domainin välitys MappedEntityyn.

## Section 4: Default-profiilin uudistus + KYL-* siirto RAVAan

- [ ] Task 11: nimeä `default_kylmalaite_talo2000.toml` → `default_kylmalaite.toml` git-historian säilyttämiseksi (`git mv`). Päivitä `loader.load_default_profile()` viittaamaan uuteen tiedostoon. Failing-testi: load_default_profile() onnistuu uudella nimellä, vanhalla nimellä syntyy `FileNotFoundError`.
- [ ] Task 12: merkitse jokainen ARK-sääntö (seinät / laatat / ovet / ikkunat / paneelit / pilarit / kaiteet / portaat / kalusteet / ARK-prefix-säännöt) `domain = "ARK"`-kentällä; säilytä Talo2000-koodit. Failing-testi: jokainen rule sisältää domainin ja kaikki ARK-säännöt valid.
- [ ] Task 13: korvaa kylmälaitesäännöt (HOYRYSTIN/LAUHDUTIN/KOMPRESSORI/jäähdytyskoneikot/säiliöt) `domain = "TATE"` + `lvi_code` -kentillä virallisten RAVA-koodien mukaan: höyrystin `T-LVI-01-01-023`, lauhdutin `T-LVI-01-01-018`, kompressori `T-LVI-01-01-017`, jäähdytyskompressorikoneikko `T-LVI-01-01-005`, vedenjäähdytyskone `T-LVI-01-01-003`, kompressorilauhdutin `T-LVI-01-01-019`, välijäähdytin `T-LVI-01-01-024`, kylmävesiasema `T-LVI-01-01-004`, kylmäainevaraajasäiliö `T-LVI-03-07-012`. Failing-testi: HOYRYSTIN-sääntö palauttaa lvi_code "T-LVI-01-01-023".
- [ ] Task 14: korvaa kylmäaineputket (LT IMU / MT IMU / MT NESTE / KYL-VIEMARI*) `domain = "TATE"` + yleinen `lvi_code = "T-LVI-02"`-kategoria + erottelu pset_overrides:lla. Korvaa kaapelihylly `domain = "TATE"` + `talotekniikka_code = "T-TATE-01-01-001"`. Failing-testi: pipe-säännöt saavat T-LVI-02 lvi_codena.

## Section 5: Mapper + ifc_writer domain-pohjainen luokitus

- [ ] Task 15: laajenna `add_talo2000_classification` → `add_classification(ifc, product, *, domain, code, name)` joka tuottaa `IfcClassification.Name = "Talo2000" | "RAVA-LVI" | "RAVA-TATE"` domainin mukaan ja luo IfcRelAssociatesClassification-relaation. Failing-testi: TATE-domain emittaa IfcClassification "RAVA-LVI", ARK säilyy "Talo2000".
- [ ] Task 16: päivitä convert_dxf-orchestrator kutsumaan `add_classification` MappedEntityn domain + koodi-kenttien mukaan; varmista että multi-classification on KIELLETTY (yksi codeset per element). Failing-testi: HOYRYSTIN-fixture → IfcEvaporator linkitetty vain RAVA-LVI:hen, EI Talo2000:een.
- [ ] Task 17: päivitä `quality.validate_ifc` Talo2000-warningi domain-tietoiseksi: ARK-elementit vaativat Talo2000-luokituksen, TATE-elementit vaativat RAVA-LVI- tai RAVA-TATE-luokituksen. Failing-testi: TATE-pipe ilman RAVA-luokitusta → warning "missing RAVA classification".

## Section 6: Integraatio + dokumentointi + plan-loppupiste

- [ ] Task 18: päivitä full-fixture- ja integration-testit odottamaan IFC4X3 + domain-pohjaisia luokituksia (ARK Talo2000, TATE RAVA). Päivitä `EXPECTED_TALO2000_CODES` ja lisää `EXPECTED_RAVA_LVI_CODES` (höyrystin/lauhdutin/kompressori).
- [ ] Task 19: päivitä `tools/solibri/dxf2ifc.bcfzip` rule-set: lisää sääntö "RAVA classification coverage" joka vaatii TATE-elementeille RAVA-LVI/RAVA-TATE-linkin. Päivitä `docs/solibri-rules.md` ja `tests/test_solibri_bcfzip.py`.
- [ ] Task 20: päivitä `tests/fixtures/solibri_reference_full.ifc` baseline IFC4X3:lle uudella default-profiililla (rebuild via `tools/solibri/build_reference_ifc.py`); päivitä `tests/snapshots/solibri/full_kylmaelement.json`-baseline jos tarvitaan.
- [ ] Task 21: kirjoita `docs/rava-classification.md` joka kuvaa domainit, RAVA-codeset:t ja virallisen JSON-API:n. Linkitä `docs/quality-gates.md`-tiedostoon.
- [ ] Task 22: plan-loppupiste — `pytest -q --tb=short` (kaikki passed), `pytest --cov=dxf2ifc --cov-report=term -q` ≥80%, `ruff check . && ruff format --check .` puhdas. Päivitä CLAUDE.md status: "Plan H valmis (<SHA>)" + Plan G:hen siirtyminen. Päivitä README.md status-taulu + Plan G "Plan H:n jälkeen" -merkki.
