# Start watcher in background (logs to state/watcher.log). Set CAREER_DRIVE_BUS_DIR first.
param([double]$Interval = 5)
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Log = Join-Path $Root "state\watcher.log"
$LogErr = Join-Path $Root "state\watcher.err.log"
$Py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not $env:CAREER_DRIVE_BUS_DIR) {
  Write-Error "Set CAREER_DRIVE_BUS_DIR to your Drive-synced career bus folder."
}
$env:JOBHUB_STATE_DIR = if ($env:JOBHUB_STATE_DIR) { $env:JOBHUB_STATE_DIR } else { (Join-Path $Root "state") }
$env:JOBHUB_WATCHER = "1"
$env:JOBHUB_DRY_RUN = if ($env:JOBHUB_DRY_RUN) { $env:JOBHUB_DRY_RUN } else { "1" }
$pyArgs = @("-m", "local.watcher", "--interval", "$Interval")
Start-Process -FilePath $Py -ArgumentList $pyArgs -WorkingDirectory $Root -RedirectStandardOutput $Log -RedirectStandardError $LogErr -WindowStyle Hidden
Write-Host "Watcher started. Log: $Log (stderr: $LogErr)"
