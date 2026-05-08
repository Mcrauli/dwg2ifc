# Split plan — kolme isoa tiedostoa

Tämä dokumentti kuvaa **suunnitelman**, ei toteutusta. Jakoa ei tehdä
yhdellä isolla committilla; jokainen vaihe on oma PR / commit jonka
jälkeen koko testisuite ajetaan vihreäksi.

| Tiedosto | Rivit | Vastuu nyt |
|---|---|---|
| `src/dxf2ifc/core/ifc_writer/builders.py` | 1321 | Kaikki `add_*`-funktiot per IFC-tyyppi |
| `src/dxf2ifc/core/dwg_preconvert.py` | 768 | COM-singleton + AutoLISP + DXFOUT-keystrokes |
| `src/dxf2ifc/core/dxf_reader.py` | 759 | ezdxf-luenta, INSERT-aggregaatio, polyline/mesh-dispatch |

Pidetään public API ehjänä: `__init__`-fasadit re-exportaavat samat
nimet kuin nyt.

## 1) `ifc_writer/builders.py` (suuri prioriteetti)

Tämä on suurin ja helpoin pilkkoa — `add_*`-funktiot ovat itsenäisiä,
eivät jaa tilaa. Refaktori on rivien siirtoa, ei logiikkamuutosta.

### Tavoite-rakenne

```
core/ifc_writer/builders/
  __init__.py              re-export-fasadi (säilyttää public API:n)
  _common.py               jaetut helperit (esim. _placement_for, _record)
  walls.py                 add_wall + add_curtain_wall
  slabs.py                 add_slab + add_floor + add_roof
  openings.py              add_door + add_window
  pipes.py                 add_pipe_segment + add_pipe_fitting
  cooling.py               add_evaporator + add_condenser + add_compressor
                           + add_cooler + add_chiller + add_unitary_equipment
  cable_carriers.py        add_cable_carrier_segment + add_cable_segment
  flow.py                  add_flow_controller + add_valve + add_damper
                           + add_air_terminal
  furniture.py             add_furniture
  proxy.py                 add_proxy + add_tank
  systems.py               add_system + assign_to_system
```

### Vaiheet

| # | Muutos | Testit |
|---|---|---|
| 1 | Luo `builders/__init__.py` joka re-exportaa **kaikki** nykyiset symbolit `builders.py`:stä. Aja koko suite — pitää passata nollamuutoksin. | `pytest -q` |
| 2 | Siirrä `_common.py` (yhteiset helperit). Pidä import `from .builders import _placement_for` toistaiseksi käytössä. | `pytest -q` |
| 3 | Siirrä `walls.py` (1 funktio kerrallaan: ensin `add_wall`, sitten loput). Päivitä `__init__.py` re-export. Hae oikeat testit. | `pytest tests/test_walls* tests/test_skeleton*` |
| 4 | Siirrä `slabs.py` samalla rytmillä. | `pytest tests/test_*slab* tests/test_*floor*` |
| 5 | Siirrä `openings.py`. | `pytest tests/test_*door* tests/test_*window*` |
| 6 | Siirrä `pipes.py`. | `pytest tests/test_*pipe*` |
| 7 | Siirrä `cooling.py`. | `pytest tests/test_*cooling* tests/test_finnish_psets*` |
| 8 | Siirrä `cable_carriers.py`. | `pytest tests/test_*cable*` |
| 9 | Siirrä `flow.py`. | `pytest tests/test_*flow*` |
| 10 | Siirrä `furniture.py`, `proxy.py`, `systems.py`. | `pytest tests/test_*proxy* tests/test_*system*` |
| 11 | Poista alkuperäinen `builders.py`. | `pytest -q` koko suite |

Lopuksi `builders.py` on poistunut, `builders/__init__.py` re-exportaa
samat nimet kuin ennen → `from dxf2ifc.core.ifc_writer.builders import add_wall`
toimii edelleen. `from dxf2ifc.core.ifc_writer import add_wall` tärkeämpi
import on edelleen `ifc_writer/__init__.py`:n re-exportin kautta.

### Riskit

- Helppo unohtaa joku symboli `builders/__init__.py`:n re-exportista →
  ImportError testeissä. Mitigaatio: aja `pytest -q` jokaisen siirron
  jälkeen, EI batch:nä.
- Jaettu helper joka käyttää toista helperin → tarvitsee `_common.py`-
  refaktorin ennen ensimmäistä siirtoa.

## 2) `dwg_preconvert.py`

Kokeellinen moduuli. Pidetään ehjänä (älä riko POC v4 -saagan
kovalla työllä saavutettua toimivaa keystroke-sekvenssiä), mutta
selkeytetään kerrokset.

### Tavoite-rakenne

```
core/dwg_preconvert/
  __init__.py              re-export: preconvert_dwg, last_explode_meshes
  com_session.py           _ensure_app, _shutdown, _force_reset_app
  lisp_body.py             _build_lisp + sysvar SAVE/RESTORE
  keystrokes.py            MAGIEXPLODE/EXPLODE/DXFOUT keystroke-sekvenssit
                           + per-phase-deadlines + liveness pings
  mesh_collect.py          _parse_stl-yhdistelmä, last_explode_meshes-cache
  preconvert.py            preconvert_dwg() orkestraattori (pieni)
```

### Vaiheet

| # | Muutos | Testit |
|---|---|---|
| 1 | Luo `dwg_preconvert/__init__.py` joka re-exportaa `preconvert_dwg` + `last_explode_meshes`. | `pytest tests/test_dwg_preconvert.py` (skipped) + `pytest tests/test_dxf_reader*.py` |
| 2 | Siirrä COM-singleton (`_ensure_app`, `_shutdown`, `_force_reset_app`) → `com_session.py`. Imports kunnossa. | `pytest -q` |
| 3 | Siirrä `_build_lisp` → `lisp_body.py`. | `pytest -q` |
| 4 | Siirrä keystroke-sekvenssit + polling → `keystrokes.py`. | `pytest -q` |
| 5 | Siirrä mesh-collect → `mesh_collect.py`. | `pytest -q` |
| 6 | Lyhennä `preconvert.py` orkestraattoriksi joka kutsuu yllä olevia. | Manuaalitesti `testimagi.dwg`:llä jos saatavilla |

### Riskit

- COM-singleton on `module-global` (`_app = None`). Jos refaktori siirtää
  sen toiseen moduuliin, sama instance pitää säilyttää. Mitigaatio:
  re-export `__init__.py`:stä, älä luo uutta singleton-instanssia per
  moduuli.
- POC v4 -saagan keystroke-järjestys on hauras. Älä optimoi sitä — vain
  siirrä rivit moduulista toiseen.

## 3) `dxf_reader.py`

Pisin tiedosto mutta sisältää eri vastuita: top-level dispatch,
INSERT-aggregaatio, polyface mesh, ACAD_PROXY_ENTITY virtual-expansion.

### Tavoite-rakenne

```
core/dxf_reader/
  __init__.py              re-export: read_dxf, list_layers
  reader.py                read_dxf top-level (dispatch + mesh_priority_layers)
  insert_aggregator.py     _aggregate_3dface_from_insert
                           (3DFACE + LWPOLYLINE-extrusion + OCS→WCS)
  proxy_expander.py        ACAD_PROXY_ENTITY.virtual_entities() handling
                           + MAGI*-natiivien proxy_layers + acis_meshes
                           lookup
  primitive_records.py     _record_from_entity (LINE, LWPOLYLINE,
                           POLYLINE, 3DFACE, MESH, INSERT, 3DSOLID)
  helpers.py               _handle, MeshBuilder, vertex-dedup
```

### Vaiheet

| # | Muutos | Testit |
|---|---|---|
| 1 | Luo `dxf_reader/__init__.py` joka re-exportaa `read_dxf` + `list_layers`. Säilytä alkuperäinen `dxf_reader.py` ehjänä, vain re-export. | `pytest tests/test_dxf_reader*.py` |
| 2 | Siirrä `_aggregate_3dface_from_insert` → `insert_aggregator.py`. | `pytest tests/test_dxf_reader_insert_3dface.py` |
| 3 | Siirrä ACAD_PROXY_ENTITY-haaraat → `proxy_expander.py`. | `pytest tests/test_dxf_reader_proxy.py` |
| 4 | Siirrä `_record_from_entity` + per-dxftype-blokit → `primitive_records.py`. | `pytest tests/test_dxf_reader.py tests/test_dxf_reader_polyface.py` |
| 5 | Pelkistä `reader.py` top-level-dispatchiksi joka kutsuu yllä olevia. | `pytest tests/test_dxf_reader*.py` |

### Riskit

- `read_dxf` jakaa tilaa (`mesh_priority_layers`, `acis_meshes`,
  `proxy_layers`) eri haarojen kesken. Refaktori vaatii että nämä
  välitetään funktioargumentteina, ei modulinvälisinä globaaleina.
  Mitigaatio: lisää eksplisiitti `ReaderContext`-dataclass jos
  argumenttilista paisuu.
- INSERT-aggregaatio + ACAD_PROXY_ENTITY voivat jakaa helper-
  funktioita (esim. vertex-dedup). Mitigaatio: laita yhteiset
  `helpers.py`:hen, älä duplikoi.

## Yleinen järjestys ja sääntö

1. **Tee yksi tiedosto kerrallaan**, järjestyksessä:
   `builders` → `dwg_preconvert` → `dxf_reader`. Helpoimmasta vaikeimpaan.
2. **Yksi commit per vaihe** — jokaisen vaiheen jälkeen koko
   `pytest -q` (deselect pre-existing failurit) + relevantit
   funktionaaliset testit.
3. **Ei logiikkamuutoksia**. Jos huomaat bugin siirron yhteydessä,
   merkitse TODO-kommentilla mutta korjaa erillisellä PR:llä.
4. **Public API muuttumaton**. `from dxf2ifc.core.ifc_writer import *`,
   `from dxf2ifc.core.dwg_preconvert import preconvert_dwg`, jne.,
   tuottavat saman tuloksen.
5. **GUI/CLI ei muutu**. `convert_dxf` ja muut korkean tason API:t
   pysyvät paikallaan.

## Vaihtoehtoinen lähestymistapa: ÄLÄ pilko

Jos refaktori hidastaa Lauri:n featuretyötä, jätä isot tiedostot
ennalleen ja sen sijaan:

- Lisää tiedoston ylä-kommentit (`### --- Section: Walls ---`) jotka
  helpottavat navigointia editorissa
- Käytä Glob/Grep tarkkaan kohdistettujen muutosten löytämiseen
- Pidä tiedostokoot kuriin uudella koodilla (mieluummin uusi moduuli
  alusta)

Tämä on hyväksyttävä strategia jos refaktorin riski > arvo. Lauri päättää
prioriteetin.
