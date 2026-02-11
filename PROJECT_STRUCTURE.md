# Chris Effect - Inventory System

## 📁 Project Structure

```
inventory_system/
├── app.py                          # Main Flask web application (PRIMARY)
├── CE.py                           # Alternative Tkinter desktop application
├── requirements.txt                # Python dependencies
├── config.ini                      # Configuration file
├── ceicon.ico                      # Application icon
│
├── /templates/                     # Web UI templates
│   └── index.html
│
├── /images/                        # Product images
│   └── [product images]
│
├── /scripts/                       # Utility scripts
│   ├── load_sample_data.py         # Load demo inventory data
│   ├── verify_system.py            # Verify system setup
│   ├── create_logo.py              # Logo creation utility
│   └── create_logo_v2.py           # Alternative logo creation
│
├── /utils/                         # Shared utilities (currently empty)
│
├── .gitignore                      # Git ignore rules
├── README.md                       # Project documentation
└── SETUP_INSTRUCTIONS.txt          # Setup guide

```

## 🚀 Quick Start

### Run the Web Version (Recommended)
```bash
python app.py
```
Opens Store Inventory Manager at `http://127.0.0.1:5000/`

### Run the Desktop Version
```bash
python CE.py
```
Opens GUI-based inventory application (requires tkinter/ttkbootstrap)

## 🛠️ Utilities

### Load Sample Data
```bash
python scripts/load_sample_data.py
```
Adds demo products to the database

### Verify System
```bash
python scripts/verify_system.py
```
Checks that all dependencies are installed correctly

## 📦 Files to Ignore (GitHub)

The `.gitignore` file automatically excludes:
- `__pycache__/`, `.venv/`, `build/`, `dist/`
- `*.db` (database files)
- `*.spec` (PyInstaller specs)
- IDE files (`.vscode/`, `.idea/`)

## 🔧 Setup

1. Clone the repository
2. Create virtual environment: `python -m venv .venv`
3. Activate: `.venv\Scripts\activate` (Windows)
4. Install dependencies: `pip install -r requirements.txt`
5. Run: `python app.py`

**Optional:** Load sample data with `python scripts/load_sample_data.py`
