$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (Test-Path -LiteralPath '..\.venv\Scripts\python.exe') {
    & '..\.venv\Scripts\python.exe' -m coursework.app
} elseif (Test-Path -LiteralPath '.venv\Scripts\python.exe') {
    & '.venv\Scripts\python.exe' -m coursework.app
} else {
    & python -m coursework.app
}
