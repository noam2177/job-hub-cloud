$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Root
& (Join-Path $Root ".venv\Scripts\python.exe") "scripts\audit_local.py"
