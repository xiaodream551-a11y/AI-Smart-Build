@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0\.."

echo === AI SmartBuild - Sync Latest Code ===
echo.

git fetch origin main

if errorlevel 1 (
    echo.
    echo [ERROR] Cannot connect to GitHub, check your network.
    echo.
    pause
    exit /b 1
)

git reset --hard origin/main

echo.
echo [OK] Synced to latest version.
echo.
pause
