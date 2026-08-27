# Astra Ollama setup helper for Windows PowerShell.
# This script does not install Ollama itself. Install Ollama from the official
# Ollama website first, then run this script from the Astra project folder.

$ErrorActionPreference = 'Stop'

Write-Host '========================================' -ForegroundColor Cyan
Write-Host '       ASTRA - OLLAMA SETUP' -ForegroundColor Cyan
Write-Host '========================================' -ForegroundColor Cyan
Write-Host ''

$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollama) {
    Write-Host 'Ollama was not found on PATH.' -ForegroundColor Yellow
    Write-Host 'Install Ollama for Windows, restart PowerShell, then run this script again.'
    exit 1
}

$model = if ($env:ASTRA_OLLAMA_MODEL) { $env:ASTRA_OLLAMA_MODEL } else { 'qwen2.5:3b-instruct' }

Write-Host "Checking Ollama model: $model"
& ollama list
Write-Host ''
Write-Host "Pulling model if necessary: $model" -ForegroundColor Cyan
& ollama pull $model

if ($LASTEXITCODE -ne 0) {
    throw "Ollama could not pull $model."
}

$envFile = Join-Path $PSScriptRoot 'config\.env'
if (-not (Test-Path $envFile)) {
    New-Item -ItemType File -Path $envFile -Force | Out-Null
}

$lines = @(Get-Content $envFile)
function Set-EnvValue([string]$key, [string]$value) {
    $script:lines = @($script:lines | Where-Object { $_ -notmatch "^\s*#?\s*$([regex]::Escape($key))\s*=" })
    $script:lines += "$key=$value"
}

Set-EnvValue 'AI_PROVIDER' 'ollama'
Set-EnvValue 'AI_MODEL' $model
Set-EnvValue 'ASTRA_OLLAMA_BASE' 'http://127.0.0.1:11434'
Set-EnvValue 'ASTRA_OLLAMA_TIMEOUT' '30'
Set-Content -Path $envFile -Value $lines -Encoding UTF8

Write-Host ''
Write-Host 'Ollama route configured successfully.' -ForegroundColor Green
Write-Host "Provider: ollama"
Write-Host "Model:    $model"
Write-Host 'Endpoint: http://127.0.0.1:11434'
Write-Host ''
Write-Host 'Test the connection with:' -ForegroundColor Cyan
Write-Host '    python tools\ollama_status.py'
Write-Host ''
Write-Host 'Then start Astra with:' -ForegroundColor Cyan
Write-Host '    python -m core.astra'
