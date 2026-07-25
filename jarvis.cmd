@echo off
title JARVIS 3.0 Engine & Backend Logs
echo ===================================================
echo   INICIALIZANDO JARVIS 3.0 (BACKEND & FRONTEND)
echo ===================================================
echo.

set PYTHONIOENCODING=utf-8
set PATH=C:\Program Files\nodejs;%PATH%

echo ⚡ Iniciando Frontend Vite e abrindo Navegador (http://localhost:5173)...
powershell -Command "Start-Process 'C:\Program Files\nodejs\npm.cmd' -ArgumentList 'run', 'dev' -WorkingDirectory '%~dp0frontend' -WindowStyle Hidden; Start-Sleep -Milliseconds 600; Start-Process 'http://localhost:5173'"


echo 🚀 Executando Backend FastAPI em primeiro plano...
echo.
cd /d "%~dp0"
"%~dp0venv\Scripts\python.exe" -m uvicorn backend.main:app --port 8000

