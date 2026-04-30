# PROGRESS

Volatile state — current build + open todos. Aiempi Plan-historia (A–H) +
bugfixit on arkistoitu `docs/PROGRESS-archive.md`:hen.

## Latest

**Build #29** (2026-04-30, SHA `76A4F5CB606034E0`)

- Repo cleanup + paketointi: `ifc_writer.py` (1908 r) → 6-moduulin paketti
  (skeleton / classification / mesh / builders / orchestrator + transforms)
- Public API ennallaan re-export-fasadin kautta — testit + GUI/CLI
  pelaa identtisesti
- Vanhat / kuolleet testit poistettu (Bugfix-12-narrowed-profile-artefaktit)
- Duplikaatti `default_kylmalaite_tate_only.toml` poistettu
- `tmp/` 610 MB → 3 MB; PROGRESS-historia archived
- 440/440 testiä passes

**Build #28** (2026-04-30, SHA `E066E277F437B40A`)

- AutoCAD COM removed → accoreconsole + STLOUT for ACIS bodies
  (no recent-files pollution, no GUI window pop, no pywin32 dependency)
- INSERT block content extracted via EXPLODE+STLOUT
  (höyrystinten kotelo + tuulettimen rengas + kannakkeet)
- 6 Finnish PSets per IFC product:
  FI_Asennus / FI_Geometria / FI_Komponentti / FI_Tuote / FI_Tekninen / FI_Sijainti
- POSITIO-blokki → Koneikko + Laitetunnus -linkitys
  (15/15 höyrystintä saa JK1/JK2/JK4 + numero 1–42 automaattisesti)
- "suunnittelualat" -luokittelu (TATE / ARK) eksplisiittisesti per tuote
- FI_Geometria field labels: Pituus hyllyille/putkille (Syvyys vain laatikoille)
- FI_Komponentti renamed: Koneikko (TEKSTI) + Laitetunnus (NUMERO)

**Test status**: 24/24 finnish_psets-testit passes. Ei-GUI-testit ~460 passes
(joitain Bugfix-12-narrowed-profile-artefakteja edelleen failauksessa,
hyväksyttävät).

## Open todos

- [ ] **DXF data quality**: 1× KYL-TIKASHYLLY 3DSOLID handle `118A` outlier-paikassa
  (X=1056k, Z=828k vs muu malli X≈730k, Z≈97k). Solibri varoittaa
  "Mallit laajasti hajallaan". Joko Lauri korjaa AutoCADissa tai konvertteri
  voisi flagata outlierit.
- [ ] **GUI Profile Editor** ei näytä FI_*-kenttiä (TOML-edit toimii käsin)
- [ ] **POSITIO-block-pattern** laajempi kattaus jos blokin nimi
  vaihtelee (nyt `positiov2*`)
- [ ] **`ifc_writer.py` (1908 riviä)** — split into add_*.py modules
  for readability (cleanup task, plan-mode)
- [ ] **Outlier-warning** convertterissa (vaihtoehtoinen täydennys
  Solibrin omalle "Mallit hajallaan" -tarkastukselle)

## Roadmap (delivered)

Plans A→H valmiit, ks. `docs/PROGRESS-archive.md` per-task-SHA-historia.
Plan I (TrueNorth-rotaatio + lisä-MEP-koodit) ei kirjoitettu —
toteutetaan jos tarve syntyy.
