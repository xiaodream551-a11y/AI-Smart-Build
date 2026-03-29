@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0\.."
set REPO_ROOT=%CD%

echo === AI SmartBuild - Windows Installation Script ===
echo.

REM Check Python
python --version 2>nul
if errorlevel 1 (
    echo [ERROR] Python not detected, please install Python 3.10+ first
    pause
    exit /b 1
)

REM Install dependencies
echo [1/3] Installing Python dependencies...
python -m pip install openpyxl

REM Check pyRevit
echo [2/3] Checking pyRevit...
if exist "%APPDATA%\pyRevit-Master" (
    echo pyRevit is installed
) else (
    echo [NOTE] pyRevit not detected, please download and install from https://github.com/pyrevitlabs/pyRevit/releases
)

REM Configure API Key
echo [3/3] Checking DeepSeek API Key...
set CONFIG_DIR=%USERPROFILE%\.ai-smart-build
if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"
if not exist "%CONFIG_DIR%\config.json" (
    echo Please edit %CONFIG_DIR%\config.json and fill in your DeepSeek API Key
    copy "%REPO_ROOT%\examples\config.example.json" "%CONFIG_DIR%\config.json" >nul
) else (
    echo Config file already exists
)

echo.
echo === Installation complete ===
echo Next steps:
echo 1. Add the directory containing AISmartBuild.extension to the pyRevit custom extensions path
echo 2. Reload pyRevit in Revit
echo 3. Edit %CONFIG_DIR%\config.json to fill in API Key
pause
