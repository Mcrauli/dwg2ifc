---
plan: B
title: Full element set — laajenna pipeline kattamaan loput 10 elementtityyppiä
status: draft
date: 2026-04-27
depends_on: A
---

# Plan B: Full element set

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps käyttävät checkbox (`- [ ]`) syntaksia. TDD per task: failing test → minimal impl → pass → commit → push.

**Goal:** Laajenna Plan A:n DXF→IFC-pipeline kattamaan kaikki 10 jäljellä olevaa Talo2000-elementtityyppiä (väliseinät, laatat, ovet, ikkunat, kylmäputket, viemäriputket, hyllyt, kaapelihyllyt, kylmäelementit, kylmälaitteet). Käytä Plan A:n kaavaa: laajenna profile → reader → mapper → geometry → ifc_writer-haarat → CLI ei muutu.

**Architecture:** Lisää uusia rule-tyyppejä `profiles/`-skeemaan (LINE/POLYLINE/CIRCLE/INSERT-block-tyypit), uusia geometriahaaroja `geometry.py`:hen ja uusia `add_<element>`-funktioita `ifc_writer.py`:hen. Mapper ja orchestrator dispatchaavat `ifc_type`-kentän perusteella.

**Tech stack:** Sama kuin Plan A:ssa (Python 3.12, ezdxf, ifcopenshell, pydantic, pytest, ruff).

---

## Repository state before this plan

Plan A 21/21 valmis (master `54140a5`). 41 testiä passed, ruff clean. Default-profiili kattaa vain `KYL-ULKOSEINA → IfcWall 1241`.

---

## Sections

1. Profile-skeeman laajennus (block-säännöt, monitasoiset attribuutit)
2. Section 2: VS / lasiväliseinät (Talo2000 1311 / 1312, IfcWall PARTITIONING)
3. Section 3: Laatat AP / VP / YP (1221 / 1235 / 1236, IfcSlab FLOOR/ROOF)
4. Section 4: Ovet — ulko-, väli-, erityisovet (1243 / 1315 / 1316, IfcDoor)
5. Section 5: Ikkunat (1242, IfcWindow)
6. Section 6: Kylmäputket LT IMU / MT IMU / MT NESTE (21xx, IfcPipeSegment)
7. Section 7: Viemäriputket KYL-VIEMARI (21xx DRAINPIPE, IfcPipeSegment)
8. Section 8: Varastointihyllyt KYL-LEVYHYLLY / TIKASHYLLY / KLHYLLYV (1331, IfcFurniture)
9. Section 9: Kaapelihyllyt (23xx, IfcFlowSegment + IfcCableCarrierSegmentType)
10. Section 10: Kylmähuone-elementit (1352, IfcBuildingElementProxy)
11. Section 11: Kylmälaitteet — höyrystin / lauhdutin / kompressori (25xx, IfcEvaporator / IfcCondenser / IfcCompressor)
12. Section 12: Integraatiotesti monielementtisellä DXF:llä + ruff/coverage-portti

---

<!-- Sectionien sisältö täytetään yksi kerrallaan PROGRESS.md:n ohjaamana. -->

## Section 1: Profile-skeeman laajennus

- Task: laajenna `profiles/schema.py` Rule-pydantic-malliin `entity_kind` (LINE/POLYLINE/CIRCLE/INSERT) ja `block_name` (vain INSERT-säännöille) (Plan A vastaava: Task 5).
- Task: lisää `profiles/schema.py`:hen `extrusion_height` ja `pset_overrides`-kentät, ja validointi joka vaatii `block_name` jos `entity_kind=INSERT` (Plan A vastaava: Task 5).
- Task: päivitä `profiles/loader.py` säilyttämään uudet kentät TOML-roundtripissä + lisää testi `tests/test_profile_schema.py` joka kattaa LINE+INSERT-säännöt (Plan A vastaava: Task 7).
- Task: laajenna `profiles/default_kylmalaite_talo2000.toml` placeholder-säännöillä joka elementtityypille (kommentoidut, täytetään myöhempinä sectioneina) (Plan A vastaava: Task 6).
