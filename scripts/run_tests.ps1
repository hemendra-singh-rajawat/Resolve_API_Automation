param(
    [string]$Env = "qa",
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

Write-Host "Generating Allure HTML report ..." -ForegroundColor Cyan
if (Get-Command allure -ErrorAction SilentlyContinue) {
    allure generate reports/allure-results -o reports/allure-report --clean
    if ($OpenReport) { allure open reports/allure-report }
} else {
    Write-Warning "Allure CLI not found. Install from https://allurereport.org/docs/install/. Raw results at reports/allure-results."
}
