# Local Windows PyInstaller build for dxf2ifc.
# Usage:  $env:DXF2IFC_VERSION = "0.1.0"; .\scripts\build_exe.ps1
# Output: dist/dxf2ifc-<version>.exe + SHA256 printed to stdout.

$ErrorActionPreference = "Stop"

if (-not $env:DXF2IFC_VERSION) {
    $env:DXF2IFC_VERSION = (Select-String -Path "src/dxf2ifc/_version.py" -Pattern '__version__\s*=\s*"([^"]+)"').Matches[0].Groups[1].Value
}

Write-Host "Building dxf2ifc.exe version $($env:DXF2IFC_VERSION)..."

uv sync --extra dev --extra gui
uv run pyinstaller build/dxf2ifc.spec --clean --noconfirm

$source = "dist/dxf2ifc.exe"
$target = "dist/dxf2ifc-$($env:DXF2IFC_VERSION).exe"

if (-not (Test-Path $source)) {
    throw "PyInstaller did not produce $source"
}

Copy-Item -Path $source -Destination $target -Force

$hash = Get-FileHash -Algorithm SHA256 -Path $target
Write-Host "Built  : $target"
Write-Host "SHA256 : $($hash.Hash)"
Set-Content -Path "$target.sha256" -Value "$($hash.Hash)  $(Split-Path -Leaf $target)"
