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

## Section 2: VS / lasiväliseinät (1311 / 1312)

- Task: lisää default-profiiliin säännöt `KYL-VALISEINA → IfcWall PARTITIONING 1311` ja `KYL-LASIVALISEINA → IfcWall PARTITIONING 1312` (Plan A vastaava: Task 6).
- Task: kirjoita `tests/test_mapper.py`:hen failing test joka asettaa molemmille layereille oikean Talo2000-koodin + PredefinedType-arvon (Plan A vastaava: Task 14).
- Task: laajenna `ifc_writer.add_wall` ottamaan vastaan `predefined_type`-parametrin ja asettamaan `IfcWall.PredefinedType` (default STANDARD, partition-säännöillä PARTITIONING) (Plan A vastaava: Task 17).
- Task: päivitä integraatiotestifixtuuri (DXF) sisältämään yksi VS-viiva ja varmista että IFC:ssä syntyy IfcWall PARTITIONING -elementti Talo2000 1311 -classification refillä (Plan A vastaava: Task 20).

## Section 3: Laatat AP / VP / YP (1221 / 1235 / 1236)

- Task: lisää default-profiiliin säännöt `KYL-ALAPOHJA → IfcSlab FLOOR 1221`, `KYL-VALIPOHJA → IfcSlab FLOOR 1235`, `KYL-YLAPOHJA → IfcSlab ROOF 1236` (Plan A vastaava: Task 6).
- Task: laajenna `dxf_reader.py` lukemaan suljetut LWPOLYLINE-entiteetit (lähtökohta laattareunalle) ja palauttamaan `PolygonGeometry`-tyyppi `types.py`:ssä (Plan A vastaava: Task 11 + 4).
- Task: kirjoita `tests/test_geometry.py`:hen `polygon_to_slab_extrusion` -failing test ja toteuta funktio `geometry.py`:hen (alas-extrudointi paksuuteen profiilista) (Plan A vastaava: Task 15).
- Task: lisää `ifc_writer.add_slab` joka tuottaa IfcSlab + PredefinedType (FLOOR/ROOF) + Talo2000-classification, ja test_ifc_writer.py-kattavuus (Plan A vastaava: Task 17).
- Task: laajenna `convert_dxf` orchestrator dispatchaamaan slab-rule entiteetit `add_slab`-kutsuun (Plan A vastaava: Task 18).

## Section 4: Ovet — ulko-, väli-, erityisovet (1243 / 1315 / 1316)

- Task: lisää default-profiiliin INSERT-säännöt `OVI-ULKO → IfcDoor 1243`, `OVI-VALI → IfcDoor 1315`, `OVI-ERITYIS → IfcDoor 1316` korkeus/leveys-attribuuttimappauksella (Plan A vastaava: Task 6).
- Task: laajenna `dxf_reader.py` lukemaan INSERT-entiteetit (block name, insertion point, rotation, scale) ja palauttamaan `BlockInstance`-tyyppi `types.py`:ssä (Plan A vastaava: Task 11 + 4).
- Task: kirjoita `tests/test_geometry.py`:hen `door_block_to_box` -failing test ja toteuta funktio joka tuottaa IfcDoor-paramater-laatikon (height/width profiilista tai INSERT-attribuutista) (Plan A vastaava: Task 15).
- Task: lisää `ifc_writer.add_door` (IfcDoor + PredefinedType + OverallHeight/Width + Talo2000-classification) ja test_ifc_writer.py-kattavuus (Plan A vastaava: Task 17).
- Task: ohjaa orchestratorista oviblokit `add_door`-kutsuun ja päivitä integraatiotesti DXF-fixtuurilla joka sisältää OVI-ULKO-blokin (Plan A vastaava: Task 18 + 20).

## Section 5: Ikkunat (1242)

- Task: lisää default-profiiliin INSERT-sääntö `IKKUNA → IfcWindow 1242` korkeus/leveys-attribuuttimappauksella (Plan A vastaava: Task 6).
- Task: kirjoita `tests/test_mapper.py`:hen failing test joka mappaa IKKUNA-blokin → IfcWindow-tyyppi + Talo2000 1242 (Plan A vastaava: Task 14).
- Task: lisää `ifc_writer.add_window` (IfcWindow + OverallHeight/Width + classification) + test_ifc_writer.py-kattavuus (Plan A vastaava: Task 17).
- Task: dispatchaa orchestrator window-rule blokit `add_window`-kutsuun ja laajenna integraatiotesti yhdellä IKKUNA-blokilla (Plan A vastaava: Task 18 + 20).

## Section 6: Kylmäputket (21xx, IfcPipeSegment)

- Task: lisää default-profiiliin LINE-säännöt `LT IMU`, `MT IMU`, `MT NESTE` → `IfcPipeSegment` Talo2000 21xx -alakoodeilla (placeholder kunnes RT-tarkennus saatavilla) ja DN-attribuuttikenttä (Plan A vastaava: Task 6).
- Task: kirjoita `tests/test_geometry.py`:hen `line_to_pipe_segment` -failing test ja toteuta funktio joka tuottaa cylinder-extrudoidun geometrian DN-halkaisijalla (Plan A vastaava: Task 15).
- Task: lisää `ifc_writer.add_pipe_segment` (IfcPipeSegment + IfcPipeSegmentType refrigeranttipredefined + Talo2000) + test_ifc_writer.py-kattavuus (Plan A vastaava: Task 17).
- Task: dispatchaa orchestrator pipe-rule LINE-entiteetit `add_pipe_segment`-kutsuun ja laajenna integraatiotesti LT IMU -viivalla (Plan A vastaava: Task 18 + 20).
