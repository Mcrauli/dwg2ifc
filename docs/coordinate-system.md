# Coordinate System & Georeferenced IFC

dxf2ifc kirjoittaa Plan G:stä lähtien georeferensoituja IFC-tiedostoja:
geometria säilyy LOCAL-koordinaateissa (origo lähellä mallin keskipistettä),
ja IFC-tiedostoon liitetään `IfcProjectedCRS` + `IfcMapConversion`-pari joka
kertoo Solibri- / Trimble-/InfraBIM-yhteensopiville työkaluille miten LOCAL
projisoidaan WORLD-koordinaatistoon.

## ETRS-TM35FIN -default (`EPSG:3067`)

Suomen virallinen projektioperhe rakennus- ja
infrahankkeissa on **ETRS-TM35FIN**, joka tunnetaan myös EPSG-koodilla
`EPSG:3067`. Tämä on dxf2ifc:n default-CRS — Helsingin keskustan
itäkoordinaatti (eastings) on noin 25 496 000 mm ja pohjoiskoordinaatti
(northings) noin 6 672 000 mm.

Profile-TOML:ssa kommentoitu osio (`[crs]`) sisältää nämä defaultit;
poista kommentit ja täytä eastings + northings projektisi koordinaateilla:

```toml
[crs]
epsg_code      = "EPSG:3067"
name           = "ETRS-TM35FIN"
geodetic_datum = "ETRS89"
eastings_mm    = 25496000.0
northings_mm   =  6672000.0
orthogonal_height_mm = 0.0
```

## IfcProjectedCRS — kenttäkonventio

dxf2ifc kirjoittaa `IfcProjectedCRS`-entiteetin seuraavin arvoin:

| Kenttä | Arvo | Esimerkki |
|---|---|---|
| `Name` | EPSG-koodi | `"EPSG:3067"` |
| `Description` | projektion ihmisluettava nimi | `"ETRS-TM35FIN"` |
| `GeodeticDatum` | datumin tunnus | `"ETRS89"` |

Tämä konventio on yhteensopiva Trimble Connect / Solibri Anywheren CRS-
parserien kanssa.

## IfcMapConversion — LOCAL → WORLD

`IfcMapConversion` linkittää mallin `IfcGeometricRepresentationContext`:n
("Model") `IfcProjectedCRS`-target-CRS:ään. Sen kentät:

- `SourceCRS` = mallin Model-konteksti (LOCAL-koordinaatisto)
- `TargetCRS` = `IfcProjectedCRS` (WORLD-koordinaatisto)
- `Eastings` / `Northings` = LOCAL-origon sijainti WORLD-koordinaateissa (mm)
- `OrthogonalHeight` = LOCAL z=0 -taso WORLD-korkeudessa (mm)
- `XAxisAbscissa` / `XAxisOrdinate` = LOCAL x-akselin suunta WORLD:ssä
  (oletus 1.0 / 0.0 — LOCAL X yhdensuuntainen WORLD itään)
- `Scale` = mahdollinen korkeus-korjauskerroin (oletus 1.0)

## Geometria pysyy LOCAL — kaksoismuunnos kielletty

**dxf2ifc kirjoittaa kaikki vertex-koordinaatit LOCAL-koordinaateissa.**
WORLD-projektio tehdään katselusovelluksessa ajonaikaisesti
`IfcMapConversion`:n perusteella. Jos geometriaan vahingossa upotetaan
WORLD-koordinaatit (esim. 25 496 000 mm), `IfcMapConversion` projisoi ne
*toisen kerran* — tämä on **double-transform-bug** ja tuottaa virheellisen
mallin.

dxf2ifc:n quality-gate (`validate_local_extent` + `validate_ifc`) tarkistaa
että yksikään `IfcCartesianPoint` ei ole yli 1 km origosta — jos ylittyy,
tulee varoitus `crs_possible_double_transform`. RuntimeError-versio
`validate_local_extent(skeleton)` käytetään testeissä, jotka haluavat
fail-fast-käyttäytymisen.

## storey_z_levels_mm — kerrosmallinnus

Profile-TOML:n `storey_z_levels_mm`-lista määrittelee kerrokset:

```toml
storey_z_levels_mm = [0.0, 3500.0, 7000.0]   # 3 kerrosta
```

Kustakin Z-tasosta syntyy yksi `IfcBuildingStorey` (nimet "Kerros 1",
"Kerros 2", …) ja sen `IfcLocalPlacement.RelativePlacement.Location[2]` =
Z-arvo. Konversio sijoittaa kunkin DXF-elementin sen Z-arvoa lähimpään,
mutta sen alle jäävään storey:hyn (ks. `resolve_storey`-helper).

| DXF-geometria | Anchor-Z |
|---|---|
| LINE | `min(start.z, end.z)` |
| LWPOLYLINE | `min(p.z for p in vertices)` |
| INSERT | `insertion_point.z` |

## max_local_extent — defensiivinen validointi

`validate_local_extent(skeleton, max_extent_mm=5_000_000.0)` skannaa
kaikki `IfcCartesianPoint`-entiteetit ja heittää `RuntimeError` jos
yksikään koordinaattikomponentti ylittää annetun rajan (oletus 5 km =
5 000 000 mm). Käytä testeissä ja CI-ympäristössä — tuotantokäytössä
varoitusversio quality-gatessa riittää.

## Yhteys MML / NLS:n paikkatietoihin

ETRS-TM35FIN-koordinaatit projektillesi saat **Maanmittauslaitoksen
karttapalvelusta** (https://kartta.paikkatietoikkuna.fi) tai
**National Land Survey API:sta** (https://www.maanmittauslaitos.fi/karttapaikka).
Klikkaa rakennuspaikkaa, valitse "Näytä koordinaatit", ja kopioi
ETRS-TM35FIN-rivi (esim. `E: 25 496 123, N: 6 672 456`). dxf2ifc-
profiilissa eastings ja northings tulevat **millimetreissä** — kerro
metri-arvo 1000:lla.

## Ei TrueNorth Plan G:ssä

`IfcGeometricRepresentationContext.TrueNorth` -rotaatio (mallin Y-akselin
suuntaaminen pohjoisesta poikkeavaan suuntaan) on jätetty **Plan G:n
MVP:n ulkopuolelle**. Mahdollisesti Plan I:ssä myöhemmin, kun käyttäjillä
on selkeä tarve poikkeavasti suunnatulle mallille.

## Avaintyökalut

- `CRSConfig` — `dxf2ifc.profiles.schema.CRSConfig` (pydantic)
- `build_ifc_project_skeleton(crs=..., storey_z_levels_mm=...)` — palauttaa
  `IfcSkeleton`
- `resolve_storey(storeys, z_mm)` — anchor-Z → storey
- `validate_local_extent(skeleton)` — RuntimeError double-transformista
- `validate_ifc(path, expect_crs=True)` — quality-gate-warningit
- CLI-flagit `--eastings`, `--northings`, `--orthogonal-height`
- GUI-dialogi `gui.crs_dialog.CRSDialog` (Profile → Set CRS…)
