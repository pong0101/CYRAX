$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'

if (-not (Test-Path $python)) {
    throw 'CYRAX virtual environment not found. Run scripts/setup_windows.ps1 first.'
}

& $python (Join-Path $root 'agent\cyrax.py')
