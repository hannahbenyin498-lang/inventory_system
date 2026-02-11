@echo off
REM Chris Effect Inventory System - Build Executable
REM This script builds a standalone .exe file for distribution
REM Run this on your development machine with: build_executable.bat

echo.
echo ============================================
echo  Chris Effect - Building Standalone Installer
echo ============================================
echo.

REM Check if virtual environment exists
if not exist ".venv\" (
    echo ERROR: Virtual environment not found!
    echo Please run: python -m venv .venv
    echo Then run: .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Check if PyInstaller is installed
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

REM Clean previous builds
echo Cleaning previous builds...
if exist "build\" rmdir /s /q build
if exist "dist\" rmdir /s /q dist
if exist "ChrisEffect.egg-info\" rmdir /s /q ChrisEffect.egg-info

REM Build the executable
echo.
echo Building standalone executable...
echo This may take 2-5 minutes...
echo.

pyinstaller --clean ^
    --onefile ^
    --windowed ^
    --name ChrisEffect ^
    --icon ceicon.ico ^
    --add-data "ceicon.ico;." ^
    --add-data "templates;templates" ^
    --add-data "images;images" ^
    --hidden-import=ttkbootstrap ^
    --hidden-import=ttkbootstrap.constants ^
    --hidden-import=PIL ^
    main.py

REM Check if build was successful
if exist "dist\ChrisEffect.exe" (
    echo.
    echo ============================================
    echo  ✓ BUILD SUCCESSFUL!
    echo ============================================
    echo.
    echo Executable: dist\ChrisEffect.exe
    echo.
    echo Next steps:
    echo 1. Test the app: dist\ChrisEffect.exe
    echo 2. Distribute dist\ChrisEffect.exe to other computers
    echo 3. On target computers, just run ChrisEffect.exe
    echo.
    pause
) else (
    echo.
    echo ============================================
    echo  ✗ BUILD FAILED!
    echo ============================================
    echo.
    echo Check the error messages above.
    echo Common issues:
    echo - Missing Python packages: pip install -r requirements.txt
    echo - Missing icon: Check ceicon.ico exists
    echo - PyInstaller error: Try pip install --upgrade pyinstaller
    echo.
    pause
    exit /b 1
)
