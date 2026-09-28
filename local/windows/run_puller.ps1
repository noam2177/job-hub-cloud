$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "venv missing: $Python" }
if (-not $env:JOBHUB_DRY_RUN) { $env:JOBHUB_DRY_RUN = "1" }
& $Python -m local.puller @args
