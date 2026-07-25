@echo off
title JARVIS 3.0 Launcher
echo ===================================================
echo   INICIALIZANDO JARVIS 3.0 (BACKEND & FRONTEND)
echo ===================================================
echo.

set PATH=C:\Program Files\nodejs;%PATH%

echo [1/3] Iniciando o backend FastAPI (Python 3.12)...
start "Jarvis 3.0 Backend" cmd /k "cd /d "%~dp0" && "%~dp0venv\Scripts\python.exe" -m uvicorn backend.main:app --port 8000 --reload"

echo [2/3] Abrindo a interface web no navegador...
start "" "http://localhost:5173"

echo [3/3] Iniciando o servidor Vite Frontend...
cd /d "%~dp0frontend"
npm run dev
