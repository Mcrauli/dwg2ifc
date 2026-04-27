---
plan: C
title: IfcSystem-ryhmittely kylmäjärjestelmille
status: draft
date: 2026-04-27
depends_on: B
---

# Plan C: IfcSystem grouping for refrigeration networks

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps käyttävät checkbox (`- [ ]`) syntaksia. TDD per task: failing test → minimal impl → pass → commit → push.

**Goal:** Ryhmittele Plan B:n tuottamat MEP-elementit (putket, laitteet, kaapelihyllyt) loogisiksi `IfcSystem`-järjestelmiksi (esim. "Refrigeration LT", "Refrigeration MT", "Drainage", "Cable carriers") niin että BIM-tarkastelija näkee kytkennät yhdellä silmäyksellä eikä ainoastaan irrallisia segmenttejä.

**Architecture:** Lisää profiilisääntöön `system_name`-kentän käyttö (jo olemassa Rule-skeemassa) → kerätään orchestrator-koodissa per-system kontekstit → luodaan IfcSystem-objekti per uniikki nimi → kytketään elementit IfcRelAssignsToGroupilla. Ei kosketa profile/reader/geometry-tasoa.

**Tech stack:** Sama kuin Plan B:ssä.

---

## Repository state before this plan

Plan A 21/21 + Plan B 50/50 valmis (master `2494841`). 143 testiä passed, coverage 91 %, ruff clean. Default-profiilin Section 6/7/9/11 säännöt eivät vielä määrittele `system_name`-kenttää — Plan C aktivoi sen ja lisää orchestrator-tason ryhmittelyn.

---

## Section 1: Profiili — system_name -arvot

- [x] Task 1: lisää `system_name = "Refrigeration LT"` LT IMU -sääntöön ja `"Refrigeration MT"` MT IMU + MT NESTE -sääntöihin default-profiilissa, päivitä loader-testi.
- [x] Task 2: lisää `system_name = "Drainage"` KYL-VIEMARI*-sääntöön ja `"Cable carriers"` KAAPELIHYLLY*-sääntöön, päivitä loader-testi.
- [x] Task 3: lisää `system_name = "Refrigeration plant"` HOYRYSTIN/LAUHDUTIN/KOMPRESSORI INSERT-sääntöihin, päivitä loader-testi.

## Section 2: Mapper — system_name extra_propsiin

- [x] Task 4: kirjoita failing test joka rakentaa Profile + Rule(system_name="X"), ajaa `apply_profile` ja varmistaa `MappedEntity.extra_props["system_name"] == "X"`. Tarkista että nykyinen mapper.apply_profile (joka jo siirtää system_name extra_propsiin) kestää testin.
- [x] Task 5: laajenna mapper-testi käyttämään default-profiilia ja varmista että LT IMU / KYL-VIEMARI / KAAPELIHYLLY / HOYRYSTIN -EntityRecordit saavat eri system_name-arvot extra_propsiinsa.

## Section 3: ifc_writer.add_system + group assignment

- [x] Task 6: kirjoita failing test `tests/test_ifc_writer.py`:hen `add_system(ifc, *, name)`-funktiolle joka luo IfcSystem entiteetin ja palauttaa sen.
- [x] Task 7: lisää `add_system` toteutus `ifc_writer.py`:hen (käytä `ifcopenshell.api.run("root.create_entity", ifc_class="IfcSystem", name=name)` ja varmista että kerran-per-name -caching toimii).
- [ ] Task 8: lisää `assign_to_system(ifc, products, system)`-helper joka käyttää `ifcopenshell.api.run("group.assign_group", ...)` tai luo IfcRelAssignsToGroup manuaalisesti, ja vastaava testi.

## Section 4: Orchestrator — kerää ja kytke

- [ ] Task 9: laajenna `convert_dxf` keräämään dict[system_name → list[product]] kun MappedEntityillä on extra_props["system_name"]. Failing test joka varmistaa että kerätyt järjestelmät ovat oikein.
- [ ] Task 10: lopuksi luo IfcSystem per kerätty nimi ja kytke products `assign_to_system`:llä. Integraatiotesti varmistaa että per-system-relaatiot löytyvät IFC:stä.

## Section 5: Integraatio + lint

- [ ] Task 11: laajenna `tests/test_integration_full.py` varmistamaan että `IfcSystem` 'Refrigeration LT' / 'Drainage' / 'Cable carriers' / 'Refrigeration plant' löytyvät full-fixture-IFC:stä ja että jokaisella on ≥1 jäsen IfcRelAssignsToGroup-relaation kautta.
- [ ] Task 12: ruff clean + `pytest --cov` ≥85 %, päivitä README/CLAUDE.md "Plan C valmis" -merkki.
