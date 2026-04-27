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
2. VS / lasiväliseinät (Talo2000 1311 / 1312, IfcWall PARTITIONING)
3. Laatat AP / VP / YP (1221 / 1235 / 1236, IfcSlab FLOOR/ROOF)
4. Ovet — ulko-, väli-, erityisovet (1243 / 1315 / 1316, IfcDoor)
5. Ikkunat (1242, IfcWindow)
6. Kylmäputket LT IMU / MT IMU / MT NESTE (21xx, IfcPipeSegment)
7. Viemäriputket KYL-VIEMARI (21xx DRAINPIPE, IfcPipeSegment)
8. Varastointihyllyt KYL-LEVYHYLLY / TIKASHYLLY / KLHYLLYV (1331, IfcFurniture)
9. Kaapelihyllyt (23xx, IfcFlowSegment + IfcCableCarrierSegmentType)
10. Kylmähuone-elementit (1352, IfcBuildingElementProxy)
11. Kylmälaitteet — höyrystin / lauhdutin / kompressori (25xx, IfcEvaporator / IfcCondenser / IfcCompressor)
12. Integraatiotesti monielementtisellä DXF:llä + ruff/coverage-portti

---

## Section 1: Profile-skeeman laajennus

- [ ] Task 1: laajenna `profiles/schema.py` Rule-pydantic-malliin `entity_kind` (LINE/POLYLINE/CIRCLE/INSERT) ja `block_name` (vain INSERT-säännöille) (Plan A vastaava: Task 5).
- [ ] Task 2: lisää `profiles/schema.py`:hen `extrusion_height` ja `pset_overrides`-kentät, ja validointi joka vaatii `block_name` jos `entity_kind=INSERT` (Plan A vastaava: Task 5).
- [ ] Task 3: päivitä `profiles/loader.py` säilyttämään uudet kentät TOML-roundtripissä + lisää testi `tests/test_profile_schema.py` joka kattaa LINE+INSERT-säännöt (Plan A vastaava: Task 7).
- [ ] Task 4: laajenna `profiles/default_kylmalaite_talo2000.toml` placeholder-säännöillä joka elementtityypille (kommentoidut, täytetään myöhempinä sectioneina) (Plan A vastaava: Task 6).

## Section 2: VS / lasiväliseinät (1311 / 1312)

- [ ] Task 5: lisää default-profiiliin säännöt `KYL-VALISEINA → IfcWall PARTITIONING 1311` ja `KYL-LASIVALISEINA → IfcWall PARTITIONING 1312` (Plan A vastaava: Task 6).
- [ ] Task 6: kirjoita `tests/test_mapper.py`:hen failing test joka asettaa molemmille layereille oikean Talo2000-koodin + PredefinedType-arvon (Plan A vastaava: Task 14).
- [ ] Task 7: laajenna `ifc_writer.add_wall` ottamaan vastaan `predefined_type`-parametrin ja asettamaan `IfcWall.PredefinedType` (default STANDARD, partition-säännöillä PARTITIONING) (Plan A vastaava: Task 17).
- [ ] Task 8: päivitä integraatiotestifixtuuri (DXF) sisältämään yksi VS-viiva ja varmista että IFC:ssä syntyy IfcWall PARTITIONING -elementti Talo2000 1311 -classification refillä (Plan A vastaava: Task 20).

## Section 3: Laatat AP / VP / YP (1221 / 1235 / 1236)

- [ ] Task 9: lisää default-profiiliin säännöt `KYL-ALAPOHJA → IfcSlab FLOOR 1221`, `KYL-VALIPOHJA → IfcSlab FLOOR 1235`, `KYL-YLAPOHJA → IfcSlab ROOF 1236` (Plan A vastaava: Task 6).
- [ ] Task 10: laajenna `dxf_reader.py` lukemaan suljetut LWPOLYLINE-entiteetit (lähtökohta laattareunalle) ja palauttamaan `PolygonGeometry`-tyyppi `types.py`:ssä (Plan A vastaava: Task 11 + 4).
- [ ] Task 11: kirjoita `tests/test_geometry.py`:hen `polygon_to_slab_extrusion` -failing test ja toteuta funktio `geometry.py`:hen (alas-extrudointi paksuuteen profiilista) (Plan A vastaava: Task 15).
- [ ] Task 12: lisää `ifc_writer.add_slab` joka tuottaa IfcSlab + PredefinedType (FLOOR/ROOF) + Talo2000-classification, ja test_ifc_writer.py-kattavuus (Plan A vastaava: Task 17).
- [ ] Task 13: laajenna `convert_dxf` orchestrator dispatchaamaan slab-rule entiteetit `add_slab`-kutsuun (Plan A vastaava: Task 18).

## Section 4: Ovet — ulko-, väli-, erityisovet (1243 / 1315 / 1316)

- [ ] Task 14: lisää default-profiiliin INSERT-säännöt `OVI-ULKO → IfcDoor 1243`, `OVI-VALI → IfcDoor 1315`, `OVI-ERITYIS → IfcDoor 1316` korkeus/leveys-attribuuttimappauksella (Plan A vastaava: Task 6).
- [ ] Task 15: laajenna `dxf_reader.py` lukemaan INSERT-entiteetit (block name, insertion point, rotation, scale) ja palauttamaan `BlockInstance`-tyyppi `types.py`:ssä (Plan A vastaava: Task 11 + 4).
- [x] Task 16: kirjoita `tests/test_geometry.py`:hen `door_block_to_box` -failing test ja toteuta funktio joka tuottaa IfcDoor-paramater-laatikon (height/width profiilista tai INSERT-attribuutista) (Plan A vastaava: Task 15).
- [x] Task 17: lisää `ifc_writer.add_door` (IfcDoor + PredefinedType + OverallHeight/Width + Talo2000-classification) ja test_ifc_writer.py-kattavuus (Plan A vastaava: Task 17).
- [x] Task 18: ohjaa orchestratorista oviblokit `add_door`-kutsuun ja päivitä integraatiotesti DXF-fixtuurilla joka sisältää OVI-ULKO-blokin (Plan A vastaava: Task 18 + 20).

## Section 5: Ikkunat (1242)

- [x] Task 19: lisää default-profiiliin INSERT-sääntö `IKKUNA → IfcWindow 1242` korkeus/leveys-attribuuttimappauksella (Plan A vastaava: Task 6).
- [x] Task 20: kirjoita `tests/test_mapper.py`:hen failing test joka mappaa IKKUNA-blokin → IfcWindow-tyyppi + Talo2000 1242 (Plan A vastaava: Task 14).
- [x] Task 21: lisää `ifc_writer.add_window` (IfcWindow + OverallHeight/Width + classification) + test_ifc_writer.py-kattavuus (Plan A vastaava: Task 17).
- [x] Task 22: dispatchaa orchestrator window-rule blokit `add_window`-kutsuun ja laajenna integraatiotesti yhdellä IKKUNA-blokilla (Plan A vastaava: Task 18 + 20).

## Section 6: Kylmäputket (21xx, IfcPipeSegment)

- [x] Task 23: lisää default-profiiliin LINE-säännöt `LT IMU`, `MT IMU`, `MT NESTE` → `IfcPipeSegment` Talo2000 21xx -alakoodeilla (placeholder kunnes RT-tarkennus saatavilla) ja DN-attribuuttikenttä (Plan A vastaava: Task 6).
- [x] Task 24: kirjoita `tests/test_geometry.py`:hen `line_to_pipe_segment` -failing test ja toteuta funktio joka tuottaa cylinder-extrudoidun geometrian DN-halkaisijalla (Plan A vastaava: Task 15).
- [x] Task 25: lisää `ifc_writer.add_pipe_segment` (IfcPipeSegment + IfcPipeSegmentType refrigeranttipredefined + Talo2000) + test_ifc_writer.py-kattavuus (Plan A vastaava: Task 17).
- [x] Task 26: dispatchaa orchestrator pipe-rule LINE-entiteetit `add_pipe_segment`-kutsuun ja laajenna integraatiotesti LT IMU -viivalla (Plan A vastaava: Task 18 + 20).

## Section 7: Viemäriputket (21xx DRAINPIPE)

- [x] Task 27: lisää default-profiiliin LINE-säännöt `KYL-VIEMARI*` (wildcard) → `IfcPipeSegment DRAINPIPE` Talo2000 21xx -alakoodilla ja default-DN (Plan A vastaava: Task 6).
- [x] Task 28: laajenna `mapper.layer_matches` käsittelemään wildcard-suffix `*` (yksinkertainen prefix-match) ja lisää failing test (Plan A vastaava: Task 10).
- [x] Task 29: ohjaa `add_pipe_segment`-kutsuun PredefinedType-parametri (`DRAINPIPE` viemärille, `REFRIGERATION` kylmäputkelle) + test_ifc_writer.py-kattavuus (Plan A vastaava: Task 17).
- [x] Task 30: laajenna integraatiotesti yhdellä KYL-VIEMARI-LATTIA-viivalla joka tuottaa IfcPipeSegment DRAINPIPE (Plan A vastaava: Task 20).

## Section 8: Varastointihyllyt (1331, IfcFurniture)

- [x] Task 31: lisää default-profiiliin INSERT-säännöt `KYL-LEVYHYLLY → IfcFurniture 1331`, `KYL-TIKASHYLLY → IfcFurniture 1331`, `KLHYLLYV → IfcFurniture 1331` korkeus/leveys/syvyys-attribuuttimappauksella (Plan A vastaava: Task 6).
- [x] Task 32: kirjoita `tests/test_geometry.py`:hen `block_to_furniture_box` -failing test ja toteuta funktio (height/width/depth profiilista tai INSERT-attribuutista) (Plan A vastaava: Task 15).
- [ ] Task 33: lisää `ifc_writer.add_furniture` (IfcFurniture + box-representaatio + Talo2000 1331) + test_ifc_writer.py-kattavuus (Plan A vastaava: Task 17).
- [ ] Task 34: dispatchaa orchestrator furniture-rule blokit `add_furniture`-kutsuun ja laajenna integraatiotesti KYL-LEVYHYLLY-blokilla (Plan A vastaava: Task 18 + 20).

## Section 9: Kaapelihyllyt (23xx)

- [ ] Task 35: lisää default-profiiliin LINE-sääntö `KAAPELIHYLLY → IfcFlowSegment` Talo2000 23xx -alakoodilla ja leveys-attribuutti (Plan A vastaava: Task 6).
- [ ] Task 36: kirjoita `tests/test_geometry.py`:hen `line_to_cable_carrier` -failing test ja toteuta funktio joka tuottaa rectangular-profile extrudoinnin reittiviivaa pitkin (Plan A vastaava: Task 15).
- [ ] Task 37: lisää `ifc_writer.add_cable_carrier_segment` joka tuottaa IfcFlowSegment + IfcCableCarrierSegmentType CABLETRUNKINGSEGMENT typed-by relation + Talo2000-classification (Plan A vastaava: Task 17).
- [ ] Task 38: dispatchaa orchestrator cable-carrier-rule LINE-entiteetit `add_cable_carrier_segment`-kutsuun ja laajenna integraatiotesti yhdellä KAAPELIHYLLY-viivalla (Plan A vastaava: Task 18 + 20).

## Section 10: Kylmähuone-elementit (1352, IfcBuildingElementProxy)

- [ ] Task 39: lisää default-profiiliin POLYLINE-/INSERT-säännöt `KYL-LEVY*` (panel) ja `KYL-NURKKA*` (corner) → IfcBuildingElementProxy 1352 paksuus-attribuutilla (Plan A vastaava: Task 6).
- [ ] Task 40: kirjoita `tests/test_geometry.py`:hen `panel_to_proxy_solid` -failing test ja toteuta funktio joka extrudoi POLYLINE-reunan paksuudeksi (Plan A vastaava: Task 15).
- [ ] Task 41: lisää `ifc_writer.add_building_element_proxy` (IfcBuildingElementProxy + ProxyType.NOTDEFINED + Talo2000 1352 + ObjectType-string elementtitunnukseen) + test_ifc_writer.py-kattavuus (Plan A vastaava: Task 17).
- [ ] Task 42: dispatchaa orchestrator proxy-rule entiteetit `add_building_element_proxy`-kutsuun ja laajenna integraatiotesti KYL-LEVY-paneelilla (Plan A vastaava: Task 18 + 20).

## Section 11: Kylmälaitteet (25xx, IfcEvaporator / IfcCondenser / IfcCompressor)

- [ ] Task 43: lisää default-profiiliin INSERT-säännöt `HOYRYSTIN → IfcEvaporator`, `LAUHDUTIN → IfcCondenser`, `KOMPRESSORI → IfcCompressor` Talo2000 25xx -alakoodeilla (placeholder kunnes RT-tarkennus saatavilla) (Plan A vastaava: Task 6).
- [ ] Task 44: kirjoita `tests/test_mapper.py`:hen failing test joka mappaa kunkin blokin oikeaan IFC-tyyppiin + Talo2000-koodiin (Plan A vastaava: Task 14).
- [ ] Task 45: lisää `ifc_writer.add_cooling_equipment` joka dispatchaa IFC-tyypin perusteella (IfcEvaporator/IfcCondenser/IfcCompressor) + box-representation + Talo2000 + test_ifc_writer.py-kattavuus (Plan A vastaava: Task 17).
- [ ] Task 46: dispatchaa orchestrator equipment-rule blokit `add_cooling_equipment`-kutsuun ja laajenna integraatiotesti yhdellä HOYRYSTIN-blokilla (Plan A vastaava: Task 18 + 20).

## Section 12: Integraatio + lint

- [ ] Task 47: luo `tests/fixtures/full_kylmaelement.dxf`-fixtuuri (LISP-skripti tai ezdxf-buildtime) joka sisältää joka section 2–11 elementtityypin yhden esiintymän (Plan A vastaava: Task 8).
- [ ] Task 48: kirjoita `tests/test_integration_full.py` joka ajaa CLI:n full-fixture-DXF:llä, validoi `ifcopenshell.validate.validate()` ei-ERROR ja tarkistaa että jokainen Talo2000-koodi (1241/1311/1221/1235/1236/1242/1243/1315/1316/1331/1352/21xx/23xx/25xx) löytyy IFC:n classification-refeistä (Plan A vastaava: Task 20).
- [ ] Task 49: aja `ruff check` + `ruff format`, korjaa kaikki ongelmat ja varmista että `pytest --cov=dxf2ifc` näyttää ≥ 85 % coveragea (Plan A vastaava: Task 21).
- [ ] Task 50: päivitä `README.md` "Status"-sectionin Plan B -tehtävälista (numeroidut taskit) ja `CLAUDE.md` "Plans B–F" -kohta merkitsemään Plan B valmiiksi (Plan A vastaava: doc-päivitys).
