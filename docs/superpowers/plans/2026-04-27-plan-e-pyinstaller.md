---
plan: E
title: PyInstaller packaging + GitHub Releases
status: draft
date: 2026-04-27
depends_on: D
---

# Plan E: PyInstaller-pakkaus + GitHub Releases

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps käyttävät `- [ ]`-syntaksia. Tehtävien testaus on osin manuaalista (Windows-host), CI-osuudessa GitHub Actions toimii pääajurina. TDD-kuria sovelletaan missä järkevää (.spec-validointi, version-stamp helper).

**Goal:** Tee dxf2ifc:stä standalone Windows .exe -jakelu jonka loppukäyttäjä voi ladata GitHub Releases -sivulta ja käynnistää ilman Python-ympäristöä. Pakkaa CLI ja GUI yhteen käynnistettävään, bundlea ifcopenshell:n IFC-schema-tiedostot, brand-fontit ja default-profiili-TOML, ja automatisoi build + release GitHub Actions -workflowlla joka triggeröityy git-tagista (`vX.Y.Z`).

**Architecture:** PyInstaller `--onefile` `--windowed` (GUI:n osalta) + erillinen console-stub CLI:lle, tai yksi onedir-build joka exposesi molemmat console-scripts. .spec-tiedosto checked-iniin, hidden imports listattuna eksplisiittisesti (`ifcopenshell`, `ezdxf`, `PySide6.QtSvg`). GitHub Actions matrix Windows-runnerilla, artifact upload + release attach.

**Tech stack:** PyInstaller 6+, GitHub Actions (windows-latest), `gh release`, säilyvät core-deps (ifcopenshell, ezdxf, PySide6).

---

## Repository state before this plan

Plan A 21/21 + Plan B 50/50 + Plan C 12/12 + Plan D 25/25 valmis (master `011bd5e`). 200 testiä passed, coverage 89 %, ruff clean. CLI- ja GUI-entry-pointit määritelty (`dxf2ifc`, `dxf2ifc-gui`). Brand-fontit `assets/fonts/` + QSS `src/dxf2ifc/gui/style.qss` jo bundle-kelpoisia.

---

## Section 1: PyInstaller bootstrap

- [ ] Task 1.1: lisää `pyproject.toml`:n `dev`-extraan `pyinstaller>=6.10` ja aja `uv sync --extra dev --extra gui`. Luo `tests/test_pyinstaller_bootstrap.py` joka tarkistaa että `import PyInstaller` toimii ja että `PyInstaller.__main__` on suoritettavissa moduulina. Smoke ainoastaan, ei .exe-buildia tässä taskissa.
- [ ] Task 1.2: luo `build/dxf2ifc.spec` PyInstaller .spec -tiedosto, joka käyttää `Analysis(['src/dxf2ifc/gui/__main__.py'], ...)` -entry-pointtia, asettaa `name='dxf2ifc'` ja `windowed=True`. Piiri-spec ainoastaan: bundlatut datat ja hidden imports tulevat section 2:ssa. Lisää `.spec`-tiedosto repoon. Lisää `tests/test_spec_file.py` joka parsii `dxf2ifc.spec` Python-evalilla ja varmistaa että `Analysis`-kutsu sisältää oikean entry-pointin.
- [ ] Task 1.3: lisää `pyproject.toml` `[tool.dxf2ifc.packaging]`-vapaaehtoiseen sektioon `version_stamp`-helper-vakio (string). Luo `src/dxf2ifc/_version.py` joka exposesi `__version__ = "0.1.0"`-stringin importattavaksi sekä `pyproject.toml`-versiosta. Failing test: `tests/test_version.py` varmistaa että `from dxf2ifc import __version__` ja `metadata.version("dxf2ifc")` palauttavat saman.
- [ ] Task 1.4: dokumentoi `docs/packaging.md` alkuun (uusi tiedosto): "Local build" -ohje (`uv run pyinstaller build/dxf2ifc.spec --clean`) ja huomautus että Linux-build ei tuota `.exe`-tiedostoa vaan ELF:n; Windows-build vaatii Windows-hostin tai GitHub Actions windows-latest -runnerin.

## Section 2: .spec-konfiguraatio + asset bundling

## Section 3: Windows build (paikallinen + CI matrix)

## Section 4: GitHub Actions release-workflow

## Section 5: Smoke + checksum + dokumentointi
