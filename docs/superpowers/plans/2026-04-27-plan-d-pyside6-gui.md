---
plan: D
title: PySide6 GUI for dxf2ifc
status: draft
date: 2026-04-27
depends_on: C
---

# Plan D: PySide6 desktop GUI

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps käyttävät checkbox (`- [ ]`) syntaksia. TDD per task missä mahdollista (Qt-UI:lle pytest-qt + offscreen platform); ei-testattavat resurssitehtävät committaa silti pienen visuaalisen tarkistuksen jälkeen.

**Goal:** Tee dxf2ifc:n päälle PySide6-pohjainen työpöytä-GUI joka wrappaa Plan A–C:n CLI-corea ja tarjoaa: (1) DXF-tiedoston valinta, (2) konversion ajo IFC:ksi yhden klikkauksen takana, (3) status- ja virheraportointi, (4) layer-preview joka listaa DXF:n layerit + niiden Talo2000-mappauksen, (5) profiilin editori joka antaa lisätä custom layer→IFC-sääntöjä ilman TOML-tiedoston käsin muokkaamista.

**Architecture:** GUI-koodi elää `src/dxf2ifc/gui/`-paketissa, kutsuu olemassa olevia `core/`-funktioita suoraan (`convert_dxf`, `read_dxf`, `apply_profile`) ja `profiles/`-loaderia. Ei muutoksia public coreen — ainoa lisäys on `Profile.to_toml(...)` -helper jos se puuttuu. QSS keskitetty `gui/style.qss` -resurssitiedostoon, fontit `assets/fonts/`-kansioon. CLAUDE.md:n design-sectionin värit ja typografia ovat ehdotuksellisia.

**Tech stack:** PySide6 6.7+, pytest-qt 4+, ruff, ifcopenshell + ezdxf (jo olemassa).

---

## Repository state before this plan

Plan A 21/21 + Plan B 50/50 + Plan C 12/12 valmis (master `8cc4fc3`). 151 testiä passed, coverage 91 %, ruff clean. Core-API on stabiili (`convert_dxf` palauttaa `dict[str, list]`-systems-mappingin) ja default-profiili kattaa kaikki tarvittavat layer-säännöt.

---

## Section 1: Bootstrap & dependencies

## Section 2: Brand assets (fontit, värit, QSS)

## Section 3: MainWindow + layout-runko

## Section 4: Convert-flow (DXF → IFC napilla)

## Section 5: Layer preview & mapping list

## Section 6: Profile editor (custom layer-säännöt)

## Section 7: Polish, packaging hooks, dokumentaatio
