# Packaging dxf2ifc

PyInstaller bundlaa CLI:n ja PySide6-GUI:n yhdeksi käynnistettäväksi binääriksi
joka voidaan jakaa loppukäyttäjälle ilman Python-asennusta. Tämä dokumentti
kuvaa paikallisen buildin, CI-buildin ja release-prosessin.

## Local build

```bash
# Asenna build-deps (PyInstaller + ifcopenshell + PySide6).
uv sync --extra dev --extra gui

# Aja PyInstaller checked-in spec-tiedostolla. --clean tyhjentää välivälineet.
uv run pyinstaller build/dxf2ifc.spec --clean --noconfirm
```

Output päätyy `dist/dxf2ifc(.exe)` -tiedostona. Spec on Plan E Section 1
-skeleton (datas, hidden_imports ja version_info täydennetään Section 2:ssa).

### Huomautus alustasta

PyInstaller ei tee cross-compilea: alustan natiivi binääri syntyy aina ajavan
host-koneen alustalle.

- **Linux-host** tuottaa ELF-binäärin nimellä `dist/dxf2ifc` (smoke-build,
  käytetään lähinnä CI-validointiin että .spec on suoritettavissa).
- **Windows-host** (Windows 10/11 tai GitHub Actions `windows-latest`-runner)
  tuottaa ohjelmoidun `dist/dxf2ifc.exe`-tiedoston, joka on lopullinen
  jakelumuoto loppukäyttäjälle.
- **macOS** ei ole virallisesti tuettu — Lauri jakaa vain Windows-builds.

Tämän projektin pääjakelu on `dxf2ifc.exe`, joka rakennetaan
GitHub Actions -workflow:lla (ks. Section 3 + 4).

## CI build

GitHub Actions ajaa `.github/workflows/build.yml`-workflow:n joka triggeröityy:

- `pull_request` (kaikki branchit)
- `push: branches: [master]`

### Windows-job (`windows-latest`)

1. Checkout + Python 3.12 + uv setup.
2. Aja `scripts/build_exe.ps1`, joka kutsuu PyInstallerin spec-tiedostolla.
3. Smoke-step: ajaa `dist/dxf2ifc-*.exe --version`. Vaaditaan exit code 0 ja
   stdout joka sisältää merkkijonon `dxf2ifc`. Jos smoke epäonnistuu (puuttuva
   ifcopenshell-skeema, hidden import, jne.), artifactia ei uploadata.
4. Upload-step julkaisee artifactin nimellä `dxf2ifc-windows`. Sisältää
   `dist/dxf2ifc-<version>.exe` ja `dist/dxf2ifc-<version>.exe.sha256`.

### Linux-smoke-job (`ubuntu-latest`)

`scripts/build_exe.sh` ajetaan PyInstallerilla samaa spec-tiedostoa vasten.
Tarkoitus on validoida että `.spec` on cross-platform-validi (datas + hidden
imports + excludes) ennen kuin Windows-build ajaa pidemmän reitin. Tuloksena
syntyy ELF-binääri jota _ei_ uploadata — Windows-job omistaa jakelu-output:n.

### Asennetut Qt-runtimet (Linux)

PySide6 vaatii ajonaikaisesti `libegl1`, `libgl1`, `libxkbcommon0` ja
`libdbus-1-3`-paketit jotta importti toimii. Workflow asentaa ne ennen
PyInstaller-buildia.

### Mitä CI _ei_ tee

- GUI-smoke (offscreen QPA) ei aja CI:ssä — se vaatii pidemmän setupin ja
  flaky-rajan, joten manuaaliajo Windows-hostilla on luotettavampi.
  `docs/packaging-smoke.md` (Plan E Task 20) listaa manuaalisen checklistin.
- PyInstaller-cache-kansiota (`%LOCALAPPDATA%\pyinstaller`) _ei_ cachetä
  artifactina — `--clean`-flag tyhjentää sen joka build:ssa, ja stale cache
  on ollut PyInstallerin tunnettu virhelähde.

## Release-prosessi

Tag-pohjainen release on Lauri-driven manuaaliprosessi — workflow tekee
buildin ja luo draft-releasen, mutta lopullisen julkaisun napauttaa
ihminen GitHub-UI:ssa.

1. **Bumpaa versio.** Päivitä molemmat:
   - `src/dxf2ifc/_version.py` (`__version__ = "X.Y.Z"`)
   - `pyproject.toml` (`version = "X.Y.Z"`)
2. **Päivitä CHANGELOG.md.** Lisää uusi `## vX.Y.Z — YYYY-MM-DD` -otsikko ja
   listaus käyttäjälle näkyvistä muutoksista (Added / Changed / Fixed).
   Release-workflow käyttää tätä `--notes-file`:nä joten teksti näkyy suoraan
   GitHub Releasessa.
3. **Commit + annotated tag.**
   ```bash
   git add src/dxf2ifc/_version.py pyproject.toml CHANGELOG.md
   git commit -m "release: vX.Y.Z"
   git tag -a vX.Y.Z -m "vX.Y.Z"
   git push origin master
   git push origin vX.Y.Z
   ```
4. **Workflow ajaa.** `.github/workflows/release.yml` triggeröityy `v*.*.*`
   -tagista, buildaa Windows-`.exe`:n, ajaa `--version`-smoke-testin, kerää
   `LICENSES.md`:n ja luo *draft* GitHub Releasen tagista. Artifactit:
   `dxf2ifc-X.Y.Z.exe`, `dxf2ifc-X.Y.Z.exe.sha256`, `LICENSES.md`.
5. **Tarkista ja julkaise.** Lataa `.exe` GitHub-UI:n draft-releasesta omalle
   Windows-koneelle, vertaa SHA256:ta `.sha256`-sidecariin, aja
   `docs/packaging-smoke.md`-checklist (Task 20). Kun kaikki vihreää,
   napauta "Publish release" GitHub-UI:ssa. Jos jokin on rikki, poista draft
   ja aloita alusta korotetulla bugfix-versiolla.

> **Älä koskaan force-poista jo julkaistua tagia** — Releases jää viittaamaan
> orpoon SHA:han ja loppukäyttäjien shasums menevät rikki. Bumpataan aina
> uusi patch-versio.

## Troubleshooting

### Windows Defender / SmartScreen blokkaa `.exe`:n

`.exe` ei ole code-signattu MVP-vaiheessa, joten Windows SmartScreen näyttää
"Windows protected your PC" -warningin ja Defender voi karanteeniin
juuri ladatun tiedoston.

- **SmartScreen**: napauta dialogissa **More info → Run anyway**.
- **Defender quarantine**: avaa "Virus & threat protection" → "Allowed
  threats" / "Protection history" ja palauta tiedosto. Tai pidä `.exe`
  user-folderin sijaan kansiossa joka ei ole reaaliaikaisen skannin
  scopessa (esim. `C:\Tools\dxf2ifc\`).
- **Pitkän aikavälin ratkaisu**: code-signing-sertifikaatti (esim.
  Sectigo / SSL.com EV CodeSigning) lisätään tulevaisuudessa Plan E:n
  follow-up:ssa. SmartScreen-reputaatio rakentuu vasta kymmenien tuhansien
  asennuksien jälkeen.

### `dxf2ifc.exe` käynnistyy mutta kaatuu "ifcopenshell schema not found"

PyInstaller ei aina ymmärrä että `ifcopenshell` lataa `IFC4.exp` /
`IFC4X3_ADD2.exp`-skemoja runtime-resourceina. Spec-tiedoston `Analysis(...)`
pitää sisältää `(ifcopenshell-data, dxf2ifc/ifcopenshell)` tai vastaava
`--add-data`. Tarkista `build/dxf2ifc.spec`:in `datas`-lista — jos puuttuu,
lisää:

```python
("path/to/site-packages/ifcopenshell/", "ifcopenshell"),
```

ja buildaa uudestaan `--clean`-flag:in kanssa.

### PySide6 antaa `ImportError: cannot find Qt platform plugin "windows"`

Symptomi: GUI ei avaudu, terminaalissa Qt-virhe. Syy: PyInstaller ei kerännyt
`PySide6/Qt/plugins/platforms/qwindows.dll`-pluginia. Korjaus: varmista että
PySide6 on yhtä versiota kuin lock-filessä ja että `--clean`-flag on käytössä
buildissa. Tarvittaessa lisää `hiddenimports=['PySide6.QtSvg',
'PySide6.QtSvgWidgets']` Spec:hen (Plan E Task 6).

### `--onefile` käynnistyy hitaasti

PyInstallerin `--onefile`-build extractoi koko payloadin `%TEMP%`:iin joka
käynnistyksessä, mikä lisää 3-8 sekuntia cold start -aikaa.

- **`--onefile`** (nykyinen oletus): yksi `.exe`, helppo jakaa, hidas
  käynnistys, Windows Defender skannaa joka kerta.
- **`--onedir`**: jakelu on `dxf2ifc/`-kansio + sen sisällä olevat DLL/PYD
  -tiedostot, käynnistys nopea (<1 s), mutta loppukäyttäjälle vaikeampi
  käsitellä (zip vaaditaan).

Jos cold start -aika nousee ongelmaksi, vaihda `.spec`:n `EXE(...)` →
`COLLECT(...)` -reseptiin ja jaa zip-paketointina.

## Icon TODO

`build/dxf2ifc.spec` ei vielä viittaa `.ico`-tiedostoon (`icon=None`). Brand-icon
suunnitellaan ja toimitetaan polkuun `assets/dxf2ifc.ico` ennen ensimmäistä
julkaisua, ja `.spec`:n `icon=None` vaihdetaan polkuun. ICO-vaatimukset:
multi-resolution (16/32/48/256 px) ja sininen-amber-paletti (CLAUDE.md
brand-värit). Kunnes icon on olemassa, .exe käyttää PyInstallerin
oletusbootloader-kuvaketta.
