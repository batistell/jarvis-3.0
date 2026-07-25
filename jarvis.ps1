$env:PYTHONIOENCODING = "utf-8"
$env:PATH = "C:\Program Files\nodejs;" + $env:PATH

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "  INICIALIZANDO JARVIS 3.0 (BACKEND & FRONTEND)    " -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/3] Iniciando o servidor Vite Frontend (Silencioso em segundo plano)..." -ForegroundColor Yellow
Start-Process -FilePath "cmd.exe" -ArgumentList "/c cd /d `"$PSScriptRoot\frontend`" && npm run dev" -WindowStyle Hidden

Write-Host "[2/3] Abrindo a interface web no navegador..." -ForegroundColor Yellow
Start-Process "http://localhost:5173"

Write-Host "[3/3] Executando o backend FastAPI em primeiro plano (Console de Logs em Tempo Real)..." -ForegroundColor Yellow
Write-Host ""

Set-Location "$PSScriptRoot"
& "$PSScriptRoot\venv\Scripts\python.exe" -m uvicorn backend.main:app --port 8000 --reload
