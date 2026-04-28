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

## Icon TODO

`build/dxf2ifc.spec` ei vielä viittaa `.ico`-tiedostoon (`icon=None`). Brand-icon
suunnitellaan ja toimitetaan polkuun `assets/dxf2ifc.ico` ennen ensimmäistä
julkaisua, ja `.spec`:n `icon=None` vaihdetaan polkuun. ICO-vaatimukset:
multi-resolution (16/32/48/256 px) ja sininen-amber-paletti (CLAUDE.md
brand-värit). Kunnes icon on olemassa, .exe käyttää PyInstallerin
oletusbootloader-kuvaketta.
