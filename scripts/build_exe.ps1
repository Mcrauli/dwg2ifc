# Local Windows PyInstaller build for dxf2ifc.
# Usage:  $env:DXF2IFC_VERSION = "0.1.0"; .\scripts\build_exe.ps1
# Output: dist/dxf2ifc-<version>.exe + SHA256 printed to stdout.

$ErrorActionPreference = "Stop"

if (-not $env:DXF2IFC_VERSION) {
    $env:DXF2IFC_VERSION = (Select-String -Path "src/dxf2ifc/_version.py" -Pattern '__version__\s*=\s*"([^"]+)"').Matches[0].Groups[1].Value
}

Write-Host "Building dxf2ifc.exe version $($env:DXF2IFC_VERSION)..."

# Native commands do not trip $ErrorActionPreference; check $LASTEXITCODE
# explicitly so a uv/pyinstaller failure cannot silently fall through to
# the Copy-Item step and ship a stale binary.
$source = "dist/dxf2ifc.exe"
$target = "dist/dxf2ifc-$($env:DXF2IFC_VERSION).exe"

# Stamp the source with mtime BEFORE the build so we can detect whether
# PyInstaller actually rebuilt it (vs. silently using a previous output).
$preBuildMtime = if (Test-Path $source) { (Get-Item $source).LastWriteTime } else { [datetime]::MinValue }

uv sync --extra dev --extra gui
if ($LASTEXITCODE -ne 0) {
    throw "uv sync failed with exit code $LASTEXITCODE"
}

uv run pyinstaller build/dxf2ifc.spec --clean --noconfirm
if ($LASTEXITCODE -ne 0) {
    throw "pyinstaller failed with exit code $LASTEXITCODE"
}

if (-not (Test-Path $source)) {
    throw "PyInstaller did not produce $source"
}

# Defence-in-depth: even if both commands returned 0, verify the source
# was actually rewritten — protects against the edge case where the spec
# file silently emits to a different output path.
if ((Get-Item $source).LastWriteTime -le $preBuildMtime) {
    throw "PyInstaller output $source was not refreshed (still $preBuildMtime). Build did not actually run."
}

Copy-Item -Path $source -Destination $target -Force

$hash = Get-FileHash -Algorithm SHA256 -Path $target
Write-Host "Built  : $target"
Write-Host "SHA256 : $($hash.Hash)"
Set-Content -Path "$target.sha256" -Value "$($hash.Hash)  $(Split-Path -Leaf $target)"
