Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "  INICIALIZANDO JARVIS 3.0 (FRONTEND & HUD ENGINE) " -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""

$env:PATH = "C:\Program Files\nodejs;" + $env:PATH

Write-Host "[1/2] Abrindo a interface web no navegador..." -ForegroundColor Yellow
Start-Process "http://localhost:5173"

Write-Host "[2/2] Iniciando o servidor Vite Frontend..." -ForegroundColor Yellow
Set-Location "$PSScriptRoot\frontend"
npm run dev
