---
plan: D
title: PySide6 GUI for dxf2ifc
status: draft
date: 2026-04-27
depends_on: C
---

# Plan D: PySide6 desktop GUI

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps käyttävät checkbox (`- [ ]`) syntaksia. TDD per task missä mahdollista (Qt-UI:lle pytest-qt + offscreen platform); ei-testattavat resurssitehtävät committaa silti pienen visuaalisen tarkistuksen jälkeen.

**Goal:** Tee dxf2ifc:n päälle PySide6-pohjainen työpöytä-GUI joka wrappaa Plan A–C:n CLI-corea ja tarjoaa: (1) DXF-tiedoston valinta, (2) konversion ajo IFC:ksi yhden klikkauksen takana, (3) status- ja virheraportointi, (4) layer-preview joka listaa DXF:n layerit + niiden Talo2000-mappauksen, (5) profiilin editori joka antaa lisätä custom layer→IFC-sääntöjä ilman TOML-tiedoston käsin muokkaamista.

**Architecture:** GUI-koodi elää `src/dxf2ifc/gui/`-paketissa, kutsuu olemassa olevia `core/`-funktioita suoraan (`convert_dxf`, `read_dxf`, `apply_profile`) ja `profiles/`-loaderia. Ei muutoksia public coreen — ainoa lisäys on `Profile.to_toml(...)` -helper jos se puuttuu. QSS keskitetty `gui/style.qss` -resurssitiedostoon, fontit `assets/fonts/`-kansioon. CLAUDE.md:n design-sectionin värit ja typografia ovat ehdotuksellisia.

**Tech stack:** PySide6 6.7+, pytest-qt 4+, ruff, ifcopenshell + ezdxf (jo olemassa).

---

## Repository state before this plan

Plan A 21/21 + Plan B 50/50 + Plan C 12/12 valmis (master `8cc4fc3`). 151 testiä passed, coverage 91 %, ruff clean. Core-API on stabiili (`convert_dxf` palauttaa `dict[str, list]`-systems-mappingin) ja default-profiili kattaa kaikki tarvittavat layer-säännöt.

---

## Section 1: Bootstrap & dependencies

- [ ] Task 1: lisää `pyproject.toml`:n `[project.optional-dependencies]`-blokkiin uusi extra `gui` jossa `PySide6>=6.7` ja `dev`-extraan `pytest-qt>=4.4`. Aja `uv sync --extra gui --extra dev` ja varmista että importti `import PySide6.QtWidgets` toimii smoke-testissä.
- [ ] Task 2: luo `src/dxf2ifc/gui/__init__.py` ja `src/dxf2ifc/gui/app.py` jossa `def run()` -funktio rakentaa `QApplication`:n, näyttää placeholder-`QMainWindow`:n ("dxf2ifc") ja palaa `app.exec()` -koodilla. Lisää `tests/test_gui_app.py` joka käyttää pytest-qt:n `qtbot`-fixtureä ja `QT_QPA_PLATFORM=offscreen` varmistamaan että ikkuna avautuu ilman exceptionia.
- [ ] Task 3: lisää `[project.scripts]`-blokkiin `dxf2ifc-gui = "dxf2ifc.gui.app:run"` ja `src/dxf2ifc/gui/__main__.py` joka kutsuu `run()`:ia. Smoke-testi varmistaa että `python -m dxf2ifc.gui --help` (tai vastaava no-op) ei kaadu.

## Section 2: Brand assets (fontit, värit, QSS)

- [ ] Task 4: luo `assets/fonts/`-kansio ja lataa Inter (400/500/600/700), Space Grotesk (500/600/700) ja JetBrains Mono (500) -OFL-lisensoidut TTF-tiedostot kansioon. Lisää `assets/fonts/LICENSES.md` jossa kaikki kolme lisenssiä ovat. Konfiguroi `pyproject.toml` `[tool.setuptools.package-data]` siten että fontit pakataan wheeliin.
- [ ] Task 5: luo `src/dxf2ifc/gui/style.qss` joka sisältää CLAUDE.md:n design-sectionin värit (gradient `#0f172a` → `#020617`, amber `#f59e0b`, blue `#60a5fa`, slate-tekstiportaat) ja typografian (Inter body, Space Grotesk headings, JetBrains Mono code). QSS:n täytyy stylata vähintään `QMainWindow`, `QPushButton[primary="true"]`, `QPushButton[secondary="true"]`, `QLabel[role="h1"]`, `QLabel[role="h2"]`, `QLabel[role="caption"]`, `QStatusBar`. Failing test (`tests/test_gui_style.py`) varmistaa että `style.qss` on valid QString jonka `QApplication.setStyleSheet` hyväksyy ilman varoituksia.
- [ ] Task 6: lisää `src/dxf2ifc/gui/theme.py`:hen `apply_theme(app: QApplication)` -funktio joka (a) rekisteröi kolme fonttiperhettä `QFontDatabase.addApplicationFont`, (b) asettaa `app.setStyleSheet(...)` `style.qss`:n sisällöllä ja (c) asettaa default-`QFont`:n Interiksi 14 px. Testi varmistaa että rekisteröidyt fonttiperheet löytyvät `QFontDatabase.families()`-listasta ja että style sheet ei ole tyhjä.

## Section 3: MainWindow + layout-runko

- [ ] Task 7: korvaa `gui/app.py`:n placeholder-`QMainWindow` `MainWindow`-luokalla `gui/main_window.py`:ssä. Layout: ylhäällä otsikko-rivi (Space Grotesk H1 "dxf2ifc" + caption "AutoCAD DXF → IFC 4"), keskellä `QSplitter` (vasemmalla file/profile-paneeli, oikealla preview/log-paneeli) ja alhaalla `QStatusBar`. Failing-test varmistaa että `MainWindow().windowTitle() == "dxf2ifc"` ja että `findChild(QSplitter)` palauttaa ei-None.
- [ ] Task 8: lisää `MainWindow.set_status(text: str, *, level: str = "info")` -helper joka päivittää `QStatusBar`-tekstin ja asettaa property-attribuutin `level` (`info`/`success`/`error`) jolla QSS värittää viestin (info-blue / success-amber / error-red). Testi varmistaa kolmen tason värit (käytä `QStatusBar.styleSheet()`-property-checkiä tai `currentMessage()`).
- [ ] Task 9: lisää `MainWindow`-konstruktoriin "menubar" jossa `File → Open DXF…`, `File → Quit` ja `Help → About`. Open DXF triggaa myöhempää convert-flowta (Section 4); Quit kutsuu `self.close()`; About näyttää `QMessageBox.about` jossa version + lisenssi. Testi varmistaa että menubarissa on tasan kolme actionia odotetuilla nimillä.

## Section 4: Convert-flow (DXF → IFC napilla)

- [ ] Task 10: lisää `gui/file_panel.py`:hen `FilePanel`-widget jossa kaksi `QLineEdit` + `QPushButton[secondary="true"]` -paria: "DXF input" (Browse → `QFileDialog.getOpenFileName` filter `*.dxf`) ja "IFC output" (Browse → `QFileDialog.getSaveFileName` filter `*.ifc`). Lisäksi yksi `QPushButton[primary="true"]` "Convert". Failing-test varmistaa että browse-napin painaminen kutsuu monkeypatchattua `QFileDialog`:a ja täyttää line-editin.
- [ ] Task 11: lisää `gui/convert_worker.py`:hen `ConvertWorker(QObject)`-luokka jossa `Signal(str)` `finished` ja `Signal(str)` `failed`. `run(dxf, out, profile)` ajaa `convert_dxf` taustasäikeessä (`QThread.create` tai `QRunnable`+`QThreadPool`) ja emittoi sopivan signaalin. Testi monkeypatchaa `convert_dxf` no-opiksi ja varmistaa että `finished` saa output-pathin.
- [ ] Task 12: kytke `FilePanel`-Convert-nappi `MainWindow`:ssa: nappi käynnistää `ConvertWorker`:n, päivittää statusbarin "Converting…" → "Done: <path>" / "Error: <msg>". Disabloi nappi ajon ajaksi. Testi simuloi koko flow:n monkeypatchatulla `convert_dxf`:llä ja varmistaa lopullisen success-statusin.
- [ ] Task 13: integraatiotestissä (offscreen QPA) aja oikea `convert_dxf` simple_wall.dxf-fixturella, varmista että GUI tuottaa oikean IFC-tiedoston ja että statusbar lukee "Done".

## Section 5: Layer preview & mapping list

## Section 6: Profile editor (custom layer-säännöt)

## Section 7: Polish, packaging hooks, dokumentaatio
