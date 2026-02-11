# Quick Start Script for CHRIS EFFECT Inventory System (PowerShell)
# This script will install dependencies and start the web server

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host " CHRIS EFFECT - Inventory System" -ForegroundColor Cyan
Write-Host " Web Server Startup" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check if Python is installed
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[1/3] Python version: $pythonVersion" -ForegroundColor Green
}
catch {
    Write-Host "[ERROR] Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python 3.8+ from python.org" -ForegroundColor Red
    pause
    exit 1
}

# Install dependencies
Write-Host "[2/3] Installing dependencies..." -ForegroundColor Yellow
pip install -q -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to install dependencies" -ForegroundColor Red
    pause
    exit 1
}
Write-Host "Installation complete" -ForegroundColor Green
Write-Host ""

# Start the server
Write-Host "[3/3] Starting server..." -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Open your browser and go to:" -ForegroundColor Cyan
Write-Host " http://127.0.0.1:5000" -ForegroundColor Green
Write-Host "" -ForegroundColor Cyan
Write-Host " Default Credentials:" -ForegroundColor Cyan
Write-Host " Admin: admin / admin" -ForegroundColor Gray
Write-Host " User:  user / user" -ForegroundColor Gray
Write-Host "" -ForegroundColor Cyan
Write-Host " Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host "========================================`n" -ForegroundColor Cyan

python app.py
