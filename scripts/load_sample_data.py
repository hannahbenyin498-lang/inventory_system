#!/usr/bin/env python3
"""
CHRIS EFFECT - Inventory System Demo Data Generator
This script loads sample inventory data into the database.

Run from the root directory:
    python scripts/load_sample_data.py
"""

import os
import sys
import sqlite3
from datetime import datetime

# Add parent directory to path to import app module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_db_path():
    """Get the path to the database file"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "store_inventory.db")

def init_db():
    """Initialize the database with required tables"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT,
            role TEXT
        )
    """)
    
    # Inventory table
    c.execute("""
        CREATE TABLE IF NOT EXISTS inventory_v2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT UNIQUE,
            name TEXT NOT NULL,
            category TEXT,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            status TEXT DEFAULT 'In Stock',
            image TEXT
        )
    """)
    
    # Sales table
    c.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            sku TEXT,
            name TEXT,
            quantity INTEGER,
            price REAL,
            sale_date TEXT
        )
    """)
    
    # Settings table
    c.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    
    # Category thresholds
    c.execute("""
        CREATE TABLE IF NOT EXISTS category_thresholds (
            category TEXT PRIMARY KEY,
            threshold INTEGER NOT NULL
        )
    """)
    
    # Check if default users exist and create them if not
    c.execute("SELECT count(*) FROM users")
    if c.fetchone()[0] == 0:
        import hashlib
        admin_pass = hashlib.sha256("admin".encode()).hexdigest()
        user_pass = hashlib.sha256("user".encode()).hexdigest()
        c.execute("INSERT INTO users VALUES (?, ?, ?)", ("admin", admin_pass, "admin"))
        c.execute("INSERT INTO users VALUES (?, ?, ?)", ("user", user_pass, "user"))
    
    conn.commit()
    conn.close()

def load_sample_data():
    """Load sample inventory data into the database"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Sample products
    sample_products = [
        ("SKU001", "MacBook Pro M3 Max", "Electronics", 25, 3499.99),
        ("SKU002", "Herman Miller Embody Chair", "Furniture", 15, 1695.00),
        ("SKU003", "Logitech MX Master 3S", "Electronics", 45, 99.99),
        ("SKU004", "Mechanical Keyboards Collection", "Electronics", 8, 149.99),
        ("SKU005", "Monitor Stand - Ergonomic", "Accessories", 32, 79.99),
        ("SKU006", "USB-C Hub 7-in-1", "Electronics", 18, 59.99),
        ("SKU007", "Wireless Mouse Pro", "Electronics", 52, 39.99),
        ("SKU008", "Desk Lamp LED", "Furniture", 24, 89.99),
        ("SKU009", "Cable Organizer Kit", "Accessories", 67, 24.99),
        ("SKU010", "Laptop Stand Aluminum", "Accessories", 12, 49.99),
        ("SKU011", "USB-C Fast Charger 65W", "Electronics", 5, 29.99),
        ("SKU012", "Webcam 4K Pro", "Electronics", 9, 129.99),
        ("SKU013", "Headphone Stand", "Accessories", 41, 34.99),
        ("SKU014", "Monitor Mount Arm", "Furniture", 19, 89.99),
        ("SKU015", "Docking Station USB-C", "Electronics", 11, 199.99),
    ]
    
    # Check if data already exists
    c.execute("SELECT COUNT(*) FROM inventory_v2")
    if c.fetchone()[0] > 0:
        print("✓ Database already contains data. Skipping sample data load.")
        conn.close()
        return
    
    print("📦 Loading sample inventory data...")
    for sku, name, category, qty, price in sample_products:
        # Calculate status
        if qty == 0:
            status = "Out of Stock"
        elif qty < 10:
            status = "Low Stock"
        else:
            status = "In Stock"
        
        try:
            c.execute(
                "INSERT INTO inventory_v2 (sku, name, category, quantity, price, status) VALUES (?, ?, ?, ?, ?, ?)",
                (sku, name, category, qty, price, status)
            )
        except sqlite3.IntegrityError:
            # SKU already exists, skip
            continue
    
    # Add some sample sales data
    sample_sales = [
        (1, "SKU001", "MacBook Pro M3 Max", 2, 3499.99),
        (2, "SKU002", "Herman Miller Embody Chair", 1, 1695.00),
        (3, "SKU003", "Logitech MX Master 3S", 3, 99.99),
        (4, "SKU007", "Wireless Mouse Pro", 5, 39.99),
    ]
    
    for pid, sku, name, qty, price in sample_sales:
        c.execute(
            "INSERT INTO sales (product_id, sku, name, quantity, price, sale_date) VALUES (?, ?, ?, ?, ?, ?)",
            (pid, sku, name, qty, price, datetime.now().isoformat())
        )
    
    conn.commit()
    conn.close()
    
    print(f"✓ Loaded {len(sample_products)} sample products")
    print(f"✓ Loaded {len(sample_sales)} sample sales records")
    print("\n✅ Your inventory is ready!\n")
    print("Login with:")
    print("  👤 Admin: admin / admin")
    print("  👤 User:  user / user")

if __name__ == "__main__":
    try:
        # Initialize the database
        init_db()
        
        # Load sample data
        load_sample_data()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
