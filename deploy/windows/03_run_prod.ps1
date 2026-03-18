param(
  [string]$ProjectDir = "C:\apps\bom-configurator",
  [string]$Bind = "127.0.0.1:8001"
)

$ErrorActionPreference = "Stop"

Write-Host "== BOM Configurator - Run (prod) ==" -ForegroundColor Cyan
Set-Location $ProjectDir

& .\.venv\Scripts\Activate.ps1

# Waitress is Windows-friendly and runs the Django WSGI app
waitress-serve --listen=$Bind bom_configurator.wsgi:application

