param(
    [string]$Env = "dev",
    [string]$Marker = "smoke",
    [int]$Parallel = 4,
    [switch]$OpenReport
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path .venv)) {
    Write-Host "Creating virtualenv .venv ..." -ForegroundColor Cyan
    python -m venv .venv
}

. .\.venv\Scripts\Activate.ps1

Write-Host "Installing/refreshing dependencies ..." -ForegroundColor Cyan
pip install --upgrade pip | Out-Null
pip install -r requirements.txt | Out-Null

Write-Host "Running suite [$Marker] against env=$Env with $Parallel workers ..." -ForegroundColor Cyan
$env:ENV = $Env
pytest -n $Parallel -m $Marker --env $Env

# --- Allure report -------------------------------------------------------------
#
# IMPORTANT: use allure-commandline >=2.27 < 2.40. Allure 2.40.0 ships with
# broken behaviors-plugin / packages-plugin loading on Windows + Java 17/21 —
# the report generates without errors but the Behaviors and Packages sidebar
# tabs come up empty (data/behaviors.json + data/packages.json are not written).
# 2.27.0 is the most recent confirmed-working pin.
#
# We resolve the Allure binary in this order:
#   1. $env:ALLURE_BIN (explicit override)
#   2. <repo-parent>/../node_modules/.bin/allure.cmd or .bat (npm install)
#   3. `allure` on PATH (any system install)

$AllureBat = $null
if ($env:ALLURE_BIN -and (Test-Path $env:ALLURE_BIN)) {
    $AllureBat = $env:ALLURE_BIN
} else {
    $Candidates = @(
        Join-Path $Root "..\..\..\node_modules\allure-commandline\dist\bin\allure.bat"  # Desktop/node_modules
        Join-Path $Root "..\..\node_modules\allure-commandline\dist\bin\allure.bat"
        Join-Path $Root "node_modules\allure-commandline\dist\bin\allure.bat"
    )
    foreach ($c in $Candidates) {
        $full = (Resolve-Path -ErrorAction SilentlyContinue $c)
        if ($full) { $AllureBat = $full.Path; break }
    }
    if (-not $AllureBat) {
        $cmd = Get-Command allure -ErrorAction SilentlyContinue
        if ($cmd) { $AllureBat = $cmd.Source }
    }
}

Write-Host "Generating Allure HTML report ..." -ForegroundColor Cyan
if ($AllureBat) {
    Write-Host "  using: $AllureBat" -ForegroundColor DarkGray
    & $AllureBat generate "reports/allure-results" -o "reports/allure-report" --clean
    if ($OpenReport) {
        Write-Host "Opening report server (Ctrl+C to stop) ..." -ForegroundColor Cyan
        & $AllureBat open "reports/allure-report"
    }
} else {
    Write-Warning "Allure CLI not found. Install via 'npm install -g allure-commandline@2.27.0' or unzip from https://github.com/allure-framework/allure2/releases. Raw results are at reports/allure-results."
}
