@echo off
title JARVIS 3.0 Launcher
echo ===================================================
echo   INICIALIZANDO JARVIS 3.0 (FRONTEND & HUD ENGINE)
echo ===================================================
echo.

set PATH=C:\Program Files\nodejs;%PATH%

echo [1/2] Abrindo a interface web no navegador...
start "" "http://localhost:5173"

echo [2/2] Iniciando o servidor Vite Frontend...
cd /d "%~dp0frontend"
npm run dev
