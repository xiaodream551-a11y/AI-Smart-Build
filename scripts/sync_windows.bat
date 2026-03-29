@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0\.."

echo === AI SmartBuild - Sync Latest Code ===
echo.

git pull --ff-only

if errorlevel 1 (
    echo.
    echo [NOTE] Sync failed, possibly due to local modification conflicts, attempting force sync...
    git stash
    git pull --ff-only
    git stash pop
)

echo.
echo === Sync complete ===
echo.
pause
