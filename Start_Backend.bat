@echo off
chcp 65001 >nul
title Shorts Finder — Backend

echo.
echo  ╔══════════════════════════════════════╗
echo  ║      Shorts Finder — Backend         ║
echo  ╚══════════════════════════════════════╝
echo.

cd /d "%~dp0backend"

if not exist ".env" (
    echo  [!] Brak pliku backend\.env
    echo  [!] Skopiuj backend\.env.example i uzupelnij klucze API
    pause
    exit /b 1
)

echo  [*] Instaluję zależności...
pip install -r requirements.txt -q

echo  [*] Uruchamiam backend na http://localhost:8000
echo  [*] Frontend: http://localhost:5173
echo.
echo  Ctrl+C aby zatrzymać
echo.

uvicorn main:app --host 0.0.0.0 --port 8000 --reload
