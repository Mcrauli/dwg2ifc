# DWG / MagiCAD preprocessing — totuus

Tämä dokumentti kerää sen mitä todella toimii, mitä ei, ja miksi.
Se on kirjoitettu jotta seuraavalla iteraatiolla **ei keksitä uudelleen**
samoja umpikujia kuin POC v1–v4 -saagassa (~16 iteraatiota,
2026-04-29 → 2026-05-07).

> **TL;DR** — DWG-input on **kokeellinen**. Core DXF-pipeline ei
> riipu siitä. Render-only MagiCAD Object Enabler ei tuota MagiCAD-
> osille IFC-geometriaa. FULL MagiCAD tuottaa mesh-tason tessellaation
> mutta ei semanttisia IFC-tyyppejä. **Suositeltu reitti**: kollegan
> `-MAGIIFCCD` AutoCAD:issa + dxf2ifc:n `--magicad-ifc`-merge.

## Mikä toimii (alpha7)

### DXF-pipeline (ydin, EI saa rikkoutua)

`.dxf` → `core/preprocessing.py` → `core/dxf_reader.py` → `core/mapper.py`
→ `core/ifc_writer/` → `output.ifc`.

Toimii ilman AutoCAD COM:ia. `accoreconsole.exe` tarvitaan vain jos
DXF:ssä on 3DSOLID/SURFACE/REGION-bodyja jotka pitää tessellöidä.

Lauri:n KYL-LISP-elementit (TIKASHYLLY, LEVYHYLLY, HÖYRYSTIMET, jne.)
luetaan natiivisti ezdxf:llä. Dynamic block -muotoiset hyllyt (anonyymit
`*U*`-blockit jotka sisältävät `closed LWPOLYLINE` + `3DFACE`) aggregoidaan
`INSERT.virtual_entities()`-kautta — soveltaa INSERT-transformaation
automaattisesti, ei tarvitse mitään ulkoista työkalua.

### DWG-pipeline (kokeellinen, optional)

`.dwg` → `core/dwg_preconvert.py` → välitilanne-DXF → DXF-pipeline.

`dwg_preconvert.py` käynnistää piilotetun (Visible=False) AutoCAD COM
-istunnon `pywin32`:lla, lähettää keystrokes:

1. `MAGIEXPLODE\nALL\n\n` — räjäyttää MagiCAD-natiivit luokat
2. `EXPLODE\nALL\n\n` — räjäyttää INSERT-blockit alemmas
3. AutoLISP-load: sysvar SAVE+RESTORE, STLOUT 3DSOLID-lapsille,
   diagnostiikkalokit
4. `DXFOUT path Enter Enter 8 Enter` (FILEDIA toggle ympärillä) →
   välitilanne-DXF
5. Document.Close(SaveChanges=False) — alkuperäinen DWG ei mutaatu

Singleton-pattern: AutoCAD-instanssi pidetään muistissa `atexit`-hookilla.
Cold-start ~14 s, lämmin ~3 s/konversio.

### MagiCAD-IFC merge

`core/ifc_merger.py` käyttää `ifcopenshell.api.project.append_asset`:ia
kopioimaan `IfcProduct`-johdannaiset MagiCAD-IFC:stä master-IFC:hen,
linkittäen ne `IfcRelContainedInSpatialStructure`-relaatiolla master:in
ensimmäiseen `IfcBuildingStorey`:hen. Spatial structure -entiteetit
(`IfcSite`, `IfcBuilding`, `IfcBuildingStorey`, `IfcSpace`) eivät kopioidu —
master:n hierarkia pysyy kanonisena.

GUI-filepicker + CLI `--magicad-ifc PATH`. DXF-syötteellä ei tarvita
AutoCAD COM:ia ollenkaan tähän reitiin.

## Mikä EI toimi (älä yritä uudelleen)

### accoreconsole + ARX

**`accoreconsole.exe` ei voi ladata `.arx`-moduuleja.** Autodesk-
dokumentoitu rajoite. Empiirisesti vahvistettu 4 spike-iteraatiolla:

```
(arxload "MagiCAD_r25x64.arx") → ARXLOAD failed
```

Sama rajoite koskee sekä DXF että DWG -formaattia. Tiedostomuodolla ei
ratkea. **MagiCAD-luokat (MAGIPathwayDevice, MAGIAccessory, jne.) jäävät
opaque ACAD_PROXY_ENTITY-tietueiksi accoreconsole:lle.**

### Render-only Object Enabler + EXPLODE

Lauri:n koneella on **MagiCAD Object Enabler render-only** (ei FULL-
lisenssiä). Tilanne:

| Toiminto | Render-only OE | FULL MagiCAD |
|---|---|---|
| ARX latautuu acad.exe:hen | ✅ | ✅ |
| MAGI*-luokat tunnistuvat natiivinimillä | ✅ | ✅ |
| `(command "_.EXPLODE" ent)` MAGI*-luokille | ❌ ei tuota 3DSOLID-lapsia | ✅ tuottaa 3DSOLID-lapsia |
| `MAGIEXPLODE` + `ALL` AutoCAD-promptilla | ⚠️ tuottaa 2D-polylineja | ✅ tuottaa 3D-geometriaa |
| `Explode()`-COM-metodi | ❌ `AttributeError: <unknown>.Explode` | ✅ |
| `GetBoundingBox()`-COM-metodi | ❌ palauttaa 20×20×0 mm placeholder | ✅ palauttaa todellisen bbox:n |
| `_.MAGIIFCEXPORT` LISP-tasolla | ❌ ei määritelty | ✅ saatavilla |
| `-MAGIIFCCD` command-line | ❌ ei tunnista | ✅ tuottaa MagiCAD-IFC:n |

**Lauri:n manuaalitestit (2026-05-07) vahvistivat**: render-only OE +
MAGIEXPLODE + EXPLODE → DWG:ssä on jäljellä **2D-polyline-viivakehikko**,
ei 3D-pintoja. STLOUT näille epäonnistuu (eivät ole closed solid:eja).
CONVTOSOLID epäonnistuu samasta syystä.

### POC v4 polyline-extrusion-strategia

POC v4:ssa kokeiltiin extrudoida MAGIEXPLODE+EXPLODE-tuottamia 2D-
polylineja takaisin 3D-volyymiksi (bbox-cuboid tai polygon-extrusion).
Tämä **hylättiin v0.2.0-alpha3:ssa** koska:

1. Geometriafidelity oli huono (placeholder-laatikoita, ei oikeaa muotoa)
2. IFC-tyypit jäivät geneerisiksi `IfcBuildingElementProxy`:ksi —
   ei MagiCAD-semantiikkaa
3. Kollegan FULL-MagiCAD-koneella `-MAGIIFCCD` tuottaa MERKITTÄVÄSTI
   parempaa IFC:tä kuin mikään extrudointi-strategia voisi

**Älä toista MAGIEXPLODE-mesh-strategiaa.** Käytä `--magicad-ifc`-mergeä.

### Muut umpikujat

- **ODA Teigha SDK** — ei MagiCAD-decoderia
- **RealDWG** — ei voi ladata MagiCAD-ARX:ää
- **MagiCAD CLI** — ei ole olemassa
- **`acad.exe /b /nologo` SW_HIDE** — ei piilota GUI:ta luotettavasti
  (AutoCAD kutsuu itse `ShowWindow(SW_SHOW)`)
- **`taskkill /F /IM acad.exe`** — DANGEROUS, voi tappaa käyttäjän
  oman istunnon

## Safety-for-all-users

DWG-preconvert on käyttäjä-koneella ajettava työkalu, ja **sen ei saa
muuttaa käyttäjän AutoCAD-asetuksia**:

- ❌ EI HKCU-rekisterikirjoituksia (`Software\Autodesk\AutoCAD\*`)
- ❌ EI `taskkill` `acad.exe`-prosessille
- ❌ EI sysvar-muutoksia jotka persistoituvat profiiliin
  (`STARTMODE`, `RECENTFILES`, `SDI`)
- ❌ EI manuaalista dialog-klikkausta käyttäjältä

Sysvarit jotka ovat **session-only ja turvallisia** asettaa:
`FILEDIA`, `CMDDIA`, `EXPERT`, `SMOOTHMESHCONVERT`, `FACETERMESHTYPE`,
`FACETERSMOOTHLEV`, `FACETERDEVNORMAL`, `FACETERDEVSURFACE`, `DELOBJ`.

## Kriittiset säännöt

1. **DWG-pipelinen muutokset eivät saa rikkoa DXF-pipelinea.** Aja
   `pytest tests/test_dxf_reader*.py tests/test_*ifc*.py` jokaisen
   DWG-muutoksen jälkeen.
2. **Kokeellinen status pysyy.** Älä mainosta DWG-tukea README:ssa
   "vakaaksi" ennen kuin Lauri vahvistaa.
3. **Älä yritä accoreconsole + ARX uudelleen.** Vahvistettu mahdoton.
4. **Älä yritä render-only OE + MAGIEXPLODE + 3DSOLID-lapset.**
   Vahvistettu mahdoton.
5. **Suositele aina ensin `-MAGIIFCCD` + `--magicad-ifc`-mergeä**
   ennen DWG-input-yritystä.

## Käyttäjän virheviestit

DWG-input voi epäonnistua hiljaa monella tasolla. `dwg_preconvert.py`
tuottaa selkeitä progress-viestejä:

- "AutoCAD COM Dispatch epäonnistui" — pywin32 puuttuu / AutoCAD ei asennettu
- "DWG-kopiointi epäonnistui" — temp-polun lukuoikeus / levy täynnä
- "AutoCAD Open epäonnistui" — DWG-versio liian uusi / korruptoitunut
- "MAGIEXPLODE / EXPLODE / DXFOUT keystroke ei lähtenyt" —
  AutoCAD-istunto jumissa, klikkaa OK näkyvissä popup:eissa
- "Kokonaistimeout 240 s" — ARX latautui hitaasti tai jumissa MagiCAD-
  popup:in takana
- "DXFOUT ei tuottanut tiedostoa" — keystrokes:t menivät ohi command-
  bufferista

Orchestrator nappaa nämä `RuntimeError`:ksi ja näyttää käyttäjälle:
"DWG-preconvert epäonnistui — MAGIEXPLODE / DXFOUT ei tuottanut
välitilanne-DXF:ää. Tarkista että AutoCAD on asennettu, ettei toinen
dxf2ifc-konversio ole käynnissä, ja ettei MagiCAD-popup keskeytä
prosessia."

## Test-fixtures

- `~/OneDrive - RADIKA OY/Tiedostot/testimagi.dwg` — Lauri:n MagiCAD-
  testi-DWG (Object Enabler -tallennettu, MAGI*-natiivit luokat).
  POC v4 -ajojen lähde, säilytetään mutta ei ole automaattisten testien
  osa (`@pytest.mark.requires_acad` skipped).

## Historia

POC v1 (Build #18-19, 2026-04-29) — accoreconsole + ARX → ARXLOAD failed.
POC v2 (2026-05-01) — visible AutoCAD COM, MESHSMOOTH dialog blokkasi.
POC v3 (2026-05-04) — Visible=True, profile WindowState mutaatiot
rikkoivat Lauri:n AutoCAD-profiilin.
POC v4 (2026-05-07, 16+ alpha-iteraatiota) — MAGIEXPLODE+EXPLODE+STLOUT,
toimi mekaanisesti mutta tuotti 2D-polylineja eikä 3D-mesh:iä.

**Ratkaisu (v0.2.0-alpha3, 2026-05-07)**: kierää koko ARX-pipeline ohi,
tuo MagiCAD-osat erillisellä `-MAGIIFCCD`-IFC:llä, mergee
`ifcopenshell.api.project.append_asset`:lla.

POC v4:n täysi konteksti:
`~/.claude/projects/.../memory/poc_v4_magicad_explode.md`.
