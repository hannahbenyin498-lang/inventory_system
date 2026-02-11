@echo off
REM Chris Effect Inventory System - Installation Script
REM Run this on target computers to set up the application
REM Usage: install.bat

setlocal enabledelayedexpansion

echo.
echo ============================================
echo  Chris Effect - Installation
echo ============================================
echo.

REM Check if already installed
if exist "store_inventory.db" (
    echo.
    echo This computer already has Chris Effect installed.
    echo Database found: store_inventory.db
    echo.
    choice /C YN /M "Continue installation anyway?"
    if errorlevel 2 exit /b 0
)

REM Check if ChrisEffect.exe exists
if not exist "ChrisEffect.exe" (
    echo ERROR: ChrisEffect.exe not found in current directory!
    echo.
    echo Please make sure:
    echo 1. You extracted the ChrisEffect archive
    echo 2. ChrisEffect.exe is in the same folder as this script
    echo.
    pause
    exit /b 1
)

echo Preparing installation...
echo.

REM Create shortcuts on Desktop
set "DESKTOP=%USERPROFILE%\Desktop"
set "EXE_PATH=%CD%\ChrisEffect.exe"

echo Creating Desktop shortcut...

REM Using PowerShell to create a shortcut (more reliable)
powershell -Command ^
    "$WshShell = New-Object -ComObject WScript.Shell;" ^
    "$Shortcut = $WshShell.CreateShortcut('%DESKTOP%\Chris Effect.lnk');" ^
    "$Shortcut.TargetPath = '%EXE_PATH%';" ^
    "$Shortcut.WorkingDirectory = '%CD%';" ^
    "$Shortcut.Description = 'Chris Effect Inventory System';" ^
    "$Shortcut.IconLocation = '%EXE_PATH%';" ^
    "$Shortcut.Save()"

if errorlevel 1 (
    echo Warning: Could not create desktop shortcut
)

echo.
echo ============================================
echo  ✓ INSTALLATION COMPLETE!
echo ============================================
echo.
echo To start the application:
echo 1. Double-click the "Chris Effect" icon on your Desktop
echo    OR
echo 2. Run ChrisEffect.exe directly
echo.
echo First Login:
echo  - Username: admin
echo  - Password: admin
echo.
echo The database will be created automatically on first run.
echo.
pause
