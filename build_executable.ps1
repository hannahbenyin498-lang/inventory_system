# Chris Effect Inventory System - Build Executable (PowerShell)
# Run as Administrator: powershell -ExecutionPolicy Bypass -File .\build_executable.ps1

param(
    [switch]$SkipClean = $false,
    [switch]$SkipTest = $false
)

function Write-Header {
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host "  $args" -ForegroundColor Cyan
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Success {
    Write-Host "✓ $args" -ForegroundColor Green
}

function Write-Warning {
    Write-Host "⚠ $args" -ForegroundColor Yellow
}

function Write-Error {
    Write-Host "✗ $args" -ForegroundColor Red
}

# Start
Write-Header "Chris Effect - Building Standalone Executable"

# Check Python
Write-Host "Checking Python installation..." -NoNewline
$pythonExe = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonExe) {
    Write-Error ""
    Write-Error "Python not found! Please install Python 3.9+"
    exit 1
}
Write-Success ""

# Check virtual environment
if (-not (Test-Path ".venv")) {
    Write-Warning "Virtual environment not found. Creating..."
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to create virtual environment"
        exit 1
    }
    Write-Success "Virtual environment created"
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -NoNewline
& ".\.venv\Scripts\Activate.ps1" | Out-Null
Write-Success ""

# Install PyInstaller
Write-Host "Checking PyInstaller..." -NoNewline
python -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Warning ""
    Write-Warning "Installing PyInstaller..."
    pip install pyinstaller | Out-Null
}
Write-Success ""

# Clean previous builds
if (-not $SkipClean) {
    Write-Host "Cleaning previous builds..." -NoNewline
    if (Test-Path "build") { Remove-Item "build" -Recurse -Force | Out-Null }
    if (Test-Path "dist") { Remove-Item "dist" -Recurse -Force | Out-Null }
    Write-Success ""
}

# Build
Write-Header "Building Executable"
Write-Host "This may take 2-5 minutes..."
Write-Host ""

pyinstaller --clean `
    --onefile `
    --windowed `
    --name ChrisEffect `
    --icon ceicon.ico `
    --add-data "ceicon.ico;." `
    --add-data "templates;templates" `
    --add-data "images;images" `
    --hidden-import=ttkbootstrap `
    --hidden-import=ttkbootstrap.constants `
    --hidden-import=PIL `
    main.py

if ($LASTEXITCODE -ne 0) {
    Write-Error "Build failed!"
    Write-Host ""
    Write-Error "Try:"
    Write-Error "1. pip install --upgrade pyinstaller"
    Write-Error "2. pip install -r requirements.txt"
    exit 1
}

# Verify
Write-Header "Verifying Build"

if (Test-Path "dist\ChrisEffect.exe") {
    $exeSize = (Get-Item "dist\ChrisEffect.exe").Length / 1MB
    Write-Success "Build successful!"
    Write-Host ""
    Write-Host "Executable Details:" -ForegroundColor Cyan
    Write-Host "  Location: dist\ChrisEffect.exe"
    Write-Host "  Size: $([Math]::Round($exeSize, 1)) MB"
    Write-Host ""
    
    # Test run
    if (-not $SkipTest) {
        Write-Host "Testing executable..." -NoNewline
        & "dist\ChrisEffect.exe" --version 2>$null | Out-Null
        Write-Success ""
    }
    
    Write-Host ""
    Write-Header "Build Complete!"
    Write-Host "Next Steps:" -ForegroundColor Cyan
    Write-Host "  1. Test: dist\ChrisEffect.exe"
    Write-Host "  2. Copy dist\ChrisEffect.exe to archive"
    Write-Host "  3. Distribute to other computers"
    Write-Host ""
}
else {
    Write-Error "Build failed - ChrisEffect.exe not found"
    exit 1
}

Write-Host "Press Enter to exit..."
Read-Host
