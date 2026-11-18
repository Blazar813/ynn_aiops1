[CmdletBinding()]
param([switch]$SkipHermes)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

if (-not $SkipHermes -and -not (Get-Command hermes -ErrorAction SilentlyContinue)) {
    Write-Host 'Installing Hermes Agent using the official Windows installer...'
    iex (irm https://hermes-agent.nousresearch.com/install.ps1)
    Write-Host 'Open a new PowerShell window before running Start-AIOps.ps1.'
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw 'Python 3.11+ is required.' }
python -m venv (Join-Path $projectRoot '.venv')
& (Join-Path $projectRoot '.venv\Scripts\python.exe') -m pip install --upgrade pip
& (Join-Path $projectRoot '.venv\Scripts\python.exe') -m pip install -r (Join-Path $projectRoot 'requirements.txt')
Write-Host "Ready. Run: .\Start-AIOps.ps1 -ServiceName payment-service -Alert 'HTTP 504 Gateway Timeout'"
