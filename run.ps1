Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Error "Virtual environment not found at .venv. Create it first: python -m venv .venv"
}

& $venvPython -m streamlit run (Join-Path $PSScriptRoot "streamlit_app.py")
