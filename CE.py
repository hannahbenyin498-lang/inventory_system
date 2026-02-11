import sys
import webbrowser
import tkinter as tk
from tkinter import messagebox, filedialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import sqlite3
import os
import csv
from datetime import datetime
import shutil
import uuid
import traceback
import time
import threading
import hashlib

# Optional camera/pyzbar support for barcode scanning
try:
    import cv2
    CV2_AVAILABLE = True
except Exception:
    CV2_AVAILABLE = False

try:
    from pyzbar import pyzbar
    PYZBAR_AVAILABLE = True
except Exception:
    PYZBAR_AVAILABLE = False

# Optional Pillow support for image preview
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

# --- Define Theme Colors ---
ThemeColors = {
    "bg_dark": "#F7F9FC",
    "bg_panel": "#FFFFFF",
    "bg_panel_alt": "#F1F5F9",
    "accent": "#1D78E6",
    "accent_dark": "#1666C4",
    "text_light": "#0F172A",
    "text_dim": "#64748B",
    "danger": "#EF4444",
    "warning": "#F59E0B",
    "success": "#22C55E",
    "border": "#E2E8F0"
}

def get_base_dir():
    return getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))

# --- LOGIN WINDOW CLASS (Refined UI) ---
class LoginWindow(ttk.Toplevel):
    def __init__(self, parent, on_login_success):
        super().__init__(parent)
        self.title("Sign In")
        self.geometry("440x580")
        self.resizable(False, False)
        self.configure(bg=ThemeColors["bg_dark"])
        self.on_login_success = on_login_success
        self.parent = parent
        
        self.place_window_center()

        self.base_dir = get_base_dir()
        self.low_stock_threshold = 10
        self.search_placeholder = "Search products, SKUs, categories..."
        self.status_var = tk.StringVar(value="Ready")
        self.time_var = tk.StringVar(value="")
        self._sort_state = {}
        db_path = os.path.join(self.base_dir, "store_inventory.db")
        self.conn = sqlite3.connect(db_path)
        self.init_users_table()

        self.setup_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def place_window_center(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def init_users_table(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT,
                role TEXT
            )
        """)
        cursor.execute("SELECT count(*) FROM users")
        if cursor.fetchone()[0] == 0:
            admin_pass = hashlib.sha256("admin".encode()).hexdigest()
            cursor.execute("INSERT INTO users VALUES (?, ?, ?)", ("admin", admin_pass, "admin"))
            user_pass = hashlib.sha256("user".encode()).hexdigest()
            cursor.execute("INSERT INTO users VALUES (?, ?, ?)", ("user", user_pass, "user"))
            self.conn.commit()

    def setup_ui(self):
        main_frame = ttk.Frame(self, padding=0)
        main_frame.pack(fill="both", expand=True)

        header_frame = ttk.Frame(main_frame, bootstyle="secondary") 
        header_frame.pack(fill="x", pady=(40, 30))
        
        ttk.Label(header_frame, text="CHRIS EFFECT", font=("Segoe UI", 22, "bold"), foreground=ThemeColors['accent'], anchor="center").pack(fill="x")
        ttk.Label(header_frame, text="Inventory System", font=("Segoe UI", 11), foreground=ThemeColors['text_dim'], anchor="center").pack(fill="x")

        card_frame = ttk.Frame(main_frame, style='Card.TFrame', padding=30)
        card_frame.pack(fill="x", padx=40)

        ttk.Label(card_frame, text="Welcome Back", font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(0, 20))

        ttk.Label(card_frame, text="Username", font=("Segoe UI", 10), foreground=ThemeColors['text_dim']).pack(anchor="w", pady=(0, 5))
        self.entry_user = ttk.Entry(card_frame, font=("Segoe UI", 11))
        self.entry_user.pack(fill="x", pady=(0, 15), ipady=5)
        self.entry_user.focus()

        ttk.Label(card_frame, text="Password", font=("Segoe UI", 10), foreground=ThemeColors['text_dim']).pack(anchor="w", pady=(0, 5))
        self.entry_pass = ttk.Entry(card_frame, show="*", font=("Segoe UI", 11))
        self.entry_pass.pack(fill="x", pady=(0, 25), ipady=5)
        self.entry_pass.bind("<Return>", lambda e: self.attempt_login())

        login_btn = ttk.Button(card_frame, text="LOG IN", style="Accent.TButton", cursor="hand2", command=self.attempt_login)
        login_btn.pack(fill="x", ipady=8)

        footer_frame = ttk.Frame(main_frame)
        footer_frame.pack(fill="x", pady=30)
        
        ttk.Label(footer_frame, text="Default Credentials:", font=("Segoe UI", 9), foreground=ThemeColors['text_dim'], anchor="center").pack(fill="x")
        
        creds_frame = ttk.Frame(footer_frame)
        creds_frame.pack(pady=5)
        ttk.Label(creds_frame, text="Admin: admin / admin", font=("Consolas", 9), bootstyle="inverse-danger", padding=3).pack(side="left", padx=5)
        ttk.Label(creds_frame, text="User: user / user", font=("Consolas", 9), bootstyle="inverse-info", padding=3).pack(side="left", padx=5)

    def attempt_login(self):
        u = self.entry_user.get().strip()
        p = self.entry_pass.get().strip()
        
        if not u or not p:
            self.flash_error("Enter username & password")
            return

        hashed = hashlib.sha256(p.encode()).hexdigest()
        cursor = self.conn.cursor()
        cursor.execute("SELECT role FROM users WHERE username=? AND password_hash=?", (u, hashed))
        row = cursor.fetchone()
        
        if row:
            role = row[0]
            self.conn.close()
            self.destroy()
            self.on_login_success(u, role)
        else:
            self.flash_error("Invalid credentials")

    def flash_error(self, message):
        if hasattr(self, 'lbl_error'):
            self.lbl_error.destroy()
        self.lbl_error = ttk.Label(
            self.entry_pass.master,
            text=f"Warning: {message}",
            foreground=ThemeColors["danger"],
            font=("Segoe UI", 9),
        )
        self.lbl_error.pack(before=self.entry_pass, anchor="w", pady=(0, 5))
        self.after(3000, lambda: self.lbl_error.destroy() if hasattr(self, 'lbl_error') else None)

    def on_close(self):
        self.conn.close()
        self.parent.destroy()
        sys.exit()

# --- MAIN APP CLASS ---
class InventoryApp:
    def __init__(self, root, username, role):
        self.root = root
        self.current_user = username
        self.current_role = role 
        self.base_dir = get_base_dir()

        self.set_window_icon()

        self._barcode_buf = ""
        self._barcode_last_time = 0.0

        self.low_stock_threshold = 10
        self.category_thresholds = {}

        self.root.title(f"CHRIS EFFECT - Dashboard | Logged in as: {username.upper()} ({role.upper()})")
        self.root.geometry("1200x800")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.style = ttk.Style()
        try:
            self.style.theme_use('flatly')
        except:
            pass
        self.configure_custom_styles()

        db_path = os.path.join(self.base_dir, "store_inventory.db")
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_table()
        self._load_settings()
        self._load_category_thresholds()

        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=0)

        self.build_sidebar()
        self.main_content_frame = ttk.Frame(self.root, padding=20)
        self.main_content_frame.grid(row=0, column=1, sticky="nsew")

        self.build_header()
        self.build_dashboard_view()
        self.build_status_bar()
        self.bind_shortcuts()
        self.show_inventory()
        self._update_clock()

    def configure_custom_styles(self):
        self.style.configure('.', background=ThemeColors['bg_dark'], foreground=ThemeColors['text_light'], font=("Segoe UI", 10))
        self.style.configure('Sidebar.TFrame', background=ThemeColors['bg_panel'])
        self.style.configure('bg_dark.TFrame', background=ThemeColors['bg_dark'])
        self.style.configure('Status.TFrame', background=ThemeColors['bg_panel'])
        self.style.configure('Status.TLabel', background=ThemeColors['bg_panel'], foreground=ThemeColors['text_dim'], font=("Segoe UI", 9))

        self.style.configure('Accent.TButton', font=("Segoe UI", 10, "bold"), background=ThemeColors['accent'], foreground="white", borderwidth=0)
        self.style.map('Accent.TButton', background=[('active', ThemeColors['accent_dark'])])
        self.style.configure('Soft.TButton', font=("Segoe UI", 10, "bold"), background=ThemeColors['bg_panel_alt'], foreground=ThemeColors['accent'], borderwidth=0)
        self.style.map('Soft.TButton', background=[('active', ThemeColors['border'])])
        self.style.configure('DarkOutline.TButton', background=ThemeColors['bg_panel'], foreground=ThemeColors['text_light'], bordercolor=ThemeColors['border'], borderwidth=1)

        self.style.configure('SidebarTitle.TLabel', background=ThemeColors['bg_panel'], foreground=ThemeColors['text_light'], font=("Segoe UI", 14, "bold"))
        self.style.configure('SidebarBtn.TButton', background=ThemeColors['bg_panel'], foreground=ThemeColors['text_dim'], font=("Segoe UI", 11), anchor="w", borderwidth=0)
        self.style.map('SidebarBtn.TButton', foreground=[('active', ThemeColors['accent'])], background=[('active', ThemeColors['bg_panel'])])
        self.style.configure('ActiveSidebarBtn.TButton', background=ThemeColors['bg_panel_alt'], foreground=ThemeColors['accent'], font=("Segoe UI", 11, "bold"), anchor="w", borderwidth=0)

        self.style.configure("Treeview", background=ThemeColors['bg_panel'], fieldbackground=ThemeColors['bg_panel'], foreground=ThemeColors['text_light'], borderwidth=0, font=("Segoe UI", 10), rowheight=36)
        self.style.configure("Treeview.Heading", background=ThemeColors['bg_panel_alt'], foreground=ThemeColors['text_dim'], font=("Segoe UI", 9, "bold"), borderwidth=1, relief="flat")
        self.style.map('Treeview', background=[('selected', ThemeColors['accent'])], foreground=[('selected', 'white')])

        self.style.configure('Card.TFrame', background=ThemeColors['bg_panel'], borderwidth=0, relief='flat')
        self.style.configure('CardTitle.TLabel', background=ThemeColors['bg_panel'], foreground=ThemeColors['text_dim'], font=("Segoe UI", 10))
        self.style.configure('CardValue.TLabel', background=ThemeColors['bg_panel'], foreground=ThemeColors['text_light'], font=("Segoe UI", 18, "bold"))

    def set_window_icon(self):
        base = self.base_dir
        candidates = [
            os.path.join(base, 'logo.jpg'),
            os.path.join(base, 'images', 'logo.jpg'),
            os.path.join(base, 'images', 'logo.ico'),
            os.path.join(base, 'logo.ico'),
        ]
        for p in candidates:
            if not os.path.exists(p): continue
            try:
                abs_p = os.path.abspath(p)
                if PIL_AVAILABLE:
                    img = Image.open(abs_p)
                    img.thumbnail((256, 256))
                    tkimg = ImageTk.PhotoImage(img)
                    self.root.iconphoto(True, tkimg)
                    self.root._icon = tkimg
                    return
                self.root.iconbitmap(abs_p)
                return
            except Exception as e:
                print(f"[ICON] Error: {e}")

    # --- HELPERS ---
    def _resolve_image_path(self, image_rel_or_abs):
        if not image_rel_or_abs: return None
        if os.path.isabs(image_rel_or_abs): return image_rel_or_abs
        return os.path.join(self.base_dir, image_rel_or_abs)

    def _preview_image_file(self, image_path, title="Image"):
        if not image_path or not os.path.exists(image_path): return
        top = tk.Toplevel(self.root)
        top.title(title)
        top.geometry("500x500")
        if PIL_AVAILABLE:
            img = Image.open(image_path)
            img.thumbnail((480, 480))
            tkimg = ImageTk.PhotoImage(img)
            lbl = tk.Label(top, image=tkimg)
            lbl.image = tkimg 
            lbl.pack(expand=True)
        else:
            tk.Label(top, text="Install Pillow to view images").pack(expand=True)

    def _set_status(self, message):
        self.status_var.set(message)

    def _update_clock(self):
        self.time_var.set(datetime.now().strftime("%b %d, %Y %I:%M %p"))
        self.root.after(30000, self._update_clock)

    def _compute_status(self, qty, category=None):
        threshold = self._get_category_threshold(category)
        if qty <= 0:
            return "Out of Stock"
        if qty < threshold:
            return "Low Stock"
        return "In Stock"

    def _get_categories(self):
        try:
            self.cursor.execute(
                "SELECT DISTINCT category FROM inventory_v2 WHERE category IS NOT NULL AND category != ''"
            )
            cats = sorted({row[0] for row in self.cursor.fetchall()})
        except Exception:
            cats = []
        defaults = ["Electronics", "Clothing", "Food", "Uncategorized"]
        for d in defaults:
            if d not in cats:
                cats.append(d)
        return cats

    def _load_settings(self):
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            self.conn.commit()
            self.cursor.execute("SELECT value FROM app_settings WHERE key='low_stock_default'")
            row = self.cursor.fetchone()
            if row and row[0].strip().isdigit():
                self.low_stock_threshold = int(row[0])
        except Exception:
            pass

    def _save_setting(self, key, value):
        self.cursor.execute(
            "INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)",
            (key, str(value)),
        )
        self.conn.commit()

    def _load_category_thresholds(self):
        self.category_thresholds = {}
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS category_thresholds (
                    category TEXT PRIMARY KEY,
                    threshold INTEGER NOT NULL
                )
            """)
            self.conn.commit()
            self.cursor.execute("SELECT category, threshold FROM category_thresholds")
            for cat, threshold in self.cursor.fetchall():
                try:
                    self.category_thresholds[cat] = int(threshold)
                except Exception:
                    continue
        except Exception:
            pass

    def _get_category_threshold(self, category):
        if not category:
            return self.low_stock_threshold
        return self.category_thresholds.get(category, self.low_stock_threshold)

    def _set_search_placeholder(self):
        if self.entry_search.get():
            return
        self.entry_search.insert(0, self.search_placeholder)
        self.entry_search.configure(foreground=ThemeColors["text_dim"])

    def _clear_search_placeholder(self):
        if self.entry_search.get() == self.search_placeholder:
            self.entry_search.delete(0, "end")
            self.entry_search.configure(foreground=ThemeColors["text_light"])

    def _focus_search(self):
        self.entry_search.focus_set()
        self._clear_search_placeholder()
        self.entry_search.selection_range(0, tk.END)

    def _on_search_focus_in(self, event=None):
        self._clear_search_placeholder()

    def _on_search_focus_out(self, event=None):
        if not self.entry_search.get().strip():
            self.entry_search.delete(0, "end")
            self._set_search_placeholder()
        self.hide_suggestions()

    def bind_shortcuts(self):
        self.root.bind_all("<Control-f>", lambda e: self._focus_search())
        self.root.bind_all("<Control-n>", lambda e: self.open_add_product_popup())
        self.root.bind_all("<Control-e>", lambda e: self.export_to_csv())
        self.root.bind_all("<Delete>", lambda e: self.delete_product() if self.current_role == "admin" else None)

    # --- UI BUILDING ---
    def build_sidebar(self):
        sidebar = ttk.Frame(self.root, style='Sidebar.TFrame', width=250, padding=20)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        logo_lbl = ttk.Label(sidebar, text="CHRIS EFFECT", style='SidebarTitle.TLabel')
        logo_lbl.pack(pady=(10, 40), anchor="w")

        ttk.Button(sidebar, text="Dashboard", style='ActiveSidebarBtn.TButton', cursor="hand2", command=self.show_dashboard).pack(fill="x", pady=5)
        ttk.Button(sidebar, text="Inventory", style='SidebarBtn.TButton', cursor="hand2", command=self.show_inventory).pack(fill="x", pady=5)
        ttk.Button(sidebar, text="Marketplace", style='SidebarBtn.TButton', cursor="hand2", command=self.show_marketplace).pack(fill="x", pady=5)
        
        ttk.Separator(sidebar, orient='horizontal').pack(fill='x', pady=20)
        
        ttk.Button(sidebar, text="Logout", style='SidebarBtn.TButton', bootstyle="danger-link", cursor="hand2", command=self.logout).pack(fill="x", pady=5, side="bottom")
        
        user_frame = ttk.Frame(sidebar, style='Sidebar.TFrame')
        user_frame.pack(side="bottom", fill="x", pady=20)
        ttk.Label(user_frame, text="User: " + self.current_user.title(), background=ThemeColors['bg_panel'], font=("Segoe UI", 12, "bold")).pack(anchor="w")
        ttk.Label(user_frame, text=self.current_role.upper(), background=ThemeColors['bg_panel'], foreground=ThemeColors['accent'], font=("Segoe UI", 9)).pack(anchor="w")

    def logout(self):
        self.conn.close()
        self.root.destroy()
        os.execl(sys.executable, sys.executable, *sys.argv)

    def build_header(self):
        self.header_frame = ttk.Frame(self.main_content_frame)
        self.header_frame.pack(fill="x", pady=(0, 20))

        search_container = ttk.Frame(self.header_frame, style="bg_dark.TFrame")
        search_container.pack(side="left", fill="x", expand=True, padx=(0, 20))

        self.entry_search = ttk.Entry(search_container, bootstyle="light", font=("Segoe UI", 11))
        self.entry_search.pack(side="left", fill="x", expand=True, ipady=5)
        self._set_search_placeholder()
        self.entry_search.bind("<FocusIn>", self._on_search_focus_in)
        self.entry_search.bind("<KeyRelease>", self.on_search_keyrelease)
        self.entry_search.bind("<FocusOut>", self._on_search_focus_out)
        self.entry_search.bind("<Return>", lambda e: self.search_product())

        ttk.Button(search_container, text="Search", bootstyle="secondary", command=self.search_product).pack(side="right", padx=5)
        ttk.Button(search_container, text="Scan", bootstyle="info", command=self.start_camera_scanner).pack(side="right", padx=5)
        ttk.Button(search_container, text="Reset", bootstyle="link", command=self.show_inventory).pack(side="right")

    def build_status_bar(self):
        self.status_bar = ttk.Frame(self.root, style="Status.TFrame")
        self.status_bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        ttk.Label(self.status_bar, textvariable=self.status_var, style="Status.TLabel").pack(
            side="left", padx=12, pady=4
        )
        ttk.Label(self.status_bar, textvariable=self.time_var, style="Status.TLabel").pack(
            side="right", padx=12
        )

    def build_dashboard_view(self):
        self.summary_frame = ttk.Frame(self.main_content_frame)
        self.summary_frame.pack(fill="x", pady=(0, 12))

        card_left = ttk.Frame(self.summary_frame)
        card_left.pack(side="left", fill="both", expand=True)

        card_right = ttk.Frame(self.summary_frame)
        card_right.pack(side="left", fill="both", expand=True, padx=(12, 0))

        mini_row = ttk.Frame(card_left)
        mini_row.pack(fill="x")

        card_total = ttk.Frame(mini_row, padding=16, style="Card.TFrame")
        card_total.pack(side="left", fill="both", expand=True, padx=(0, 10))
        ttk.Label(card_total, text="TOTAL ITEMS", style="CardTitle.TLabel").pack(anchor="w")
        self.lbl_total_products = ttk.Label(card_total, text="0", style="CardValue.TLabel")
        self.lbl_total_products.pack(anchor="w", pady=(6, 0))

        card_low = ttk.Frame(mini_row, padding=16, style="Card.TFrame")
        card_low.pack(side="left", fill="both", expand=True)
        ttk.Label(card_low, text="LOW STOCK", style="CardTitle.TLabel").pack(anchor="w")
        self.lbl_low_stock = ttk.Label(card_low, text="0", style="CardValue.TLabel")
        self.lbl_low_stock.pack(anchor="w", pady=(6, 0))

        card_value = ttk.Frame(card_right, padding=18, style="Card.TFrame")
        card_value.pack(fill="both", expand=True)
        ttk.Label(card_value, text="TOTAL INVENTORY VALUE", style="CardTitle.TLabel").pack(anchor="w")
        self.lbl_inventory_value = ttk.Label(card_value, text="$0.00", style="CardValue.TLabel")
        self.lbl_inventory_value.pack(anchor="w", pady=(10, 4))
        self.lbl_total_qty = ttk.Label(card_value, text="Updated just now", foreground=ThemeColors["text_dim"])
        self.lbl_total_qty.pack(anchor="w")

        action_row = ttk.Frame(self.main_content_frame)
        action_row.pack(fill="x", pady=(8, 20))
        ttk.Label(action_row, text="Inventory Dashboard", font=("Segoe UI", 20, "bold")).pack(side="left")

        ttk.Button(action_row, text="+ Add New", style="Accent.TButton", cursor="hand2", command=self.open_add_product_popup).pack(side="right", padx=5)
        ttk.Button(action_row, text="Record Sale", bootstyle='warning', cursor="hand2", command=self.open_record_sale_popup).pack(side="right", padx=5)
        ttk.Button(action_row, text="Import CSV", bootstyle='secondary', cursor="hand2", command=self.import_from_csv).pack(side="right", padx=5)
        ttk.Button(action_row, text="Low Stock Rules", bootstyle='info', cursor="hand2", command=self.open_thresholds_popup).pack(side="right", padx=5)

        low_frame = ttk.Frame(self.main_content_frame)
        low_frame.pack(fill="x", pady=(0, 16))
        ttk.Label(low_frame, text="Low Stock Alerts", font=("Segoe UI", 14, "bold")).pack(anchor="w")

        alerts = ttk.Frame(self.main_content_frame)
        alerts.pack(fill="x", pady=(6, 20))

        try:
            self.cursor.execute(
                "SELECT id, name, category, quantity FROM inventory_v2 WHERE quantity > 0 ORDER BY quantity ASC LIMIT 3"
            )
            low_rows = self.cursor.fetchall()
        except Exception:
            low_rows = []

        if not low_rows:
            ttk.Label(alerts, text="No low stock items.", foreground=ThemeColors["text_dim"]).pack(anchor="w")
        else:
            for pid, name, category, qty in low_rows:
                card = ttk.Frame(alerts, padding=12, style="Card.TFrame")
                card.pack(fill="x", pady=6)
                top = ttk.Frame(card)
                top.pack(fill="x")
                ttk.Label(top, text=name, font=("Segoe UI", 11, "bold")).pack(side="left")
                ttk.Label(top, text=f"{qty} units remaining", foreground=ThemeColors["text_dim"]).pack(side="right")
                ttk.Label(card, text=category or "Uncategorized", foreground=ThemeColors["text_dim"]).pack(anchor="w", pady=(4, 6))
                ttk.Button(card, text="Restock", style="Soft.TButton", command=lambda p=pid: self.open_edit_product_popup(p)).pack(anchor="w")

        recent_frame = ttk.Frame(self.main_content_frame)
        recent_frame.pack(fill="x", pady=(0, 8))
        ttk.Label(recent_frame, text="Recent Activity", font=("Segoe UI", 14, "bold")).pack(anchor="w")

        activity = ttk.Frame(self.main_content_frame)
        activity.pack(fill="x")

        try:
            self.cursor.execute(
                "SELECT name, quantity, sale_date FROM sales ORDER BY sale_date DESC LIMIT 5"
            )
            recent_rows = self.cursor.fetchall()
        except Exception:
            recent_rows = []

        if not recent_rows:
            ttk.Label(activity, text="No recent sales.", foreground=ThemeColors["text_dim"]).pack(anchor="w")
        else:
            for name, qty, sale_date in recent_rows:
                row = ttk.Frame(activity, padding=10, style="Card.TFrame")
                row.pack(fill="x", pady=6)
                ttk.Label(row, text=f"{name}", font=("Segoe UI", 11, "bold")).pack(side="left")
                ttk.Label(row, text=f"-{qty}", foreground=ThemeColors["danger"]).pack(side="right")
                ttk.Label(row, text=sale_date.split("T")[0], foreground=ThemeColors["text_dim"]).pack(anchor="w")

    def _build_inventory_view(self):
        for child in list(self.main_content_frame.winfo_children()):
            if child is self.header_frame: continue
            child.destroy()

        action_row = ttk.Frame(self.main_content_frame)
        action_row.pack(fill="x", pady=(0, 20))
        ttk.Label(action_row, text="Inventory", font=("Segoe UI", 20, "bold")).pack(side="left")

        ttk.Button(action_row, text="+ Add New", style="Accent.TButton", cursor="hand2", command=self.open_add_product_popup).pack(side="right", padx=5)
        ttk.Button(action_row, text="Edit Selected", bootstyle='info', cursor="hand2", command=self.open_edit_product_popup).pack(side="right", padx=5)
        ttk.Button(action_row, text="Record Sale", bootstyle='warning', cursor="hand2", command=self.open_record_sale_popup).pack(side="right", padx=5)
        ttk.Button(action_row, text="Import CSV", bootstyle='secondary', cursor="hand2", command=self.import_from_csv).pack(side="right", padx=5)
        ttk.Button(action_row, text="Export CSV", bootstyle='secondary', cursor="hand2", command=self.export_to_csv).pack(side="right", padx=5)

        self.btn_delete = ttk.Button(action_row, text="Delete Selected", style='DarkOutline.TButton', bootstyle="danger", cursor="hand2", command=self.delete_product)
        self.btn_delete.pack(side="right", padx=5)
        if self.current_role != 'admin':
            self.btn_delete.configure(state='disabled')

        self.table_frame = ttk.Frame(self.main_content_frame, style='Sidebar.TFrame', padding=2)
        self.table_frame.pack(fill="both", expand=True)

        cols = ("ID", "SKU", "Title", "Category", "QTY", "Price", "Status")
        self.tree = ttk.Treeview(self.table_frame, columns=cols, show="headings", selectmode="extended") 

        widths = [50, 100, 250, 120, 80, 100, 100]
        aligns = ["w", "w", "w", "w", "center", "e", "center"]
        
        for col, w, a in zip(cols, widths, aligns):
            self.tree.heading(col, text=col, anchor=a, command=lambda c=col: self.sort_treeview(c, False))
            self.tree.column(col, width=w, anchor=a)

        sb = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        
        self.tree.bind("<Double-1>", self.show_product_image_popup)
        self.tree.tag_configure('low_stock', foreground=ThemeColors['warning'])
        self.tree.tag_configure('out_stock', foreground=ThemeColors['danger'])
        self.tree.tag_configure('odd', background=ThemeColors['bg_panel'])
        self.tree.tag_configure('even', background=ThemeColors['bg_panel_alt'])

        self.setup_context_menu()

    def _coerce_sort_value(self, col, value):
        if col in ("ID", "QTY"):
            try:
                return int(value)
            except Exception:
                return 0
        if col == "Price":
            try:
                return float(str(value).replace("$", ""))
            except Exception:
                return 0.0
        return str(value).lower()

    def sort_treeview(self, col, reverse):
        data = []
        for child in self.tree.get_children(""):
            value = self.tree.set(child, col)
            data.append((self._coerce_sort_value(col, value), child))
        data.sort(reverse=reverse)
        for index, (_, child) in enumerate(data):
            self.tree.move(child, "", index)
        self.tree.heading(col, command=lambda c=col: self.sort_treeview(c, not reverse))

    def setup_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=0)

        self.context_menu.add_command(label="Edit", command=self.open_edit_product_popup)
        self.context_menu.add_separator()

        if self.current_role == 'admin':
            self.context_menu.add_command(label="Delete Selected", command=self.delete_product)
            self.context_menu.add_separator()

        self.context_menu.add_command(label="Record Sale", command=self.open_record_sale_popup)
        self.context_menu.add_command(label="View Image", command=self.show_product_image_popup)

        def do_popup(event):
            try:
                item = self.tree.identify_row(event.y)
                if item:
                    if item not in self.tree.selection():
                        self.tree.selection_set(item)
                    self.context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.context_menu.grab_release()

        self.tree.bind("<Button-3>", do_popup)

    # --- DATABASE & LOGIC ---
    def create_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory_v2 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT,
                name TEXT NOT NULL,
                category TEXT,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                status TEXT DEFAULT 'In Stock',
                image TEXT
            )
        """)
        self.cursor.execute("""
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
        self.conn.commit()

    def delete_product(self):
        if self.current_role != 'admin':
            messagebox.showerror("Permission Denied", "Only Admins can delete items.")
            return

        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Error", "Please select items to delete.")
            return

        count = len(selected_items)
        if not messagebox.askyesno("Confirm", f"Delete {count} items?"):
            return

        try:
            for item in selected_items:
                vals = self.tree.item(item)['values']
                if vals:
                    self.cursor.execute("DELETE FROM inventory_v2 WHERE id=?", (vals[0],))
            self.conn.commit()
            self.show_inventory()
            self.refresh_summary()
            messagebox.showinfo("Success", "Items deleted.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed: {e}")
    
    def refresh_summary(self):
        try:
            self.cursor.execute("SELECT COUNT(*), COALESCE(SUM(quantity),0), COALESCE(SUM(quantity*price),0) FROM inventory_v2")
            res = self.cursor.fetchone()
            self.cursor.execute("SELECT category, quantity FROM inventory_v2")
            low = 0
            for category, qty in self.cursor.fetchall():
                if self._compute_status(qty, category) == "Low Stock":
                    low += 1
            
            self.lbl_total_products.config(text=str(res[0]))
            if hasattr(self, "lbl_total_qty"):
                self.lbl_total_qty.config(text=f"Total quantity: {res[1]}")
            self.lbl_inventory_value.config(text=f"${res[2]:.2f}")
            self.lbl_low_stock.config(text=str(low))
        except: pass

    def show_inventory(self):
        if not hasattr(self, "tree") or not self.tree.winfo_exists():
            self._build_inventory_view()
        self.tree.delete(*self.tree.get_children())
        self.cursor.execute("SELECT id, sku, name, category, quantity, price, status FROM inventory_v2")
        updates = []
        rows = self.cursor.fetchall()
        for idx, r in enumerate(rows):
            pid, sku, name, category, qty, price, status = r
            new_status = self._compute_status(qty, category)
            if new_status != status:
                updates.append((new_status, pid))
                status = new_status
            tags = ['even' if idx % 2 == 0 else 'odd']
            if status == "Low Stock":
                tags.append('low_stock')
            elif status == "Out of Stock":
                tags.append('out_stock')
            self.tree.insert("", "end", values=(pid, sku, name, category, qty, f"{price:.2f}", status), tags=tuple(tags))
        if updates:
            self.cursor.executemany("UPDATE inventory_v2 SET status=? WHERE id=?", updates)
            self.conn.commit()
        self.refresh_summary()
        self._set_status(f"Loaded {len(rows)} items")

    def search_product(self):
        term = self.entry_search.get().strip()
        if not term or term == self.search_placeholder:
            return self.show_inventory()
        self.tree.delete(*self.tree.get_children())
        self.cursor.execute(
            "SELECT id, sku, name, category, quantity, price, status FROM inventory_v2 "
            "WHERE name LIKE ? OR sku LIKE ? OR category LIKE ?",
            ('%'+term+'%', '%'+term+'%', '%'+term+'%')
        )
        rows = self.cursor.fetchall()
        updates = []
        for idx, r in enumerate(rows):
            pid, sku, name, category, qty, price, status = r
            new_status = self._compute_status(qty, category)
            if new_status != status:
                updates.append((new_status, pid))
                status = new_status
            tags = ['even' if idx % 2 == 0 else 'odd']
            if status == "Low Stock":
                tags.append('low_stock')
            elif status == "Out of Stock":
                tags.append('out_stock')
            self.tree.insert("", "end", values=(pid, sku, name, category, qty, f"{price:.2f}", status), tags=tuple(tags))
        if updates:
            self.cursor.executemany("UPDATE inventory_v2 SET status=? WHERE id=?", updates)
            self.conn.commit()
        self._set_status(f"Search results: {len(rows)} items")
        return len(rows)

    def on_search_keyrelease(self, event):
        term = self.entry_search.get().strip()
        if term and term != self.search_placeholder:
            self.query_suggestions(term)
        else:
            self.hide_suggestions()

    def query_suggestions(self, term):
        try:
            self.cursor.execute("SELECT name FROM inventory_v2 WHERE name LIKE ? LIMIT 5", ('%'+term+'%',))
            rows = [r[0] for r in self.cursor.fetchall()]
            if rows: self.show_suggestions(rows)
            else: self.hide_suggestions()
        except: pass

    def show_suggestions(self, texts):
        if not hasattr(self, 'sugg_win') or not self.sugg_win:
            self.sugg_win = tk.Toplevel(self.root)
            self.sugg_win.wm_overrideredirect(True)
            self.sugg_lb = tk.Listbox(self.sugg_win)
            self.sugg_lb.pack(fill='both', expand=True)
            self.sugg_lb.bind('<Button-1>', lambda e: self.apply_sugg())
        self.sugg_lb.delete(0, 'end')
        for t in texts: self.sugg_lb.insert('end', t)
        x, y, w = self.entry_search.winfo_rootx(), self.entry_search.winfo_rooty() + self.entry_search.winfo_height(), self.entry_search.winfo_width()
        self.sugg_win.geometry(f"{w}x{len(texts)*20}+{x}+{y}")
        self.sugg_win.deiconify()

    def hide_suggestions(self):
        if hasattr(self, 'sugg_win'): self.sugg_win.withdraw()

    def apply_sugg(self):
        if self.sugg_lb.curselection():
            txt = self.sugg_lb.get(self.sugg_lb.curselection())
            self.entry_search.delete(0, 'end')
            self.entry_search.insert(0, txt)
            self.search_product()
            self.hide_suggestions()

    # --- POPUPS ---
    def open_thresholds_popup(self):
        top = ttk.Toplevel(self.root)
        top.title("Low Stock Thresholds")
        top.geometry("520x520")
        top.transient(self.root)
        top.grab_set()

        self._load_category_thresholds()

        wrap = ttk.Frame(top, padding=16)
        wrap.pack(fill="both", expand=True)

        default_frame = ttk.Labelframe(wrap, text="Default Threshold", padding=10)
        default_frame.pack(fill="x", pady=(0, 12))

        default_var = tk.StringVar(value=str(self.low_stock_threshold))
        ttk.Label(default_frame, text="Default quantity threshold:").pack(side="left")
        default_entry = ttk.Entry(default_frame, textvariable=default_var, width=8)
        default_entry.pack(side="left", padx=8)

        def save_default():
            try:
                val = int(default_var.get().strip())
                if val < 0:
                    raise ValueError
            except Exception:
                messagebox.showerror("Invalid", "Default threshold must be a non-negative integer.")
                return
            self.low_stock_threshold = val
            self._save_setting("low_stock_default", val)
            self._refresh_threshold_tree(tree)
            self.show_inventory()
            self.refresh_summary()
            self._set_status("Default threshold updated")

        ttk.Button(default_frame, text="Save", style="Accent.TButton", command=save_default).pack(side="left", padx=6)

        list_frame = ttk.Labelframe(wrap, text="Category Overrides", padding=10)
        list_frame.pack(fill="both", expand=True)

        tree = ttk.Treeview(list_frame, columns=("Category", "Threshold"), show="headings", height=8)
        tree.heading("Category", text="Category")
        tree.heading("Threshold", text="Threshold")
        tree.column("Category", width=240, anchor="w")
        tree.column("Threshold", width=140, anchor="center")
        tree.pack(fill="both", expand=True, side="left")

        sb = ttk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")

        form = ttk.Frame(wrap)
        form.pack(fill="x", pady=(10, 0))

        ttk.Label(form, text="Category:").grid(row=0, column=0, sticky="w")
        cat_var = tk.StringVar()
        cat_box = ttk.Combobox(form, textvariable=cat_var, values=self._get_categories(), state="normal")
        cat_box.grid(row=0, column=1, sticky="ew", padx=6)

        ttk.Label(form, text="Threshold:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        thr_var = tk.StringVar()
        thr_entry = ttk.Entry(form, textvariable=thr_var)
        thr_entry.grid(row=1, column=1, sticky="ew", padx=6, pady=(6, 0))

        form.grid_columnconfigure(1, weight=1)

        btns = ttk.Frame(wrap)
        btns.pack(fill="x", pady=(10, 0))

        def load_selected(event=None):
            sel = tree.selection()
            if not sel:
                return
            cat, thr = tree.item(sel[0], "values")
            cat_var.set(cat)
            if isinstance(thr, str) and thr.startswith("Default"):
                thr_var.set(str(self.low_stock_threshold))
            else:
                thr_var.set(str(thr))

        def save_override():
            cat = cat_var.get().strip()
            if not cat:
                messagebox.showerror("Invalid", "Category is required.")
                return
            try:
                val = int(thr_var.get().strip())
                if val < 0:
                    raise ValueError
            except Exception:
                messagebox.showerror("Invalid", "Threshold must be a non-negative integer.")
                return
            self.cursor.execute(
                "INSERT OR REPLACE INTO category_thresholds (category, threshold) VALUES (?, ?)",
                (cat, val),
            )
            self.conn.commit()
            self.category_thresholds[cat] = val
            self._refresh_threshold_tree(tree)
            self.show_inventory()
            self.refresh_summary()
            self._set_status(f"Set {cat} threshold to {val}")

        def clear_override():
            cat = cat_var.get().strip()
            if not cat:
                sel = tree.selection()
                if sel:
                    cat = tree.item(sel[0], "values")[0]
            if not cat:
                return
            self.cursor.execute("DELETE FROM category_thresholds WHERE category=?", (cat,))
            self.conn.commit()
            if cat in self.category_thresholds:
                del self.category_thresholds[cat]
            self._refresh_threshold_tree(tree)
            self.show_inventory()
            self.refresh_summary()
            self._set_status(f"Cleared {cat} override")

        ttk.Button(btns, text="Save Override", bootstyle="success", command=save_override).pack(side="left", expand=True, fill="x", padx=(0, 6))
        ttk.Button(btns, text="Clear Override", bootstyle="secondary", command=clear_override).pack(side="left", expand=True, fill="x")

        tree.bind("<<TreeviewSelect>>", load_selected)
        self._refresh_threshold_tree(tree)

    def _refresh_threshold_tree(self, tree):
        tree.delete(*tree.get_children())
        cats = sorted(set(self._get_categories()) | set(self.category_thresholds.keys()))
        for cat in cats:
            if cat in self.category_thresholds:
                tree.insert("", "end", values=(cat, self.category_thresholds[cat]))
            else:
                tree.insert("", "end", values=(cat, f"Default ({self.low_stock_threshold})"))

    def open_add_product_popup(self):
        self.add_popup = ttk.Toplevel(self.root)
        self.add_popup.title("Add Product")
        self.add_popup.geometry("420x520")
        self.add_popup.transient(self.root)
        self.add_popup.grab_set()
        frame = ttk.Frame(self.add_popup, padding=20)
        frame.pack(fill='both')
        
        ttk.Label(frame, text="Name:").pack(anchor='w')
        self.pop_name = ttk.Entry(frame)
        self.pop_name.pack(fill='x')
        self.pop_name.focus_set()
        
        ttk.Label(frame, text="SKU:").pack(anchor='w')
        self.pop_sku = ttk.Entry(frame)
        self.pop_sku.pack(fill='x')
        
        ttk.Label(frame, text="Category:").pack(anchor='w')
        self.pop_cat = ttk.Combobox(frame, values=self._get_categories(), state="normal")
        self.pop_cat.pack(fill='x')
        self.pop_cat.set("Uncategorized")
        
        ttk.Label(frame, text="Qty:").pack(anchor='w')
        self.pop_qty = ttk.Entry(frame)
        self.pop_qty.pack(fill='x')
        
        ttk.Label(frame, text="Price:").pack(anchor='w')
        self.pop_price = ttk.Entry(frame)
        self.pop_price.pack(fill='x')
        
        self.pop_img_path = None
        ttk.Button(frame, text="Select Image", command=self.select_image).pack(pady=10)
        
        ttk.Button(frame, text="Save", style='Accent.TButton', command=self.save_product).pack(fill='x', pady=20)

    def select_image(self):
        f = filedialog.askopenfilename(filetypes=[("Images", "*.jpg;*.png;*.jpeg")])
        if f:
            dest_dir = os.path.join(self.base_dir, 'images')
            os.makedirs(dest_dir, exist_ok=True)
            ext = os.path.splitext(f)[1]
            unique_name = f"{uuid.uuid4().hex}{ext}"
            shutil.copy(f, os.path.join(dest_dir, unique_name))
            self.pop_img_path = os.path.join('images', unique_name)
            messagebox.showinfo("Image", "Image Selected")

    def save_product(self):
        try:
            name = self.pop_name.get().strip()
            sku = self.pop_sku.get().strip()
            qty_text = self.pop_qty.get().strip()
            price_text = self.pop_price.get().strip()

            if not name or not sku:
                messagebox.showerror("Error", "Name and SKU are required.")
                return
            try:
                qty = int(qty_text)
                if qty < 0:
                    raise ValueError
            except Exception:
                messagebox.showerror("Error", "Quantity must be a non-negative integer.")
                return
            try:
                price = float(price_text)
                if price < 0:
                    raise ValueError
            except Exception:
                messagebox.showerror("Error", "Price must be a non-negative number.")
                return

            cat = self.pop_cat.get().strip() or "Uncategorized"
            self.cursor.execute("SELECT 1 FROM inventory_v2 WHERE sku=?", (sku,))
            if self.cursor.fetchone():
                messagebox.showerror("Duplicate SKU", "A product with this SKU already exists.")
                return

            status = self._compute_status(qty, cat)
            self.cursor.execute(
                "INSERT INTO inventory_v2 (sku, name, category, quantity, price, status, image) VALUES (?,?,?,?,?,?,?)",
                (sku, name, cat, qty, price, status, self.pop_img_path),
            )
            self.conn.commit()
            self.add_popup.destroy()
            self.show_inventory()
            self._set_status(f"Added product: {name}")
        except Exception as e:
            messagebox.showerror("Error", f"Invalid Input: {e}")

    def open_edit_product_popup(self, pid=None):
        if pid is None:
            sel = self.tree.selection()
            if not sel:
                messagebox.showwarning("Select", "Please select a product to edit.")
                return
            pid = self.tree.item(sel[0])["values"][0]
        self.cursor.execute(
            "SELECT sku, name, category, quantity, price, image FROM inventory_v2 WHERE id=?",
            (pid,),
        )
        row = self.cursor.fetchone()
        if not row:
            messagebox.showerror("Error", "Selected product not found.")
            return
        sku, name, category, qty, price, image = row

        self.edit_popup = ttk.Toplevel(self.root)
        self.edit_popup.title("Edit Product")
        self.edit_popup.geometry("420x520")
        self.edit_popup.transient(self.root)
        self.edit_popup.grab_set()

        frame = ttk.Frame(self.edit_popup, padding=20)
        frame.pack(fill="both")

        ttk.Label(frame, text="Name:").pack(anchor="w")
        self.edit_name = ttk.Entry(frame)
        self.edit_name.pack(fill="x")
        self.edit_name.insert(0, name)

        ttk.Label(frame, text="SKU:").pack(anchor="w")
        self.edit_sku = ttk.Entry(frame)
        self.edit_sku.pack(fill="x")
        self.edit_sku.insert(0, sku)

        ttk.Label(frame, text="Category:").pack(anchor="w")
        self.edit_cat = ttk.Combobox(frame, values=self._get_categories(), state="normal")
        self.edit_cat.pack(fill="x")
        self.edit_cat.set(category or "Uncategorized")

        ttk.Label(frame, text="Qty:").pack(anchor="w")
        self.edit_qty = ttk.Entry(frame)
        self.edit_qty.pack(fill="x")
        self.edit_qty.insert(0, str(qty))

        ttk.Label(frame, text="Price:").pack(anchor="w")
        self.edit_price = ttk.Entry(frame)
        self.edit_price.pack(fill="x")
        self.edit_price.insert(0, str(price))

        self.edit_img_path = image
        ttk.Button(frame, text="Change Image", command=self.select_edit_image).pack(pady=10)

        ttk.Button(
            frame,
            text="Update",
            style="Accent.TButton",
            command=lambda: self.update_product(pid),
        ).pack(fill="x", pady=20)

    def select_edit_image(self):
        f = filedialog.askopenfilename(filetypes=[("Images", "*.jpg;*.png;*.jpeg")])
        if f:
            dest_dir = os.path.join(self.base_dir, "images")
            os.makedirs(dest_dir, exist_ok=True)
            ext = os.path.splitext(f)[1]
            unique_name = f"{uuid.uuid4().hex}{ext}"
            shutil.copy(f, os.path.join(dest_dir, unique_name))
            self.edit_img_path = os.path.join("images", unique_name)
            messagebox.showinfo("Image", "Image Selected")

    def update_product(self, pid):
        try:
            name = self.edit_name.get().strip()
            sku = self.edit_sku.get().strip()
            qty_text = self.edit_qty.get().strip()
            price_text = self.edit_price.get().strip()

            if not name or not sku:
                messagebox.showerror("Error", "Name and SKU are required.")
                return
            try:
                qty = int(qty_text)
                if qty < 0:
                    raise ValueError
            except Exception:
                messagebox.showerror("Error", "Quantity must be a non-negative integer.")
                return
            try:
                price = float(price_text)
                if price < 0:
                    raise ValueError
            except Exception:
                messagebox.showerror("Error", "Price must be a non-negative number.")
                return

            cat = self.edit_cat.get().strip() or "Uncategorized"
            self.cursor.execute(
                "SELECT id FROM inventory_v2 WHERE sku=? AND id!=?",
                (sku, pid),
            )
            if self.cursor.fetchone():
                messagebox.showerror(
                    "Duplicate SKU", "Another product already uses this SKU."
                )
                return

            status = self._compute_status(qty, cat)
            self.cursor.execute(
                "UPDATE inventory_v2 SET sku=?, name=?, category=?, quantity=?, price=?, status=?, image=? WHERE id=?",
                (sku, name, cat, qty, price, status, self.edit_img_path, pid),
            )
            self.conn.commit()
            self.edit_popup.destroy()
            self.show_inventory()
            self._set_status(f"Updated product: {name}")
        except Exception as e:
            messagebox.showerror("Error", f"Update failed: {e}")

    def open_record_sale_popup(self, product_id=None):
        self.sale_popup = ttk.Toplevel(self.root)
        self.sale_popup.title("Record Sale")
        self.sale_popup.geometry("300x250")
        f = ttk.Frame(self.sale_popup, padding=20)
        f.pack(fill='both')

        if product_id is None:
            sel = self.tree.selection()
            if sel:
                product_id = self.tree.item(sel[0])["values"][0]
        
        self.cursor.execute("SELECT id, name, quantity FROM inventory_v2")
        rows = self.cursor.fetchall()
        if not rows:
            messagebox.showinfo("Sale", "No products available.")
            self.sale_popup.destroy()
            return
        items = [f"{r[0]} - {r[1]} (Qty: {r[2]})" for r in rows]
        id_map = {r[0]: f"{r[0]} - {r[1]} (Qty: {r[2]})" for r in rows}
        
        ttk.Label(f, text="Product:").pack(anchor='w')
        self.sale_cb = ttk.Combobox(f, values=items, state="readonly")
        self.sale_cb.pack(fill='x')
        if product_id in id_map:
            self.sale_cb.set(id_map[product_id])
        
        ttk.Label(f, text="Qty Sold:").pack(anchor='w')
        self.sale_qty_entry = ttk.Entry(f)
        self.sale_qty_entry.pack(fill='x')
        self.sale_qty_entry.bind("<Return>", lambda e: self.confirm_sale())
        
        ttk.Button(f, text="Confirm", style='Accent.TButton', command=self.confirm_sale).pack(fill='x', pady=20)

    def confirm_sale(self):
        try:
            sel = self.sale_cb.get()
            if not sel: return
            pid = int(sel.split(' - ')[0])
            qty_sold = int(self.sale_qty_entry.get())

            if qty_sold <= 0:
                messagebox.showerror("Error", "Quantity must be greater than zero.")
                return
            
            self.cursor.execute("SELECT quantity, price, name, sku, category FROM inventory_v2 WHERE id=?", (pid,))
            cur_qty, price, name, sku, category = self.cursor.fetchone()
            
            if qty_sold > cur_qty:
                messagebox.showerror("Error", "Not enough stock")
                return
                
            new_qty = cur_qty - qty_sold
            status = self._compute_status(new_qty, category)
            self.cursor.execute("UPDATE inventory_v2 SET quantity=?, status=? WHERE id=?", (new_qty, status, pid))
            self.cursor.execute("INSERT INTO sales (product_id, sku, name, quantity, price, sale_date) VALUES (?,?,?,?,?,?)",
                                (pid, sku, name, qty_sold, price, datetime.now().isoformat()))
            self.conn.commit()
            self.sale_popup.destroy()
            self.show_inventory()
            messagebox.showinfo("Success", "Sale Recorded")
            self._set_status(f"Sale recorded: {name} (-{qty_sold})")
        except Exception as e: messagebox.showerror("Error", str(e))

    def show_product_image_popup(self, event=None):
        sel = self.tree.selection()
        if not sel: return
        pid = self.tree.item(sel)['values'][0]
        self.cursor.execute("SELECT image FROM inventory_v2 WHERE id=?", (pid,))
        res = self.cursor.fetchone()
        if res and res[0] and os.path.exists(os.path.join(self.base_dir, res[0])):
            self._preview_image_file(os.path.join(self.base_dir, res[0]), "Image Preview")
        else:
            messagebox.showinfo("Info", "No image found")

    def show_marketplace(self):
        # 1. Clear existing content EXCEPT the header
        for child in list(self.main_content_frame.winfo_children()):
            if child is self.header_frame: continue
            child.destroy()

        # 2. Setup Scrollable Area
        market_frame = ttk.Frame(self.main_content_frame)
        market_frame.pack(fill='both', expand=True)

        canvas = tk.Canvas(market_frame, bg=ThemeColors['bg_dark'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(market_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style='bg_dark.TFrame')

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 3. Fetch Data
        self.cursor.execute("SELECT id, name, price, image FROM inventory_v2")
        rows = self.cursor.fetchall()
        columns = 4
        thumb_size = (150, 150)
        self._marketplace_images = [] 

        for index, row_data in enumerate(rows):
            pid, name, price, img_rel = row_data
            r, c = index // columns, index % columns

            card = ttk.Frame(scrollable_frame, style='Card.TFrame', padding=10)
            card.grid(row=r, column=c, padx=15, pady=15, sticky="nsew")

            img_path = self._resolve_image_path(img_rel)
            tk_image = None
            if img_path and os.path.exists(img_path) and PIL_AVAILABLE:
                try:
                    pil_img = Image.open(img_path)
                    pil_img.thumbnail(thumb_size)
                    tk_image = ImageTk.PhotoImage(pil_img)
                    self._marketplace_images.append(tk_image) 
                except: pass

            if tk_image:
                img_lbl = ttk.Label(card, image=tk_image, background=ThemeColors['bg_panel'])
                img_lbl.pack(pady=(0, 10))
                img_lbl.bind("<Button-1>", lambda e, p=img_path, n=name: self._preview_image_file(p, n))
            else:
                ttk.Label(card, text="[No Image]", font=("Segoe UI", 9), background=ThemeColors['bg_panel'], foreground=ThemeColors['text_dim']).pack(pady=(0, 10), ipady=20)

            ttk.Label(card, text=name, font=("Segoe UI", 11, "bold"), background=ThemeColors['bg_panel'], wraplength=140, justify="center").pack()
            ttk.Label(card, text=f"${price:.2f}", font=("Segoe UI", 10), foreground=ThemeColors['accent'], background=ThemeColors['bg_panel']).pack()
            ttk.Button(card, text="Buy Now", style="Accent.TButton", width=10, command=lambda p=pid: self.quick_sell(p)).pack(pady=(10, 0))

    def quick_sell(self, product_id):
        self.open_record_sale_popup(product_id=product_id)
        
    def show_dashboard(self):
        # FIX: Clear current view to prevent overlap
        for child in list(self.main_content_frame.winfo_children()):
            if child is self.header_frame: continue
            child.destroy()
            
        self.build_dashboard_view()
        self.refresh_summary()
        self._set_status("Dashboard loaded")

    def _prompt_conflict_handling(self):
        dialog = ttk.Toplevel(self.root)
        dialog.title("CSV Conflicts")
        dialog.geometry("360x220")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(
            dialog,
            text="Conflicts detected in the import file.\nChoose how to handle them:",
            justify="left",
        ).pack(padx=16, pady=(16, 10), anchor="w")

        choice_var = tk.StringVar(value="update")

        ttk.Radiobutton(
            dialog,
            text="Update existing items",
            variable=choice_var,
            value="update",
        ).pack(anchor="w", padx=16)
        ttk.Radiobutton(
            dialog,
            text="Skip conflicting rows",
            variable=choice_var,
            value="skip",
        ).pack(anchor="w", padx=16, pady=(0, 6))

        btns = ttk.Frame(dialog)
        btns.pack(fill="x", padx=16, pady=(10, 16))

        result = {"value": None}

        def on_ok():
            result["value"] = choice_var.get()
            dialog.destroy()

        def on_cancel():
            result["value"] = None
            dialog.destroy()

        ttk.Button(btns, text="Continue", style="Accent.TButton", command=on_ok).pack(side="left", expand=True, fill="x", padx=(0, 6))
        ttk.Button(btns, text="Cancel", bootstyle="secondary", command=on_cancel).pack(side="left", expand=True, fill="x")

        dialog.wait_window()
        return result["value"]

    def _read_csv_rows(self, path):
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            rows = list(reader)
        if not rows:
            return []
        header = [c.strip().lower() for c in rows[0]]
        has_header = any(h in ("name", "title", "sku", "quantity", "qty", "price", "category") for h in header)
        if has_header:
            with open(path, newline="", encoding="utf-8-sig") as f:
                dict_reader = csv.DictReader(f)
                return list(dict_reader)
        columns = ["id", "sku", "name", "category", "quantity", "price", "status", "image"]
        mapped = []
        for r in rows:
            row = {}
            for i, col in enumerate(columns):
                if i < len(r):
                    row[col] = r[i]
            mapped.append(row)
        return mapped

    def _normalize_csv_row(self, row):
        norm = {}
        for k, v in row.items():
            key = str(k).strip().lower()
            norm[key] = v.strip() if isinstance(v, str) else v
        if "title" in norm and "name" not in norm:
            norm["name"] = norm["title"]
        if "qty" in norm and "quantity" not in norm:
            norm["quantity"] = norm["qty"]
        if "barcode" in norm and (not norm.get("sku")):
            norm["sku"] = norm["barcode"]
        return norm

    def _parse_int(self, value):
        if value is None or str(value).strip() == "":
            return None
        try:
            return int(float(str(value).strip()))
        except Exception:
            return None

    def _parse_float(self, value):
        if value is None or str(value).strip() == "":
            return None
        try:
            return float(str(value).strip())
        except Exception:
            return None

    def import_from_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")])
        if not path:
            return
        try:
            rows = self._read_csv_rows(path)
        except Exception as e:
            messagebox.showerror("Import Failed", f"Could not read CSV:\n{e}")
            return
        if not rows:
            messagebox.showinfo("Import", "No rows found in the CSV.")
            return

        self.cursor.execute("SELECT id, sku FROM inventory_v2")
        existing_ids = {int(r[0]) for r in self.cursor.fetchall() if r[0] is not None}
        self.cursor.execute("SELECT sku FROM inventory_v2 WHERE sku IS NOT NULL AND sku != ''")
        existing_skus = {r[0] for r in self.cursor.fetchall()}

        choice = None
        imported = updated = skipped = invalid = 0

        for raw in rows:
            row = self._normalize_csv_row(raw)
            name = str(row.get("name", "")).strip()
            sku = str(row.get("sku", "")).strip()
            category = str(row.get("category", "")).strip() or "Uncategorized"
            qty = self._parse_int(row.get("quantity"))
            price = self._parse_float(row.get("price"))
            row_id = self._parse_int(row.get("id"))
            image = row.get("image") or None

            if not name or qty is None or price is None:
                invalid += 1
                continue
            if qty < 0 or price < 0:
                invalid += 1
                continue

            conflict_id = row_id is not None and row_id in existing_ids
            conflict_sku = bool(sku) and sku in existing_skus

            if conflict_id or conflict_sku:
                if choice is None:
                    choice = self._prompt_conflict_handling()
                    if choice is None:
                        return
                if choice == "skip":
                    skipped += 1
                    continue

                status = self._compute_status(qty, category)
                if conflict_id:
                    self.cursor.execute(
                        "UPDATE inventory_v2 SET sku=?, name=?, category=?, quantity=?, price=?, status=?, image=? WHERE id=?",
                        (sku, name, category, qty, price, status, image, row_id),
                    )
                else:
                    self.cursor.execute(
                        "UPDATE inventory_v2 SET name=?, category=?, quantity=?, price=?, status=?, image=? WHERE sku=?",
                        (name, category, qty, price, status, image, sku),
                    )
                updated += 1
            else:
                status = self._compute_status(qty, category)
                self.cursor.execute(
                    "INSERT INTO inventory_v2 (sku, name, category, quantity, price, status, image) VALUES (?,?,?,?,?,?,?)",
                    (sku, name, category, qty, price, status, image),
                )
                imported += 1
                if sku:
                    existing_skus.add(sku)

        self.conn.commit()
        self.show_inventory()
        self.refresh_summary()
        messagebox.showinfo(
            "Import Complete",
            f"Imported: {imported}\nUpdated: {updated}\nSkipped: {skipped}\nInvalid: {invalid}",
        )
        self._set_status(f"Imported CSV: {imported} new, {updated} updated, {skipped} skipped, {invalid} invalid")

    def _lookup_scanned_code(self, code):
        if not code:
            return
        if not hasattr(self, "tree") or not self.tree.winfo_exists():
            self.show_dashboard()
        self.entry_search.delete(0, "end")
        self.entry_search.insert(0, code)
        self.entry_search.configure(foreground=ThemeColors["text_light"])
        count = self.search_product()
        if count == 0:
            messagebox.showinfo("Not Found", f"No item matched code: {code}")
        else:
            self._set_status(f"Scan matched {count} item(s)")

    def _update_scanner_preview(self):
        if not hasattr(self, "_scanner_top") or not self._scanner_top.winfo_exists():
            return
        if not getattr(self, "_scanner_active", False):
            return
        if PIL_AVAILABLE and getattr(self, "_scanner_frame", None) is not None:
            try:
                frame = cv2.cvtColor(self._scanner_frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame)
                img.thumbnail((360, 240))
                tkimg = ImageTk.PhotoImage(img)
                self._scanner_preview.configure(image=tkimg)
                self._scanner_preview.image = tkimg
            except Exception:
                pass
        self.root.after(100, self._update_scanner_preview)

    def _scanner_loop(self, auto_stop=True):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self.root.after(0, lambda: self._scanner_status.set("Camera not available"))
            return
        self._scanner_active = True
        self.root.after(0, lambda: self._scanner_status.set("Scanning..."))
        while not self._scanner_stop.is_set():
            ret, frame = cap.read()
            if not ret:
                continue
            self._scanner_frame = frame
            codes = pyzbar.decode(frame)
            if codes:
                code = codes[0].data.decode("utf-8", errors="ignore")
                if code and code != getattr(self, "_scanner_last_code", ""):
                    self._scanner_last_code = code
                    self.root.after(0, lambda c=code: self._on_scanned_code(c))
                    if auto_stop:
                        break
        cap.release()
        self._scanner_active = False
        self._scanner_stop.set()
        self.root.after(0, lambda: self._scanner_status.set("Scanner stopped"))

    def _on_scanned_code(self, code):
        if hasattr(self, "_scanner_entry") and self._scanner_entry.winfo_exists():
            self._scanner_entry.delete(0, "end")
            self._scanner_entry.insert(0, code)
        self._lookup_scanned_code(code)

    def start_camera_scanner(self):
        if hasattr(self, "_scanner_top") and self._scanner_top and self._scanner_top.winfo_exists():
            self._scanner_top.lift()
            return

        self._scanner_top = ttk.Toplevel(self.root)
        self._scanner_top.title("Barcode Scanner")
        self._scanner_top.geometry("420x520")
        self._scanner_top.transient(self.root)
        self._scanner_top.grab_set()

        container = ttk.Frame(self._scanner_top, padding=16)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text="Barcode / SKU:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self._scanner_entry = ttk.Entry(container)
        self._scanner_entry.pack(fill="x", pady=(4, 8))
        self._scanner_entry.bind("<Return>", lambda e: self._lookup_scanned_code(self._scanner_entry.get().strip()))

        ttk.Button(
            container,
            text="Lookup",
            style="Accent.TButton",
            command=lambda: self._lookup_scanned_code(self._scanner_entry.get().strip()),
        ).pack(fill="x")

        ttk.Separator(container).pack(fill="x", pady=12)

        self._scanner_status = tk.StringVar(value="Scanner idle")
        ttk.Label(container, textvariable=self._scanner_status).pack(anchor="w")

        scanner_available = CV2_AVAILABLE and PYZBAR_AVAILABLE
        if not scanner_available:
            ttk.Label(
                container,
                text="Camera scanning unavailable. Install opencv-python and pyzbar\nor use manual entry above.",
                foreground=ThemeColors["text_dim"],
                justify="left",
            ).pack(anchor="w", pady=(6, 0))
        else:
            self._scanner_preview = ttk.Label(container)
            self._scanner_preview.pack(pady=(8, 6))

            controls = ttk.Frame(container)
            controls.pack(fill="x")

            self._scanner_stop = threading.Event()
            self._scanner_active = False
            self._scanner_last_code = ""

            def start_scan():
                if self._scanner_active:
                    return
                self._scanner_stop.clear()
                auto_stop = True
                t = threading.Thread(target=self._scanner_loop, args=(auto_stop,), daemon=True)
                t.start()
                self._scanner_thread = t
                self._update_scanner_preview()

            def stop_scan():
                self._scanner_stop.set()

            ttk.Button(controls, text="Start Camera", bootstyle="success", command=start_scan).pack(side="left", expand=True, fill="x", padx=(0, 6))
            ttk.Button(controls, text="Stop", bootstyle="secondary", command=stop_scan).pack(side="left", expand=True, fill="x")

        def on_close():
            try:
                if hasattr(self, "_scanner_stop"):
                    self._scanner_stop.set()
            except Exception:
                pass
            self._scanner_top.destroy()

        self._scanner_top.protocol("WM_DELETE_WINDOW", on_close)
        self._set_status("Scanner ready")

    def export_to_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv")
        if path:
            self.cursor.execute("SELECT id, sku, name, category, quantity, price, status, image FROM inventory_v2")
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["id", "sku", "name", "category", "quantity", "price", "status", "image"])
                writer.writerows(self.cursor.fetchall())
            messagebox.showinfo("Export", "Saved.")
            self._set_status(f"Exported CSV to {path}")

    def on_close(self):
        self.conn.close()
        self.root.destroy()

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    root = ttk.Window(themename="cyborg")
    root.withdraw() 

    def launch_app(user, role):
        root.deiconify() 
        app = InventoryApp(root, user, role)

    login_win = LoginWindow(root, launch_app)
    root.mainloop()
