param([switch]$SkipPull)
$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $project
$ollama = Join-Path $project 'work\local-model\runtime\ollama.exe'
if (-not (Test-Path -LiteralPath $ollama)) {
    throw 'Local Ollama runtime is missing. Download the official Windows package first; see README.md.'
}
$env:OLLAMA_HOST = '127.0.0.1:11434'
$env:OLLAMA_NO_CLOUD = '1'
$env:OLLAMA_MODELS = Join-Path $project 'work\local-model\models'
New-Item -ItemType Directory -Force -Path $env:OLLAMA_MODELS | Out-Null
$ready = $false
try { $null = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 2; $ready = $true } catch { }
if (-not $ready) {
    Start-Process -FilePath $ollama -ArgumentList 'serve' -WorkingDirectory $project -WindowStyle Hidden
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        try { $null = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 2; $ready = $true; break } catch { }
    }
}
if (-not $ready) { throw 'The local Ollama service did not start.' }
$tags = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 5
if (-not ($tags.models | Where-Object { $_.name -eq 'qwen3:4b' })) {
    if ($SkipPull) { throw 'qwen3:4b is not installed. Run this script without -SkipPull.' }
    & $ollama pull qwen3:4b
    if ($LASTEXITCODE -ne 0) { throw 'Model download failed.' }
}
$existingMargin = $null
try { $existingMargin = Invoke-RestMethod -Uri 'http://127.0.0.1:8765/api/health' -TimeoutSec 3 } catch { }
if ($existingMargin.app -eq 'Margin') {
    Write-Host 'Margin is already running at http://127.0.0.1:8765/'
    return
}
$bundledPython = 'C:\Users\Aashr\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$python = if (Test-Path -LiteralPath $bundledPython) { $bundledPython } else { (Get-Command python -ErrorAction Stop).Source }
Write-Host 'Margin is available at http://127.0.0.1:8765/'
& $python -u -m app.server
