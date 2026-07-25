$env:PYTHONIOENCODING = "utf-8"
$env:PATH = "C:\Program Files\nodejs;" + $env:PATH

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "  INICIALIZANDO JARVIS 3.0 (BACKEND & FRONTEND)    " -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Inicia o Frontend em segundo plano e aguarda 600ms para a porta 5173 estar pronta
Write-Host "⚡ Iniciando Frontend Vite & Navegador (http://localhost:5173)..." -ForegroundColor Yellow
Start-Process "C:\Program Files\nodejs\npm.cmd" -ArgumentList "run", "dev" -WorkingDirectory "$PSScriptRoot\frontend" -WindowStyle Hidden
Start-Sleep -Milliseconds 600
Start-Process "http://localhost:5173"


# 2. Executa o Backend FastAPI em primeiro plano
Write-Host "🚀 Executando Backend FastAPI (Console em Tempo Real)..." -ForegroundColor Green
Write-Host ""

Set-Location "$PSScriptRoot"
& "$PSScriptRoot\venv\Scripts\python.exe" -m uvicorn backend.main:app --port 8000

