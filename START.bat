@echo off
REM Quick Start Script for CHRIS EFFECT Inventory System
REM This script will install dependencies and start the web server

cls
echo.
echo ========================================
echo  CHRIS EFFECT - Inventory System
echo  Web Server Startup
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from python.org
    pause
    exit /b 1
)

echo [1/3] Checking Python installation...
python --version
echo OK
echo.

REM Install or upgrade dependencies
echo [2/3] Installing dependencies...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo OK
echo.

REM Start the server
echo [3/3] Starting server...
echo.
echo ========================================
echo  Open your browser and go to:
echo  http://127.0.0.1:5000
echo.
echo  Default Credentials:
echo  Admin: admin / admin
echo  User:  user / user
echo.
echo  Press Ctrl+C to stop the server
echo ========================================
echo.

python app.py
