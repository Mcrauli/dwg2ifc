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

## Section 2: Mapper — system_name extra_propsiin

## Section 3: ifc_writer.add_system + group assignment

## Section 4: Orchestrator — kerää ja kytke

## Section 5: Integraatio + lint
