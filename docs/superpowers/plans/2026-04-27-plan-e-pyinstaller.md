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

## Section 2: .spec-konfiguraatio + asset bundling

## Section 3: Windows build (paikallinen + CI matrix)

## Section 4: GitHub Actions release-workflow

## Section 5: Smoke + checksum + dokumentointi
