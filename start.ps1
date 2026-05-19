# start.ps1 - HER Launcher
Set-Location $PSScriptRoot

Write-Host ""
Write-Host "  ==============================" -ForegroundColor Magenta
Write-Host "     HER v1.0" -ForegroundColor Magenta
Write-Host "     Human Emotion Resonance" -ForegroundColor Magenta
Write-Host "  ==============================" -ForegroundColor Magenta
Write-Host ""

$exePath = Join-Path $PSScriptRoot "AI_Companion.exe"

if (Test-Path $exePath) {
    Write-Host "  Starting..." -ForegroundColor Green
    & $exePath
} else {
    Write-Host "  Starting (dev mode)..." -ForegroundColor Green
    python "$PSScriptRoot\assistant.py"
    pause
}
