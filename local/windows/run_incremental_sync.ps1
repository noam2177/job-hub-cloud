# Task Scheduler friendly: incremental sync dry-run or apply.
param(
  [switch]$Apply,
  [switch]$CheckBq
)
$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location $Root
$Py = Join-Path $Root ".venv\Scripts\python.exe"
$Args = @("scripts\incremental_sync_to_bq.py")
if ($Apply) { $Args += "--apply" }
if ($CheckBq) { $Args += "--check-bq" }
& $Py @Args
