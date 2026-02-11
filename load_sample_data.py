"""
CHRIS EFFECT - Inventory System Demo Data Generator
This script loads sample inventory data into the database
"""

import app as inventory_app
import sqlite3

def load_sample_data():
    conn = inventory_app.get_db()
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
        print("Database already contains data. Skipping sample data load.")
        conn.close()
        return
    
    print("Loading sample inventory data...")
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
            "INSERT INTO sales (product_id, sku, name, quantity, price, sale_date) VALUES (?, ?, ?, ?, ?, datetime('now'))",
            (pid, sku, name, qty, price)
        )
    
    conn.commit()
    conn.close()
    
    print(f"✓ Loaded {len(sample_products)} sample products")
    print(f"✓ Loaded {len(sample_sales)} sample sales")
    print("\nYour inventory is ready!")
    print("\nLogin with:")
    print("  Admin: admin / admin")
    print("  User:  user / user")

if __name__ == "__main__":
    # Initialize the database
    inventory_app.init_db()
    
    # Load sample data
    load_sample_data()
