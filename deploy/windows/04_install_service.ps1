param(
  [string]$ProjectDir = "C:\apps\bom-configurator",
  [string]$ServiceName = "BOMConfigurator",
  [string]$Bind = "127.0.0.1:8001",
  [string]$NssmPath = "C:\tools\nssm\nssm.exe"
)

$ErrorActionPreference = "Stop"

if (!(Test-Path $NssmPath)) {
  throw "nssm.exe not found at $NssmPath. Download NSSM and set -NssmPath."
}

Set-Location $ProjectDir

$exe = Join-Path $ProjectDir ".venv\Scripts\waitress-serve.exe"
if (!(Test-Path $exe)) {
  throw "waitress-serve.exe not found. Run deploy\\windows\\01_setup.ps1 first."
}

& $NssmPath install $ServiceName $exe "--listen=$Bind" "bom_configurator.wsgi:application"
& $NssmPath set $ServiceName AppDirectory $ProjectDir
& $NssmPath set $ServiceName Start SERVICE_AUTO_START
& $NssmPath set $ServiceName AppStdout (Join-Path $ProjectDir "logs\service.out.log")
& $NssmPath set $ServiceName AppStderr (Join-Path $ProjectDir "logs\service.err.log")
& $NssmPath set $ServiceName AppRotateFiles 1
& $NssmPath set $ServiceName AppRotateOnline 1
& $NssmPath set $ServiceName AppRotateSeconds 86400

if (!(Test-Path (Join-Path $ProjectDir "logs"))) {
  New-Item -ItemType Directory -Path (Join-Path $ProjectDir "logs") | Out-Null
}

Start-Service $ServiceName
Write-Host "Service installed and started: $ServiceName" -ForegroundColor Green

