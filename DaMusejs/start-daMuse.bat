@echo off
REM DaMuse Process Management Script
REM This script ensures only one instance of DaMuse runs at a time

echo 🤖 DaMuse Process Manager
echo =========================

REM Check for existing DaMuse processes
echo 🔍 Checking for existing DaMuse processes...
for /f "tokens=2" %%i in ('tasklist /FI "IMAGENAME eq node.exe" /FO CSV ^| findstr "DaMuse"') do (
    echo ⚠️  Found existing DaMuse process: %%i
    set FOUND_PROCESS=1
)

if defined FOUND_PROCESS (
    echo.
    echo ⚠️  Found existing DaMuse processes!
    echo Do you want to kill existing processes and start fresh? (y/N)
    set /p response=
    if /i "%response%"=="y" (
        echo 🛑 Terminating existing DaMuse processes...
        taskkill /F /FI "WINDOWTITLE eq DaMuse*" 2>nul
        taskkill /F /FI "COMMANDLINE eq *DaMuse.js*" 2>nul
        echo ✅ Existing processes terminated
        timeout /t 2 /nobreak >nul
    ) else (
        echo ❌ Cannot start DaMuse - other instances are running
        echo Please stop existing instances first or choose 'y' to kill them
        pause
        exit /b 1
    )
) else (
    echo ✅ No existing DaMuse processes found
)

REM Change to DaMuse directory
cd /d "G:\GitHub\DaMuse\DaMusejs"

REM Verify required files exist
if not exist "DaMuse.js" (
    echo ❌ DaMuse.js not found in current directory
    echo Current directory: %CD%
    pause
    exit /b 1
)

if not exist "package.json" (
    echo ❌ package.json not found in current directory
    pause
    exit /b 1
)

REM Start DaMuse
echo.
echo 🚀 Starting DaMuse...
echo 📁 Working directory: %CD%
echo ⏰ Start time: %DATE% %TIME%
echo.

npm start

if errorlevel 1 (
    echo ❌ Failed to start DaMuse
    pause
    exit /b 1
)
