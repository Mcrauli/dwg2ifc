# Manuaalinen Windows-smoke-checklist

Tämä on **Lauri-driven** ihmistesti jonka tarkoitus on varmistaa ennen
julkaisua, että `dxf2ifc-vX.Y.Z.exe` käynnistyy ja muuntaa testifiikstuurin
oikein. Aja jokaisella draft-releasella ennen "Publish release"-napin
painamista. Yksikään step ei ole automatisoitu — GUI-launch on liian flaky
CI:ssä, ja end-to-end Windows-IFC-validointi on rakennettu manuaaliseksi.

> Vie tämä ulos sandboxista: smoke ajetaan **paikallisella Windows-koneella**,
> ei GitHub Actions -runnerilla.

## 1. Lataa artifact draft-releasesta

1. Avaa GitHub Releases -sivu ja valitse uusin **Draft**.
2. Lataa `Assets`-osiosta:
   - `dxf2ifc-vX.Y.Z.exe`
   - `dxf2ifc-vX.Y.Z.exe.sha256`
   - `LICENSES.md`
3. Säilytä tiedostot samassa kansiossa, esim. `C:\Temp\dxf2ifc-smoke\`.

## 2. Tarkista SHA256

PowerShellissä samassa kansiossa:

```powershell
Get-FileHash -Algorithm SHA256 dxf2ifc-vX.Y.Z.exe
Get-Content dxf2ifc-vX.Y.Z.exe.sha256
```

Hashin pitää matsata sidecar-tiedoston ensimmäistä saraketta. Jos eivät
matsaa: **älä julkaise**, lataa uudelleen ja vertaa uudestaan.

## 3. Käynnistä GUI

1. Tuplaklikkaa `dxf2ifc-vX.Y.Z.exe`. Windows SmartScreen voi näyttää
   "Windows protected your PC" -dialogin (allekirjoittamaton MVP-build):
   napauta **More info → Run anyway**.
2. Sovelluksen pitää avautua n. 3-8 sekunnissa (PyInstaller-onefile cold start).
3. Tarkista visuaaliset elementit:
   - **Otsikko**: "dxf2ifc" (Space Grotesk)
   - **Brand-väri**: amber (`#f59e0b`) Convert-painikkeessa
   - **Status bar**: "Ready"
   - **Vasen paneeli**: Files & profile + Layer table (tyhjä)
   - **Oikea paneeli**: Preview & log (tyhjä, JetBrains Mono)

## 4. Konvertoi simple_wall.dxf

1. **File → Open DXF…** ja valitse `tests/fixtures/simple_wall.dxf` (kopioi
   reposta etukäteen).
2. Layer table:n pitää listata `KYL-ULKOSEINA` ja Preview & log:in näyttää:
   `Loaded simple_wall.dxf: 1 entities across 1 layers`.
3. Kirjoita output-polku, esim. `C:\Temp\dxf2ifc-smoke\simple_wall.ifc`.
4. Napauta **Convert**. Status bar: `Converting…` → `Done`. Preview & log:iin
   ilmestyy `Wrote simple_wall.ifc` vihreällä.
5. Avaa output Solibri Anywhere -lukijassa. Pitäisi näkyä yksi seinä,
   Talo2000-koodi `1241`. Jos Solibri valittaa schema-virheestä, **älä
   julkaise**.

## 5. CLI-smoke PowerShellissä

```powershell
.\dxf2ifc-vX.Y.Z.exe --version
.\dxf2ifc-vX.Y.Z.exe convert tests/fixtures/simple_wall.dxf C:\Temp\cli_out.ifc
```

Molempien pitää exit-koodi 0 ja tuottaa validi IFC-tiedosto. `--version`
tulostaa `dxf2ifc <X.Y.Z>`.

## 6. Julkaise tai hylkää

- **Kaikki vihreää** → palaa GitHub-UI:hin ja napauta **Publish release**.
- **Yksikin punainen** → poista draft, kirjaa virhe issueksi, bumppaa
  bugfix-versio (esim. `v0.1.1`) ja aja prosessi uudestaan
  (`docs/packaging.md` → "Release-prosessi").
