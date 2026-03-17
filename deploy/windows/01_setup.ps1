param(
  [string]$ProjectDir = "C:\apps\bom-configurator"
)

$ErrorActionPreference = "Stop"

Write-Host "== BOM Configurator - Windows setup ==" -ForegroundColor Cyan
Write-Host "ProjectDir: $ProjectDir"

Set-Location $ProjectDir

if (!(Test-Path ".\.venv")) {
  py -m venv .venv
}

& .\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt

if (!(Test-Path ".\.env")) {
  Copy-Item ".\.env.example" ".\.env"
  Write-Host "Created .env from .env.example. Please edit .env now." -ForegroundColor Yellow
}

Write-Host "Setup done." -ForegroundColor Green

