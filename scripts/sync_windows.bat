@echo off
setlocal
cd /d "%~dp0\.."

echo === AI 智建 - 同步最新代码 ===
echo.

git pull --ff-only

if errorlevel 1 (
    echo.
    echo [提示] 同步失败，可能有本地修改冲突，尝试强制同步...
    git stash
    git pull --ff-only
    git stash pop
)

echo.
echo === 同步完成 ===
echo.
pause
