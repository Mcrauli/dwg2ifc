# PROGRESS

**Current plan:** Plan B — Full element set (skeleton committed `6eb66ce`).

**Current task:** Plan B kirjoitusvaihe (Mode B, section 1/12).

**Mode:** B (plan-kirjoitus, section 9/12: Kaapelihyllyt)

**Seuraavaksi:** täytä Plan B Section 9 -alle 3–5 task-riviä joka kattaa kaapelihyllyt → IfcFlowSegment + IfcCableCarrierSegmentType CABLETRUNKINGSEGMENT (23xx). LINE/POLYLINE → reitti. Sitten PROGRESS.md → section 10/12.

## Plan A status (21/21) ✅
- [x] Task 1–14 — scaffolding, types, profile loader, dxf reader, mapper (SHA-historia README + commit-log)
- [x] Task 15 — `WallExtrusion` + `line_to_wall_extrusion` (`6c63c22`)
- [x] Task 16 — `build_ifc_project_skeleton` + `write_ifc` (`05e8aca`)
- [x] Task 17 — `add_wall` + `add_talo2000_classification` (`6283cc6`)
- [x] Task 18 — `convert_dxf` orchestrator (`ea5a9a2`)
- [x] Task 19 — argparse CLI + `__main__.py` (`3fd647b`)
- [x] Task 20 — integration test + `ifcopenshell.validate` (`3da2df0`)
- [x] Task 21 — ruff clean + 41 testiä passed, 84 % coverage (`54140a5`)

## Plan B status (skeleton, 0/N)
- [ ] Section 1: Profile-skeeman laajennus
- [ ] Section 2: VS / lasiväliseinät (1311 / 1312)
- [ ] Section 3: Laatat AP / VP / YP (1221 / 1235 / 1236)
- [ ] Section 4: Ovet (1243 / 1315 / 1316)
- [ ] Section 5: Ikkunat (1242)
- [ ] Section 6: Kylmäputket (21xx)
- [ ] Section 7: Viemäriputket (21xx DRAINPIPE)
- [ ] Section 8: Varastointihyllyt (1331)
- [ ] Section 9: Kaapelihyllyt (23xx)
- [ ] Section 10: Kylmähuone-elementit (1352)
- [ ] Section 11: Kylmälaitteet (25xx)
- [ ] Section 12: Integraatio + lint

**Viimeisin tila:** Plan A valmis. Plan B skeleton master-branchissa (`6eb66ce`). Mode B aloitettu, sectionit 12 kpl.

**Tämän session muutokset:**
- Plan B skeleton-tiedosto luotu (`6eb66ce`).
- Käynnissä: section 1 -sisällön kirjoitus.

**Kesken:** Plan B sectionien sisältö (1/12 → 12/12).

**Blokkerit:** ei.
