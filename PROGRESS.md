# PROGRESS

**Current plan:** Plan B — Full element set (kirjoitettu, 50 tehtävää, master `083f8cd`).

**Current task:** Plan B Task 34 — orchestrator dispatch + integraatiotesti KYL-LEVYHYLLY.

**Mode:** A (implementointi).

**Seuraavaksi:** lisää convert_dxf:ään `elif m.ifc_type == "IfcFurniture"` haara (kutsuu add_furniture + add_talo2000_classification). Lisää integraatiotesti KYL-LEVYHYLLY + KLHYLLY-LEVY -blokilla → IfcFurniture + 1331.

## Plan A status (21/21) ✅
- [x] Task 1–14 — scaffolding, types, profile loader, dxf reader, mapper (commit-historia)
- [x] Task 15 — `WallExtrusion` + `line_to_wall_extrusion` (`6c63c22`)
- [x] Task 16 — `build_ifc_project_skeleton` + `write_ifc` (`05e8aca`)
- [x] Task 17 — `add_wall` + `add_talo2000_classification` (`6283cc6`)
- [x] Task 18 — `convert_dxf` orchestrator (`ea5a9a2`)
- [x] Task 19 — argparse CLI + `__main__.py` (`3fd647b`)
- [x] Task 20 — integration test + `ifcopenshell.validate` (`3da2df0`)
- [x] Task 21 — ruff clean + 41 testiä passed, 84 % coverage (`54140a5`)

## Plan B status (33/50)

### Section 1: Profile-skeeman laajennus ✅
- [x] Task 1: laajenna `profiles/schema.py` Rule-malliin `entity_kind` (LINE/POLYLINE/CIRCLE/INSERT) ja `block_name` (`faaac8c`)
- [x] Task 2: lisää `extrusion_height` ja `pset_overrides`-kentät + INSERT-validointi (`29f01e4`)
- [x] Task 3: päivitä `profiles/loader.py` säilyttämään uudet kentät + `tests/test_profile_schema.py` (`a8cbe50`)
- [x] Task 4: laajenna default TOML kommentoiduilla placeholder-säännöillä joka elementtityypille (`35c18f6`)

### Section 2: VS / lasiväliseinät (1311 / 1312) ✅
- [x] Task 5: default-profiilin VS- ja lasiväliseinä-säännöt (`97ab1b0`)
- [x] Task 6: failing test `tests/test_mapper.py` partition-säännöille (`cb77e9c`)
- [x] Task 7: `ifc_writer.add_wall` + `predefined_type` -parametri (`b101565`)
- [x] Task 8: integraatiotesti VS-viivalla → IfcWall PARTITIONING 1311 (`f051083`)

### Section 3: Laatat AP / VP / YP (1221 / 1235 / 1236) ✅
- [x] Task 9: default-profiilin laattasäännöt (`62f0f2e`)
- [x] Task 10: `dxf_reader.py` LWPOLYLINE-luku + `PolygonGeometry`-tyyppi (`5d10e66`)
- [x] Task 11: `polygon_to_slab_extrusion` testi + impl (`88517c7`)
- [x] Task 12: `ifc_writer.add_slab` + classification (`3d9e15f`)
- [x] Task 13: orchestrator dispatch slab-rule (`0c13013`)

### Section 4: Ovet (1243 / 1315 / 1316)
- [x] Task 14: default-profiilin INSERT-ovisäännöt (`36c5c51`)
- [x] Task 15: `dxf_reader.py` INSERT-luku + `BlockInstance`-tyyppi (`6427278`)
- [x] Task 16: `door_block_to_box` testi + impl (`efd9f9a`)
- [x] Task 17: `ifc_writer.add_door` (`4848061`)
- [x] Task 18: orchestrator dispatch + integraatiotesti OVI-ULKO (`813e4a6`)

### Section 5: Ikkunat (1242)
- [x] Task 19: default-profiilin IKKUNA-INSERT-sääntö (`d5451df`)
- [x] Task 20: `tests/test_mapper.py` IKKUNA-mappaustesti (`2902de2`)
- [x] Task 21: `ifc_writer.add_window` (`4488a48`)
- [x] Task 22: orchestrator dispatch + integraatiotesti IKKUNA (`5db11be`)

### Section 6: Kylmäputket (21xx, IfcPipeSegment)
- [x] Task 23: default-profiilin LT IMU / MT IMU / MT NESTE -säännöt (`5db22b1`)
- [x] Task 24: `line_to_pipe_segment` testi + impl (`9f1a51c`)
- [x] Task 25: `ifc_writer.add_pipe_segment` + IfcPipeSegmentType (`b5ff242`)
- [x] Task 26: orchestrator dispatch + integraatiotesti LT IMU (`770978f`)

### Section 7: Viemäriputket (21xx DRAINPIPE)
- [x] Task 27: default-profiilin KYL-VIEMARI*-sääntö (`7cf669f`)
- [x] Task 28: `mapper.layer_matches` wildcard-suffix-tuki (`8904ce1`)
- [x] Task 29: `add_pipe_segment` predefined_type DRAINPIPE/REFRIGERATION (`1bc2082`)
- [x] Task 30: integraatiotesti KYL-VIEMARI-LATTIA (`a07f315`)

### Section 8: Varastointihyllyt (1331, IfcFurniture)
- [x] Task 31: default-profiilin KYL-LEVYHYLLY/TIKASHYLLY/KLHYLLYV-säännöt (`8d5b662`)
- [x] Task 32: `block_to_furniture_box` testi + impl (`fcca98e`)
- [x] Task 33: `ifc_writer.add_furniture` (`17a7358`)
- [ ] Task 34: orchestrator dispatch + integraatiotesti KYL-LEVYHYLLY

### Section 9: Kaapelihyllyt (23xx)
- [ ] Task 35: default-profiilin KAAPELIHYLLY-LINE-sääntö
- [ ] Task 36: `line_to_cable_carrier` testi + impl
- [ ] Task 37: `ifc_writer.add_cable_carrier_segment` + IfcCableCarrierSegmentType CABLETRUNKINGSEGMENT
- [ ] Task 38: orchestrator dispatch + integraatiotesti KAAPELIHYLLY

### Section 10: Kylmähuone-elementit (1352, IfcBuildingElementProxy)
- [ ] Task 39: default-profiilin KYL-LEVY*/KYL-NURKKA*-säännöt
- [ ] Task 40: `panel_to_proxy_solid` testi + impl
- [ ] Task 41: `ifc_writer.add_building_element_proxy`
- [ ] Task 42: orchestrator dispatch + integraatiotesti KYL-LEVY

### Section 11: Kylmälaitteet (25xx)
- [ ] Task 43: default-profiilin HOYRYSTIN/LAUHDUTIN/KOMPRESSORI-INSERT-säännöt
- [ ] Task 44: `tests/test_mapper.py` kylmälaitemappaustesti
- [ ] Task 45: `ifc_writer.add_cooling_equipment` dispatcher (IfcEvaporator/IfcCondenser/IfcCompressor)
- [ ] Task 46: orchestrator dispatch + integraatiotesti HOYRYSTIN

### Section 12: Integraatio + lint
- [ ] Task 47: `tests/fixtures/full_kylmaelement.dxf` (kaikki section 2–11 elementtityypit)
- [ ] Task 48: `tests/test_integration_full.py` (kaikki Talo2000-koodit löytyvät IFC:stä)
- [ ] Task 49: ruff clean + ≥85 % coverage
- [ ] Task 50: README.md + CLAUDE.md status-päivitys (Plan B valmis)

**Viimeisin tila:** Plan A 21/21 valmis. Plan B 33/50 — Sectionit 1–7 valmis, Section 8 etenee (3/4).

**Tämän session muutokset:**
- Plan B Task 2: Rule-skeeman `extrusion_height` + `pset_overrides` -kentät, `model_validator` joka vaatii `block_name` INSERT-säännöille (`29f01e4`). 10 schema-testiä passed.
- Plan B Task 3: TOML-roundtrip-testit + loader negative test INSERT-without-block_name (`a8cbe50`). Loader itse ei vaatinut muutoksia. 17 schema+loader-testiä passed.
- Plan B Task 4: kommentoidut placeholder-säännöt section 2–11 element-tyypeille default TOML:ssa (`35c18f6`). 6 loader-testiä passed.
- Plan B Task 5: aktivoi KYL-VALISEINA ja KYL-LASIVALISEINA -säännöt default-profiiliin (PARTITIONING 1311/1312) (`97ab1b0`). 7 loader-testiä passed.
- Plan B Task 6: mapper-test joka varmistaa partition-mappingin default-profiililla (`cb77e9c`). 11 mapper-testiä passed.
- Plan B Task 7: `add_wall` ottaa explicit `predefined_type`-kwargia (default STANDARD), orchestrator forwardaa MappedEntity.predefined_type:n (`b101565`). 9 ifc_writer-testiä passed.
- Plan B Task 8: integraatiotesti joka generoi KYL-VALISEINA-DXF:n ezdxf:llä, ajaa convert_dxf:n ja varmistaa IfcWall PARTITIONING + Talo2000 1311 (`f051083`). 2 integration-testiä passed. ✅ Section 2 valmis.
- Plan B Task 9: aktivoi slab-säännöt KYL-ALAPOHJA/VALIPOHJA/YLAPOHJA default-profiiliin (1221 FLOOR / 1235 FLOOR / 1236 ROOF) (`62f0f2e`). 8 loader-testiä passed.
- Plan B Task 10: PolygonGeometry types.py:hen + dxf_reader lukemaan suljetut LWPOLYLINE-entiteetit (`5d10e66`). 11 reader+types-testiä passed.
- Plan B Task 11: SlabExtrusion-dataclass + polygon_to_slab_extrusion (`88517c7`). 8 geometry-testiä passed.
- Plan B Task 12: add_slab tuottaa IfcSlab + extruded outline + spatial containment (`3d9e15f`). 12 ifc_writer-testiä passed.
- Plan B Task 13: convert_dxf orchestrator dispatchaa IfcSlab + integraatiotesti KYL-ALAPOHJA → 1221 (`0c13013`). 15 ifc_writer+integration-testiä passed. ✅ Section 3 valmis.
- Plan B Task 14: aktivoi ovi-INSERT-säännöt KYL-OVET-ULKO/VALI/ERITYIS default-profiiliin (1243/1315/1316) (`36c5c51`). 9 loader-testiä passed.
- Plan B Task 15: BlockInstance types.py:hen + dxf_reader lukemaan INSERT-entiteetit (insertion_point/rotation_rad/scale) (`6427278`). 12 reader+types-testiä passed.
- Plan B Task 16: DoorBoxExtrusion-dataclass + door_block_to_box (`efd9f9a`). 12 geometry-testiä passed.
- Plan B Task 17: add_door tuottaa IfcDoor + OverallHeight/Width + box-extrusion + spatial containment (`4848061`). 17 ifc_writer-testiä passed.
- Plan B Task 18: convert_dxf dispatchaa IfcDoor + integraatiotesti OVI-ULKO BLOCK+INSERT → 1243 (`813e4a6`). 21 ifc_writer+integration-testiä passed. ✅ Section 4 valmis.
- Plan B Task 19: aktivoi KYL-IKKUNA INSERT-sääntö default-profiiliin (IfcWindow 1242) (`d5451df`). 10 loader-testiä passed.
- Plan B Task 20: mapper-testi joka mappaa IKKUNA INSERT default-profiililla → IfcWindow 1242 (`2902de2`). 12 mapper-testiä passed.
- Plan B Task 21: add_window tuottaa IfcWindow + OverallHeight/Width + box-extrusion (`4488a48`). 21 ifc_writer-testiä passed.
- Plan B Task 22: convert_dxf dispatchaa IfcWindow + integraatiotesti IKKUNA BLOCK+INSERT → 1242 (`5db11be`). 5 integration-testiä passed. ✅ Section 5 valmis.
- Plan B Task 23: aktivoi LT IMU / MT IMU / MT NESTE -säännöt default-profiiliin (IfcPipeSegment REFRIGERATION 2151/2152/2153 + DN pset_overrides) (`5db22b1`). 11 loader-testiä passed.
- Plan B Task 24: PipeSegmentExtrusion-dataclass + line_to_pipe_segment (`9f1a51c`). 16 geometry-testiä passed.
- Plan B Task 25: add_pipe_segment + IfcPipeSegmentType + USERDEFINED-fallback ei-validille IfcPipeSegmentTypeEnum-arvolle (`b5ff242`). 25 ifc_writer-testiä passed.
- Plan B Task 26: convert_dxf dispatchaa IfcPipeSegment + mapper välittää Pset_PipeSegmentOccurrence.NominalDiameter → extra_props default_diameter_mm + integraatiotesti LT IMU → 2151 (`770978f`). 18 integration+mapper-testiä passed. ✅ Section 6 valmis.
- Plan B Task 27: aktivoi KYL-VIEMARI* DRAINPIPE-sääntö default-profiiliin (`7cf669f`). 12 loader-testiä passed.
- Plan B Task 28: layer_matches wildcard-suffix regression-testit KYL-VIEMARI*:lle (`8904ce1`). 17 mapper-testiä passed.
- Plan B Task 29: add_pipe_segment-testit DRAINPIPE-arvolle (USERDEFINED + ObjectType + jaettu IfcPipeSegmentType) (`1bc2082`). 27 ifc_writer-testiä passed.
- Plan B Task 30: integraatiotesti KYL-VIEMARI-LATTIA → IfcPipeSegment DRAINPIPE + 2160 (`a07f315`). 7 integration-testiä passed. ✅ Section 7 valmis.
- Plan B Task 31: aktivoi KYL-LEVYHYLLY/TIKASHYLLY/TIKASHYLLY-V INSERT-säännöt default-profiiliin (IfcFurniture 1331) (`8d5b662`). 13 loader-testiä passed.
- Plan B Task 32: FurnitureBoxExtrusion + block_to_furniture_box (`fcca98e`). 20 geometry-testiä passed.
- Plan B Task 33: add_furniture tuottaa IfcFurniture + box-extrusion + spatial containment (`17a7358`). 30 ifc_writer-testiä passed.

**Kesken:** Plan B Task 34–50 (17 jäljellä).

**Blokkerit:** ei.
