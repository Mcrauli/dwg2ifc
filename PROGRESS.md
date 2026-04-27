# PROGRESS

**Current plan:** Plan C — IfcSystem-ryhmittely (kirjoittamatta).

**Current task:** Plan C Task 1 — kirjoita Plan C:n skeleton (IfcSystem-ryhmittely kylmäjärjestelmille).

**Mode:** B (plan-kirjoitus).

**Seuraavaksi:** kirjoita `docs/superpowers/plans/2026-04-27-plan-c-ifcsystem-grouping.md` skeleton: YAML frontmatter + 1–3 rivin intro + section-otsikot. Sen jälkeen täytä section-task-rivit yksi kerrallaan.

## Plan A status (21/21) ✅
- [x] Task 1–14 — scaffolding, types, profile loader, dxf reader, mapper (commit-historia)
- [x] Task 15 — `WallExtrusion` + `line_to_wall_extrusion` (`6c63c22`)
- [x] Task 16 — `build_ifc_project_skeleton` + `write_ifc` (`05e8aca`)
- [x] Task 17 — `add_wall` + `add_talo2000_classification` (`6283cc6`)
- [x] Task 18 — `convert_dxf` orchestrator (`ea5a9a2`)
- [x] Task 19 — argparse CLI + `__main__.py` (`3fd647b`)
- [x] Task 20 — integration test + `ifcopenshell.validate` (`3da2df0`)
- [x] Task 21 — ruff clean + 41 testiä passed, 84 % coverage (`54140a5`)

## Plan B status (50/50) ✅

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
- [x] Task 34: orchestrator dispatch + integraatiotesti KYL-LEVYHYLLY (`05c8f43`)

### Section 9: Kaapelihyllyt (23xx)
- [x] Task 35: default-profiilin KAAPELIHYLLY-LINE-sääntö (`e3af094`)
- [x] Task 36: `line_to_cable_carrier` testi + impl (`8dda18e`)
- [x] Task 37: `ifc_writer.add_cable_carrier_segment` + IfcCableCarrierSegmentType CABLETRUNKINGSEGMENT (`b2203f6`)
- [x] Task 38: orchestrator dispatch + integraatiotesti KAAPELIHYLLY (`ea1d99b`)

### Section 10: Kylmähuone-elementit (1352, IfcBuildingElementProxy)
- [x] Task 39: default-profiilin KYL-LEVY*/KYL-NURKKA*-säännöt (`9fdd6c4`)
- [x] Task 40: `panel_to_proxy_solid` testi + impl (`02077bd`)
- [x] Task 41: `ifc_writer.add_building_element_proxy` (`5fc61c6`)
- [x] Task 42: orchestrator dispatch + integraatiotesti KYL-LEVY (`be47f57`)

### Section 11: Kylmälaitteet (25xx)
- [x] Task 43: default-profiilin HOYRYSTIN/LAUHDUTIN/KOMPRESSORI-INSERT-säännöt (`ddb872f`)
- [x] Task 44: `tests/test_mapper.py` kylmälaitemappaustesti (`c4fce3e`)
- [x] Task 45: `ifc_writer.add_cooling_equipment` dispatcher (IfcEvaporator/IfcCondenser/IfcCompressor) (`e0e2c25`)
- [x] Task 46: orchestrator dispatch + integraatiotesti HOYRYSTIN (`1ba3a65`)

### Section 12: Integraatio + lint
- [x] Task 47: `tests/fixtures/full_kylmaelement.dxf` (kaikki section 2–11 elementtityypit) (`58ac2e4`)
- [x] Task 48: `tests/test_integration_full.py` (kaikki Talo2000-koodit löytyvät IFC:stä) (`536fa50`)
- [x] Task 49: ruff clean + ≥85 % coverage (`cab7ea7`, 143 passed, 91 %)
- [x] Task 50: README.md + CLAUDE.md status-päivitys (Plan B valmis) (`2494841`)

**Viimeisin tila:** Plan A 21/21 valmis. **Plan B 50/50 valmis** ✅. Seuraavana Plan C (kirjoittamatta).

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
- Plan B Task 34: convert_dxf dispatchaa IfcFurniture + integraatiotesti KYL-LEVYHYLLY KLHYLLY-LEVY → 1331 (`05c8f43`). 8 integration-testiä passed. ✅ Section 8 valmis.
- Plan B Task 35: aktivoi KAAPELIHYLLY*-sääntö default-profiiliin (IfcCableCarrierSegment CABLETRUNKINGSEGMENT 2380) (`e3af094`). 14 loader-testiä passed.
- Plan B Task 36: CableCarrierSegmentExtrusion-dataclass + line_to_cable_carrier (`8dda18e`). 24 geometry-testiä passed.
- Plan B Task 37: add_cable_carrier_segment + IfcCableCarrierSegmentType CABLETRUNKINGSEGMENT + USERDEFINED-fallback (`b2203f6`). 34 ifc_writer-testiä passed.
- Plan B Task 38: convert_dxf dispatchaa IfcCableCarrierSegment + integraatiotesti KAAPELIHYLLY → 2380 (`ea1d99b`). 9 integration-testiä passed. ✅ Section 9 valmis.
- Plan B Task 39: aktivoi KYL-LEVY*/KYL-NURKKA* POLYLINE-säännöt default-profiiliin (IfcBuildingElementProxy 1352) (`9fdd6c4`). 15 loader-testiä passed.
- Plan B Task 40: PanelExtrusion-dataclass + panel_to_proxy_solid (`02077bd`). 28 geometry-testiä passed.
- Plan B Task 41: add_building_element_proxy tuottaa IfcBuildingElementProxy + arbitrary closed profile -extrusion (`5fc61c6`). 37 ifc_writer-testiä passed.
- Plan B Task 42: convert_dxf dispatchaa IfcBuildingElementProxy + integraatiotesti KYL-LEVY → 1352 (`be47f57`). 10 integration-testiä passed. ✅ Section 10 valmis.
- Plan B Task 43: aktivoi HOYRYSTIN/LAUHDUTIN/KOMPRESSORI INSERT-säännöt default-profiiliin (Evaporator/Condenser/Compressor 2510/2520/2530) (`ddb872f`). 16 loader-testiä passed.
- Plan B Task 44: mapper-testit kylmälaite INSERT-mappauksille (`c4fce3e`). 18 mapper-testiä passed.
- Plan B Task 45: add_cooling_equipment dispatcher IfcEvaporator/IfcCondenser/IfcCompressor box-extrusion (`e0e2c25`). 42 ifc_writer-testiä passed.
- Plan B Task 46: convert_dxf dispatchaa cooling equipment + integraatiotesti KYL-HOYRYSTIN HOYRYSTIN → IfcEvaporator 2510 (`1ba3a65`). 11 integration-testiä passed. ✅ Section 11 valmis.
- Plan B Task 47: full_kylmaelement_dxf conftest-fixture (kaikki Section 2–11 elementit) (`58ac2e4`).
- Plan B Task 48: tests/test_integration_full.py joka varmistaa kaikki Section 2–11 Talo2000-koodit + IFC-validointi (`536fa50`). 3 testiä passed.
- Plan B Task 49: ruff format kolmelle uudelle tiedostolle, koko suite 143 passed, coverage 91 % (`cab7ea7`).
- Plan B Task 50: README + CLAUDE.md status-päivitys Plan B valmiiksi (`2494841`). 🎉 Plan B 50/50.

**Kesken:** Plan C kirjoitettava (Mode B).

**Blokkerit:** ei.
