---
plan: F
title: Solibri spec verification + IFC quality gates
status: draft
date: 2026-04-28
depends_on: E
---

# Plan F: Solibri-spec-verifiointi + IFC quality gates

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps käyttävät `- [ ]`-syntaksia. Solibri Anywhere on Lauri-hostattu desktop-tool — automaation tasot eroavat: `ifcopenshell.validate` ajaa CI:ssä, Solibri-rule-validointi on Lauri-driven manuaaliprosessi jolla on dokumentoitu rule-set + raportointiformaatti. TDD-kuri sovelletaan tooling-koodissa (rule-set-loader, raportin parsija, CI-step), validoinnin sisältö verifioidaan referenssimallin kautta.

**Goal:** Varmista että dxf2ifc:n tuottamat IFC 4 -tiedostot läpäisevät YTV 2012 + Talo2000 -vaatimukset suomalaisessa BIM-validointityönkulussa. Tarjoa kaksitasoinen quality gate: (1) kevyt automaattinen `ifcopenshell.validate` joka ajaa CI:ssä joka push:lla; (2) raskas Solibri-rule-validointi joka ajaa Lauri-driven manuaalitestissä jokaista release-candidate:a vasten ja jonka tulokset checkataan repoon snapshot-raporttina.

**Architecture:** `tools/solibri/`-kansio joka sisältää (a) `dxf2ifc.bcfzip`-rule-setin BCF-formaatissa, (b) `verify.py`-skripti joka ajaa `solibri-cli`:n (Solibri Anywhere CLI) annettua IFC:tä vasten ja kirjoittaa raportin `reports/`:iin, (c) `parse_report.py` joka muuntaa Solibrin XML-raportin pythonia ystävällisempään dict:iin. CI:ssä ifcopenshell.validate ajaa kaikille tuotetuille IFC:lle (full-fixture + simple_wall) ja epäonnistuu kovan virheen kohdalla. Solibri-snapshot tallennetaan `tests/snapshots/solibri/`:iin git-LFS:ää käyttämättä (XML on pieni).

**Tech stack:** Solibri Anywhere CLI (Windows-only), `ifcopenshell.validate` (jo riippuvuus), `lxml` raportin parsintaan, CI matrix Linux-runnerilla automaattiseen tasoon.

---

## Repository state before this plan

Plan A 21/21 + Plan B 50/50 + Plan C 12/12 + Plan D 25/25 + Plan E 23/23 valmis (master `b27b8c6`). 246 testiä passed, coverage 89 %, ruff clean. Windows .exe jaetaan tag-pohjaisen draft-releasen kautta GitHub Actions -workflow:lla. Default-profiili tuottaa kaikkien 11 Talo2000-elementtityypin IFC-entiteetit + 4 IfcSystem-ryhmää.

---

## Section 1: Automaattinen ifcopenshell.validate -gate

- [ ] Task 1: lisää `src/dxf2ifc/core/quality.py` `validate_ifc(path) -> ValidationReport` -wrapper joka kutsuu `ifcopenshell.validate.validate(file, json=True, return_json=True)` ja palauttaa structured-tuloksen (errors-lista + summary). TDD: failing-testi `tests/test_quality.py` joka antaa Plan B:n full-fixture-IFC:n ja odottaa `len(report.errors) == 0`.
- [ ] Task 2: laajenna `quality.validate_ifc` raportoimaan myös YTV-spesifit tarkistukset: kaikki IfcWall / IfcSlab / IfcDoor / IfcWindow -entiteetit pitää olla luokiteltu `IfcRelAssociatesClassification` Talo2000-koodilla. Failing-testi: profiili joka tuottaa luokittelemattoman seinän → report.warnings sisältää "missing Talo2000 classification".
- [ ] Task 3: lisää CLI-flag `dxf2ifc convert --validate` joka kutsuu `validate_ifc` muunnoksen jälkeen ja exit-koodi 1 jos errors > 0. Failing-testi: simple_wall.dxf + custom-profile joka generoi virheellisen IFC:n → CLI palauttaa 1 ja stderr sisältää virheen kuvaus.
- [ ] Task 4: lisää orchestrator-options `convert_dxf(..., validate: bool = False)` joka palauttaa `(IfcFile, ValidationReport | None)`. Päivitä GUI MainWindow näyttämään report.errors PreviewLogPanelissa convert-vaiheen jälkeen jos validate=True. Failing-testi: GUI-mock convert+validate, error-rivi näkyy preview-lokissa.

## Section 2: Solibri rule-set ja referenssimallit

- [ ] Task 5: luo `tools/solibri/dxf2ifc.bcfzip` BCF 2.1 -formaatissa joka sisältää YTV 2012 + Talo2000 -minimiruleset:in. Lähde: Solibri Anywhere "Talo2000 classification" -ruleset + manuaalisesti laaditut YTV-säännöt (units, classification coverage, IfcSystem-grouping). Tiedostot binäärimuodossa `tools/solibri/`-kansiossa.
- [ ] Task 6: luo `tests/fixtures/solibri_reference_full.ifc` joka on Granlund/Sweco-referenssi-IFC pelkistettynä (yksi seinä per Talo2000-koodi, yksi laite per kylmälaitetyyppi) — käytetään Solibri-tarkistuksen "tämä pitäisi mennä läpi"-baseline:ksi. Failing-testi: load-test joka varmistaa fixture loadattavissa ifcopenshell:llä.
- [ ] Task 7: dokumentoi `docs/solibri-rules.md`:ssä jokainen rule-set-sääntö suomeksi: nimi, mitä validoi, viite YTV-osaan tai RT-korttiin. Lukijan pitää pystyä ymmärtämään pelkkänä tekstinä mitä Solibri tarkistaa ilman että avaa Solibrin.

## Section 3: solibri-cli runner + raportin parsija

- [ ] Task 8: kirjoita `tools/solibri/verify.py` joka kutsuu Solibri Anywhere CLI:tä (`Solibri.exe -load $ifc -ruleset $bcfzip -output $report.xml -exit`) Windows-hostissa. TDD: failing-testi mock-subprocessilla joka varmistaa että komennon argumentit ovat oikein muodostettu — itse Solibri-prosessia ei ajeta CI:ssä.
- [ ] Task 9: kirjoita `tools/solibri/parse_report.py` joka parsii Solibrin XML-raportin (lxml) listaksi `RuleResult`-dictejä (rule_name, severity, ifc_guid, message). Failing-testi: pieni mock-XML-fixture (`tests/fixtures/solibri_report_sample.xml`) → parsija palauttaa odotetut entry:t.
- [ ] Task 10: lisää `python -m dxf2ifc.tools.solibri verify input.ifc output.xml` -CLI-entry joka ketjuttaa verify.py + parse_report.py. Vaatii Solibri Anywhere -asennuksen, sandboxissa skip-marker. Failing-testi: ilman Solibri:ä CLI palauttaa selkeän virheen "Solibri.exe not found in PATH".

## Section 4: Snapshot-raportit + diffaus

- [ ] Task 11: tallenna `tests/snapshots/solibri/full_kylmaelement.json` baseline-raportti joka generoidaan kerran Lauri-driven manuaalitestissä (Solibri Anywhere) full_kylmaelement-fixture:lle ja committoidaan reposta. Failing-testi: snapshot-tiedosto on JSON jonka skeema vastaa parse_report.py:n outputtia.
- [ ] Task 12: kirjoita `tools/solibri/diff_snapshot.py` joka vertaa uutta raporttia baseline:iin ja palauttaa erot (uudet rule-failurit, kadonneet rule-passit). Failing-testi: kaksi mock-raporttia → diff palauttaa odotetut delta-entry:t.
- [ ] Task 13: lisää `pytest`-marker `@pytest.mark.solibri` joka skipautuu jos `Solibri.exe` ei ole PATH:ssa, ja `tests/test_solibri_snapshot.py` joka markerin alla ajaa täyden ketjun (verify → parse → diff vs. baseline) — Lauri-driven CI-target. Default ei aja.

## Section 5: CI-integraatio + dokumentaatio + plan-loppupiste

- [ ] Task 14: laajenna `.github/workflows/build.yml` ajamaan `pytest tests/test_quality.py -q` Linux-jobissa kun Section 1 valmis. ifcopenshell.validate-gate ei vaadi Solibri-asennusta. Failing-testi: workflow-tiedoston yaml-skeema sisältää quality-step:n ennen artifact-uploadia.
- [ ] Task 15: lisää `docs/quality-gates.md` joka kuvaa kahden tason gate-prosessin: (a) automaattinen ifcopenshell.validate joka ajaa CI:ssä joka push:lla, (b) manuaalinen Solibri-snapshot-verify Lauri-driven ennen jokaista tag-releasea. Linkitä `docs/packaging-smoke.md`-checklistiin.
- [ ] Task 16: plan-loppupiste — aja `pytest -q --tb=short` (kaikki passed), `pytest --cov=dxf2ifc --cov-report=term -q` ≥80%, `ruff check . && ruff format --check .` puhdas. Päivitä CLAUDE.md status: "Plan F valmis (<SHA>)". Päivitä README.md status-taulu Plan F ✅. Plan G:lle siirrytään PLAN-TRANSITIONissa (Coordinate System & Georeferenced IFC).
