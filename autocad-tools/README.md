# autocad-tools — AutoLISP-piirtotyökalut

AutoCAD/BricsCAD-piirtotyökalut joilla kylmälaitepiirustukset tehdään.
Ne tuottavat `KYL-*`-layerit ja INSERT-blokit jotka ovat **dwg2ifc:n
pääsyöte** — LISP-puoli ja parseri ovat yksi kytketty kokonaisuus, ja
ne ovat täällä samassa repossa jotta konvertterin ylläpitäjällä on
molemmat päät käden ulottuvilla.

## Sisältö

- **`*.lsp`** — AutoLISP-komennot. Mm. `POSITIO` (numerointi), `KLH` /
  `KLHL` / `KLHT` (kylmälaitehyllyt), `HY1`–`HY3` (höyrystimet),
  `KONEIKKO`, `LAUHDUTIN`, `VARUSTEET` (sähkövarusteet), `KOTELO`,
  `REIKAVARAUS` / `RV` (KYL-reikävarausblocki, GUID-attribuutilla),
  `KAATO3D`, putkityökalu. `klhylly.lsp` on AutoCAD-, `klhylly-brics.lsp`
  BricsCAD-variantti. `_loader.lsp` lataa työkalut.
- **`*.dwg`** — blokkien lähde-DWG:t (höyrystin, koneikko, lauhdutin,
  positio, levy-/tikashylly, kotelo, varusteet). LISP-komennot
  INSERT:äävät nämä piirustukseen.

## Suhde autocad-lisp-ohjeet-repoon

Loppukäyttäjän jakelu — asennuspaketti + ohjesivusto — elää erillisessä
repossa **[`autocad-lisp-ohjeet`](https://github.com/Mcrauli/autocad-lisp-ohjeet)**
(GitHub Pages -sivusto + `make-bundle.ps1` joka paketoi nämä tiedostot
ZIP:iin, sekä CUIX-ribbon + installer).

Tämä kansio on **kopio** tuon repon `files/`-kansion `.lsp`- ja
`.dwg`-tiedostoista. Jos muokkaat työkaluja täällä ja loppukäyttäjien
jakelupaketin pitää pysyä ajan tasalla, vie sama muutos myös
autocad-lisp-ohjeet-repon `files/`-kansioon ja aja siellä
`make-bundle.ps1`.

## Miten LISP ↔ parseri kytkeytyvät

- LISP-komennot luovat `KYL-*`-layereille geometriaa ja INSERT-blokkeja,
  joissa on ATTDEF-attribuutteja.
- `dwg2ifc` tunnistaa `KYL-*`-layerit
  (`src/dwg2ifc/profiles/default_kylmalaite.toml`) ja blokkien
  ATTRIB-kentät (`src/dwg2ifc/core/block_attribs.py`).
- **Jos layer-nimet tai blokki-attribuutit muuttuvat täällä**, tarkista
  että profiili-TOML ja `block_attribs.py` vastaavat — muuten konversio
  ei tunnista uutta layeria/kenttää.
