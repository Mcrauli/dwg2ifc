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

## Icon TODO

`build/dxf2ifc.spec` ei vielä viittaa `.ico`-tiedostoon (`icon=None`). Brand-icon
suunnitellaan ja toimitetaan polkuun `assets/dxf2ifc.ico` ennen ensimmäistä
julkaisua, ja `.spec`:n `icon=None` vaihdetaan polkuun. ICO-vaatimukset:
multi-resolution (16/32/48/256 px) ja sininen-amber-paletti (CLAUDE.md
brand-värit). Kunnes icon on olemassa, .exe käyttää PyInstallerin
oletusbootloader-kuvaketta.
