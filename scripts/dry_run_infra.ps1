# Prints infra deploy commands (DRY_RUN=1). No cloud changes.
$Root = Split-Path $PSScriptRoot -Parent
$bash = "bash"
$env:PROJECT = "noam-job-hub-123"
$env:DRY_RUN = "1"
foreach ($script in @("40_cloud_run_sync.sh", "41_scheduler_sync.sh", "42_gcs_ledger_backup.sh", "20_vm.sh", "30_pubsub.sh")) {
  Write-Host "`n=== infra/$script ===" -ForegroundColor Cyan
  & $bash (Join-Path $Root "infra\$script") 2>&1
}
