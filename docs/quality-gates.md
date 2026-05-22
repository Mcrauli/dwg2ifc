# Quality gates — kahden tason laatuprosessi

dwg2ifc:n IFC-luovutuksen oikeellisuus varmistetaan kahdella toisiaan
täydentävällä portilla. Tason 1 portti automatisoituu CI:ssä joka pushilla.
Tason 2 portin Lauri ajaa manuaalisesti ennen jokaista tag-pohjaista
releasea.

## Taso 1 — automaattinen `ifcopenshell.validate` -gate

**Mitä:** `dwg2ifc.core.quality.validate_ifc(path)` wrappaa
`ifcopenshell.validate.validate(file, json=True, return_json=True)` ja
palauttaa structured `ValidationReport`-tuloksen (errors, warnings,
summary). Wrapperi täydentää schema-virheet myös YTV 2012 -spesifillä
Talo2000-luokittelutarkistuksella: jos `IfcWall`, `IfcSlab`, `IfcDoor`
tai `IfcWindow` ei ole kytketty `IfcRelAssociatesClassification`-relation
kautta `Talo2000`-codesetiin, tulee warning `"missing Talo2000
classification"`.

**Mitä tarkistaa:**

- IFC-skeeman validisuus (entity-relations, attribute-tyypit, geometria).
- IFC4-yksiköiden olemassaolo (millimetri, IfcUnitAssignment).
- `IfcRelAssociatesClassification`-linkki Talo2000-codesetiin
  jokaiselle pakolliselle entity-tyypille.

**Missä ajetaan:**

- **CLI:** `dwg2ifc convert input.dxf out.ifc --validate` palauttaa exit
  1 jos errors > 0; warningit ja errors printataan stderr:ään. Käytä
  tätä tuotantoautomaation osana.
- **GUI:** `convert_dxf` ajetaan validate=True -vaihtoehdolla, ja
  PreviewLogPanelissa näkyvät summary, warnings ja errors. Käyttäjälle
  riittää että näkee onko luovutus puhdas yhdellä silmäyksellä.
- **CI:** `.github/workflows/build.yml`:n Linux-job ajaa joka pushilla
  `uv run pytest tests/test_quality.py` -komennon, joka varmistaa että
  Plan B:n full-fixture passaa cleanisti (0 errors, 0 Talo2000-warnings).

**Ei tarvitse Solibri-asennusta.** Kaikki tason 1 osat ovat
ifcopenshell-puhtaita ja ajautuvat sandboxissa, CI:ssä ja Lauri:n
Windowsilla samalla logiikalla.

## Taso 2 — manuaalinen Solibri-snapshot-verify

**Mitä:** Lauri ajaa Solibri Anywhere CLI:n
`tools/solibri/dwg2ifc.bcfzip`-rulesetillä referenssimallia vasten
(esim. `tests/fixtures/solibri_reference_full.ifc`) ja vertaa tuloksen
committed-baselineen `tests/snapshots/solibri/full_kylmaelement.json`.
Helper-skriptit:

- `tools/solibri/verify.py` — `Solibri.exe -load -ruleset -output -exit`
- `tools/solibri/parse_report.py` — XML→`RuleResult`-dict
- `tools/solibri/diff_snapshot.py` — `SnapshotDelta(added, removed)`
- `python -m tools.solibri verify --ifc … --ruleset … --report …`
- `tests/test_solibri_snapshot_chain.py` (gated `@pytest.mark.solibri`)

**Mitä tarkistaa (`tools/solibri/dwg2ifc.bcfzip` 5 sääntöä):**

1. Units are millimetres
2. Talo2000 classification coverage
3. IfcSystem grouping for refrigeration networks
4. Cold-room panels emit IfcBuildingElementProxy 1352
5. Cooling equipment uses MEP entity types (Evaporator/Condenser/Compressor)

Säännöt on kuvattu tarkemmin [docs/solibri-rules.md](solibri-rules.md).

**Missä ajetaan:** Lauri-driven, ennen tag-releasea. CI ei voi ajaa,
koska Solibri Anywhere on lisensoitu desktop-ohjelma. Pytest-marker
`solibri` skippautuu automaattisesti `Solibri.exe`-binäärin puuttuessa.

## Release-flow

1. Push master:iin → taso 1 ajaa CI:ssä.
2. Kun `release.yml` on valmis julkaisemaan tagin, suorita
   [docs/packaging-smoke.md](packaging-smoke.md)-checklist Windowsilla.
3. Avaa Solibri Anywhere, tuo `tools/solibri/dwg2ifc.bcfzip` ruleset:ksi,
   lataa referenssi-IFC, aja säännöt ja vie raportti.
4. Aja `python -m tools.solibri verify ...` ja varmista että diff vs.
   baseline on tyhjä (`SnapshotDelta.is_clean is True`).
5. Päivitä `tests/snapshots/solibri/full_kylmaelement.json`, jos uusia
   sallittuja sääntöpoikkeamia tunnistettiin.
6. Vasta sitten julkaise tagin draft-release lopulliseksi.

## Domain-pohjainen luokitus (Plan H)

Plan H:n jälkeen Taso 1 -gate tarkistaa rinnakkain Talo2000- ja RAVA-
luokitukset suunnittelualan mukaan: ARK-puolen rakennusosat (Talo 2000) ja
TATE-puolen tuoteosat (RAVA-LVI / RAVA-TATE). Domain-säännöt, codeset:t ja
viralliset koodit on kuvattu [`docs/rava-classification.md`](rava-classification.md):ssä.

Plan G:n jälkeen Taso 1 -gate sisältää myös **CRS-coverage-tarkistuksen**
(`crs_orphan_map_conversion`, `crs_missing_map_conversion`,
`crs_possible_double_transform`). Solibri-rule-set:iin lisätty rule #7
"CRS coverage" (`tools/solibri/dwg2ifc.bcfzip`) tekee saman
manuaalisesti Tasolla 2. Yksityiskohdat ja ETRS-TM35FIN-konventio:
[`docs/coordinate-system.md`](coordinate-system.md).

## Mitä Plan F EI vielä kata

- Solibri-tarkistuksen automatisointi — ei mahdollista ilman lisenssipalvelinta.
- ~~IFC 4.3 -migraatio + RAVA-luokitus~~ — toteutettu Plan H:ssa
  (ks. [`docs/rava-classification.md`](rava-classification.md)).
- ~~Coordinate System / georeferenced IFC~~ — toteutettu Plan G:ssa
  (ks. [`docs/coordinate-system.md`](coordinate-system.md)).
