@echo off
chcp 65001 >nul
title Shorts Finder — Frontend

echo.
echo  ╔══════════════════════════════════════╗
echo  ║      Shorts Finder — Frontend        ║
echo  ╚══════════════════════════════════════╝
echo.

cd /d "%~dp0frontend"

if not exist "node_modules" (
    echo  [*] Instaluję node_modules...
    npm install
)

echo  [*] Uruchamiam frontend na http://localhost:5173
echo  [*] Backend musi działać na http://localhost:8000
echo.
echo  Ctrl+C aby zatrzymać
echo.

npm run dev
