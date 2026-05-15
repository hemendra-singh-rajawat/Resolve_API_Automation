# Always open the Allure report over HTTP — never file://.
#
# Why this script exists:
#   Double-clicking reports/allure-report/index.html opens it via file://,
#   which makes the browser block every fetch() the SPA performs to load its
#   data files. Result: indefinite "Loading..." widgets or 404/500 errors.
#
# What this script does:
#   1. Picks the Allure binary (override via $env:ALLURE_BIN if needed).
#   2. Starts `allure open` (or `serve` if no report has been generated yet).
#   3. Prints the URL — paste into your browser if it didn't open automatically.
#
# Stop the server with Ctrl+C in the window this opens.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$AllureBat = $env:ALLURE_BIN
if (-not $AllureBat -or -not (Test-Path $AllureBat)) {
    $Candidates = @(
        "..\..\..\node_modules\allure-commandline\dist\bin\allure.bat"  # Desktop/node_modules
        "..\..\node_modules\allure-commandline\dist\bin\allure.bat"
        "node_modules\allure-commandline\dist\bin\allure.bat"
    )
    foreach ($c in $Candidates) {
        $full = Resolve-Path -ErrorAction SilentlyContinue $c
        if ($full) { $AllureBat = $full.Path; break }
    }
    if (-not $AllureBat) {
        $cmd = Get-Command allure -ErrorAction SilentlyContinue
        if ($cmd) { $AllureBat = $cmd.Source }
    }
}

if (-not $AllureBat) {
    Write-Error "Allure binary not found. Run: npm install --no-save allure-commandline@2.27.0"
    exit 1
}

Write-Host "Using Allure: $AllureBat" -ForegroundColor DarkGray

if (Test-Path "reports\allure-report\index.html") {
    Write-Host "Serving generated report (Ctrl+C to stop) ..." -ForegroundColor Cyan
    & $AllureBat open "reports\allure-report"
} elseif (Test-Path "reports\allure-results") {
    Write-Host "No generated report — running 'allure serve' on raw results ..." -ForegroundColor Cyan
    & $AllureBat serve "reports\allure-results"
} else {
    Write-Error "Nothing to open. Run pytest first to generate reports/allure-results."
    exit 1
}
