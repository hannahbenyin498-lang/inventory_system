"""
CHRIS EFFECT - System Verification Script
Verifies all components are properly installed and configured
"""

import os
import sys
import importlib.util

def check_python_version():
    """Check Python version"""
    version = sys.version_info
    print(f"Python Version: {version.major}.{version.minor}.{version.micro}", end="")
    if version.major >= 3 and version.minor >= 8:
        print(" ✓")
        return True
    else:
        print(" ✗ (Requires 3.8+)")
        return False

def check_files_exist():
    """Check if required files exist"""
    required_files = [
        'app.py',
        'requirements.txt',
        'templates/index.html',
        'store_inventory.db',
        'START.bat',
        'README.md',
    ]
    
    print("\nChecking files:")
    all_ok = True
    for file in required_files:
        exists = os.path.exists(file)
        status = "✓" if exists else "✗"
        print(f"  {file:<30} {status}")
        if not exists:
            all_ok = False
    
    return all_ok

def check_dependencies():
    """Check if Python dependencies are installed"""
    required_packages = {
        'flask': 'Flask',
        'flask_cors': 'Flask-CORS',
    }
    
    print("\nChecking dependencies:")
    all_ok = True
    for module, package_name in required_packages.items():
        try:
            __import__(module)
            print(f"  {package_name:<30} ✓")
        except ImportError:
            print(f"  {package_name:<30} ✗ (Not installed)")
            all_ok = False
    
    return all_ok

def check_database():
    """Check database"""
    print("\nChecking database:")
    if os.path.exists('store_inventory.db'):
        size = os.path.getsize('store_inventory.db')
        print(f"  Database file: ✓ ({size} bytes)")
        
        # Try to connect
        try:
            import sqlite3
            conn = sqlite3.connect('store_inventory.db')
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            tables = c.fetchone()[0]
            conn.close()
            print(f"  Tables: ✓ ({tables} found)")
            return True
        except Exception as e:
            print(f"  Database connection: ✗ ({e})")
            return False
    else:
        print("  Database file: No (Will be created on first run)")
        return True

def check_network():
    """Check if port 5000 is available"""
    print("\nChecking network:")
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = s.connect_ex(('127.0.0.1', 5000))
        s.close()
        
        if result == 0:
            print("  Port 5000: ✗ (Already in use)")
            return False
        else:
            print("  Port 5000: ✓ (Available)")
            return True
    except Exception as e:
        print(f"  Network check: ✗ ({e})")
        return False

def show_next_steps():
    """Show next steps"""
    print("\n" + "="*50)
    print("NEXT STEPS:")
    print("="*50)
    print("\n1. Install dependencies (if not already done):")
    print("   pip install -r requirements.txt")
    print("\n2. Start the server:")
    print("   python app.py")
    print("\n3. Open browser to:")
    print("   http://127.0.0.1:5000")
    print("\n4. Login with:")
    print("   Username: admin")
    print("   Password: admin")
    print("\n5. (Optional) Load sample data:")
    print("   python load_sample_data.py")
    print("\n" + "="*50)

def main():
    print("\n" + "="*50)
    print("CHRIS EFFECT - System Verification")
    print("="*50 + "\n")
    
    checks = [
        ("Python", check_python_version),
        ("Files", check_files_exist),
        ("Dependencies", check_dependencies),
        ("Database", check_database),
        ("Network", check_network),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"Error checking {name}: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*50)
    print("SUMMARY:")
    print("="*50)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {name:<20} {status}")
    
    print(f"\n  Overall: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n✓ All systems ready!")
        show_next_steps()
        return 0
    else:
        print("\n✗ Some checks failed. Please review the output above.")
        if not results[2][1]:  # Dependencies
            print("\nTry running: pip install -r requirements.txt")
        return 1

if __name__ == "__main__":
    sys.exit(main())
