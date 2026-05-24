@echo off
REM NAMMA MALIGE DASHBOARD LAUNCHER
REM Easy way to start the dashboard without a terminal
chcp 65001 > nul
color 0A
title Namma Malige Launcher
echo ====================================
echo   NAMMA MALIGE DASHBOARD
echo ====================================
echo.
echo [1/3] Starting Dashboard Server...
cd dashboard-new
if not exist node_modules (
    echo First-time setup: Installing dependencies...
    call npm install
)
start "Namma Malige Dashboard" cmd /k "npm run dev"
cd ..
echo.
echo [2/3] Waiting for server to start...
timeout /t 8 /nobreak > nul
echo.
echo [3/3] Opening Dashboard...
start http://localhost:3000
echo.
echo ====================================
echo   DASHBOARD IS LIVE!
echo   http://localhost:3000
echo ====================================
echo.
echo This window will close in 5 seconds...
timeout /t 5 /nobreak > nul
