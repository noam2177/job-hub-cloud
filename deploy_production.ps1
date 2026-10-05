# One-click cloud deploy wrapper for infra/*.sh (bash). Default is dry-run until operator confirms billing.
param(
    [string]$Project = "noam-job-hub-123",
    [string]$Region = "us-central1",
    [string]$Zone = "us-central1-a",
    [switch]$ConfirmDeploy
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Infra = Join-Path $Root "infra"

function Resolve-Bash {
    $candidates = @(
        "C:\Program Files\Git\bin\bash.exe",
        "C:\Program Files (x86)\Git\bin\bash.exe",
        (Get-Command bash -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source)
    ) | Where-Object { $_ -and (Test-Path $_) -and ($_ -notlike "*\\Windows\\System32\\bash.exe") }
    if (-not $candidates) {
        throw "Git Bash (bash.exe) not found. Install Git for Windows or run infra/*.sh from WSL."
    }
    return $candidates[0]
}

function Invoke-InfraScript {
    param(
        [string]$Name,
        [string[]]$ExtraArgs = @()
    )
    $scriptPath = Join-Path $Infra $Name
    if (-not (Test-Path $scriptPath)) {
        throw "Missing infra script: $scriptPath"
    }
    Write-Host ""
    Write-Host "=== infra/$Name ===" -ForegroundColor Cyan
    $env:PROJECT = $Project
    $env:REGION = $Region
    $env:ZONE = $Zone
    $env:DRY_RUN = $DryRun
    & $Bash $scriptPath @ExtraArgs
    if ($LASTEXITCODE -ne 0) {
        throw "infra/$Name failed with exit code $LASTEXITCODE"
    }
}

if ($ConfirmDeploy) {
    $answer = "y"
} else {
    $prompt = "Approve full cloud deploy (890 NIS budget may apply)? (y/n)"
    $answer = Read-Host $prompt
}
if ($answer -match '^[Yy]$') {
    $DryRun = "0"
    Write-Host "DRY_RUN=0 live deploy (GCP charges possible)." -ForegroundColor Yellow
} else {
    Write-Host "Cancelled. No cloud changes." -ForegroundColor Green
    exit 0
}

$Bash = Resolve-Bash
$gcloudBin = Join-Path $env:LOCALAPPDATA "Google\Cloud SDK\google-cloud-sdk\bin"
if (Test-Path $gcloudBin) {
    $env:PATH = "$gcloudBin;$env:PATH"
}
Write-Host "Project=$Project Region=$Region Zone=$Zone Bash=$Bash"

$ledgerDefault = Join-Path $env:CAREER_DRIVE_BUS_DIR "ledger\jobs.json"
if (-not $env:LEDGER_PATH -and (Test-Path $ledgerDefault)) {
    $env:LEDGER_PATH = $ledgerDefault
}

Invoke-InfraScript "00_project.sh"
Invoke-InfraScript "01_apis.sh" -ExtraArgs @("g0")
Invoke-InfraScript "01_apis.sh" -ExtraArgs @("p1")
Invoke-InfraScript "01_apis.sh" -ExtraArgs @("p5")
Invoke-InfraScript "10_bq.sh"
Invoke-InfraScript "20_vm.sh"
Invoke-InfraScript "21_harden.sh"
Invoke-InfraScript "30_pubsub.sh"
Invoke-InfraScript "40_cloud_run_sync.sh"
Invoke-InfraScript "41_scheduler_sync.sh"
if ($env:LEDGER_PATH) {
    Invoke-InfraScript "42_gcs_ledger_backup.sh"
} else {
    Write-Host "Skipping 42_gcs_ledger_backup.sh - set LEDGER_PATH or CAREER_DRIVE_BUS_DIR/ledger/jobs.json" -ForegroundColor DarkYellow
}

Write-Host ""
Write-Host "Deploy sequence finished. See docs/gcp/HANDOVER_PRODUCTION.md" -ForegroundColor Green
