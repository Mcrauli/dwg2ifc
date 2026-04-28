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

- [ ] Task 5: laajenna `build_ifc_project_skeleton` ottamaan `crs: CRSConfig | None = None`-kwarg. Jos None, skeleton pysyy nykyisenä (ei georeferenssiä). Failing-testi: skeleton crs=None → ei IfcProjectedCRS-entiteettiä, mutta IFC-validate clean.
- [ ] Task 6: jos `crs` annettu, kirjoita `IfcProjectedCRS`-entity (Name=`epsg_code`, Description=`name`, GeodeticDatum=`geodetic_datum`, MapUnit=mm) ja kytke se `IfcGeometricRepresentationContext.HasCoordinateOperation`-kautta `IfcMapConversion`:iin (Eastings/Northings/OrthogonalHeight/XAxisAbscissa/XAxisOrdinate/Scale CRSConfigista). Failing-testit: crs-attribuutit IFC:ssä, IfcMapConversion linkki ProjectedCRS:ään, ifcopenshell.validate clean.
- [ ] Task 7: scale + orthogonal_height -edge-case-testit: CRSConfig orthogonal_height_mm=15000 (kerrostalon räystäs) ja scale=0.999 (korkeuskorjaus) → IfcMapConversion-arvot vastaavat (mm SI-yksikkö). Failing-testi: kahden CRS-konfiguraation pareittainen vertailu IFC-attribuutteihin.

## Section 3: Site → Building → Storey -placement-hierarkia

- [ ] Task 8: `build_ifc_project_skeleton` palauttaa nyt rakenteen `IfcSite → IfcBuilding → list[IfcBuildingStorey]` storey_z_levels_mm:n mukaan (nimet "Kerros 1", "Kerros 2", …). IfcLocalPlacement-ketju Site→Building→Storey on relatiivinen, Storey-Z syntyy `IfcAxis2Placement3D.Location[2]=z_level_mm`. Failing-testit: 1-storey-default, 3-storey-list, IfcLocalPlacement-parent-relaatiot.
- [ ] Task 9: lisää `resolve_storey(storeys: list[IfcBuildingStorey], z_mm: float) -> IfcBuildingStorey`-helper joka palauttaa korkeimman storeyn jonka z_level ≤ z (eli "kerros johon elementti kuuluu"). Edge case: z alle ensimmäisen → palauta storeys[0] + warning. Failing-testit: 5 case (alin, ylin, keskellä, alle alimman → fallback, tasan kerros-z:llä).
- [ ] Task 10: päivitä `build_ifc_project_skeleton`-tyyppisen funktion paluuarvot: dataclass `IfcSkeleton` (file, project, site, building, storeys, contexts). Päivitä kaikki kutsujat (convert_dxf, testit) käyttämään uutta tuplerakennetta (kaikki vanhat 1-storey-testit toimivat skeletons.storeys[0]:n kautta). Failing-testi: skeleton.storeys-kentän olemassaolo ja len.

## Section 4: Element-add-funktiot kerros-aware + orchestrator dispatch storeyhin

- [ ] Task 11: päivitä `add_wall` / `add_slab` / `add_door` / `add_window` / `add_pipe_segment` / `add_furniture` / `add_cable_carrier_segment` / `add_building_element_proxy` / `add_cooling_equipment` ottamaan `storey: IfcBuildingStorey`-parametri (kwarg, default = None → fallback ensimmäiseen storey:hin via `IfcSkeleton.storeys[0]`). Sisäinen IfcRelContainedInSpatialStructure linkitetään storey:hyn (ei enää suoraan building:iin). Failing-testit: kaksi storey:tä, jokainen add_* sijoittaa elementin oikeaan storey:hyn (RelContainedInSpatialStructure-RelatingStructure check).
- [ ] Task 12: laajenna `convert_dxf`-orchestrator: jokaiselle MappedEntity:lle resolvoi storey `resolve_storey(skeleton.storeys, entity_anchor_z_mm)`. Anchor-z = LineGeometry → `min(start.z, end.z)`, PolygonGeometry → `min(p.z for p in points)`, BlockInstance → `insertion_point.z`. Failing-testit: full-fixture jossa kerros-2-elementit (z=3500) menevät storeys[1]:een ja kerros-1 (z=0) storeys[0]:aan.
- [ ] Task 13: geometria-validaattori `validate_local_extent(skeleton, max_extent_mm: float = 5_000_000)` joka skannaa kaikki IfcShapeRepresentation-vertex-koordinaatit ja heittää RuntimeError jos local-koordinaatti ylittää max_extent (defensiivinen tarkistus kaksoismuunnos-bugille — geometria pysyy LOCAL, eli ei koskaan saisi olla 25_496_000:ssa). Failing-testit: clean-pass + simulated-double-transform → RuntimeError.

## Section 5: CLI + GUI georeferenssi-input + validointi (max_coord + MapConversion-required)

## Section 6: Integraatio + dokumentointi + plan-loppupiste
