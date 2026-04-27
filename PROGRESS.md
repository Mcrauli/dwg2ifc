# PROGRESS

**Current plan:** Plan A — Core CLI wall pipeline.

**Current task:** Task 16 — IFC writer project hierarchy skeleton (`build_ifc_project_skeleton`, `write_ifc`).

**Seuraavaksi:** lue plan A:n Task 16 -sektio. Luo `tests/test_ifc_writer.py` failing-testeillä (kolme testiä: hierarchy, millimetre units, write_ifc), aja `pytest tests/test_ifc_writer.py` vahvistaaksesi `ModuleNotFoundError: dxf2ifc.core.ifc_writer`, toteuta `src/dxf2ifc/core/ifc_writer.py` (build_ifc_project_skeleton + write_ifc), aja pytest uudelleen (odotus: 3 passed), committaa `feat(core): add IFC 4 project skeleton with millimetre units`. Vaatii `ifcopenshell`-paketin.

**Viimeisin tila:** Tasks 1–15 valmiit master-branchissa. Task 15 SHA `6c63c22` (`WallExtrusion` + `line_to_wall_extrusion`). Remote `https://github.com/Mcrauli/dxf2ifc` synkassa.
