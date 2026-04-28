---
plan: H
title: IFC 4.3 migration + RAVA classification (domain-based)
status: draft
date: 2026-04-28
depends_on: F
---

# Plan H: IFC 4.3 -migraatio + RAVA-luokitus (domain-pohjainen)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps käyttävät `- [ ]`-syntaksia. Tämä plan vaihtaa skeeman IFC4 → IFC4X3 ja siirtää TATE/kylmälaitteet pois Talo2000:sta RAVA-koodien (LVI-TUOTEOSA / TALOTEKNIIKKA-TUOTEOSA) alle. ARK-puolella (seinät/laatat/ovet/ikkunat/paneelit) Talo2000 säilyy. Multi-classification on KIELLETTY: jokainen elementti saa täsmälleen yhden codesetin domainin mukaan. RAVA-koodit ladataan virallisesta `koodistot.suomi.fi`-JSON-API:sta tooling-skriptillä; codesetit cachetetaan `src/dxf2ifc/profiles/rava/`-kansioon committoituna JSON:nä.

**Goal:** Tuottaa IFC 4.3 -tiedostot RAVA Pro3 -yhteensopivina, jolloin TATE-luokittelu (LVI- ja talotekniikka-tuoteosat sekä -järjestelmät) tulee suoraan RAVA-koodistosta. Lauri:n kylmälaiteasiakkaiden BIM-luovutus on tällöin Suomen valtion tuoteosa-koodiston (RAVA) -yhteensopiva, mikä on edellytys julkisen sektorin urakoissa ja täydentää Talo2000:n ARK-luovutuksen.

**Architecture:** Vaihe A on puhtaasti skeeman vaihto + regressio (kaikki nykyiset 314 testiä passaa IFC4X3:lla). Vaihe B muuttaa profiili-skeeman: `Rule.domain` on uusi pakollinen `Literal["ARK", "TATE"]`, ja yksi kolmesta koodi-kentästä täytetään (`talo2000_code` / `lvi_code` / `talotekniikka_code`). Mapper + ifc_writer kunnioittavat domainia: ARK-elementeille emitoidaan IfcRelAssociatesClassification Talo2000:een, TATE-elementeille RAVAan. Default-profiilin nimi vaihtuu `default_kylmalaite_talo2000.toml` → `default_kylmalaite.toml`, ja kylmälaitteet siirtyvät RAVA-koodien alle.

**Tech stack:** ifcopenshell ≥ 0.8.5 (IFC4X3 tuettu), ezdxf, pydantic, requests (RAVA-koodien lataaminen), tomli-w. Ei uusia juuri-deps:eja.

---

## Repository state before this plan

Plan A 21/21 + Plan B 50/50 + Plan C 12/12 + Plan D 25/25 + Plan E 23/23 + Plan F 16/16 valmis. Bugfix kierros 2 valmis (placement 1000× -bugi `2f827ea`, xref-prefix mapper `230f327`, ARK layer-säännöt `b1df8c3`). Master `b1df8c3`. 314 testiä passed + 1 skipped (Solibri-marker). Coverage 91 %.

---

## Section 1: IFC4X3-skeema-migraatio

## Section 2: RAVA-koodien lataaminen (4 codesetin sync)

## Section 3: Profile-skeeman domain-laajennus

## Section 4: Default-profiilin uudistus + KYL-* siirto RAVAan

## Section 5: Mapper + ifc_writer domain-pohjainen luokitus

## Section 6: Integraatio + dokumentointi + plan-loppupiste
