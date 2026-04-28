---
plan: G
title: Coordinate System & Georeferenced IFC (ETRS-TM35FIN + IfcMapConversion)
status: draft
date: 2026-04-28
depends_on: H
---

# Plan G: Coordinate System & Georeferenced IFC

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps käyttävät `- [ ]`-syntaksia. Tämä plan lisää georeferenssin (IfcProjectedCRS + IfcMapConversion) ja täyden Site→Building→Storey→Element placement-hierarkian. Geometria pidetään LOCAL-koordinaateissa, world-sijainti syntyy MapConversionin kautta — kaksoismuunnos on kielletty.

**Goal:** Tuottaa Solibri/RAVA-yhteensopivat georefenced IFC-tiedostot suomalaiseen ETRS-TM35FIN (EPSG:3067) -tasokoordinaatistoon. Profiilissa määritellään Eastings/Northings + storey_z_levels, ja kaikki elementit asettuvat oikealle kerrokselle oikealle paikkansa kohdistuvana paikalliseen origo:oon. Georeferenssi tekee dxf2ifc:n kelvolliseksi BIM-luovutuksiin julkisen sektorin urakoissa, joissa CRS-tieto on vaatimuksena.

**Architecture:** Profile-skeemaan lisätään `CRSConfig` (eastings/northings + scale + rotation + storey_z_levels). `build_ifc_project_skeleton` saa `crs: CRSConfig | None`-parametrin: jos annettu, kirjoitetaan IfcProjectedCRS + IfcMapConversion. `IfcSite` siirtyy täydeksi placement-juureksi, sen alle IfcBuilding, sitten N×IfcBuildingStorey storey_z_levels:n mukaan. Element-add-funktiot (add_wall/add_slab/...) ottavat `storey: IfcBuildingStorey`-parametrin spatial-containmentiin. Geometria pysyy LOCAL-koordinaateissa (DXF:n koordinaatit suoraan), ei kaksoismuunnoksia. Validointi: max_coord ±10 km warning, IfcMapConversion-pakollinen jos CRS määritelty, geometria-vertexit ≤ profile.max_local_extent_mm.

**Tech stack:** ifcopenshell ≥ 0.8.5 (IFC4X3 tuettu Plan H:sta), pydantic (CRSConfig), tomli-w. Ei uusia juuri-deps:eja.

---

## Repository state before this plan

Plan A–F + H valmis. Master `<TBD>`. 302 ei-GUI testiä passed + 1 skipped (Solibri-marker). IFC4X3 + RAVA-luokitus käytössä Plan H:sta. Bugfix kierros 1+2+3 valmis.

---

## Section 1: CRSConfig profile-skeemaan + storey_z_levels

## Section 2: IfcProjectedCRS + IfcMapConversion -kirjoitus skeletoniin

## Section 3: Site → Building → Storey -placement-hierarkia

## Section 4: Element-add-funktiot kerros-aware + orchestrator dispatch storeyhin

## Section 5: CLI + GUI georeferenssi-input + validointi (max_coord + MapConversion-required)

## Section 6: Integraatio + dokumentointi + plan-loppupiste
