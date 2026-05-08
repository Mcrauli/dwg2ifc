# DWG / MagiCAD preprocessing — historiallinen kontekstilappu

> **Status v0.2.0-alpha10 (2026-05-08)**: DWG-input on **POISTETTU**
> kokonaan. Vain `.dxf`-input. MagiCAD-osat tulevat erikseen kollegan
> `-MAGIIFCCD`-IFC:n kautta `--magicad-ifc`-mergellä. Tämä dokumentti
> kerää sen mitä todella opittiin POC v1–v4 -saagasta jotta seuraavalla
> iteraatiolla **ei keksitä uudelleen** samoja umpikujia.

## Suositeltu reitti tänään

```
1. Kollega ajaa AutoCAD:in command-linelle:  -MAGIIFCCD
   → MagiCAD tuottaa korkeatasoisen .ifc:n
     (oikeat IfcDuctSegment / IfcAirTerminal + MagiCAD-PSet:t)

2. Lauri saa .dxf:n + .ifc:n kollegalta

3. dxf2ifc:
     DXF input  = lähtö-DXF
     MagiCAD-IFC = kollegan .ifc
     Convert
   → core/ifc_merger.py
     ifcopenshell.api.project.append_asset
     → master.ifc jossa molemmat puolet samassa IfcBuildingStorey:ssä
```

DXF-pipelinen MAGI*-luokat + ACAD_PROXY_ENTITY skipataan automaattisesti
kun `magicad_ifc_path` on annettu (`read_dxf(skip_magicad=True)`),
estäen duplikaatit.

## Mitä EI toimi (älä yritä uudelleen)

### 1. accoreconsole + ARX

**`accoreconsole.exe` ei voi ladata `.arx`-moduuleja.** Autodesk-
dokumentoitu rajoite. Empiirisesti vahvistettu 4 spike-iteraatiolla:

```
(arxload "MagiCAD_r25x64.arx") → ARXLOAD failed
```

Sama rajoite koskee sekä DXF että DWG -formaattia. Tiedostomuodolla ei
ratkea. **MagiCAD-luokat (MAGIPathwayDevice, MAGIAccessory, jne.) jäävät
opaque ACAD_PROXY_ENTITY-tietueiksi accoreconsole:lle.**

### 2. Render-only Object Enabler + EXPLODE

| Toiminto | Render-only OE | FULL MagiCAD |
|---|---|---|
| ARX latautuu acad.exe:hen | ✅ | ✅ |
| MAGI*-luokat tunnistuvat natiivinimillä | ✅ | ✅ |
| `(command "_.EXPLODE" ent)` MAGI*-luokille | ❌ ei tuota 3DSOLID-lapsia | ✅ tuottaa 3DSOLID-lapsia |
| `MAGIEXPLODE` + `ALL` AutoCAD-promptilla | ⚠️ tuottaa 2D-polylineja | ✅ tuottaa 3D-geometriaa |
| `Explode()`-COM-metodi | ❌ `AttributeError: <unknown>.Explode` | ✅ |
| `GetBoundingBox()`-COM-metodi | ❌ palauttaa 20×20×0 mm placeholder | ✅ palauttaa todellisen bbox:n |

Lauri:n manuaalitestit (2026-05-07) vahvistivat: render-only OE +
MAGIEXPLODE + EXPLODE → DWG:ssä on jäljellä **2D-polyline-viivakehikko**,
ei 3D-pintoja. STLOUT näille epäonnistuu (eivät ole closed solid:eja).
CONVTOSOLID epäonnistuu samasta syystä.

### 3. POC v4 polyline-extrusion-strategia

POC v4:ssa kokeiltiin extrudoida MAGIEXPLODE+EXPLODE-tuottamia 2D-
polylineja takaisin 3D-volyymiksi (bbox-cuboid tai polygon-extrusion).
Tämä **hylättiin v0.2.0-alpha3:ssa** koska:

1. Geometriafidelity oli huono (placeholder-laatikoita, ei oikeaa muotoa)
2. IFC-tyypit jäivät geneerisiksi `IfcBuildingElementProxy`:ksi —
   ei MagiCAD-semantiikkaa
3. Kollegan FULL-MagiCAD-koneella `-MAGIIFCCD` tuottaa MERKITTÄVÄSTI
   parempaa IFC:tä kuin mikään extrudointi-strategia voisi

### 4. AutoCAD COM Visible=False keystroke-pohjainen DXFOUT

POC v4:n viimeisin yritys oli ajaa hidden AutoCAD:ia DWG → välitilanne-
DXF -muunnokseen. Tämä toimi mekaanisesti mutta:

- Käyttäjä-kone-kohtainen luotettavuus: AutoCAD:in versio, MagiCAD-ARX,
  käyttäjän profiili, taustalla pyörivä toinen AutoCAD-istunto, jne.
- Hauras keystroke-järjestys (FILEDIA toggle, DXFOUT-prompt-puskuri,
  per-phase deadlines, liveness pings, force-reset-singleton)
- ~768 riviä koodia hyvin kapeasta käyttötapauksesta

**Päätös v0.2.0-alpha10 (2026-05-08)**: DWG-input + `dwg_preconvert.py`
poistettu kokonaan. `pywin32`-dependency poistettu. `--no-preprocess-proxies`
CLI-flag poistettu. GUI:n "Pikakonversio" + "MagiCAD/proxy-objektien
geometria" -checkboxit poistettu — kaikki samalla committilla.

### 5. Muut umpikujat

- **ODA Teigha SDK** — ei MagiCAD-decoderia
- **RealDWG** — ei voi ladata MagiCAD-ARX:ää
- **MagiCAD CLI** — ei ole olemassa (paitsi `-MAGIIFCCD` AutoCAD:in sisällä)
- **`acad.exe /b /nologo` SW_HIDE** — ei piilota GUI:ta luotettavasti
- **`taskkill /F /IM acad.exe`** — DANGEROUS, voi tappaa käyttäjän
  oman istunnon

## Mitä jos käyttäjä haluaa silti DWG-tuen?

Käyttäjän pitää muuntaa DWG → DXF itse ennen dxf2ifc:tä:

1. **AutoCAD `DXFOUT`** — toimii kaikilla AutoCAD-versioilla, käyttäjä
   ajaa tämän käsin ennen dxf2ifc:n käynnistystä
2. **ODA File Converter** — ilmainen kolmannen osapuolen työkalu
3. **TrueView** — Autodesk:in ilmainen DWG-katselin tukee SaveAs
   DXF:ksi

Tämän jälkeen DXF menee normaaliin pipelineen.

## Historia

| Vaihe | Aika | Yritys | Lopputulos |
|---|---|---|---|
| POC v1 (Build #18-19) | 2026-04-29 | accoreconsole + ARX | ARXLOAD failed |
| POC v2 | 2026-05-01 | visible AutoCAD COM, MESHSMOOTH | dialog blokkasi |
| POC v3 | 2026-05-04 | Visible=True + WindowState | rikkoi käyttäjän AutoCAD-profiilin |
| POC v4 (16+ alphaa) | 2026-05-07 | MAGIEXPLODE+EXPLODE+STLOUT | 2D-polylinet, ei 3D-mesh:iä |
| **v0.2.0-alpha3** | 2026-05-07 | **MagiCAD-IFC merge** kollegan `-MAGIIFCCD`-tuotokselle | ✅ Toimii |
| v0.2.0-alpha10 | 2026-05-08 | **DWG-input + COM-pipeline poistettu kokonaan** | Ratkaisu: pelkkä DXF + IFC-merge |

POC v4:n täysi konteksti:
`~/.claude/projects/.../memory/poc_v4_magicad_explode.md`.

## Kriittiset säännöt

1. **Älä palauta DWG-input:tia.** Sitä yritettiin 16+ kertaa eri tavoilla,
   kaikki hauraita.
2. **Älä yritä accoreconsole + ARX uudelleen.** Vahvistettu mahdoton.
3. **Älä yritä render-only OE + MAGIEXPLODE + 3DSOLID-lapset.**
   Vahvistettu mahdoton.
4. **`-MAGIIFCCD` + merge on ainoa luotettava reitti** MagiCAD-osille.
5. Jos joku seuraavassa keskustelussa pyytää "DWG-tukea takaisin",
   linkitä tämä dokumentti — pelkkä DXF + merge-reitti hoitaa kaikki
   järkevät käyttötapaukset.
