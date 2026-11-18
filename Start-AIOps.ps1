[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$ServiceName,
    [Parameter(Mandatory=$true)][string]$Alert,
    [switch]$AutoRemediate,
    [string]$ApprovalToken = '',
    [int]$MaxTurns = 8,
    [string]$Model = ''
)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path $PSScriptRoot).Path
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { throw 'Virtual environment not found. Run .\scripts\Install-AIOps.ps1 first.' }
if (-not (Get-Command hermes -ErrorAction SilentlyContinue)) { throw 'Hermes CLI not found. Open a new PowerShell after installing Hermes.' }

$runRoot = Join-Path $projectRoot 'artifacts\runs'
New-Item -ItemType Directory -Force -Path $runRoot | Out-Null
$runFile = Join-Path $runRoot ("{0:yyyyMMdd-HHmmss}-{1}.jsonl" -f (Get-Date), ($ServiceName -replace '[^A-Za-z0-9_-]', '_'))

$env:AIOPS_PROJECT_ROOT = $projectRoot
$env:PYTHONPATH = $projectRoot
$env:HERMES_HOME = Join-Path $projectRoot '.hermes'
New-Item -ItemType Directory -Force -Path $env:HERMES_HOME | Out-Null
Copy-Item (Join-Path $projectRoot 'config\hermes-aiops.yaml') (Join-Path $env:HERMES_HOME 'config.yaml') -Force
$env:AIOPS_ALLOW_MUTATIONS = if ($AutoRemediate) { 'true' } else { 'false' }
$env:AIOPS_APPROVAL_TOKEN = $ApprovalToken

$mutationInstruction = if ($AutoRemediate) { 'If remediation is justified, execute exactly one bounded remediation and verify health afterward.' } else { 'Do not execute mutations; provide the recommended remediation as a dry-run only.' }
$query = @"
You are an SRE incident-response agent. Investigate this alert using the aiops MCP tools.
Service: $ServiceName
Alert: $Alert
Workflow: obtain incident context, search logs, check health, determine the most likely cause, then $mutationInstruction
Rules: use only the aiops MCP tools; do not invent observations; report evidence, decision, action result, and residual risk in concise Japanese.
"@

$args = @('chat', '--oneshot', '--quiet', '-q', $query, '--format', 'stream-json', '--max-turns', $MaxTurns.ToString(), '--source', 'tool')
if ($Model) { $args += @('--model', $Model) }
Write-Host "Starting Hermes Agentic AIOps run: $runFile"
& hermes @args 2>&1 | Tee-Object -FilePath $runFile
if ($LASTEXITCODE -ne 0) { throw "Hermes exited with code $LASTEXITCODE. See $runFile" }
Write-Host "Audit log: $runFile"
