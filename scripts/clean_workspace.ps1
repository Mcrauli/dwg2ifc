# Remove transient build/smoke artifacts. Safe to run any time.
# YTV reference docs in tmp/ are preserved.
param([switch]$Deep)

Set-Location $PSScriptRoot/..

Write-Host "Cleaning tmp/ smoke artifacts..." -ForegroundColor Cyan
Remove-Item -Recurse -Force tmp/probe_*, tmp/smoke_*.ifc, tmp/verify_*.py -ErrorAction SilentlyContinue

if ($Deep) {
    Write-Host "Deep clean: build/, dist/, .pytest_cache, __pycache__..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force build/dwg2ifc, dist/dwg2ifc.exe -ErrorAction SilentlyContinue
    Get-ChildItem -Path . -Include __pycache__,.pytest_cache,.ruff_cache -Recurse -Force -ErrorAction SilentlyContinue |
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
}

$tmpSize = (Get-ChildItem tmp/ -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB
Write-Host ("tmp/ now: {0:N1} MB" -f $tmpSize) -ForegroundColor Green
