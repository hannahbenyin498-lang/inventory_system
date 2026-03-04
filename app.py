import os
import sys
import sqlite3
import csv
import uuid
import shutil
import hashlib
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps

from flask import Flask, render_template_string, request, jsonify, send_file, send_from_directory, Response
from flask_cors import CORS
import threading
import time
try:
    import webview
except ImportError:
    webview = None

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "store_inventory.db")
IMAGES_DIR = os.path.join(BASE_DIR, "images")
os.makedirs(IMAGES_DIR, exist_ok=True)

# --- Flask App Setup ---
app = Flask(__name__, static_folder=BASE_DIR)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
CORS(app)

# --- Database Helper Functions ---
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
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
    
    # Admin roles/privileges table
    c.execute("""
        CREATE TABLE IF NOT EXISTS admin_privileges (
            username TEXT PRIMARY KEY,
            admin_role TEXT NOT NULL,
            permissions TEXT,
            created_at TEXT
        )
    """)
    
    # Check if default users exist
    c.execute("SELECT count(*) FROM users")
    if c.fetchone()[0] == 0:
        admin_pass = hashlib.sha256("admin".encode()).hexdigest()
        user_pass = hashlib.sha256("user".encode()).hexdigest()
        director_pass = hashlib.sha256("director".encode()).hexdigest()
        developer_pass = hashlib.sha256("developer".encode()).hexdigest()
        
        # Create default users
        c.execute("INSERT INTO users VALUES (?, ?, ?)", ("admin", admin_pass, "admin"))
        c.execute("INSERT INTO users VALUES (?, ?, ?)", ("user", user_pass, "user"))
        c.execute("INSERT INTO users VALUES (?, ?, ?)", ("director", director_pass, "admin"))
        c.execute("INSERT INTO users VALUES (?, ?, ?)", ("deputy_director", admin_pass, "admin"))
        c.execute("INSERT INTO users VALUES (?, ?, ?)", ("developer", developer_pass, "admin"))
        
        # Add admin privileges
        c.execute("INSERT INTO admin_privileges VALUES (?, ?, ?, ?)", 
                 ("admin", "system_admin", "all", datetime.now().isoformat()))
        c.execute("INSERT INTO admin_privileges VALUES (?, ?, ?, ?)", 
                 ("director", "director", "inventory,sales,users,reports,settings", datetime.now().isoformat()))
        c.execute("INSERT INTO admin_privileges VALUES (?, ?, ?, ?)", 
                 ("deputy_director", "deputy_director", "inventory,sales,reports", datetime.now().isoformat()))
        c.execute("INSERT INTO admin_privileges VALUES (?, ?, ?, ?)", 
                 ("developer", "developer", "system,debug,all", datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

# --- Authentication & Authorization ---
# In-memory token store for RBAC with multi-client support
token_store = {}  # {token: {username, role, login_time, expires_at, client_info, device_id}}
TOKEN_EXPIRY_HOURS = 24  # Token expiration time

def cleanup_expired_tokens():
    """Remove expired tokens from store"""
    current_time = datetime.now()
    expired = [token for token, data in token_store.items() if data.get('expires_at') < current_time]
    for token in expired:
        del token_store[token]
    return len(expired)

def require_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth = request.headers.get('Authorization')
        if not auth:
            return jsonify({'error': 'Unauthorized'}), 401
        
        # Clean up expired tokens periodically
        if len(token_store) % 10 == 0:
            cleanup_expired_tokens()
        
        # Verify token is valid and not expired
        if auth not in token_store:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        token_data = token_store[auth]
        if token_data.get('expires_at') < datetime.now():
            del token_store[auth]
            return jsonify({'error': 'Token expired'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

def require_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token or token not in token_store:
            return jsonify({'error': 'Unauthorized'}), 401
        
        token_data = token_store[token]
        # Check expiration
        if token_data.get('expires_at') < datetime.now():
            del token_store[token]
            return jsonify({'error': 'Token expired'}), 401
        
        user_role = token_data.get('role')
        if user_role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

def get_user_from_token(token):
    """Get username and role from token, checking expiration"""
    if token in token_store:
        token_data = token_store[token]
        # Check if token is expired
        if token_data.get('expires_at') < datetime.now():
            del token_store[token]
            return None
        return token_data
    return None

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    device_id = data.get('device_id', '').strip() or str(uuid.uuid4())
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    conn = get_db()
    c = conn.cursor()
    hashed = hashlib.sha256(password.encode()).hexdigest()
    c.execute("SELECT username, role FROM users WHERE username=? AND password_hash=?", (username, hashed))
    row = c.fetchone()
    conn.close()
    
    if row:
        # Generate secure random token
        token = secrets.token_urlsafe(32)
        login_time = datetime.now()
        expires_at = login_time + timedelta(hours=TOKEN_EXPIRY_HOURS)
        
        # Store token with metadata for multi-client support
        token_store[token] = {
            'username': username,
            'role': row['role'],
            'login_time': login_time.isoformat(),
            'expires_at': expires_at,
            'device_id': device_id,
            'client_info': {
                'user_agent': request.headers.get('User-Agent', 'Unknown'),
                'ip_address': request.remote_addr
            }
        }
        
        return jsonify({
            'success': True,
            'username': username,
            'role': row['role'],
            'token': token,
            'device_id': device_id,
            'expires_at': expires_at.isoformat(),
            'expires_in_hours': TOKEN_EXPIRY_HOURS
        })
    
    return jsonify({'error': 'Invalid credentials'}), 401

# --- Dashboard/Analytics ---
@app.route('/api/dashboard', methods=['GET'])
@require_login
def get_dashboard():
    conn = get_db()
    c = conn.cursor()
    
    # Total products and quantity
    c.execute("SELECT COUNT(*), COALESCE(SUM(quantity),0), COALESCE(SUM(quantity*price),0) FROM inventory_v2")
    total_prod, total_qty, total_value = c.fetchone()
    
    # Low stock count
    c.execute("SELECT COUNT(*) FROM inventory_v2 WHERE status='Low Stock'")
    low_stock = c.fetchone()[0]
    
    # Out of stock count
    c.execute("SELECT COUNT(*) FROM inventory_v2 WHERE status='Out of Stock'")
    out_stock = c.fetchone()[0]
    
    # Get category distribution
    c.execute("SELECT category, SUM(quantity) as qty FROM inventory_v2 GROUP BY category ORDER BY qty DESC LIMIT 5")
    categories = [{'name': row[0] or 'Uncategorized', 'qty': row[1]} for row in c.fetchall()]
    
    # Recent sales
    c.execute("SELECT name, quantity, price, sale_date FROM sales ORDER BY sale_date DESC LIMIT 10")
    recent_sales = [dict(row) for row in c.fetchall()]
    
    conn.close()
    
    return jsonify({
        'total_products': total_prod or 0,
        'total_quantity': total_qty or 0,
        'total_value': round(total_value or 0, 2),
        'low_stock': low_stock or 0,
        'out_of_stock': out_stock or 0,
        'categories': categories,
        'recent_sales': recent_sales
    })

# --- Inventory Management ---
@app.route('/api/inventory', methods=['GET'])
@require_login
def get_inventory():
    conn = get_db()
    c = conn.cursor()
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()
    status = request.args.get('status', '').strip()
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 12, type=int)
    
    # Build query with filters
    query = "SELECT id, sku, name, category, quantity, price, status, image FROM inventory_v2 WHERE 1=1"
    params = []
    
    if search:
        query += " AND (name LIKE ? OR sku LIKE ? OR category LIKE ?)"
        params.extend(['%' + search + '%', '%' + search + '%', '%' + search + '%'])
    
    if category:
        query += " AND category = ?"
        params.append(category)
    
    if status:
        query += " AND status = ?"
        params.append(status)
    
    if min_price is not None:
        query += " AND price >= ?"
        params.append(min_price)
    
    if max_price is not None:
        query += " AND price <= ?"
        params.append(max_price)
    
    query += " ORDER BY name"
    
    # Get total count
    count_query = f"SELECT COUNT(*) FROM inventory_v2 WHERE 1=1"
    if search:
        count_query += " AND (name LIKE ? OR sku LIKE ? OR category LIKE ?)"
    if category:
        count_query += " AND category = ?"
    if status:
        count_query += " AND status = ?"
    if min_price is not None:
        count_query += " AND price >= ?"
    if max_price is not None:
        count_query += " AND price <= ?"
    
    c.execute(count_query, params)
    total = c.fetchone()[0]
    
    # Apply pagination
    offset = (page - 1) * limit
    query += f" LIMIT {limit} OFFSET {offset}"
    
    c.execute(query, params)
    items = [dict(row) for row in c.fetchall()]
    conn.close()
    
    return jsonify({
        'items': items,
        'total': total,
        'page': page,
        'limit': limit,
        'pages': (total + limit - 1) // limit
    })

@app.route('/api/inventory', methods=['POST'])
@require_login
def add_product():
    data = request.json
    name = data.get('name', '').strip()
    sku = data.get('sku', '').strip()
    category = data.get('category', 'Uncategorized').strip() or 'Uncategorized'
    quantity = int(data.get('quantity', 0))
    price = float(data.get('price', 0))
    image = data.get('image', '').strip() or None
    
    if not name or not sku:
        return jsonify({'error': 'Name and SKU required'}), 400
    
    if quantity < 0 or price < 0:
        return jsonify({'error': 'Quantity and price must be non-negative'}), 400
    
    conn = get_db()
    c = conn.cursor()
    
    # Check for duplicate SKU
    c.execute("SELECT 1 FROM inventory_v2 WHERE sku=?", (sku,))
    if c.fetchone():
        conn.close()
        return jsonify({'error': 'SKU already exists'}), 400
    
    # Determine status
    threshold = get_category_threshold(category)
    if quantity == 0:
        status = 'Out of Stock'
    elif quantity < threshold:
        status = 'Low Stock'
    else:
        status = 'In Stock'
    
    c.execute("""
        INSERT INTO inventory_v2 (sku, name, category, quantity, price, status, image)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (sku, name, category, quantity, price, status, image))
    
    conn.commit()
    product_id = c.lastrowid
    conn.close()
    
    return jsonify({'id': product_id, 'message': 'Product added', 'image': image}), 201

@app.route('/api/inventory/<int:product_id>', methods=['GET'])
@require_login
def get_product(product_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, sku, name, category, quantity, price, status, image FROM inventory_v2 WHERE id=?", (product_id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        return jsonify({'error': 'Product not found'}), 404
    
    return jsonify(dict(row))

@app.route('/api/inventory/<int:product_id>', methods=['PUT'])
@require_login
def update_product(product_id):
    data = request.json
    name = data.get('name', '').strip()
    category = data.get('category', 'Uncategorized').strip() or 'Uncategorized'
    quantity = int(data.get('quantity', 0))
    price = float(data.get('price', 0))
    image = data.get('image', '').strip() or None
    
    if not name:
        return jsonify({'error': 'Name required'}), 400
    
    conn = get_db()
    c = conn.cursor()
    
    # Determine status
    threshold = get_category_threshold(category)
    if quantity == 0:
        status = 'Out of Stock'
    elif quantity < threshold:
        status = 'Low Stock'
    else:
        status = 'In Stock'
    
    c.execute("""
        UPDATE inventory_v2 
        SET name=?, category=?, quantity=?, price=?, status=?, image=?
        WHERE id=?
    """, (name, category, quantity, price, status, image, product_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Product updated'})

@app.route('/api/inventory/<int:product_id>', methods=['DELETE'])
@require_admin
def delete_product(product_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM inventory_v2 WHERE id=?", (product_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Product deleted'})

# --- Sales Recording ---
@app.route('/api/sales', methods=['POST'])
@require_login
def record_sale():
    data = request.json
    product_id = data.get('product_id')
    quantity_sold = int(data.get('quantity', 0))
    
    if quantity_sold <= 0:
        return jsonify({'error': 'Quantity must be greater than zero'}), 400
    
    conn = get_db()
    c = conn.cursor()
    
    # Get product
    c.execute("SELECT sku, name, quantity, price, category FROM inventory_v2 WHERE id=?", (product_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Product not found'}), 404
    
    sku, name, current_qty, price, category = row
    
    if quantity_sold > current_qty:
        conn.close()
        return jsonify({'error': 'Not enough stock'}), 400
    
    new_qty = current_qty - quantity_sold
    threshold = get_category_threshold(category)
    if new_qty == 0:
        status = 'Out of Stock'
    elif new_qty < threshold:
        status = 'Low Stock'
    else:
        status = 'In Stock'
    
    # Update inventory
    c.execute("UPDATE inventory_v2 SET quantity=?, status=? WHERE id=?", (new_qty, status, product_id))
    
    # Record sale
    c.execute("""
        INSERT INTO sales (product_id, sku, name, quantity, price, sale_date)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (product_id, sku, name, quantity_sold, price, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Sale recorded', 'new_quantity': new_qty})

@app.route('/api/sales', methods=['GET'])
@require_login
def get_sales():
    conn = get_db()
    c = conn.cursor()
    limit = request.args.get('limit', 50, type=int)
    c.execute("SELECT id, name, quantity, price, sale_date FROM sales ORDER BY sale_date DESC LIMIT ?", (limit,))
    sales = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(sales)

# --- CSV Import/Export ---
@app.route('/api/import-csv', methods=['POST'])
@require_admin
def import_csv():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'Only CSV files allowed'}), 400
    
    try:
        imported = updated = skipped = invalid = 0
        conn = get_db()
        c = conn.cursor()
        
        # Get existing SKUs
        c.execute("SELECT sku FROM inventory_v2 WHERE sku IS NOT NULL AND sku != ''")
        existing_skus = {row[0] for row in c.fetchall()}
        
        # Process CSV
        reader = csv.DictReader(file.stream.read().decode('utf-8').splitlines())
        for row in reader:
            name = row.get('name', '').strip()
            sku = row.get('sku', '').strip()
            category = row.get('category', 'Uncategorized').strip() or 'Uncategorized'
            
            try:
                qty = int(row.get('quantity', 0))
                price = float(row.get('price', 0))
            except:
                invalid += 1
                continue
            
            if not name or qty < 0 or price < 0:
                invalid += 1
                continue
            
            threshold = get_category_threshold(category)
            if qty == 0:
                status = 'Out of Stock'
            elif qty < threshold:
                status = 'Low Stock'
            else:
                status = 'In Stock'
            
            if sku and sku in existing_skus:
                c.execute("""
                    UPDATE inventory_v2 
                    SET name=?, category=?, quantity=?, price=?, status=?
                    WHERE sku=?
                """, (name, category, qty, price, status, sku))
                updated += 1
            else:
                c.execute("""
                    INSERT INTO inventory_v2 (sku, name, category, quantity, price, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (sku, name, category, qty, price, status))
                imported += 1
                if sku:
                    existing_skus.add(sku)
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'imported': imported,
            'updated': updated,
            'skipped': skipped,
            'invalid': invalid
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/export-csv', methods=['GET'])
@require_login
def export_csv():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, sku, name, category, quantity, price, status, image FROM inventory_v2")
    rows = c.fetchall()
    conn.close()
    
    output = "id,sku,name,category,quantity,price,status,image\n"
    for row in rows:
        output += f"{row[0]},{row[1]},{row[2]},{row[3]},{row[4]},{row[5]},{row[6]},{row[7] or ''}\n"
    
    return output, 200, {'Content-Disposition': 'attachment; filename=inventory.csv'}

# --- Image Upload ---
@app.route('/api/upload-image', methods=['POST'])
@require_login
def upload_image():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400
    
    # Validate file type
    allowed_ext = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_ext:
        return jsonify({'error': f'File type not allowed. Must be: {" ".join(allowed_ext)}'}), 400
    
    # Check file size (max 5MB)
    max_size = 5 * 1024 * 1024
    file.seek(0, os.SEEK_END)
    file_length = file.tell()
    file.seek(0)
    
    if file_length > max_size:
        return jsonify({'error': 'File too large. Maximum size: 5MB'}), 400
    
    if file_length == 0:
        return jsonify({'error': 'File is empty'}), 400
    
    try:
        # Save file with unique name
        unique_name = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(IMAGES_DIR, unique_name)
        file.save(filepath)
        
        return jsonify({
            'success': True,
            'path': f'images/{unique_name}',
            'filename': unique_name,
            'size': file_length
        })
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/images/<path:filename>')
def serve_image(filename):
    return send_from_directory(IMAGES_DIR, filename)

# --- Categories ---
@app.route('/api/categories', methods=['GET'])
@require_login
def get_categories():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT DISTINCT category FROM inventory_v2 WHERE category IS NOT NULL AND category != '' ORDER BY category")
    cats = [row[0] for row in c.fetchall()]
    conn.close()
    
    defaults = ["Electronics", "Clothing", "Food", "Uncategorized"]
    for d in defaults:
        if d not in cats:
            cats.append(d)
    
    return jsonify(sorted(cats))

# --- Thresholds ---
def get_category_threshold(category):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT value FROM app_settings WHERE key='low_stock_default'")
    default = c.fetchone()
    default_threshold = int(default[0]) if default else 10
    
    c.execute("SELECT threshold FROM category_thresholds WHERE category=?", (category,))
    row = c.fetchone()
    conn.close()
    
    return int(row[0]) if row else default_threshold

@app.route('/api/thresholds', methods=['GET'])
@require_login
def get_thresholds():
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT value FROM app_settings WHERE key='low_stock_default'")
    default = c.fetchone()
    default_threshold = int(default[0]) if default else 10
    
    c.execute("SELECT category, threshold FROM category_thresholds")
    overrides = {row[0]: row[1] for row in c.fetchall()}
    
    conn.close()
    return jsonify({'default': default_threshold, 'overrides': overrides})

@app.route('/api/thresholds/default', methods=['PUT'])
@require_login
def set_default_threshold():
    data = request.json
    value = int(data.get('value', 10))
    
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)", ('low_stock_default', str(value)))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Default threshold updated'})

@app.route('/api/thresholds/<category>', methods=['PUT'])
@require_login
def set_category_threshold(category):
    data = request.json
    value = int(data.get('value', 10))
    
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO category_thresholds (category, threshold) VALUES (?, ?)", (category, value))
    conn.commit()
    conn.close()
    
    return jsonify({'message': f'Threshold for {category} updated'})

@app.route('/api/thresholds/<category>', methods=['DELETE'])
@require_login
def delete_category_threshold(category):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM category_thresholds WHERE category=?", (category,))
    conn.commit()
    conn.close()
    
    return jsonify({'message': f'Threshold for {category} cleared'})

@app.route('/api/admin-users', methods=['GET'])
@require_admin
def get_admin_users():
    """Get list of all users with admin privileges"""
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT u.username, u.role, ap.admin_role, ap.permissions, ap.created_at
        FROM users u
        LEFT JOIN admin_privileges ap ON u.username = ap.username
        WHERE u.role = 'admin'
        ORDER BY u.username
    """)
    admins = []
    for row in c.fetchall():
        admins.append({
            'username': row[0],
            'role': row[1],
            'admin_role': row[2] or 'user',
            'permissions': row[3] or '',
            'created_at': row[4]
        })
    conn.close()
    return jsonify(admins)

@app.route('/api/admin-users/<username>', methods=['PUT'])
@require_admin
def update_admin_privileges(username):
    """Update admin privileges for a user"""
    token = request.headers.get('Authorization')
    current_user = get_user_from_token(token)
    
    if current_user['username'] == username:
        return jsonify({'error': 'Cannot modify your own privileges'}), 400
    
    data = request.json
    admin_role = data.get('admin_role', 'user').strip()
    permissions = data.get('permissions', '').strip()
    
    valid_roles = ['user', 'director', 'deputy_director', 'developer', 'system_admin']
    if admin_role not in valid_roles:
        return jsonify({'error': f'Invalid admin role. Must be one of: {" ".join(valid_roles)}'}), 400
    
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO admin_privileges (username, admin_role, permissions, created_at)
        VALUES (?, ?, ?, ?)
    """, (username, admin_role, permissions, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    return jsonify({
        'message': f'Admin privileges updated for {username}',
        'admin_role': admin_role,
        'permissions': permissions
    })
@app.route('/api/user-info', methods=['GET'])
@require_login
def get_user_info():
    token = request.headers.get('Authorization')
    user_data = get_user_from_token(token)
    if user_data:
        return jsonify({
            'username': user_data['username'],
            'role': user_data['role'],
            'is_admin': user_data['role'] == 'admin'
        })
    return jsonify({'error': 'User not found'}), 404

@app.route('/api/logout', methods=['POST'])
@require_login
def logout():
    """Logout current session (device)"""
    token = request.headers.get('Authorization')
    if token in token_store:
        del token_store[token]
    return jsonify({'message': 'Logged out successfully'})

@app.route('/api/sessions', methods=['GET'])
@require_login
def get_sessions():
    """Get all active sessions for current user"""
    token = request.headers.get('Authorization')
    current_user_data = token_store.get(token)
    
    if not current_user_data:
        return jsonify({'error': 'Invalid token'}), 401
    
    current_username = current_user_data['username']
    
    # Find all active sessions for this user
    sessions = []
    for session_token, session_data in token_store.items():
        if session_data['username'] == current_username:
            is_current = session_token == token
            session_info = {
                'token': session_token[:8] + '...',  # Obfuscate token
                'device_id': session_data.get('device_id'),
                'login_time': session_data.get('login_time'),
                'expires_at': session_data.get('expires_at').isoformat() if isinstance(session_data.get('expires_at'), datetime) else session_data.get('expires_at'),
                'user_agent': session_data.get('client_info', {}).get('user_agent'),
                'ip_address': session_data.get('client_info', {}).get('ip_address'),
                'is_current': is_current
            }
            sessions.append(session_info)
    
    return jsonify(sessions)

@app.route('/api/sessions/logout-all', methods=['POST'])
@require_login
def logout_all_sessions():
    """Logout all sessions for current user except this one (optional)"""
    token = request.headers.get('Authorization')
    current_user_data = token_store.get(token)
    
    if not current_user_data:
        return jsonify({'error': 'Invalid token'}), 401
    
    current_username = current_user_data['username']
    data = request.json or {}
    keep_current = data.get('keep_current', True)  # Keep current session active if True
    
    # Remove all sessions for this user
    sessions_removed = 0
    tokens_to_remove = []
    for session_token, session_data in token_store.items():
        if session_data['username'] == current_username:
            if keep_current and session_token == token:
                continue  # Keep current session
            tokens_to_remove.append(session_token)
            sessions_removed += 1
    
    for session_token in tokens_to_remove:
        del token_store[session_token]
    
    return jsonify({
        'message': f'Logged out {sessions_removed} session(s)',
        'sessions_removed': sessions_removed,
        'current_session_active': keep_current
    })

# --- User Management (Admin Only) ---
@app.route('/api/users', methods=['GET'])
@require_admin
def get_all_users():
    """Get list of all users (admin only)"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT username, role FROM users ORDER BY username")
    users = [{'username': row['username'], 'role': row['role']} for row in c.fetchall()]
    conn.close()
    return jsonify(users)

@app.route('/api/users', methods=['POST'])
@require_admin
def create_user():
    """Create new user (admin only)"""
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    role = data.get('role', 'user')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    if role not in ['user', 'admin']:
        return jsonify({'error': 'Role must be user or admin'}), 400
    
    conn = get_db()
    c = conn.cursor()
    
    # Check if user already exists
    c.execute("SELECT username FROM users WHERE username=?", (username,))
    if c.fetchone():
        conn.close()
        return jsonify({'error': 'Username already exists'}), 409
    
    # Create new user
    hashed = hashlib.sha256(password.encode()).hexdigest()
    try:
        c.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", 
                 (username, hashed, role))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'username': username, 'role': role}), 201
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<username>', methods=['DELETE'])
@require_admin
def delete_user(username):
    """Delete user (admin only, cannot delete self)"""
    token = request.headers.get('Authorization')
    current_user = get_user_from_token(token)
    
    # Prevent admin from deleting themselves
    if current_user['username'] == username:
        return jsonify({'error': 'Cannot delete your own account'}), 400
    
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE username=?", (username,))
    conn.commit()
    conn.close()
    return jsonify({'message': f'User {username} deleted'})

@app.route('/api/users/<username>/role', methods=['PUT'])
@require_admin
def update_user_role(username):
    """Update user role (admin only, cannot change own role)"""
    token = request.headers.get('Authorization')
    current_user = get_user_from_token(token)
    
    # Prevent admin from changing their own role
    if current_user['username'] == username:
        return jsonify({'error': 'Cannot change your own role'}), 400
    
    data = request.json
    new_role = data.get('role', '').strip()
    
    if new_role not in ['user', 'admin']:
        return jsonify({'error': 'Role must be user or admin'}), 400
    
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET role=? WHERE username=?", (new_role, username))
    conn.commit()
    conn.close()
    return jsonify({'message': f'User {username} role updated to {new_role}'})

# --- Web UI Routes ---
HTML_TEMPLATE = """<!DOCTYPE html>
<html class="dark" lang="en">
<head>
    <meta charset="utf-8"/>
    <meta content="width=device-width, initial-scale=1.0" name="viewport"/>
    <title>Inventory Dashboard - CHRIS EFFECT</title>
    <script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet"/>
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet"/>
    <script id="tailwind-config">
        tailwind.config = {
            darkMode: "class",
            theme: {
                extend: {
                    colors: {
                        "primary": "#3b82f6",
                        "navy-950": "#020617",
                        "navy-900": "#0f172a",
                        "navy-800": "#1e293b",
                        "glass-white": "rgba(255, 255, 255, 0.03)",
                        "glass-border": "rgba(255, 255, 255, 0.08)",
                    },
                    fontFamily: {
                        "sans": ["'Plus Jakarta Sans'", "sans-serif"]
                    },
                },
            },
        }
    </script>
    <style type="text/tailwindcss">
        @layer base {
            body {
                @apply bg-navy-950 text-slate-100 antialiased selection:bg-primary/30;
                font-family: 'Plus Jakarta Sans', sans-serif;
            }
        }
        .glass-card {
            background: rgba(30, 41, 59, 0.4);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.08);
        }
        .status-glow-red {
            box-shadow: 0 0 12px rgba(239, 68, 68, 0.3);
        }
        .status-glow-emerald {
            box-shadow: 0 0 12px rgba(16, 185, 129, 0.3);
        }
        .status-glow-blue {
            box-shadow: 0 0 12px rgba(59, 130, 246, 0.3);
        }
        .hide-scrollbar::-webkit-scrollbar {
            display: none;
        }
        .hide-scrollbar {
            -ms-overflow-style: none;
            scrollbar-width: none;
        }
    </style>
</head>
<body class="min-h-screen">
    <div id="app"></div>

    <script>
        // GLOBAL STATE
        let currentView = 'dashboard';
        let allProducts = [];
        let roleUser = '';
        let appDiv = null;
        let api = {};

        // API HELPER (Global scope)
        api = {
            async get(url) {
                const res = await fetch(url, {
                    headers: {'Authorization': localStorage.getItem('currentToken')}
                });
                if (!res.ok) throw new Error('API error');
                return res.json();
            },
            async post(url, data) {
                const res = await fetch(url, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': localStorage.getItem('currentToken')
                    },
                    body: JSON.stringify(data)
                });
                if (!res.ok) throw new Error('API error');
                return res.json();
            },
            async put(url, data) {
                const res = await fetch(url, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': localStorage.getItem('currentToken')
                    },
                    body: JSON.stringify(data)
                });
                if (!res.ok) throw new Error('API error');
                return res.json();
            },
            async delete(url) {
                const res = await fetch(url, {
                    method: 'DELETE',
                    headers: {'Authorization': localStorage.getItem('currentToken')}
                });
                if (!res.ok) throw new Error('API error');
                return res.json();
            }
        };

        // GLOBAL FUNCTIONS
        function renderUI() {
            let html = `
            <header class="sticky top-0 z-50 bg-navy-950/80 backdrop-blur-xl border-b border-white/5">
                <div class="flex items-center justify-between px-5 h-16">
                    <div class="flex items-center gap-3">
                        <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/20 text-primary border border-primary/20">
                            <span class="material-symbols-outlined text-[22px]">inventory_2</span>
                        </div>
                        <div>
                            <h1 class="text-base font-extrabold tracking-tight leading-none text-white">Inventory</h1>
                            <p class="text-[11px] font-medium text-slate-400 mt-0.5">CHRIS EFFECT</p>
                        </div>
                    </div>
                    <div class="flex items-center gap-3">
                        <button onclick="currentView='settings'; renderUI()" class="relative flex h-10 w-10 items-center justify-center rounded-full text-slate-400 hover:bg-white/5 transition-all">
                            <span class="material-symbols-outlined">settings</span>
                        </button>
                        <button onclick="logout()" class="relative flex h-10 w-10 items-center justify-center rounded-full text-slate-400 hover:bg-white/5 transition-all">
                            <span class="material-symbols-outlined">logout</span>
                        </button>
                        <div class="h-9 w-9 rounded-full ring-2 ring-white/10 flex items-center justify-center bg-primary/20 text-primary text-sm font-bold">
                            ${localStorage.getItem('currentUser').charAt(0).toUpperCase()}
                        </div>
                    </div>
                </div>
            </header>
            `;

            if (currentView === 'dashboard') {
                html += getDashboardHTML();
            } else if (currentView === 'gallery') {
                html += getProductGalleryHTML();
            } else if (currentView === 'stock') {
                html += getStockHTML();
            } else if (currentView === 'sales') {
                html += getSalesHTML();
            } else if (currentView === 'settings') {
                html += getSettingsHTML();
            } else if (currentView === 'add') {
                html += getAddInventoryMenuHTML();
            } else if (currentView === 'addManual') {
                html += getAddManualHTML();
            }

            html += `
            <button onclick="currentView='add'; renderUI()" class="fixed right-6 bottom-28 h-14 w-14 rounded-2xl bg-primary text-white shadow-2xl shadow-primary/40 flex items-center justify-center hover:scale-105 active:scale-95 transition-all z-[60] border border-white/20">
                <span class="material-symbols-outlined text-[28px]">add</span>
            </button>
            <nav class="fixed bottom-0 left-0 right-0 bg-navy-950/90 backdrop-blur-2xl border-t border-white/5 px-6 pt-3 pb-8 z-50">
                <div class="flex items-center justify-center gap-8 max-w-md mx-auto">
                    <a onclick="currentView='dashboard'; renderUI()" class="flex flex-col items-center gap-1.5 ${currentView === 'dashboard' ? 'text-primary' : 'text-slate-500 hover:text-slate-300'} transition-colors cursor-pointer">
                        <span class="material-symbols-outlined text-[24px]">grid_view</span>
                        <span class="text-[9px] font-extrabold uppercase tracking-widest">Dashboard</span>
                    </a>
                    <a onclick="currentView='gallery'; renderUI()" class="flex flex-col items-center gap-1.5 ${currentView === 'gallery' ? 'text-primary' : 'text-slate-500 hover:text-slate-300'} transition-colors cursor-pointer">
                        <span class="material-symbols-outlined text-[24px]">collections</span>
                        <span class="text-[9px] font-extrabold uppercase tracking-widest">Products</span>
                    </a>
                    <a onclick="currentView='sales'; renderUI()" class="flex flex-col items-center gap-1.5 ${currentView === 'sales' ? 'text-primary' : 'text-slate-500 hover:text-slate-300'} transition-colors cursor-pointer">
                        <span class="material-symbols-outlined text-[24px]">point_of_sale</span>
                        <span class="text-[9px] font-extrabold uppercase tracking-widest">Sales</span>
                    </a>
                    <a onclick="alert('Analytics - Coming Soon')" class="flex flex-col items-center gap-1.5 text-slate-500 hover:text-slate-300 transition-colors cursor-pointer">
                        <span class="material-symbols-outlined text-[24px]">analytics</span>
                        <span class="text-[9px] font-extrabold uppercase tracking-widest">Stats</span>
                    </a>
                </div>
            </nav>
            `;

            appDiv.innerHTML = html;
            if (currentView === 'dashboard') {
                loadDashboard();
            } else if (currentView === 'gallery') {
                loadProductGallery();
            } else if (currentView === 'stock') {
                loadStock();
            } else if (currentView === 'sales') {
                loadStock();  // Load products for dropdown
                loadSales();  // Load sales history
                // Set up event listeners for sales form
                setTimeout(() => {
                    const select = document.getElementById('saleProductSelect');
                    const qtyInput = document.getElementById('saleQtyInput');
                    if (select) select.addEventListener('change', updateSalePriceDisplay);
                    if (qtyInput) qtyInput.addEventListener('input', updateSalePriceDisplay);
                }, 100);
            } else if (currentView === 'settings') {
                if (roleUser === 'admin') {
                    loadAdminUsers();
                }
            } else if (currentView === 'addManual') {
                setTimeout(() => {
                    const form = document.getElementById('addProductForm');
                    if (form) {
                        form.addEventListener('submit', async (e) => {
                            e.preventDefault();
                            const sku = document.getElementById('formSku').value.trim();
                            const name = document.getElementById('formName').value.trim();
                            const category = document.getElementById('formCategory').value.trim() || 'Uncategorized';
                            const quantity = parseInt(document.getElementById('formQuantity').value);
                            const price = parseFloat(document.getElementById('formPrice').value);
                            const image = document.getElementById('formImagePath').value || null;
                            
                            if (!sku || !name) {
                                alert('SKU and Name are required');
                                return;
                            }
                            
                            try {
                                await api.post('/api/inventory', {sku, name, category, quantity, price, image});
                                alert('Product added successfully!');
                                currentView = 'stock';
                                renderUI();
                            } catch (error) {
                                alert('Error adding product: ' + error.message);
                            }
                        });
                    }
                }, 100);
            }
        }

        function getProductGalleryHTML() {
            return `
            <main class="pb-32 px-5 pt-6">
                <div class="mb-6">
                    <div class="flex items-center justify-between mb-4">
                        <h2 class="text-[24px] font-extrabold text-white">Product Gallery</h2>
                        <div class="flex gap-2">
                            <input type="text" id="gallerySearch" placeholder="Search by name, SKU..." class="px-4 py-2 bg-navy-800/50 border border-white/10 rounded-lg text-white placeholder:text-slate-500 focus:outline-none focus:border-primary/50 text-sm" onkeyup="applyGalleryFilters()"/>
                        </div>
                    </div>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
                    <!-- Filters Sidebar -->
                    <div class="md:col-span-1">
                        <div class="glass-card rounded-2xl p-4 sticky top-20">
                            <h3 class="font-bold text-white mb-4">Filters</h3>
                            
                            <div class="mb-4">
                                <label class="text-slate-400 text-xs font-semibold uppercase mb-2 block">Category</label>
                                <select id="galleryCategory" class="w-full bg-navy-800/50 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none" onchange="applyGalleryFilters()">
                                    <option value="">All Categories</option>
                                </select>
                            </div>
                            
                            <div class="mb-4">
                                <label class="text-slate-400 text-xs font-semibold uppercase mb-2 block">Stock Status</label>
                                <select id="galleryStatus" class="w-full bg-navy-800/50 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none" onchange="applyGalleryFilters()">
                                    <option value="">All Items</option>
                                    <option value="In Stock">In Stock</option>
                                    <option value="Low Stock">Low Stock</option>
                                    <option value="Out of Stock">Out of Stock</option>
                                </select>
                            </div>

                            <div class="mb-4">
                                <label class="text-slate-400 text-xs font-semibold uppercase mb-3 block">Price Range</label>
                                <div class="space-y-2">
                                    <input type="number" id="minPrice" placeholder="Min" class="w-full bg-navy-800/50 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none" onchange="applyGalleryFilters()"/>
                                    <input type="number" id="maxPrice" placeholder="Max" class="w-full bg-navy-800/50 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none" onchange="applyGalleryFilters()"/>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Products Grid -->
                    <div class="md:col-span-3">
                        <div id="galleryProductsContainer" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                            <div class="col-span-full text-center py-12">
                                <p class="text-slate-400">Loading products...</p>
                            </div>
                        </div>

                        <!-- Pagination -->
                        <div id="galleryPagination" class="flex items-center justify-center gap-2 mt-8 mb-6"></div>
                    </div>
                </div>

                <!-- Edit Product Modal -->
                <div id="editProductModal" class="fixed inset-0 bg-black/50 backdrop-blur-sm hidden z-[100] flex items-center justify-center p-4">
                    <div class="glass-card rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                        <div class="sticky top-0 bg-navy-950/95 border-b border-white/10 p-6 flex items-center justify-between">
                            <h2 class="text-2xl font-bold text-white">Edit Product</h2>
                            <button onclick="closeEditModal()" class="text-slate-400 hover:text-white">
                                <span class="material-symbols-outlined text-[28px]">close</span>
                            </button>
                        </div>
                        <div class="p-6 space-y-4">
                            <div>
                                <label class="text-slate-400 text-sm font-semibold mb-2 block">Product Image</label>
                                <div id="editImagePreview" class="mb-3"></div>
                                <div class="flex items-center gap-3">
                                    <input type="file" id="editProductImage" accept="image/jpeg,image/png,image/gif,image/webp,image/bmp" class="flex-1 bg-navy-800/50 border border-white/10 rounded-lg px-4 py-2 text-slate-400 file:bg-blue-600 file:text-white file:border-0 file:rounded file:px-3 file:py-1 file:cursor-pointer hover:border-white/20 transition"/>
                                    <button type="button" onclick="uploadEditProductImage()" class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium whitespace-nowrap">Upload</button>
                                </div>
                                <button type="button" onclick="removeEditProductImage()" class="mt-2 text-sm text-red-400 hover:text-red-300">Remove Image</button>
                            </div>
                            <div>
                                <label class="text-slate-400 text-sm font-semibold mb-2 block">Product Name</label>
                                <input type="text" id="editProductName" class="w-full bg-navy-800/50 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-primary/50"/>
                            </div>
                            <div class="grid grid-cols-2 gap-4">
                                <div>
                                    <label class="text-slate-400 text-sm font-semibold mb-2 block">SKU</label>
                                    <input type="text" id="editProductSku" disabled class="w-full bg-navy-800/50 border border-white/10 rounded-lg px-4 py-2 text-slate-500 cursor-not-allowed"/>
                                </div>
                                <div>
                                    <label class="text-slate-400 text-sm font-semibold mb-2 block">Category</label>
                                    <input type="text" id="editProductCategory" class="w-full bg-navy-800/50 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-primary/50"/>
                                </div>
                            </div>
                            <div class="grid grid-cols-2 gap-4">
                                <div>
                                    <label class="text-slate-400 text-sm font-semibold mb-2 block">Quantity</label>
                                    <input type="number" id="editProductQty" min="0" class="w-full bg-navy-800/50 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-primary/50"/>
                                </div>
                                <div>
                                    <label class="text-slate-400 text-sm font-semibold mb-2 block">Price</label>
                                    <input type="number" id="editProductPrice" min="0" step="0.01" class="w-full bg-navy-800/50 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-primary/50"/>
                                </div>
                            </div>
                            <div id="editProductStatusMessage" class="text-slate-400 text-sm"></div>
                            <div class="flex gap-3 pt-4">
                                <button onclick="saveProductEdits()" class="flex-1 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-medium">Save Changes</button>
                                <button onclick="closeEditModal()" class="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg font-medium">Cancel</button>
                            </div>
                        </div>
                    </div>
                </div>
            </main>
            `;
        }

        function getDashboardHTML() {
            return `
            <main class="pb-32">
                <div class="px-5 pt-6 pb-2">
                    <div class="relative">
                        <span class="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 text-[20px]">search</span>
                        <input id="searchInput" class="w-full bg-navy-900/50 border-white/10 rounded-2xl py-3.5 pl-11 pr-4 text-[13px] text-white placeholder:text-slate-500 focus:ring-primary/50 focus:border-primary/50 transition-all outline-none" placeholder="Search products, SKUs, suppliers..." type="text" onkeyup="handleSearch()"/>
                    </div>
                </div>
                <section class="mt-4" id="statsSection"></section>
                <section class="mt-10 px-5" id="analyticsSection"></section>
                <section class="mt-10 px-5" id="activitiesSection"></section>
            </main>
            `;
        }

        function getStockHTML() {
            return `
            <main class="pb-32 px-5 pt-6">
                <div class="flex items-center justify-between mb-6">
                    <h2 class="text-[20px] font-extrabold text-white">Stock Management</h2>
                    <div class="flex gap-2">
                        <button onclick="exportCSV()" class="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg text-sm font-medium">Export</button>
                        <button onclick="importCSV()" class="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg text-sm font-medium">Import</button>
                    </div>
                </div>
                <div class="glass-card rounded-2xl overflow-x-auto">
                    <table class="w-full text-sm">
                        <thead class="bg-navy-800/50 border-b border-white/5">
                            <tr>
                                <th class="px-4 py-3 text-left text-slate-300 font-semibold">Image</th>
                                <th class="px-6 py-3 text-left text-slate-300 font-semibold">SKU</th>
                                <th class="px-6 py-3 text-left text-slate-300 font-semibold">Name</th>
                                <th class="px-6 py-3 text-center text-slate-300 font-semibold">Qty</th>
                                <th class="px-6 py-3 text-right text-slate-300 font-semibold">Price</th>
                                <th class="px-6 py-3 text-center text-slate-300 font-semibold">Status</th>
                                <th class="px-6 py-3 text-center text-slate-300 font-semibold">Actions</th>
                            </tr>
                        </thead>
                        <tbody id=\"stockTable\"></tbody>
                    </table>
                </div>
            </main>
            `;
        }

        function getSettingsHTML() {
            return `
            <main class="pb-32 px-5 pt-6 max-w-4xl mx-auto">
                <h2 class="text-[20px] font-extrabold text-white mb-6">Settings</h2>
                
                <div class="glass-card rounded-2xl p-6 mb-6">
                    <h3 class="text-lg font-bold text-white mb-4">User Profile</h3>
                    <div class="mb-6">
                        <p class="text-slate-400">Username: <span class="text-white font-semibold">${localStorage.getItem('currentUser')}</span></p>
                        <p class="text-slate-400">Role: <span class="text-white font-semibold">${localStorage.getItem('currentRole').toUpperCase()}</span></p>
                    </div>
                    <button onclick="logout()" class="px-6 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium">Logout</button>
                </div>
                
                ${localStorage.getItem('currentRole') === 'admin' ? `
                <div class="glass-card rounded-2xl p-6">
                    <h3 class="text-lg font-bold text-white mb-4">Admin Users & Privileges</h3>
                    <div id="adminUsersList" class="space-y-3">
                        <p class="text-slate-400 text-sm">Loading admin users...</p>
                    </div>
                </div>
                ` : ''}
            </main>
            `;
        }

        function getAddInventoryMenuHTML() {
            return `
            <main class="pb-32 px-5 pt-10 max-w-2xl mx-auto">
                <div class="mb-10">
                    <h2 class="text-3xl font-extrabold text-white">Add to Inventory</h2>
                    <p class="text-slate-400 mt-2">Select how you would like to add items to your stock levels today.</p>
                </div>
                <div class="space-y-4">
                    <div onclick="alert('Barcode scanner integration coming soon!')" class="glass-card p-6 rounded-3xl flex items-center justify-between cursor-pointer border border-white/10 hover:border-blue-500/50 transition-all hover:bg-blue-500/5">
                        <div class="flex-1">
                            <div class="flex items-center gap-2 mb-2">
                                <span class="font-bold text-lg text-white">Scan Barcode</span>
                                <span class="bg-blue-500/20 text-blue-400 text-[10px] px-2 py-0.5 rounded font-black uppercase">Fastest</span>
                            </div>
                            <p class="text-xs text-slate-400 mb-3">Use your camera to identify and add products quickly.</p>
                            <p class="text-blue-400 text-xs font-bold">Open Scanner →</p>
                        </div>
                        <div class="h-16 w-16 rounded-2xl bg-blue-500/10 flex items-center justify-center text-blue-400 flex-shrink-0 ml-4"><span class="material-symbols-outlined text-4xl">barcode_scanner</span></div>
                    </div>
                    <div onclick="currentView='addManual'; renderUI()" class="glass-card p-6 rounded-3xl flex items-center justify-between cursor-pointer border border-white/10 hover:border-emerald-500/50 transition-all hover:bg-emerald-500/5">
                        <div class="flex-1">
                            <span class="font-bold text-lg text-white block mb-2">Manual Entry</span>
                            <p class="text-xs text-slate-400 mb-3">Type in product details via a detailed form.</p>
                            <p class="text-emerald-400 text-xs font-bold">Start Form <span class="material-symbols-outlined text-sm" style="vertical-align: middle;">edit_note</span></p>
                        </div>
                        <div class="h-16 w-16 rounded-2xl bg-emerald-500/10 flex items-center justify-center text-emerald-400 flex-shrink-0 ml-4"><span class="material-symbols-outlined text-4xl">add_box</span></div>
                    </div>
                    <div onclick="importCSV()" class="glass-card p-6 rounded-3xl flex items-center justify-between cursor-pointer border border-white/10 hover:border-orange-500/50 transition-all hover:bg-orange-500/5">
                        <div class="flex-1">
                            <span class="font-bold text-lg text-white block mb-2">Bulk Import</span>
                            <p class="text-xs text-slate-400 mb-3">Upload CSV or Excel spreadsheets with multiple items.</p>
                            <p class="text-orange-400 text-xs font-bold">Upload File <span class="material-symbols-outlined text-sm" style="vertical-align: middle;">upload_file</span></p>
                        </div>
                        <div class="h-16 w-16 rounded-2xl bg-orange-500/10 flex items-center justify-center text-orange-400 flex-shrink-0 ml-4"><span class="material-symbols-outlined text-4xl">description</span></div>
                    </div>
                </div>
            </main>
            `;
        }

        function getAddManualHTML() {
            return `
            <main class="pb-32 px-5 pt-6 max-w-2xl mx-auto">
                <div class="mb-6 flex items-center gap-3">
                    <button onclick="currentView='add'; renderUI()" class="flex items-center gap-2 text-slate-400 hover:text-slate-300 transition">
                        <span class="material-symbols-outlined">arrow_back</span>
                        <span class="text-sm">Back</span>
                    </button>
                    <h2 class="text-[20px] font-extrabold text-white">Manual Entry</h2>
                </div>
                <div class="glass-card rounded-2xl p-6">
                    <form id="addProductForm" class="space-y-4">
                        <div>
                            <label class="text-slate-400 text-sm font-semibold">SKU *</label>
                            <input type="text" id="formSku" placeholder="e.g., SKU-12345" required class="w-full mt-2 bg-navy-800/50 border border-white/10 rounded-lg px-4 py-2 text-white placeholder:text-slate-500 focus:outline-none focus:border-primary/50"/>
                        </div>
                        <div>
                            <label class="text-slate-400 text-sm font-semibold">Product Name *</label>
                            <input type="text" id="formName" placeholder="e.g., Laptop" required class="w-full mt-2 bg-navy-800/50 border border-white/10 rounded-lg px-4 py-2 text-white placeholder:text-slate-500 focus:outline-none focus:border-primary/50"/>
                        </div>
                        <div>
                            <label class="text-slate-400 text-sm font-semibold">Category</label>
                            <input type="text" id="formCategory" placeholder="e.g., Electronics" class="w-full mt-2 bg-navy-800/50 border border-white/10 rounded-lg px-4 py-2 text-white placeholder:text-slate-500 focus:outline-none focus:border-primary/50"/>
                        </div>
                        <div class="grid grid-cols-2 gap-4">
                            <div>
                                <label class="text-slate-400 text-sm font-semibold">Quantity *</label>
                                <input type="number" id="formQuantity" placeholder="0" value="1" min="0" required class="w-full mt-2 bg-navy-800/50 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-primary/50"/>
                            </div>
                            <div>
                                <label class="text-slate-400 text-sm font-semibold">Price *</label>
                                <input type="number" id="formPrice" placeholder="0.00" value="0" min="0" step="0.01" required class="w-full mt-2 bg-navy-800/50 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-primary/50"/>
                            </div>
                        </div>
                        <div>
                            <label class="text-slate-400 text-sm font-semibold">Product Image</label>
                            <div class="mt-2 flex items-center gap-4">
                                <input type="file" id="formImage" accept="image/jpeg,image/png,image/gif,image/webp,image/bmp" class="flex-1 bg-navy-800/50 border border-white/10 rounded-lg px-4 py-2 text-slate-400 file:bg-blue-600 file:text-white file:border-0 file:rounded file:px-3 file:py-1 file:cursor-pointer hover:border-white/20 transition"/>
                                <button type="button" onclick="uploadProductImage()" class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium whitespace-nowrap">Upload</button>
                            </div>
                            <div id="imagePreview" class="mt-4"></div>
                            <input type="hidden" id="formImagePath" value=""/>
                        </div>
                        <button type="submit" class="w-full mt-6 px-6 py-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-semibold transition">Add Product</button>
                    </form>
                </div>
            </main>
            `;
        }

        function getSalesHTML() {
            return `
            <main class="pb-32 px-5 pt-6 max-w-4xl mx-auto">
                <h2 class="text-[20px] font-extrabold text-white mb-6">Record Sale</h2>
                
                <div class="glass-card rounded-2xl p-6 mb-8">
                    <h3 class="text-lg font-bold text-white mb-4">New Sale</h3>
                    <div class="space-y-4">
                        <div>
                            <label class="text-slate-400 text-sm font-semibold">Select Product</label>
                            <select id="saleProductSelect" class="w-full mt-2 bg-navy-800/50 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-primary">
                                <option value="">Choose a product...</option>
                                ${allProducts.map(p => `<option value="${p.id}" data-stock="${p.quantity}" data-price="${p.price}">${p.name} (SKU: ${p.sku}) - Stock: ${p.quantity}</option>`).join('')}
                            </select>
                        </div>
                        <div class="grid grid-cols-2 gap-4">
                            <div>
                                <label class="text-slate-400 text-sm font-semibold">Quantity Sold</label>
                                <input type="number" id="saleQtyInput" min="1" value="1" class="w-full mt-2 bg-navy-800/50 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-primary"/>
                            </div>
                            <div>
                                <label class="text-slate-400 text-sm font-semibold">Unit Price</label>
                                <input type="text" id="salePriceDisplay" readonly class="w-full mt-2 bg-navy-800/50 border border-white/10 rounded-lg px-4 py-2 text-slate-400 cursor-not-allowed"/>
                            </div>
                        </div>
                        <div class="pt-4 border-t border-white/10">
                            <p class="text-slate-400 text-sm mb-2">Total Amount</p>
                            <p class="text-3xl font-extrabold text-primary">$<span id="saleTotalDisplay">0.00</span></p>
                        </div>
                        <button onclick="submitSale()" class="w-full mt-4 px-6 py-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-semibold transition">Record Sale</button>
                    </div>
                </div>

                <h2 class="text-[20px] font-extrabold text-white mb-6 mt-8">Sales History</h2>
                <div class="glass-card rounded-2xl overflow-hidden">
                    <table class="w-full text-sm">
                        <thead class="border-b border-white/10 bg-navy-800/20">
                            <tr>
                                <th class="px-6 py-3 text-left text-slate-400 font-semibold">Product</th>
                                <th class="px-6 py-3 text-center text-slate-400 font-semibold">Qty</th>
                                <th class="px-6 py-3 text-right text-slate-400 font-semibold">Price</th>
                                <th class="px-6 py-3 text-right text-slate-400 font-semibold">Total</th>
                                <th class="px-6 py-3 text-slate-400 font-semibold">Date</th>
                            </tr>
                        </thead>
                        <tbody id="salesTableBody"></tbody>
                    </table>
                </div>
            </main>
            `;
        }

        let galleryCurrentPage = 1;
        let galleryFilters = {};

        async function loadProductGallery(page = 1) {
            try {
                galleryCurrentPage = page;
                const search = document.getElementById('gallerySearch')?.value || '';
                const category = document.getElementById('galleryCategory')?.value || '';
                const status = document.getElementById('galleryStatus')?.value || '';
                const minPrice = document.getElementById('minPrice')?.value || '';
                const maxPrice = document.getElementById('maxPrice')?.value || '';

                galleryFilters = {search, category, status, minPrice, maxPrice};

                let url = '/api/inventory?page=' + page + '&limit=12';
                if (search) url += '&search=' + encodeURIComponent(search);
                if (category) url += '&category=' + encodeURIComponent(category);
                if (status) url += '&status=' + encodeURIComponent(status);
                if (minPrice) url += '&min_price=' + minPrice;
                if (maxPrice) url += '&max_price=' + maxPrice;

                const response = await api.get(url);
                const {items, total, pages, page: currentPage} = response;

                // Render products
                const container = document.getElementById('galleryProductsContainer');
                if (items.length === 0) {
                    container.innerHTML = '<div class="col-span-full text-center py-12"><p class="text-slate-400">No products found</p></div>';
                } else {
                    container.innerHTML = items.map(p => `
                        <div class="glass-card rounded-2xl overflow-hidden hover:border-primary/50 transition-all group border border-white/10 flex flex-col">
                            <div class="relative h-48 bg-navy-800/50 overflow-hidden">
                                ${p.image ? `
                                    <img src="${p.image}" alt="${p.name}" class="w-full h-full object-cover group-hover:scale-105 transition-transform"/>
                                ` : `
                                    <div class="w-full h-full flex items-center justify-center bg-gradient-to-br from-navy-800 to-navy-900 text-slate-600">
                                        <span class="material-symbols-outlined text-6xl">image_not_supported</span>
                                    </div>
                                `}
                                <div class="absolute top-3 right-3">
                                    <span class="px-3 py-1 rounded-full text-xs font-bold ${p.status === 'In Stock' ? 'bg-emerald-500/20 text-emerald-400' : p.status === 'Low Stock' ? 'bg-orange-500/20 text-orange-400' : 'bg-red-500/20 text-red-400'}">
                                        ${p.status}
                                    </span>
                                </div>
                            </div>
                            <div class="p-4 flex-1 flex flex-col">
                                <p class="text-xs text-slate-500 font-semibold mb-1">${p.sku || 'NO SKU'}</p>
                                <h3 class="text-white font-bold mb-1 line-clamp-2">${p.name}</h3>
                                <p class="text-slate-400 text-xs mb-3">${p.category || 'Uncategorized'}</p>
                                <div class="flex items-center justify-between mb-4 flex-1">
                                    <p class="text-primary font-bold text-lg">$${p.price.toFixed(2)}</p>
                                    <p class="text-slate-400 text-xs">${p.quantity} in stock</p>
                                </div>
                                <div class="flex gap-2">
                                    <button onclick="openEditModal(${p.id}, '${p.name}', '${p.sku}', '${p.category}', ${p.quantity}, ${p.price}, '${p.image || ''}')" class="flex-1 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-1">
                                        <span class="material-symbols-outlined text-[18px]">edit</span> Edit
                                    </button>
                                    ${roleUser === 'admin' ? `<button onclick="deleteGalleryProduct(${p.id})" class="flex-1 px-3 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-1">
                                        <span class="material-symbols-outlined text-[18px]">delete</span> Delete
                                    </button>` : ''}
                                </div>
                            </div>
                        </div>
                    `).join('');
                }

                // Render pagination
                const paginationDiv = document.getElementById('galleryPagination');
                let paginationHTML = '<div class="flex items-center gap-2">';
                if (currentPage > 1) {
                    paginationHTML += `<button onclick="loadProductGallery(1)" class="px-3 py-2 rounded bg-navy-800 text-white hover:bg-navy-700">First</button>`;
                    paginationHTML += `<button onclick="loadProductGallery(${currentPage - 1})" class="px-3 py-2 rounded bg-navy-800 text-white hover:bg-navy-700">Prev</button>`;
                }

                for (let i = Math.max(1, currentPage - 2); i <= Math.min(pages, currentPage + 2); i++) {
                    paginationHTML += `<button onclick="loadProductGallery(${i})" class="px-3 py-2 rounded ${i === currentPage ? 'bg-primary text-white' : 'bg-navy-800 text-white hover:bg-navy-700'}">${i}</button>`;
                }

                if (currentPage < pages) {
                    paginationHTML += `<button onclick="loadProductGallery(${currentPage + 1})" class="px-3 py-2 rounded bg-navy-800 text-white hover:bg-navy-700">Next</button>`;
                    paginationHTML += `<button onclick="loadProductGallery(${pages})" class="px-3 py-2 rounded bg-navy-800 text-white hover:bg-navy-700">Last</button>`;
                }
                paginationHTML += `<span class="text-slate-400 text-sm ml-4">Page ${currentPage} of ${pages}</span></div>`;
                paginationDiv.innerHTML = paginationHTML;

                // Load categories if first load
                if (document.getElementById('galleryCategory').options.length === 1) {
                    const categories = await api.get('/api/categories');
                    const catSelect = document.getElementById('galleryCategory');
                    categories.forEach(cat => {
                        const option = document.createElement('option');
                        option.value = cat;
                        option.textContent = cat;
                        catSelect.appendChild(option);
                    });
                }
            } catch (error) {
                console.error('Error loading products:', error);
            }
        }

        function applyGalleryFilters() {
            loadProductGallery(1);
        }

        function openEditModal(id, name, sku, category, quantity, price, image) {
            const modal = document.getElementById('editProductModal');
            document.getElementById('editProductName').value = name;
            document.getElementById('editProductSku').value = sku;
            document.getElementById('editProductCategory').value = category;
            document.getElementById('editProductQty').value = quantity;
            document.getElementById('editProductPrice').value = price;
            document.getElementById('editProductStatusMessage').textContent = '';
            document.getElementById('editProductImage').value = '';
            modal.dataset.productId = id;
            modal.dataset.currentImage = image || '';
            displayEditProductImage(image);
            modal.classList.remove('hidden');
        }

        function closeEditModal() {
            const modal = document.getElementById('editProductModal');
            modal.classList.add('hidden');
            delete modal.dataset.productId;
        }

        function displayEditProductImage(imagePath) {
            const preview = document.getElementById('editImagePreview');
            if (!imagePath) {
                preview.innerHTML = '<p class="text-slate-500 text-sm">No image</p>';
                return;
            }
            preview.innerHTML = `
                <img src="${imagePath}" alt="Product" class="h-32 w-full rounded-lg object-cover border border-white/10"/>
            `;
        }

        async function uploadEditProductImage() {
            const fileInput = document.getElementById('editProductImage');
            if (!fileInput.files.length) {
                alert('Please select an image file');
                return;
            }

            const file = fileInput.files[0];
            const formData = new FormData();
            formData.append('file', file);

            try {
                const res = await fetch('/api/upload-image', {
                    method: 'POST',
                    headers: {'Authorization': localStorage.getItem('currentToken')},
                    body: formData
                });

                const data = await res.json();
                if (data.success) {
                    const modal = document.getElementById('editProductModal');
                    modal.dataset.currentImage = data.path;
                    displayEditProductImage(data.path);
                    fileInput.value = '';
                    alert('Image uploaded successfully!');
                } else {
                    alert('Upload failed: ' + data.error);
                }
            } catch (error) {
                alert('Upload error: ' + error.message);
            }
        }

        function removeEditProductImage() {
            const modal = document.getElementById('editProductModal');
            modal.dataset.currentImage = '';
            displayEditProductImage('');
            document.getElementById('editProductImage').value = '';
        }

        async function saveProductEdits() {
            const modal = document.getElementById('editProductModal');
            const productId = parseInt(modal.dataset.productId);
            const name = document.getElementById('editProductName').value.trim();
            const category = document.getElementById('editProductCategory').value.trim() || 'Uncategorized';
            const quantity = parseInt(document.getElementById('editProductQty').value);
            const price = parseFloat(document.getElementById('editProductPrice').value);
            const image = modal.dataset.currentImage || null;
            const statusDiv = document.getElementById('editProductStatusMessage');

            if (!name) {
                statusDiv.textContent = 'Product name is required';
                return;
            }

            if (isNaN(quantity) || quantity < 0) {
                statusDiv.textContent = 'Quantity must be a non-negative number';
                return;
            }

            if (isNaN(price) || price < 0) {
                statusDiv.textContent = 'Price must be a non-negative number';
                return;
            }

            try {
                await api.put(`/api/inventory/${productId}`, {
                    name,
                    category,
                    quantity,
                    price,
                    image
                });
                statusDiv.textContent = 'Changes saved successfully!';
                statusDiv.classList.remove('text-slate-400');
                statusDiv.classList.add('text-emerald-400');
                setTimeout(() => {
                    closeEditModal();
                    loadProductGallery(galleryCurrentPage);
                }, 1000);
            } catch (error) {
                statusDiv.textContent = 'Error saving changes: ' + error.message;
                statusDiv.classList.remove('text-slate-400');
                statusDiv.classList.add('text-red-400');
            }
        }

        async function deleteGalleryProduct(id) {
            if (!confirm('Are you sure you want to delete this product?')) return;

            try {
                await api.delete(`/api/inventory/${id}`);
                alert('Product deleted successfully!');
                loadProductGallery(galleryCurrentPage);
            } catch (error) {
                alert('Error deleting product: ' + error.message);
            }
        }

        async function loadDashboard() {
            try {
                const dashboard = await api.get('/api/dashboard');
                const section = document.getElementById('statsSection');
                if (!section) return;

                section.innerHTML = `<div class="flex gap-4 px-5 overflow-x-auto hide-scrollbar snap-x">
                    <div class="flex-shrink-0 w-[180px] snap-start rounded-2xl p-5 bg-gradient-to-br from-primary to-blue-700 text-white shadow-lg shadow-primary/20">
                        <p class="text-[10px] font-extrabold opacity-70 uppercase tracking-[0.1em]">Total Items</p>
                        <p class="text-3xl font-extrabold mt-1">${dashboard.total_products}</p>
                        <div class="mt-4 flex items-center text-[11px] font-bold bg-white/20 w-fit px-2 py-1 rounded-lg">
                            <span class="material-symbols-outlined text-[14px] mr-1">inventory_2</span> ${dashboard.total_quantity}
                        </div>
                    </div>
                    <div class="flex-shrink-0 w-[160px] snap-start rounded-2xl p-5 glass-card">
                        <div class="flex justify-between items-start mb-4">
                            <div class="h-8 w-8 rounded-lg bg-red-500/10 flex items-center justify-center text-red-500">
                                <span class="material-symbols-outlined text-[18px]">warning</span>
                            </div>
                        </div>
                        <p class="text-[10px] font-bold text-slate-500 uppercase">Low Stock</p>
                        <p class="text-2xl font-extrabold mt-1 text-white">${dashboard.low_stock}</p>
                    </div>
                    <div class="flex-shrink-0 w-[160px] snap-start rounded-2xl p-5 glass-card">
                        <div class="flex justify-between items-start mb-4">
                            <div class="h-8 w-8 rounded-lg bg-orange-500/10 flex items-center justify-center text-orange-500">
                                <span class="material-symbols-outlined text-[18px]">priority_high</span>
                            </div>
                        </div>
                        <p class="text-[10px] font-bold text-slate-500 uppercase">Out of Stock</p>
                        <p class="text-2xl font-extrabold mt-1 text-white">${dashboard.out_of_stock}</p>
                    </div>
                    <div class="flex-shrink-0 w-[180px] snap-start rounded-2xl p-5 glass-card">
                        <div class="flex justify-between items-start mb-4">
                            <div class="h-8 w-8 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400">
                                <span class="material-symbols-outlined text-[18px]">payments</span>
                            </div>
                        </div>
                        <p class="text-[10px] font-bold text-slate-500 uppercase">Total Value</p>
                        <p class="text-2xl font-extrabold mt-1 text-white">$${dashboard.total_value.toLocaleString()}</p>
                    </div>
                </div>`;
            } catch (error) {
                console.error('Error loading dashboard:', error);
            }
        }

        async function loadStock() {
            try {
                const products = await api.get('/api/inventory');
                allProducts = products;
                const table = document.getElementById('stockTable');
                if (!table) return;

                table.innerHTML = products.map(p => `
                <tr class="border-b border-white/5 hover:bg-navy-800/30 transition">
                    <td class="px-4 py-4">
                        ${p.image ? `<img src="${p.image}" alt="${p.name}" class="h-12 w-12 rounded-lg object-cover border border-white/10 hover:border-primary/50 transition cursor-pointer" onclick="window.open('${p.image}')" title="Click to view full image"/>` : `<div class="h-12 w-12 rounded-lg bg-slate-700 flex items-center justify-center text-slate-500"><span class="material-symbols-outlined text-[20px]">image_not_supported</span></div>`}
                    </td>
                    <td class="px-6 py-4 text-slate-300">${p.sku || '-'}</td>
                    <td class="px-6 py-4 text-slate-300">${p.name}</td>
                    <td class="px-6 py-4 text-center font-semibold">${p.quantity}</td>
                    <td class="px-6 py-4 text-right font-semibold">$${p.price.toFixed(2)}</td>
                    <td class="px-6 py-4 text-center">
                        <span class="px-3 py-1 rounded-full text-xs font-bold ${p.status === 'In Stock' ? 'bg-emerald-500/20 text-emerald-400' : p.status === 'Low Stock' ? 'bg-orange-500/20 text-orange-400' : 'bg-red-500/20 text-red-400'}">
                            ${p.status}
                        </span>
                    </td>
                    <td class="px-6 py-4 text-center">
                        <button onclick="editProduct(${p.id})" class="text-primary hover:opacity-70 transition mr-3">
                            <span class="material-symbols-outlined text-[20px]">edit</span>
                        </button>
                        ${roleUser === 'admin' ? `<button onclick="deleteProduct(${p.id})" class="text-red-500 hover:opacity-70 transition">
                            <span class="material-symbols-outlined text-[20px]">delete</span>
                        </button>` : ''}
                    </td>
                </tr>
                `).join('');
            } catch (error) {
                console.error('Error loading stock:', error);
            }
        }

        function handleSearch() {
            const term = document.getElementById('searchInput')?.value || '';
            if (term.length > 2) {
                api.get(`/api/inventory?search=${encodeURIComponent(term)}`).then(results => {
                    allProducts = results;
                    loadStock();
                }).catch(e => console.error('Search error:', e));
            }
        }

        function showAddProductModal() {
            const sku = prompt('Enter SKU:');
            if (!sku) return;
            const name = prompt('Enter Product Name:');
            if (!name) return;
            const qty = parseInt(prompt('Enter Quantity:'));
            if (isNaN(qty)) return;
            const price = parseFloat(prompt('Enter Price:'));
            if (isNaN(price)) return;

            api.post('/api/inventory', {sku, name, quantity: qty, price}).then(() => {
                alert('Product added!');
                loadStock();
            }).catch(e => alert('Error: ' + e.message));
        }

        function editProduct(id) {
            const p = allProducts.find(x => x.id === id);
            if (!p) return;
            const name = prompt('Edit name:', p.name);
            if (!name) return;
            const qty = parseInt(prompt('Edit quantity:', p.quantity));
            if (isNaN(qty)) return;
            const price = parseFloat(prompt('Edit price:', p.price));
            if (isNaN(price)) return;

            api.put(`/api/inventory/${id}`, {name, quantity: qty, price, category: p.category}).then(() => {
                alert('Product updated!');
                loadStock();
            }).catch(e => alert('Error: ' + e.message));
        }

        async function deleteProduct(id) {
            if (confirm('Delete this product?')) {
                try {
                    await api.delete(`/api/inventory/${id}`);
                    alert('Product deleted!');
                    loadStock();
                } catch (error) {
                    alert('Error: ' + error.message);
                }
            }
        }

        async function exportCSV() {
            try {
                const response = await fetch('/api/export-csv', {
                    headers: {'Authorization': localStorage.getItem('currentToken')}
                });
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'inventory.csv';
                a.click();
            } catch (error) {
                alert('Export failed: ' + error.message);
            }
        }

        function importCSV() {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = '.csv';
            input.onchange = async (e) => {
                const file = e.target.files[0];
                const formData = new FormData();
                formData.append('file', file);
                try {
                    const res = await fetch('/api/import-csv', {
                        method: 'POST',
                        headers: {'Authorization': localStorage.getItem('currentToken')},
                        body: formData
                    });
                    const data = await res.json();
                    alert(`Imported: ${data.imported}, Updated: ${data.updated}, Invalid: ${data.invalid}`);
                    loadStock();
                } catch (error) {
                    alert('Import failed: ' + error.message);
                }
            };
            input.click();
        }

        async function uploadProductImage() {
            const fileInput = document.getElementById('formImage');
            if (!fileInput.files.length) {
                alert('Please select an image file');
                return;
            }
            
            const file = fileInput.files[0];
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                const res = await fetch('/api/upload-image', {
                    method: 'POST',
                    headers: {'Authorization': localStorage.getItem('currentToken')},
                    body: formData
                });
                
                const data = await res.json();
                if (data.success) {
                    document.getElementById('formImagePath').value = data.path;
                    const preview = document.getElementById('imagePreview');
                    preview.innerHTML = `
                        <div class="flex items-center gap-4 p-4 bg-navy-800/30 rounded-lg border border-emerald-500/30">
                            <img src="${data.path}" alt="Preview" class="h-20 w-20 rounded object-cover border border-white/10"/>
                            <div class="flex-1">
                                <p class="text-slate-300 text-sm font-semibold">${data.filename}</p>
                                <p class="text-slate-400 text-xs">${(data.size / 1024).toFixed(1)} KB</p>
                            </div>
                            <button type="button" onclick="document.getElementById('formImagePath').value=''; document.getElementById('imagePreview').innerHTML=''; document.getElementById('formImage').value='';" class="text-red-400 hover:text-red-300">
                                <span class="material-symbols-outlined">close</span>
                            </button>
                        </div>
                    `;
                    alert('Image uploaded successfully!');
                } else {
                    alert('Upload failed: ' + data.error);
                }
            } catch (error) {
                alert('Upload error: ' + error.message);
            }
        }

        function updateSalePriceDisplay() {
            const select = document.getElementById('saleProductSelect');
            const priceDisplay = document.getElementById('salePriceDisplay');
            const totalDisplay = document.getElementById('saleTotalDisplay');
            const qtyInput = document.getElementById('saleQtyInput');
            
            if (!select.value) {
                priceDisplay.value = '';
                totalDisplay.textContent = '0.00';
                return;
            }
            
            const option = select.options[select.selectedIndex];
            const price = parseFloat(option.dataset.price);
            const qty = parseInt(qtyInput.value) || 1;
            
            priceDisplay.value = '$' + price.toFixed(2);
            totalDisplay.textContent = (price * qty).toFixed(2);
        }

        async function submitSale() {
            const select = document.getElementById('saleProductSelect');
            const qtyInput = document.getElementById('saleQtyInput');
            
            if (!select.value) {
                alert('Please select a product');
                return;
            }
            
            const productId = parseInt(select.value);
            const quantity = parseInt(qtyInput.value);
            const stock = parseInt(select.options[select.selectedIndex].dataset.stock);
            
            if (quantity <= 0) {
                alert('Quantity must be greater than 0');
                return;
            }
            
            if (quantity > stock) {
                alert(`Not enough stock! Available: ${stock}`);
                return;
            }
            
            try {
                const result = await api.post('/api/sales', {product_id: productId, quantity});
                alert(`Sale recorded! New stock: ${result.new_quantity}`);
                
                // Reset form
                select.value = '';
                qtyInput.value = '1';
                updateSalePriceDisplay();
                
                // Reload data
                await loadStock();
                await loadSales();
                renderUI();
            } catch (error) {
                alert('Error recording sale: ' + error.message);
            }
        }

        async function loadSales() {
            try {
                const sales = await api.get('/api/sales?limit=50');
                const tbody = document.getElementById('salesTableBody');
                if (!tbody) return;

                tbody.innerHTML = sales.map(s => `
                <tr class="border-b border-white/5 hover:bg-navy-800/30 transition">
                    <td class="px-6 py-4 text-slate-300">${s.name}</td>
                    <td class="px-6 py-4 text-center font-semibold">${s.quantity}</td>
                    <td class="px-6 py-4 text-right font-semibold">$${s.price.toFixed(2)}</td>
                    <td class="px-6 py-4 text-right font-semibold text-emerald-400">$${(s.quantity * s.price).toFixed(2)}</td>
                    <td class="px-6 py-4 text-slate-400 text-sm">${new Date(s.sale_date).toLocaleString()}</td>
                </tr>
                `).join('');
            } catch (error) {
                console.error('Error loading sales:', error);
            }
        }

        async function loadAdminUsers() {
            try {
                const admins = await api.get('/api/admin-users');
                const listDiv = document.getElementById('adminUsersList');
                if (!listDiv) return;

                listDiv.innerHTML = admins.map(admin => `
                <div class="flex items-center justify-between p-4 bg-navy-800/30 rounded-lg border border-white/10 hover:border-blue-500/30 transition">
                    <div class="flex-1">
                        <p class="text-white font-semibold">${admin.username}</p>
                        <div class="flex items-center gap-2 mt-1">
                            <span class="text-xs px-2 py-1 rounded bg-blue-500/20 text-blue-400">${admin.admin_role.replace(/_/g, ' ').toUpperCase()}</span>
                            <span class="text-xs text-slate-400">${admin.permissions}</span>
                        </div>
                    </div>
                    <div class="text-right">
                        <p class="text-xs text-slate-400">Since ${new Date(admin.created_at).toLocaleDateString()}</p>
                    </div>
                </div>
                `).join('');
            } catch (error) {
                console.error('Error loading admin users:', error);
            }
        }

        function logout() {
            localStorage.clear();
            location.reload();
        }

        // AUTHENTICATION CHECK AND INITIALIZATION
        const currentUser = localStorage.getItem('currentUser');
        const currentToken = localStorage.getItem('currentToken');
        
        if (!currentUser || !currentToken) {
            // Show login page
            showLoginPage();
        } else {
            // Initialize main app
            roleUser = localStorage.getItem('currentRole');
            appDiv = document.getElementById('app');
            renderUI();
            loadDashboard();
        }

        function showLoginPage() {
            document.body.innerHTML = `
            <div class="flex items-center justify-center min-h-screen bg-navy-950">
                <div class="w-full max-w-md mx-auto px-6">
                    <div class="mb-12 text-center">
                        <div class="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/20 text-primary border border-primary/20 mx-auto mb-4">
                            <span class="material-symbols-outlined text-[28px]">inventory_2</span>
                        </div>
                        <h1 class="text-2xl font-extrabold text-white">CHRIS EFFECT</h1>
                        <p class="text-slate-400 mt-2">Inventory System</p>
                    </div>
                    <div class="glass-card rounded-3xl p-8">
                        <h2 class="text-xl font-bold text-white mb-6">Welcome Back</h2>
                        <form id="loginForm">
                            <div class="mb-4">
                                <label class="block text-sm font-medium text-slate-300 mb-2">Username</label>
                                <input type="text" id="username" placeholder="Enter username" class="w-full px-4 py-2 bg-navy-900/50 border border-white/10 rounded-lg text-white placeholder:text-slate-500 focus:outline-none focus:border-primary/50">
                            </div>
                            <div class="mb-6">
                                <label class="block text-sm font-medium text-slate-300 mb-2">Password</label>
                                <input type="password" id="password" placeholder="Enter password" class="w-full px-4 py-2 bg-navy-900/50 border border-white/10 rounded-lg text-white placeholder:text-slate-500 focus:outline-none focus:border-primary/50">
                            </div>
                            <button type="submit" class="w-full bg-primary hover:bg-blue-600 text-white font-bold py-2 px-4 rounded-lg transition-all">LOG IN</button>
                        </form>
                        <div class="mt-6 pt-6 border-t border-white/10">
                            <p class="text-xs text-slate-400 text-center mb-3">Default Credentials:</p>
                            <p class="text-xs text-slate-400 text-center mb-1">Admin: <span class="text-slate-300">admin / admin</span></p>
                            <p class="text-xs text-slate-400 text-center">User: <span class="text-slate-300">user / user</span></p>
                        </div>
                    </div>
                </div>
            </div>
            `;

            document.getElementById('loginForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const username = document.getElementById('username').value;
                const password = document.getElementById('password').value;

                try {
                    // Generate a device ID for this client if not already set
                    let deviceId = localStorage.getItem('deviceId');
                    if (!deviceId) {
                        deviceId = 'device_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
                        localStorage.setItem('deviceId', deviceId);
                    }
                    
                    const response = await fetch('/api/login', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({username, password, device_id: deviceId})
                    });
                    
                    if (response.ok) {
                        const data = await response.json();
                        localStorage.setItem('currentUser', data.username);
                        localStorage.setItem('currentToken', data.token);
                        localStorage.setItem('currentRole', data.role);
                        localStorage.setItem('tokenExpiry', data.expires_at);
                        location.reload();
                    } else {
                        alert('Invalid credentials');
                    }
                } catch (error) {
                    alert('Login failed: ' + error.message);
                }
            });
        }
    </script>
</body>
</html>"""

@app.route('/', methods=['GET'])
def index():
    return render_template_string(HTML_TEMPLATE)

# --- Error Handlers ---
@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Server error'}), 500

# --- Startup ---
def startup():
    init_db()

def run_flask():
    """Run Flask server in background thread"""
    app.run(debug=False, host='127.0.0.1', port=5000, use_reloader=False)

if __name__ == '__main__':
    startup()
    
    # Try to run as desktop app with PyWebView, fall back to web mode
    if webview:
        # Start Flask in background thread
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        time.sleep(2)  # Give Flask time to start
        
        # Create and show desktop window
        webview.create_window(
            title='Store Inventory Manager',
            url='http://127.0.0.1:5000/',
            background_color='#0f172a',
            min_size=(1024, 768)
        )
        webview.start(debug=False)
    else:
        # Fallback to web mode if PyWebView not available
        print("PyWebView not found. Running in web mode.")
        print("Open http://127.0.0.1:5000/ in your browser")
        app.run(debug=True, host='127.0.0.1', port=5000)
