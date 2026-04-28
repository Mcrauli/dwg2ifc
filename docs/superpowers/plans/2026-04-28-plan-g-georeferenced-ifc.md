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

- [ ] Task 1: lisää `src/dxf2ifc/profiles/schema.py`:hen `CRSConfig`-pydantic-malli kentin: `epsg_code: str = "EPSG:3067"`, `name: str = "ETRS-TM35FIN"`, `geodetic_datum: str = "ETRS89"`, `eastings_mm: float`, `northings_mm: float`, `orthogonal_height_mm: float = 0.0`, `x_axis_abscissa: float = 1.0`, `x_axis_ordinate: float = 0.0`, `scale: float = 1.0`. Failing-testit: defaultit + serialization + invalid scale (<= 0) heittää ValueError.
- [ ] Task 2: laajenna `Profile`-malli kentin `crs: CRSConfig | None = None` ja `storey_z_levels_mm: list[float] = Field(default_factory=lambda: [0.0])`. Pydantic-validator: storey_z_levels_mm strictly increasing + jokainen 0 ≤ z ≤ 100000 mm; vähintään 1 alkio. Failing-testit: 3 case (default 1-storey, 3-storey [0, 3500, 7000], invalid descending list).
- [ ] Task 3: päivitä `profiles/loader.py` `load_profile` + `dump_profile` round-trippaamaan crs-objekti ja storey_z_levels_mm-lista TOML:n läpi. Failing-testi: Profile crs:llä → dump → load → identtinen, ja default-profile (ei crs:ää) round-trippaa None:n eikä emit:tä `[crs]`-osiota.
- [ ] Task 4: lisää `src/dxf2ifc/profiles/default_kylmalaite.toml`-tiedostoon kommentoitu `[crs]`-osio (esimerkki Helsinki-keskustan ETRS-TM35FIN-arvoilla, eastings 25496000, northings 6672000) + `storey_z_levels_mm = [0.0]` (yksi kerros default). Failing-testi: default profile load → `profile.crs is None` (kommentoitu) ja `profile.storey_z_levels_mm == [0.0]`.

## Section 2: IfcProjectedCRS + IfcMapConversion -kirjoitus skeletoniin

## Section 3: Site → Building → Storey -placement-hierarkia

## Section 4: Element-add-funktiot kerros-aware + orchestrator dispatch storeyhin

## Section 5: CLI + GUI georeferenssi-input + validointi (max_coord + MapConversion-required)

## Section 6: Integraatio + dokumentointi + plan-loppupiste
