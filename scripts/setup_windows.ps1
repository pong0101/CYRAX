$ErrorActionPreference = 'Stop'

Write-Host '=== CYRAX setup ===' -ForegroundColor Cyan

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw 'Python launcher (py) was not found. Install Python 3.12 first.'
}

$root = Split-Path -Parent $PSScriptRoot
$venv = Join-Path $root '.venv'

if (-not (Test-Path $venv)) {
    py -3.12 -m venv $venv
}

& (Join-Path $venv 'Scripts\python.exe') -m pip install --upgrade pip
& (Join-Path $venv 'Scripts\python.exe') -m pip install -r (Join-Path $root 'requirements.txt')

Write-Host ''
Write-Host 'CYRAX environment is ready.' -ForegroundColor Green
Write-Host 'Next: make sure Ollama is running and qwen3:8b is available.'
Write-Host 'Then run:'
Write-Host "  & '$venv\Scripts\python.exe' '$root\agent\cyrax.py'"
