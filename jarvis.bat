@echo off
title JARVIS 3.0 Engine & Backend Logs
echo ===================================================
echo   INICIALIZANDO JARVIS 3.0 (BACKEND & FRONTEND)
echo ===================================================
echo.

set PYTHONIOENCODING=utf-8
set PATH=C:\Program Files\nodejs;%PATH%

echo [1/3] Iniciando o servidor Vite Frontend (Silencioso em segundo plano)...
powershell -Command "Start-Process cmd.exe -ArgumentList '/c cd /d ""%~dp0frontend"" && npm run dev' -WindowStyle Hidden"

echo [2/3] Abrindo a interface web no navegador...
start "" "http://localhost:5173"

echo [3/3] Executando o backend FastAPI em primeiro plano (Console de Logs em Tempo Real)...
echo.
cd /d "%~dp0"
"%~dp0venv\Scripts\python.exe" -m uvicorn backend.main:app --port 8000 --reload
