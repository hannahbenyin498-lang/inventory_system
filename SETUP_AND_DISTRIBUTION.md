# Chris Effect - Setup & Distribution Guide

## 📦 Creating an Installer

### For Developers (Building the Executable)

#### Prerequisites
- Windows 7 or later
- Python 3.9+ installed
- Git (optional, for cloning)

#### Step 1: Prepare Development Environment
```bash
# Clone or download the repository
git clone https://github.com/hannahbenyin498-lang/inventory_system.git
cd inventory_system

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt
pip install pyinstaller
```

#### Step 2: Build the Executable
Double-click **`build_executable.bat`** in the project folder.

This script will:
1. ✅ Verify your setup
2. ✅ Clean previous builds
3. ✅ Build `dist\ChrisEffect.exe`
4. ✅ Package all required files

**Build takes 2-5 minutes**

#### Step 3: Test the Executable
```bash
# Run from command line
dist\ChrisEffect.exe

# Or double-click: dist\ChrisEffect.exe
```

Login with:
- **Admin:** admin / admin
- **User:** user / user

#### Step 4: Distribute
The file **`dist\ChrisEffect.exe`** is ready to distribute!

---

## 💾 Installation on Target Computers

### For End Users

#### Option A: Automated Installation (Recommended)
1. Download **ChrisEffect.exe** and **install.bat** to a folder
2. Double-click **install.bat**
3. Follow the prompts
4. Click the desktop shortcut to run

#### Option B: Manual Installation
1. Download **ChrisEffect.exe** to any folder
2. Double-click **ChrisEffect.exe**
3. Login with default credentials

---

## 📋 Distribution Checklist

### Files Needed for Distribution

```
ChrisEffect-Windows/
├── ChrisEffect.exe           ⭐ Main application (required)
├── install.bat               📋 Installation script (optional)
├── README.txt                📖 Quick start guide
└── SYSTEM_REQUIREMENTS.txt   ℹ️  System requirements
```

### Create Distribution Package

#### Option 1: ZIP Archive
```bash
# Compress for distribution
# 1. Create folder: ChrisEffect-Windows
# 2. Copy ChrisEffect.exe to it
# 3. Copy install.bat to it
# 4. Right-click → Send to → Compressed folder
# 5. Email or upload ChrisEffect-Windows.zip
```

#### Option 2: Self-Extracting Installer (7-Zip)
```bash
# Download 7-Zip from: https://7-zip.org/
# 1. Create folder with ChrisEffect.exe + install.bat
# 2. Right-click → 7-Zip → Create self-extracting archive
# 3. Rename to ChrisEffect-Setup.exe
```

#### Option 3: Professional Installer (Inno Setup)
Create setup with custom welcome screen, license agreement, etc.
[See Advanced Setup section below]

---

## 🔧 System Requirements

### Minimum System Requirements
- **OS:** Windows 7 or later (32-bit or 64-bit)
- **RAM:** 512 MB
- **Disk Space:** 150 MB (for extracted files)
- **.NET Framework:** Not required (included in executable)

### No Additional Installation Needed
✅ Python not required on target computers  
✅ All dependencies bundled in executable  
✅ No registry modifications  
✅ Can run from USB drive  

---

## 🛠️ Advanced: Create Professional Installer with Inno Setup

### Prerequisites
- Download Inno Setup: https://jrsoftware.org/isdl.php

### Create Inno Setup Script

Create `setup-inno.iss`:

```ini
[Setup]
AppName=Chris Effect
AppVersion=1.0
DefaultDirName={pf}\ChrisEffect
DefaultGroupName=Chris Effect
OutputBaseFilename=ChrisEffect-Setup
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=LICENSE.txt

[Files]
Source: "{#SourcePath}\dist\ChrisEffect.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Chris Effect"; Filename: "{app}\ChrisEffect.exe"
Name: "{commondesktop}\Chris Effect"; Filename: "{app}\ChrisEffect.exe"; IconIndex: 0

[Run]
Filename: "{app}\ChrisEffect.exe"; Description: "Launch Chris Effect"; Flags: postinstall nowait skipifsilent
```

### Build Installer
1. Open `setup-inno.iss` with Inno Setup
2. Click "Compile"
3. Get `Output\ChrisEffect-Setup.exe`

---

## 📊 Troubleshooting Installation

### Issue: "Missing DLL" Error
**Solution:** The .exe file is corrupted. Re-download or rebuild.

### Issue: "Cannot find ceicon.ico"
**Solution:** This should be included in the exe. Rebuild with:
```bash
build_executable.bat
```

### Issue: Database already exists, can't start fresh
**Solution:** Delete `store_inventory.db` in the installation folder

### Issue: "Not a valid Win32 application"
**Solution:** Wrong architecture (32-bit vs 64-bit). Rebuild for correct arch:
```bash
# For 32-bit systems, modify build_executable.bat
# For 64-bit systems, current build is fine
```

---

## 🔐 Database Management

### Default First Run
- Database (`store_inventory.db`) created automatically
- Default users created:
  - admin / admin
  - user / user

### Backup Database
```bash
# Copy this file to backup:
# %APPDATA%\ChrisEffect\store_inventory.db
# Or install_folder\store_inventory.db
```

### Reset Database
1. Delete `store_inventory.db`
2. Restart application
3. New database created with defaults

---

## 📧 Distribution Methods

### Email
```
Size: ~80-120 MB (ChrisEffect.exe)
Method: 
1. Zip the executable
2. Send via email with install.bat
```

### USB Drive
```
1. Copy ChrisEffect.exe + install.bat to USB
2. Recipient plugs in USB
3. Runs install.bat
4. Done!
```

### Website Download
```
1. Upload ChrisEffect-Setup.exe to website
2. Create download link
3. Users download and run
4. Windows SmartScreen may warn (new app)
   - Click "More info" → "Run anyway"
```

### Network Share
```
1. Place ChrisEffect.exe on network share
2. Users map network drive
3. Run installation script
4. Creates local copy
```

---

## 🔄 Updates & Version Management

### Creating Update Packages
1. Modify source code
2. Run `build_executable.bat` again
3. Distribute new `.exe` file
4. Users download new version and replace old one

### Version Detection
The executable version is embedded. To update:
1. Increment version in `ChrisEffect.spec`
2. Rebuild all installers

---

## ✅ Verification Checklist

- [ ] ChrisEffect.exe created successfully
- [ ] ChrisEffect.exe runs without errors
- [ ] Login works (admin/admin)
- [ ] Can create/edit products
- [ ] Can export CSV
- [ ] Database persists between runs
- [ ] Database file is in exe folder
- [ ] Install.bat creates desktop shortcut
- [ ] Installation on clean computer works
- [ ] No Python required on target computer

---

## 📞 Support

For issues:
1. Check **System Requirements** above
2. Try deleting `store_inventory.db` and restarting
3. Rebuild executable with `build_executable.bat`
4. Check Windows Event Viewer for errors

---

**Happy distributing!** 🚀
