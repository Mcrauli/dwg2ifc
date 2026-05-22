# Packaging dwg2ifc

PyInstaller bundlaa CLI:n ja PySide6-GUI:n yhdeksi käynnistettäväksi binääriksi
joka voidaan jakaa loppukäyttäjälle ilman Python-asennusta. Tämä dokumentti
kuvaa paikallisen buildin, CI-buildin ja release-prosessin.

## Local build

```bash
# Asenna build-deps (PyInstaller + ifcopenshell + PySide6).
uv sync --extra dev --extra gui

# Aja PyInstaller checked-in spec-tiedostolla. --clean tyhjentää välivälineet.
uv run pyinstaller build/dwg2ifc.spec --clean --noconfirm
```

Output päätyy `dist/dwg2ifc(.exe)` -tiedostona. Spec on Plan E Section 1
-skeleton (datas, hidden_imports ja version_info täydennetään Section 2:ssa).

## Installer (Inno Setup)

PyInstaller-exen ympärille käännetään **Inno Setup 6** -installeri jota Lauri
jakelee loppukäyttäjille `.\scripts\build_installer.ps1`-skriptillä. Installer
näyttää oikealta Windows-asennusohjelmalta (Start-menu -merkintä,
Apps & Features -uninstaller, version-info), mikä vähentää SmartScreenin
"unknown publisher" -kitkaa verrattuna paljaaseen `.exe`:hen.

```powershell
# Asenna Inno Setup 6 kerran: https://jrsoftware.org/isinfo.php
# Build-ketju: PyInstaller exe → ISCC compile → dist/dwg2ifc-Setup-<v>.exe
.\scripts\build_installer.ps1
```

Installer-konfig on `build/installer.iss`. Avainpäätökset:

- **`PrivilegesRequired=lowest`** + `PrivilegesRequiredOverridesAllowed=dialog`
  → asennetaan oletuksena per-user (`%LOCALAPPDATA%\Programs\dwg2ifc`), ei
  UAC-promptia eikä admin-oikeuksia. Käyttäjä voi halutessaan elevoida
  Program Files -asennukseen wizard-dialogista.
- **Stable `AppId`** GUID → upgrade/uninstall toimii oikein versioiden välillä.
  ÄLÄ koskaan vaihda GUIDia — muuten vanhaa asennusta ei pystytä päivittämään.
- **`x64compatible`** ainoa tuettu arkkitehtuuri (PySide6 + ifcopenshell
  vaativat 64-bittisen Pythonin).
- **`compression=lzma2/max`** → installer ~40-60% pienempi kuin paljas
  PyInstaller-exe.
- **Suomi + englanti** -kielet.

### Build pipeline

`scripts/build_installer.ps1` ajaa:
1. `scripts/build_exe.ps1` → `dist/dwg2ifc.exe` + `dist/dwg2ifc-<v>.exe`
2. `dist/LICENSES.md`-fallback (CI:n release.yml korvaa sen rikkaammalla
   versiolla ennen installerin compilea).
3. ISCC-compile `build/installer.iss` → `dist/dwg2ifc-Setup-<v>.exe`
4. SHA256-sidecar `dist/dwg2ifc-Setup-<v>.exe.sha256`

CI:n `windows-latest`-runnerit pitävät Inno Setup 6:n esiasennettuna, joten
workflowt eivät vaadi erillistä install-stepiä.

### SmartScreen-realiteetit

Allekirjoittamaton installer saa edelleen "Windows protected your PC"
-varoituksen ensimmäisillä latauksilla — SmartScreen-reputaatio rakentuu
vasta latausmäärän kasvaessa tai EV-code-signing-sertifikaatilla. Per-user
asennus + GitHub Releases -domain vähentävät kitkaa, mutta eivät poista
varoitusta täysin. Loppukäyttäjän ohje: **More info → Run anyway**.

Code signing -hookki (`signtool sign /f cert.pfx /tr http://timestamp.digicert.com
/fd sha256 /td sha256 ...`) lisätään `build_installer.ps1`:een kun
sertifikaatti on hankittu — sekä `dwg2ifc.exe`:lle ennen ISCC-compilea
että installerille sen jälkeen.

### Huomautus alustasta

PyInstaller ei tee cross-compilea: alustan natiivi binääri syntyy aina ajavan
host-koneen alustalle.

- **Linux-host** tuottaa ELF-binäärin nimellä `dist/dwg2ifc` (smoke-build,
  käytetään lähinnä CI-validointiin että .spec on suoritettavissa).
- **Windows-host** (Windows 10/11 tai GitHub Actions `windows-latest`-runner)
  tuottaa ohjelmoidun `dist/dwg2ifc.exe`-tiedoston, joka on lopullinen
  jakelumuoto loppukäyttäjälle.
- **macOS** ei ole virallisesti tuettu — Lauri jakaa vain Windows-builds.

Tämän projektin pääjakelu on `dwg2ifc.exe`, joka rakennetaan
GitHub Actions -workflow:lla (ks. Section 3 + 4).

## CI build

GitHub Actions ajaa `.github/workflows/build.yml`-workflow:n joka triggeröityy:

- `pull_request` (kaikki branchit)
- `push: branches: [master]`

### Windows-job (`windows-latest`)

1. Checkout + Python 3.12 + uv setup.
2. Aja `scripts/build_exe.ps1`, joka kutsuu PyInstallerin spec-tiedostolla.
3. Smoke-step: ajaa `dist/dwg2ifc-*.exe --version`. Vaaditaan exit code 0 ja
   stdout joka sisältää merkkijonon `dwg2ifc`. Jos smoke epäonnistuu (puuttuva
   ifcopenshell-skeema, hidden import, jne.), artifactia ei uploadata.
4. Upload-step julkaisee artifactin nimellä `dwg2ifc-windows`. Sisältää
   `dist/dwg2ifc-<version>.exe` ja `dist/dwg2ifc-<version>.exe.sha256`.

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
   - `src/dwg2ifc/_version.py` (`__version__ = "X.Y.Z"`)
   - `pyproject.toml` (`version = "X.Y.Z"`)
2. **Päivitä CHANGELOG.md.** Lisää uusi `## vX.Y.Z — YYYY-MM-DD` -otsikko ja
   listaus käyttäjälle näkyvistä muutoksista (Added / Changed / Fixed).
   Release-workflow käyttää tätä `--notes-file`:nä joten teksti näkyy suoraan
   GitHub Releasessa.
3. **Commit + annotated tag.**
   ```bash
   git add src/dwg2ifc/_version.py pyproject.toml CHANGELOG.md
   git commit -m "release: vX.Y.Z"
   git tag -a vX.Y.Z -m "vX.Y.Z"
   git push origin master
   git push origin vX.Y.Z
   ```
4. **Workflow ajaa.** `.github/workflows/release.yml` triggeröityy `v*.*.*`
   -tagista, buildaa Windows-`.exe`:n + Inno Setup -installerin, ajaa
   smoke-testit, kerää `LICENSES.md`:n ja luo *draft* GitHub Releasen tagista.
   Artifactit: `dwg2ifc-X.Y.Z.exe`, `dwg2ifc-X.Y.Z.exe.sha256`,
   `dwg2ifc-Setup-X.Y.Z.exe`, `dwg2ifc-Setup-X.Y.Z.exe.sha256`, `LICENSES.md`.
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
  scopessa (esim. `C:\Tools\dwg2ifc\`).
- **Pitkän aikavälin ratkaisu**: code-signing-sertifikaatti (esim.
  Sectigo / SSL.com EV CodeSigning) lisätään tulevaisuudessa Plan E:n
  follow-up:ssa. SmartScreen-reputaatio rakentuu vasta kymmenien tuhansien
  asennuksien jälkeen.

### `dwg2ifc.exe` käynnistyy mutta kaatuu "ifcopenshell schema not found"

PyInstaller ei aina ymmärrä että `ifcopenshell` lataa `IFC4.exp` /
`IFC4X3_ADD2.exp`-skemoja runtime-resourceina. Spec-tiedoston `Analysis(...)`
pitää sisältää `(ifcopenshell-data, dwg2ifc/ifcopenshell)` tai vastaava
`--add-data`. Tarkista `build/dwg2ifc.spec`:in `datas`-lista — jos puuttuu,
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
- **`--onedir`**: jakelu on `dwg2ifc/`-kansio + sen sisällä olevat DLL/PYD
  -tiedostot, käynnistys nopea (<1 s), mutta loppukäyttäjälle vaikeampi
  käsitellä (zip vaaditaan).

Jos cold start -aika nousee ongelmaksi, vaihda `.spec`:n `EXE(...)` →
`COLLECT(...)` -reseptiin ja jaa zip-paketointina.

## Icon

`build/dwg2ifc.spec` ja `build/installer.iss` poimivat `assets/dwg2ifc.ico`:n
automaattisesti jos tiedosto on olemassa — muuten PyInstaller-bootloaderin
default-icon ja Inno Setupin default-installer-icon. ICO-vaatimukset:
multi-resolution (16/32/48/256 px) ja sininen-amber-paletti (CLAUDE.md
brand-värit). Kun `assets/dwg2ifc.ico` on lisätty, ei spec- eikä iss-tiedostoon
tarvitse koskea — seuraava build poimii sen automaattisesti.
