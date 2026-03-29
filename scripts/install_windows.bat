@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0\.."
set REPO_ROOT=%CD%

echo === AI 智建 - Windows 安装脚本 ===
echo.

REM 检查 Python
python --version 2>nul
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

REM 安装依赖
echo [1/3] 安装 Python 依赖...
python -m pip install openpyxl

REM 检查 pyRevit
echo [2/3] 检查 pyRevit...
if exist "%APPDATA%\pyRevit-Master" (
    echo pyRevit 已安装
) else (
    echo [提示] 未检测到 pyRevit，请从 https://github.com/pyrevitlabs/pyRevit/releases 下载安装
)

REM 配置 API Key
echo [3/3] 检查 DeepSeek API Key...
set CONFIG_DIR=%USERPROFILE%\.ai-smart-build
if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"
if not exist "%CONFIG_DIR%\config.json" (
    echo 请编辑 %CONFIG_DIR%\config.json 并填入你的 DeepSeek API Key
    copy "%REPO_ROOT%\examples\config.example.json" "%CONFIG_DIR%\config.json" >nul
) else (
    echo 配置文件已存在
)

echo.
echo === 安装完成 ===
echo 下一步：
echo 1. 把包含 AISmartBuild.extension 的目录加入 pyRevit 自定义扩展路径
echo 2. 在 Revit 中重载 pyRevit
echo 3. 编辑 %CONFIG_DIR%\config.json 填入 API Key
pause
