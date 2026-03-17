param(
  [string]$ProjectDir = "C:\apps\bom-configurator"
)

$ErrorActionPreference = "Stop"

Write-Host "== BOM Configurator - DB init ==" -ForegroundColor Cyan
Set-Location $ProjectDir

& .\.venv\Scripts\Activate.ps1

python manage.py migrate
python manage.py collectstatic --noinput
python manage.py import_csv_data

Write-Host "DB init done." -ForegroundColor Green

