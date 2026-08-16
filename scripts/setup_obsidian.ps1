$ErrorActionPreference = 'Stop'

$vault = if ($env:CYRAX_OBSIDIAN_VAULT) {
    $env:CYRAX_OBSIDIAN_VAULT
} else {
    'F:\AI\CYRAX-Vault'
}

Write-Host "=== CYRAX Obsidian memory ===" -ForegroundColor Cyan
Write-Host "Vault: $vault"

$folders = @(
    '00_CYRAX',
    '01_Memory',
    '02_Projects',
    '03_Knowledge',
    '04_Logs',
    '99_Inbox'
)

New-Item -ItemType Directory -Force -Path $vault | Out-Null
foreach ($folder in $folders) {
    New-Item -ItemType Directory -Force -Path (Join-Path $vault $folder) | Out-Null
}

$identity = Join-Path $vault '00_CYRAX\Identity.md'
if (-not (Test-Path $identity)) {
    @'
---
type: cyrax-identity
source: CYRAX
---

# CYRAX Identity

CYRAX is a local-first AI agent.

- Model: Qwen3:8b
- Runtime: Ollama + Open Interpreter
- Long-term memory: this Obsidian vault
- Project repository: pong0101/CYRAX

## Memory rule

Obsidian is persistent memory, not an unquestionable source of truth. Current evidence takes priority when conflicts exist.
'@ | Set-Content -Path $identity -Encoding UTF8
}

$system = Join-Path $vault '00_CYRAX\System.md'
if (-not (Test-Path $system)) {
    @'
---
type: cyrax-system
source: CYRAX
---

# CYRAX System

## Runtime

- Ollama: http://127.0.0.1:11434
- Model: qwen3:8b
- Open Interpreter: 0.4.3

## Memory

CYRAX searches this vault before answering questions that may depend on long-term context.
'@ | Set-Content -Path $system -Encoding UTF8
}

$readme = Join-Path $vault 'README.md'
if (-not (Test-Path $readme)) {
    @'
# CYRAX Second Brain

This is the persistent Obsidian memory vault used by CYRAX.

- `00_CYRAX` — identity and system notes
- `01_Memory` — durable memories
- `02_Projects` — project knowledge
- `03_Knowledge` — general knowledge
- `04_Logs` — CYRAX interaction logs
- `99_Inbox` — temporary notes and incoming information

Open this folder as an Obsidian vault.
'@ | Set-Content -Path $readme -Encoding UTF8
}

Write-Host "Obsidian vault ready: $vault" -ForegroundColor Green
