$ErrorActionPreference = 'Stop'

Write-Host '=== CYRAX setup ===' -ForegroundColor Cyan

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw 'Python launcher (py) was not found. Install Python 3.12 first.'
}

$root = Split-Path -Parent $PSScriptRoot
$venv = Join-Path $root '.venv'
$python = Join-Path $venv 'Scripts\python.exe'

if (-not (Test-Path $venv)) {
    py -3.12 -m venv $venv
}

& $python -m pip install --upgrade pip

# Open Interpreter 0.4.3 still imports pkg_resources, so keep setuptools < 81.
& $python -m pip install 'setuptools<81'

# Open Interpreter 0.4.3 declares tiktoken<0.8, while modern LiteLLM
# requires tiktoken>=0.8. Installing them in one pip resolution is
# impossible, so install the runtime pieces in a controlled order.
& $python -m pip install 'litellm==1.97.0' 'tiktoken==0.8.0' 'ollama==0.6.2' 'PyYAML==6.0.3'
& $python -m pip install 'open-interpreter==0.4.3' --no-deps

# Remaining Open Interpreter dependencies.
& $python -m pip install `
  'anthropic==0.37.1' `
  'astor==0.8.1' `
  'git-python==1.0.3' `
  'google-generativeai==0.7.2' `
  'html2image==2.0.7' `
  'html2text==2024.2.26' `
  'inquirer==3.4.1' `
  'ipykernel==6.31.0' `
  'jupyter-client==8.9.1' `
  'matplotlib==3.11.1' `
  'nltk==3.10.3' `
  'platformdirs==4.11.3' `
  'psutil==5.9.8' `
  'pydantic==2.13.4' `
  'pyperclip==1.11.0' `
  'pyreadline3==3.5.6' `
  'rich==13.9.4' `
  'selenium==4.47.0' `
  'send2trash==1.8.3' `
  'shortuuid==1.0.13' `
  'six==1.17.0' `
  'starlette==0.37.2' `
  'tokentrim==0.1.13' `
  'toml==0.10.2' `
  'typer==0.12.5' `
  'webdriver-manager==4.1.2' `
  'wget==3.2' `
  'yaspin==3.4.0'

# setup_windows.ps1 is intentionally strict: reaching this point means every
# command above completed successfully.
& $python -c "import interpreter, ollama, tiktoken; print('CYRAX runtime imports: OK'); print('tiktoken:', tiktoken.__version__)"

# Create the default Obsidian second-brain vault outside the Git repository.
& $PSScriptRoot\setup_obsidian.ps1

Write-Host ''
Write-Host 'CYRAX environment is ready.' -ForegroundColor Green
Write-Host 'Obsidian second brain is ready.' -ForegroundColor Green
Write-Host 'Next: make sure Ollama is running and qwen3:8b is available.'
Write-Host 'Then run:'
Write-Host "  & '$python' '$root\agent\cyrax.py'"
