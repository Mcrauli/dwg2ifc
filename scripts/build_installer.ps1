# Build dwg2ifc Inno Setup installer.
#
# Pipeline:
#   1. Run scripts/build_exe.ps1 → dist/dwg2ifc.exe + dist/dwg2ifc-<v>.exe
#   2. Ensure dist/LICENSES.md exists (generate fallback if missing).
#   3. Locate ISCC.exe (Inno Setup 6 compiler).
#   4. Compile build/installer.iss → dist/dwg2ifc-Setup-<v>.exe
#   5. Print + write SHA256 sidecar.
#
# Usage:  .\scripts\build_installer.ps1
# Output: dist/dwg2ifc-Setup-<version>.exe
#         dist/dwg2ifc-Setup-<version>.exe.sha256

$ErrorActionPreference = "Stop"

# 1. PyInstaller build (delegates to the existing exe-only script)
& "$PSScriptRoot\build_exe.ps1"

$version = $env:DXF2IFC_VERSION
if (-not $version) { throw "DXF2IFC_VERSION not set after build_exe.ps1" }

$root = (Resolve-Path "$PSScriptRoot\..").Path
$dist = Join-Path $root "dist"
$sourceExe = Join-Path $dist "dwg2ifc.exe"
$licensesFile = Join-Path $dist "LICENSES.md"

if (-not (Test-Path $sourceExe)) {
    throw "PyInstaller did not produce $sourceExe"
}

# 2. LICENSES.md fallback — release.yml writes a richer version, but local
#    builds and build.yml CI need a placeholder so [Files] does not skip it.
if (-not (Test-Path $licensesFile)) {
    @(
        "# dwg2ifc - third-party licenses",
        "",
        "Full license text and source links:",
        "https://github.com/Mcrauli/dwg2ifc"
    ) -join "`n" | Set-Content -Encoding UTF8 -Path $licensesFile
}

# 3. Locate ISCC.exe. windows-latest GitHub runners ship Inno Setup 6
#    pre-installed; local Windows installs land in Program Files (x86).
$iscc = $env:ISCC
if (-not $iscc -or -not (Test-Path $iscc)) {
    $candidates = @(
        "${Env:ProgramFiles}\Inno Setup 6\ISCC.exe",
        "${Env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    )
    $iscc = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $iscc) {
    throw "ISCC.exe not found. Install Inno Setup 6 (https://jrsoftware.org/isinfo.php) or set `$env:ISCC."
}

# 4. Optional brand icon (assets/dwg2ifc.ico arrives in a follow-up commit).
$iconFile = Join-Path $root "assets\dwg2ifc.ico"
$hasIcon = Test-Path $iconFile

# Inno Setup's VersionInfoVersion accepts only pure-numeric X.Y.Z.W —
# strip the PEP 440 pre-release suffix (e.g. "0.1.6a1" → "0.1.6") and
# pad with zeroes to four components so the .iss can plug it directly
# into the [Setup] VersionInfoVersion line.
$numericVersion = $version -replace '[A-Za-z].*$', ''
$parts = @($numericVersion -split '\.' | Where-Object { $_ -ne '' })
while ($parts.Count -lt 4) { $parts += '0' }
$numericVersion = ($parts[0..3] -join '.')

$issPath = Join-Path $root "build\installer.iss"
$isccArgs = @(
    "/Qp",
    "/DAppVersion=$version",
    "/DAppNumericVersion=$numericVersion",
    "/DSourceExe=$sourceExe",
    "/DLicensesFile=$licensesFile",
    "/DOutputDir=$dist"
)
if ($hasIcon) { $isccArgs += "/DIconFile=$iconFile" }
$isccArgs += $issPath

Write-Host "Compiling installer with ISCC: $iscc"
& $iscc @isccArgs
if ($LASTEXITCODE -ne 0) { throw "ISCC failed (exit $LASTEXITCODE)" }

# 5. Hash the installer.
$installer = Join-Path $dist "dwg2ifc-Setup-$version.exe"
if (-not (Test-Path $installer)) { throw "Installer missing after ISCC: $installer" }

$hash = Get-FileHash -Algorithm SHA256 -Path $installer
Write-Host "Built  : $installer"
Write-Host "SHA256 : $($hash.Hash)"
Set-Content -Path "$installer.sha256" -Value "$($hash.Hash)  $(Split-Path -Leaf $installer)"
