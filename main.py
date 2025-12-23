"""
Abaad 3D Print Manager v4.0 (ERP Edition)
Main Application Entry Point with RBAC
Professional GUI with Modern Design
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime
from pathlib import Path
import sys
import os

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src import (
    get_database, Order, PrintItem, FilamentSpool, Customer, Printer,
    PrintSettings, FilamentHistory, OrderStatus, PaymentMethod, SupportType, 
    SpoolCategory, SpoolStatus, PaymentSource, format_time, generate_id, now_str,
    DEFAULT_RATE_PER_GRAM, DEFAULT_COST_PER_GRAM, TRASH_THRESHOLD_GRAMS,
    TOLERANCE_THRESHOLD_GRAMS, calculate_payment_fee,
    # Failures and expenses
    PrintFailure, Expense, FailureReason, ExpenseCategory, FailureSource
)

from src.logic import (
    get_auth_manager, get_cura_vision, UserRole, Permission,
    PILLOW_AVAILABLE, TESSERACT_AVAILABLE
)

from src.ui import LoginDialog, ChangePasswordDialog, AdminPanel, Colors

try:
    from src.utils import generate_receipt, generate_quote, generate_invoice, REPORTLAB_AVAILABLE
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    from src.logic import extract_from_cura_screenshot
    CURA_VISION_AVAILABLE = get_cura_vision().is_available
except:
    CURA_VISION_AVAILABLE = False

# Check for matplotlib availability for charts
MATPLOTLIB_AVAILABLE = False
try:
    import matplotlib
    matplotlib.use('TkAgg')
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    pass


class App:
    def __init__(self, root, user):
        self.root = root
        self.user = user
        self.auth = get_auth_manager()
        self.root.title(f"Abaad ERP v4.0 - {user.display_name or user.username}")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 700)
        self.root.configure(bg=Colors.BG)
        
        # Try to set window icon - works on Windows, Linux, and Mac
        try:
            import sys
            icon_set = False
            
            # Try ICO first (Windows)
            ico_path = Path(__file__).parent / "assets" / "Print3D_Manager.ico"
            if ico_path.exists() and sys.platform == 'win32':
                try:
                    self.root.iconbitmap(str(ico_path))
                    icon_set = True
                except:
                    pass
            
            # Fallback to PNG (works on Linux, Mac, and Windows)
            if not icon_set:
                png_path = Path(__file__).parent / "assets" / "Abaad.png"
                if png_path.exists():
                    try:
                        self.icon_img = tk.PhotoImage(file=str(png_path))
                        self.root.iconphoto(True, self.icon_img)
                        icon_set = True
                    except:
                        pass
            
            # Also set window title icon for Linux window managers
            if sys.platform != 'win32':
                self.root.wm_iconname('Abaad ERP')
        except Exception as e:
            print(f"Could not set window icon: {e}")
        
        self.db = get_database()
        self.current_order = None
        self.selected_customer = None
        
        self._setup_styles()
        self._build_ui()
        self._load_all_data()
        self._update_status_bar()
    
    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # General styles
        style.configure("TFrame", background=Colors.BG)
        style.configure("TLabel", background=Colors.BG, font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10), padding=6)
        
        # Notebook tabs
        style.configure("TNotebook", background=Colors.BG)
        style.configure("TNotebook.Tab", padding=[20, 10], font=("Segoe UI", 11))
        style.map("TNotebook.Tab", 
                  background=[("selected", Colors.PRIMARY), ("!selected", Colors.CARD)],
                  foreground=[("selected", "white"), ("!selected", Colors.TEXT)])
        
        # Custom label styles
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"), foreground=Colors.TEXT)
        style.configure("Subtitle.TLabel", font=("Segoe UI", 12), foreground=Colors.TEXT_SECONDARY)
        style.configure("Header.TLabel", font=("Segoe UI", 13, "bold"), foreground=Colors.PRIMARY)
        
        # LabelFrame
        style.configure("TLabelframe", background=Colors.BG, borderwidth=1)
        style.configure("TLabelframe.Label", font=("Segoe UI", 10, "bold"), 
                       foreground=Colors.PRIMARY, background=Colors.BG)
        
        # Entry & Combobox
        style.configure("TEntry", padding=5)
        style.configure("TCombobox", padding=5)
        
        # Treeview
        style.configure("Treeview", font=("Segoe UI", 10), rowheight=28)
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), 
                       background=Colors.PRIMARY, foreground="white")
        style.map("Treeview", background=[("selected", Colors.PRIMARY_LIGHT)])
        
        # Accent button
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))
    
    def _build_ui(self):
        """Build the main UI with header, content, and status bar"""
        
        # === HEADER BAR ===
        header = tk.Frame(self.root, bg=Colors.PRIMARY, height=70)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        # Left side - Logo & Title
        left_header = tk.Frame(header, bg=Colors.PRIMARY)
        left_header.pack(side=tk.LEFT, padx=20, pady=10)
        
        tk.Label(left_header, text="🖨️", font=("Segoe UI", 28), 
                bg=Colors.PRIMARY, fg="white").pack(side=tk.LEFT)
        
        title_frame = tk.Frame(left_header, bg=Colors.PRIMARY)
        title_frame.pack(side=tk.LEFT, padx=10)
        
        tk.Label(title_frame, text="Abaad ERP", font=("Segoe UI", 18, "bold"),
                fg="white", bg=Colors.PRIMARY).pack(anchor=tk.W)
        tk.Label(title_frame, text="3D Print Management System", font=("Segoe UI", 9),
                fg="#94a3b8", bg=Colors.PRIMARY).pack(anchor=tk.W)
        
        # Right side - User info
        right_header = tk.Frame(header, bg=Colors.PRIMARY)
        right_header.pack(side=tk.RIGHT, padx=20)
        
        # Feature badges
        badge_frame = tk.Frame(right_header, bg=Colors.PRIMARY)
        badge_frame.pack(side=tk.LEFT, padx=20)
        
        if REPORTLAB_AVAILABLE:
            self._create_badge(badge_frame, "📄 PDF", Colors.SUCCESS)
        if CURA_VISION_AVAILABLE:
            self._create_badge(badge_frame, "🤖 AI", Colors.SUCCESS)
        
        # User info
        user_frame = tk.Frame(right_header, bg=Colors.PRIMARY)
        user_frame.pack(side=tk.LEFT, padx=10)
        
        role_icon = "👑" if self.user.role == UserRole.ADMIN.value else "👤"
        role_name = "Admin" if self.user.role == UserRole.ADMIN.value else "User"
        role_color = Colors.WARNING if self.user.role == UserRole.ADMIN.value else Colors.INFO
        
        tk.Label(user_frame, text=f"{role_icon} {self.user.display_name or self.user.username}", 
                font=("Segoe UI", 11, "bold"), fg="white", bg=Colors.PRIMARY).pack(side=tk.LEFT, padx=5)
        
        # Role badge
        role_badge = tk.Frame(user_frame, bg=role_color, padx=8, pady=2)
        role_badge.pack(side=tk.LEFT, padx=5)
        tk.Label(role_badge, text=role_name, font=("Segoe UI", 9, "bold"), 
                fg="white", bg=role_color).pack()
        
        # Switch user button
        switch_btn = tk.Button(user_frame, text="🔄 Switch", font=("Segoe UI", 9),
                              command=self._logout, relief=tk.FLAT, bd=0,
                              bg="#ef4444", fg="white", cursor="hand2",
                              padx=10, pady=4)
        switch_btn.pack(side=tk.LEFT, padx=(15, 0))
        
        # === MAIN CONTENT ===
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=15, pady=(10, 0))
        
        # Build tabs based on user permissions
        self._build_orders_tab()
        self._build_customers_tab()
        self._build_filament_tab()
        self._build_printers_tab()
        self._build_failures_tab()  # Print failures tracking
        self._build_expenses_tab()  # Business expenses tracking
        
        # Admin-only tabs
        if self.auth.has_permission(Permission.VIEW_STATISTICS):
            self._build_stats_tab()
            if MATPLOTLIB_AVAILABLE:
                self._build_analytics_tab()  # NEW: Visual analytics with charts
        
        self._build_trash_tab()  # NEW: Access to deleted orders
        
        if self.auth.has_permission(Permission.MANAGE_SETTINGS):
            self._build_settings_tab()
        
        if self.auth.has_permission(Permission.MANAGE_USERS):
            self._build_admin_tab()
        
        # Fix order numbering on startup if needed
        self.db.fix_order_numbering()
        
        # === STATUS BAR ===
        self.status_bar = tk.Frame(self.root, bg=Colors.BG_DARK, height=35)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_bar.pack_propagate(False)
        
        self.status_left = tk.Label(self.status_bar, text="Ready", font=("Segoe UI", 9),
                                   bg=Colors.BG_DARK, fg=Colors.TEXT_LIGHT)
        self.status_left.pack(side=tk.LEFT, padx=15)
        
        self.status_right = tk.Label(self.status_bar, text="", font=("Segoe UI", 9),
                                    bg=Colors.BG_DARK, fg=Colors.TEXT_LIGHT)
        self.status_right.pack(side=tk.RIGHT, padx=15)
    
    def _create_badge(self, parent, text, color):
        """Create a small status badge"""
        badge = tk.Frame(parent, bg=color, padx=6, pady=2)
        badge.pack(side=tk.LEFT, padx=3)
        tk.Label(badge, text=text, font=("Segoe UI", 8, "bold"),
                bg=color, fg="white").pack()
    
    def _update_status_bar(self):
        """Update status bar with current info"""
        stats = self.db.get_statistics()
        orders = len(self.db.get_all_orders())
        spools = len([s for s in self.db.get_all_spools() if s.is_active])
        
        self.status_left.config(text=f"📦 {orders} Orders  |  🎨 {spools} Active Spools  |  💰 {stats.total_revenue:.0f} EGP Revenue")
        self.status_right.config(text=f"v4.0 ERP  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    def _build_admin_tab(self):
        """Admin Panel tab - Admin only"""
        admin_panel = AdminPanel(self.notebook, self.db)
        self.notebook.add(admin_panel, text="👑 Admin Panel")
    
    def _change_password(self):
        """Open change password dialog"""
        ChangePasswordDialog(self.root)
    
    def _logout(self):
        """Switch user - go back to role selection"""
        if messagebox.askyesno("Switch User", "Switch to a different user role?"):
            self.auth.logout()
            self.root.destroy()
            main()  # Restart with login
    
    def _set_status(self, message):
        """Update status bar message"""
        self.status_left.config(text=message)
        self.root.update_idletasks()
    
    def _build_orders_tab(self):
        tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(tab, text="📦 Orders")
        
        # Left panel - Order list
        left = ttk.Frame(tab)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 15))
        
        # Header with title and new button
        header = ttk.Frame(left)
        header.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header, text="📦 Order Management", style="Title.TLabel").pack(side=tk.LEFT)
        
        new_btn = tk.Button(header, text="➕ New Order", font=("Segoe UI", 10, "bold"),
                           bg=Colors.SUCCESS, fg="white", relief=tk.FLAT, padx=15, pady=5,
                           cursor="hand2", command=self._new_order)
        new_btn.pack(side=tk.RIGHT)
        
        # Search and filter row
        search_f = ttk.Frame(left)
        search_f.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(search_f, text="🔍").pack(side=tk.LEFT, padx=(0, 5))
        self.order_search = ttk.Entry(search_f, width=25, font=("Segoe UI", 10))
        self.order_search.pack(side=tk.LEFT, padx=5)
        self.order_search.insert(0, "Search orders...")
        self.order_search.bind('<FocusIn>', lambda e: self.order_search.delete(0, tk.END) if self.order_search.get() == "Search orders..." else None)
        self.order_search.bind('<FocusOut>', lambda e: self.order_search.insert(0, "Search orders...") if not self.order_search.get() else None)
        self.order_search.bind('<KeyRelease>', lambda e: self._filter_orders())
        
        ttk.Label(search_f, text="Status:").pack(side=tk.LEFT, padx=(15, 5))
        self.status_filter = ttk.Combobox(search_f, values=["All"] + [s.value for s in OrderStatus], 
                                          state="readonly", width=12)
        self.status_filter.set("All")
        self.status_filter.pack(side=tk.LEFT, padx=5)
        self.status_filter.bind('<<ComboboxSelected>>', lambda e: self._filter_orders())
        
        # Orders list with scrollbar
        list_frame = ttk.Frame(left)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        cols = ("Order#", "Customer", "Items", "Total", "Status", "Date", "R&D")
        self.orders_tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=22)
        for col, w in zip(cols, [70, 140, 50, 80, 90, 90, 45]):
            self.orders_tree.heading(col, text=col)
            self.orders_tree.column(col, width=w, anchor=tk.CENTER if col not in ["Customer"] else tk.W)
        
        scroll = ttk.Scrollbar(list_frame, command=self.orders_tree.yview)
        self.orders_tree.configure(yscrollcommand=scroll.set)
        self.orders_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.orders_tree.bind('<<TreeviewSelect>>', self._on_order_select)
        
        # Right panel - Order details
        right = ttk.Frame(tab)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Order title with icon
        title_frame = ttk.Frame(right)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.order_title = ttk.Label(title_frame, text="📝 New Order", style="Title.TLabel")
        self.order_title.pack(side=tk.LEFT)
        
        cust_f = ttk.LabelFrame(right, text="Customer", padding=8)
        cust_f.pack(fill=tk.X, pady=5)
        
        row1 = ttk.Frame(cust_f)
        row1.pack(fill=tk.X)
        ttk.Label(row1, text="Name:").pack(side=tk.LEFT)
        self.cust_name = ttk.Entry(row1, width=20)
        self.cust_name.pack(side=tk.LEFT, padx=5)
        ttk.Label(row1, text="Phone:").pack(side=tk.LEFT, padx=(10, 0))
        self.cust_phone = ttk.Entry(row1, width=15)
        self.cust_phone.pack(side=tk.LEFT, padx=5)
        ttk.Button(row1, text="🔍", command=self._find_customer).pack(side=tk.LEFT, padx=5)
        
        row2 = ttk.Frame(cust_f)
        row2.pack(fill=tk.X, pady=(5, 0))
        ttk.Label(row2, text="Status:").pack(side=tk.LEFT)
        self.order_status = ttk.Combobox(row2, values=[s.value for s in OrderStatus], state="readonly", width=12)
        self.order_status.set("Draft")
        self.order_status.pack(side=tk.LEFT, padx=5)
        self.rd_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row2, text="🔬 R&D Project", variable=self.rd_var, command=self._on_rd_toggle).pack(side=tk.LEFT, padx=15)
        
        items_f = ttk.LabelFrame(right, text="Print Items", padding=8)
        items_f.pack(fill=tk.BOTH, expand=True, pady=5)
        
        items_tb = ttk.Frame(items_f)
        items_tb.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(items_tb, text="+ Add", command=self._add_item).pack(side=tk.LEFT, padx=2)
        ttk.Button(items_tb, text="Edit", command=self._edit_item).pack(side=tk.LEFT, padx=2)
        ttk.Button(items_tb, text="Remove", command=self._remove_item).pack(side=tk.LEFT, padx=2)
        ttk.Button(items_tb, text="Set Weight", command=self._set_actual_weight).pack(side=tk.LEFT, padx=2)
        
        cols = ("Name", "Color", "Weight", "Time", "Settings", "Qty", "Rate", "Total")
        self.items_tree = ttk.Treeview(items_f, columns=cols, show="headings", height=7)
        for col, w in zip(cols, [100, 60, 55, 45, 80, 30, 40, 60]):
            self.items_tree.heading(col, text=col)
            self.items_tree.column(col, width=w)
        self.items_tree.pack(fill=tk.BOTH, expand=True)
        
        totals_f = ttk.LabelFrame(right, text="Payment & Totals", padding=8)
        totals_f.pack(fill=tk.X, pady=5)
        
        row_t1 = ttk.Frame(totals_f)
        row_t1.pack(fill=tk.X)
        ttk.Label(row_t1, text="Base:").pack(side=tk.LEFT)
        self.base_total_lbl = ttk.Label(row_t1, text="0.00")
        self.base_total_lbl.pack(side=tk.LEFT, padx=5)
        ttk.Label(row_t1, text="Actual:").pack(side=tk.LEFT, padx=(10, 0))
        self.actual_total_lbl = ttk.Label(row_t1, text="0.00", font=("Segoe UI", 10, "bold"), foreground=Colors.PRIMARY)
        self.actual_total_lbl.pack(side=tk.LEFT, padx=5)
        ttk.Label(row_t1, text="Disc:").pack(side=tk.LEFT, padx=(10, 0))
        self.discount_lbl = ttk.Label(row_t1, text="0%", foreground=Colors.SUCCESS)
        self.discount_lbl.pack(side=tk.LEFT, padx=5)
        
        row_t1b = ttk.Frame(totals_f)
        row_t1b.pack(fill=tk.X, pady=(3, 0))
        ttk.Label(row_t1b, text="Order Disc %:").pack(side=tk.LEFT)
        self.order_discount_entry = ttk.Entry(row_t1b, width=5)
        self.order_discount_entry.insert(0, "0")
        self.order_discount_entry.pack(side=tk.LEFT, padx=5)
        self.order_discount_entry.bind('<KeyRelease>', lambda e: self._calc_totals())
        self.order_discount_amt_lbl = ttk.Label(row_t1b, text="(-0.00)", foreground=Colors.SUCCESS)
        self.order_discount_amt_lbl.pack(side=tk.LEFT, padx=5)
        self.tolerance_lbl = ttk.Label(row_t1b, text="", foreground=Colors.SUCCESS)
        self.tolerance_lbl.pack(side=tk.LEFT, padx=10)
        
        row_t2 = ttk.Frame(totals_f)
        row_t2.pack(fill=tk.X, pady=(5, 0))
        ttk.Label(row_t2, text="Payment:").pack(side=tk.LEFT)
        self.payment_method = ttk.Combobox(row_t2, values=[p.value for p in PaymentMethod], state="readonly", width=12)
        self.payment_method.set(PaymentMethod.CASH.value)
        self.payment_method.pack(side=tk.LEFT, padx=5)
        self.payment_method.bind('<<ComboboxSelected>>', lambda e: self._calc_totals())
        ttk.Label(row_t2, text="Fee:").pack(side=tk.LEFT, padx=(5, 0))
        self.payment_fee_lbl = ttk.Label(row_t2, text="0.00")
        self.payment_fee_lbl.pack(side=tk.LEFT, padx=5)
        ttk.Label(row_t2, text="Ship:").pack(side=tk.LEFT, padx=(5, 0))
        self.shipping_entry = ttk.Entry(row_t2, width=6)
        self.shipping_entry.insert(0, "0")
        self.shipping_entry.pack(side=tk.LEFT, padx=5)
        self.shipping_entry.bind('<KeyRelease>', lambda e: self._calc_totals())
        
        row_t2b = ttk.Frame(totals_f)
        row_t2b.pack(fill=tk.X, pady=(3, 0))
        ttk.Label(row_t2b, text="Received:").pack(side=tk.LEFT)
        self.amount_received_entry = ttk.Entry(row_t2b, width=8)
        self.amount_received_entry.insert(0, "0")
        self.amount_received_entry.pack(side=tk.LEFT, padx=5)
        self.amount_received_entry.bind('<KeyRelease>', lambda e: self._calc_totals())
        self.rounding_loss_lbl = ttk.Label(row_t2b, text="Rounding: 0", foreground=Colors.WARNING)
        self.rounding_loss_lbl.pack(side=tk.LEFT, padx=10)
        
        row_t3 = ttk.Frame(totals_f)
        row_t3.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(row_t3, text="TOTAL:", font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT)
        self.total_lbl = ttk.Label(row_t3, text="0.00 EGP", font=("Segoe UI", 14, "bold"), foreground=Colors.PRIMARY)
        self.total_lbl.pack(side=tk.LEFT, padx=10)
        ttk.Label(row_t3, text="Profit:").pack(side=tk.LEFT, padx=(15, 0))
        self.profit_lbl = ttk.Label(row_t3, text="0.00", foreground=Colors.SUCCESS)
        self.profit_lbl.pack(side=tk.LEFT, padx=5)
        self.rd_cost_lbl = ttk.Label(row_t3, text="", foreground=Colors.PURPLE)
        self.rd_cost_lbl.pack(side=tk.LEFT, padx=10)
        
        # Action buttons with better styling
        actions = ttk.Frame(right)
        actions.pack(fill=tk.X, pady=10)
        
        # Primary action - Save
        save_btn = tk.Button(actions, text="💾 Save Order", font=("Segoe UI", 10, "bold"),
                            bg=Colors.PRIMARY, fg="white", relief=tk.FLAT, padx=15, pady=6,
                            cursor="hand2", command=self._save_order)
        save_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Document generation buttons
        doc_frame = ttk.Frame(actions)
        doc_frame.pack(side=tk.LEFT, padx=10)
        
        tk.Button(doc_frame, text="📄 Quote", font=("Segoe UI", 9),
                 bg=Colors.INFO, fg="white", relief=tk.FLAT, padx=10, pady=4,
                 cursor="hand2", command=self._gen_quote_pdf).pack(side=tk.LEFT, padx=2)
        tk.Button(doc_frame, text="🧾 Receipt", font=("Segoe UI", 9),
                 bg=Colors.INFO, fg="white", relief=tk.FLAT, padx=10, pady=4,
                 cursor="hand2", command=self._gen_receipt_pdf).pack(side=tk.LEFT, padx=2)
        tk.Button(doc_frame, text="📋 Text", font=("Segoe UI", 9),
                 bg=Colors.TEXT_SECONDARY, fg="white", relief=tk.FLAT, padx=10, pady=4,
                 cursor="hand2", command=self._gen_receipt).pack(side=tk.LEFT, padx=2)
        
        # Secondary actions
        if self.auth.has_permission(Permission.DELETE_ORDER):
            tk.Button(actions, text="🗑️ Delete", font=("Segoe UI", 9),
                     bg=Colors.DANGER, fg="white", relief=tk.FLAT, padx=10, pady=4,
                     cursor="hand2", command=self._delete_order).pack(side=tk.RIGHT, padx=2)
        
        tk.Button(actions, text="✨ New", font=("Segoe UI", 9),
                 bg=Colors.SUCCESS, fg="white", relief=tk.FLAT, padx=10, pady=4,
                 cursor="hand2", command=self._new_order).pack(side=tk.RIGHT, padx=2)
        
        # Notes section
        notes_frame = ttk.LabelFrame(right, text="📝 Order Notes", padding=5)
        notes_frame.pack(fill=tk.X, pady=(5, 0))
        self.order_notes = tk.Text(notes_frame, height=2, font=("Segoe UI", 10), 
                                  relief=tk.FLAT, bg=Colors.CARD)
        self.order_notes.pack(fill=tk.X)

    def _build_customers_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="👥 Customers")
        
        left = ttk.Frame(tab)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        header = ttk.Frame(left)
        header.pack(fill=tk.X)
        ttk.Label(header, text="Customer Archive", style="Title.TLabel").pack(side=tk.LEFT)
        
        if self.auth.has_permission(Permission.MANAGE_CUSTOMERS):
            ttk.Button(header, text="+ Add", command=self._add_customer).pack(side=tk.RIGHT)
        
        self.cust_search = ttk.Entry(left, width=30)
        self.cust_search.pack(fill=tk.X, pady=5)
        self.cust_search.bind('<KeyRelease>', lambda e: self._filter_customers())
        
        cols = ("Name", "Phone", "Disc", "Orders", "Spent")
        self.custs_tree = ttk.Treeview(left, columns=cols, show="headings", height=20)
        for col, w in zip(cols, [140, 100, 50, 50, 80]):
            self.custs_tree.heading(col, text=col)
            self.custs_tree.column(col, width=w)
        self.custs_tree.pack(fill=tk.BOTH, expand=True)
        self.custs_tree.bind('<<TreeviewSelect>>', self._on_cust_select)
        
        right = ttk.Frame(tab)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        ttk.Label(right, text="Customer Details", style="Title.TLabel").pack(anchor=tk.W)
        
        form = ttk.LabelFrame(right, text="Info", padding=10)
        form.pack(fill=tk.X, pady=5)
        
        for i, (lbl, attr) in enumerate([("Name:", "cd_name"), ("Phone:", "cd_phone"), ("Email:", "cd_email"), ("Disc %:", "cd_discount")]):
            ttk.Label(form, text=lbl).grid(row=i, column=0, sticky=tk.W, pady=2)
            e = ttk.Entry(form, width=35)
            e.grid(row=i, column=1, sticky=tk.EW, pady=2, padx=5)
            setattr(self, attr, e)
        
        self.cust_stats = ttk.Label(right, text="")
        self.cust_stats.pack(anchor=tk.W, pady=5)
        
        btn_f = ttk.Frame(right)
        btn_f.pack(fill=tk.X, pady=5)
        
        if self.auth.has_permission(Permission.MANAGE_CUSTOMERS):
            ttk.Button(btn_f, text="Save", command=self._save_customer).pack(side=tk.LEFT, padx=3)
        
        ttk.Button(btn_f, text="New Order", command=self._order_for_cust).pack(side=tk.LEFT, padx=3)
        
        if self.auth.has_permission(Permission.MANAGE_CUSTOMERS):
            ttk.Button(btn_f, text="Delete", command=self._del_customer).pack(side=tk.LEFT, padx=3)
    
    def _build_filament_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="🎨 Filament")
        
        header = ttk.Frame(tab)
        header.pack(fill=tk.X)
        ttk.Label(header, text="Filament Inventory", style="Title.TLabel").pack(side=tk.LEFT)
        
        if self.auth.has_permission(Permission.MANAGE_INVENTORY):
            ttk.Button(header, text="+ New Spool (840)", command=self._add_new_spool).pack(side=tk.RIGHT, padx=5)
            ttk.Button(header, text="+ Remaining (FREE)", command=self._add_remaining_spool).pack(side=tk.RIGHT, padx=5)
        
        # Enhanced summary with visual indicators
        summary_frame = ttk.LabelFrame(tab, text="📊 Inventory Overview", padding=8)
        summary_frame.pack(fill=tk.X, pady=5)
        
        self.spool_summary = ttk.Label(summary_frame, text="", font=("Segoe UI", 10))
        self.spool_summary.pack(anchor=tk.W)
        
        # Usage stats
        self.filament_stats = ttk.Label(summary_frame, text="", font=("Segoe UI", 9), foreground=Colors.TEXT_SECONDARY)
        self.filament_stats.pack(anchor=tk.W, pady=(5, 0))
        
        # Visual usage bar
        usage_bar_frame = ttk.Frame(summary_frame)
        usage_bar_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Label(usage_bar_frame, text="Overall Usage: ").pack(side=tk.LEFT)
        self.usage_bar = tk.Canvas(usage_bar_frame, width=300, height=20, bg=Colors.BG, highlightthickness=1, highlightbackground=Colors.BORDER)
        self.usage_bar.pack(side=tk.LEFT, padx=5)
        self.usage_label = ttk.Label(usage_bar_frame, text="0%")
        self.usage_label.pack(side=tk.LEFT)
        
        # Loan summary frame
        loan_frame = ttk.LabelFrame(tab, text="💳 Loan/Payment Status", padding=8)
        loan_frame.pack(fill=tk.X, pady=5)
        self.loan_summary = ttk.Label(loan_frame, text="", font=("Segoe UI", 9))
        self.loan_summary.pack(anchor=tk.W)
        
        cols = ("Name", "Color", "Type", "Initial", "Current", "Used%", "Cost/g", "Payment", "Status")
        self.spools_tree = ttk.Treeview(tab, columns=cols, show="headings", height=12)
        for col, w in zip(cols, [140, 70, 55, 60, 60, 50, 50, 130, 60]):
            self.spools_tree.heading(col, text=col)
            self.spools_tree.column(col, width=w)
        self.spools_tree.pack(fill=tk.BOTH, expand=True)
        
        # Configure row tags for coloring
        self.spools_tree.tag_configure('low', background='#fef3c7')
        self.spools_tree.tag_configure('empty', background='#fee2e2')
        self.spools_tree.tag_configure('trash', background='#e5e7eb')
        self.spools_tree.tag_configure('loan_unpaid', background='#fce7f3')  # Pink for unpaid loans
        self.spools_tree.tag_configure('loan_paid', background='#d1fae5')  # Green for paid loans
        
        btn_f = ttk.Frame(tab)
        btn_f.pack(fill=tk.X, pady=5)
        
        if self.auth.has_permission(Permission.MANAGE_INVENTORY):
            ttk.Button(btn_f, text="Edit", command=self._edit_spool).pack(side=tk.LEFT, padx=3)
            ttk.Button(btn_f, text="💳 Payment", command=self._edit_spool_payment).pack(side=tk.LEFT, padx=3)
            ttk.Button(btn_f, text="Delete", command=self._del_spool).pack(side=tk.LEFT, padx=3)
            ttk.Button(btn_f, text="🗑️ Trash", command=self._move_to_trash).pack(side=tk.LEFT, padx=3)
        
        ttk.Button(btn_f, text="📜 History", command=self._view_filament_history).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_f, text="📊 Color Chart", command=self._show_color_chart).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_f, text="📈 Consumption", command=self._show_consumption_chart).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_f, text="Refresh", command=self._load_spools).pack(side=tk.LEFT, padx=3)
    
    def _build_printers_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="🖨️ Printers")
        
        header = ttk.Frame(tab)
        header.pack(fill=tk.X)
        ttk.Label(header, text="Printer Management", style="Title.TLabel").pack(side=tk.LEFT)
        
        if self.auth.has_permission(Permission.MANAGE_PRINTERS):
            ttk.Button(header, text="+ Add Printer", command=self._add_printer).pack(side=tk.RIGHT)
        
        cols = ("Name", "Model", "Printed", "Time", "Nozzles", "Elec Cost", "Status")
        self.printers_tree = ttk.Treeview(tab, columns=cols, show="headings", height=10)
        for col, w in zip(cols, [100, 150, 80, 80, 60, 80, 70]):
            self.printers_tree.heading(col, text=col)
            self.printers_tree.column(col, width=w)
        self.printers_tree.pack(fill=tk.BOTH, expand=True, pady=5)
        
        detail_f = ttk.LabelFrame(tab, text="Printer Details", padding=10)
        detail_f.pack(fill=tk.X, pady=5)
        self.printer_detail = ttk.Label(detail_f, text="Select a printer to view details")
        self.printer_detail.pack(anchor=tk.W)
        self.printers_tree.bind('<<TreeviewSelect>>', self._on_printer_select)
        
        btn_f = ttk.Frame(tab)
        btn_f.pack(fill=tk.X)
        
        if self.auth.has_permission(Permission.MANAGE_PRINTERS):
            ttk.Button(btn_f, text="Edit", command=self._edit_printer).pack(side=tk.LEFT, padx=3)
            ttk.Button(btn_f, text="Reset Nozzle", command=self._reset_nozzle).pack(side=tk.LEFT, padx=3)
    
    def _build_failures_tab(self):
        """Print failures tracking tab"""
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="⚠️ Failures")
        
        # Header
        header = ttk.Frame(tab)
        header.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header, text="⚠️ Print Failures", style="Title.TLabel").pack(side=tk.LEFT)
        
        add_btn = tk.Button(header, text="➕ Log Failure", font=("Segoe UI", 10, "bold"),
                           bg=Colors.DANGER, fg="white", relief=tk.FLAT, padx=15, pady=5,
                           cursor="hand2", command=self._add_failure)
        add_btn.pack(side=tk.RIGHT)
        
        # Summary
        self.failure_summary = ttk.Label(tab, text="Loading...", style="Subtitle.TLabel")
        self.failure_summary.pack(anchor=tk.W, pady=5)
        
        # Filter
        filter_f = ttk.Frame(tab)
        filter_f.pack(fill=tk.X, pady=5)
        ttk.Label(filter_f, text="Source:").pack(side=tk.LEFT)
        self.failure_filter = ttk.Combobox(filter_f, values=["All"] + [s.value for s in FailureSource],
                                          state="readonly", width=15)
        self.failure_filter.set("All")
        self.failure_filter.pack(side=tk.LEFT, padx=5)
        self.failure_filter.bind('<<ComboboxSelected>>', lambda e: self._load_failures())
        
        # Failures list
        cols = ("Date", "Source", "Order/Item", "Reason", "Filament", "Cost")
        self.failures_tree = ttk.Treeview(tab, columns=cols, show="headings", height=12)
        for col, w in zip(cols, [90, 110, 180, 130, 70, 70]):
            self.failures_tree.heading(col, text=col)
            self.failures_tree.column(col, width=w)
        self.failures_tree.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Details panel
        detail_f = ttk.LabelFrame(tab, text="Failure Details", padding=10)
        detail_f.pack(fill=tk.X, pady=5)
        self.failure_detail = ttk.Label(detail_f, text="Select a failure to view details")
        self.failure_detail.pack(anchor=tk.W)
        self.failures_tree.bind('<<TreeviewSelect>>', self._on_failure_select)
        
        # Buttons
        btn_f = ttk.Frame(tab)
        btn_f.pack(fill=tk.X, pady=5)
        ttk.Button(btn_f, text="🔄 Refresh", command=self._load_failures).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_f, text="🗑️ Delete", command=self._delete_failure).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_f, text="📊 Stats", command=self._show_failure_stats).pack(side=tk.LEFT, padx=3)
    
    def _build_expenses_tab(self):
        """Business expenses tracking tab"""
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="💰 Expenses")
        
        # Header
        header = ttk.Frame(tab)
        header.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header, text="💰 Business Expenses", style="Title.TLabel").pack(side=tk.LEFT)
        
        add_btn = tk.Button(header, text="➕ Add Expense", font=("Segoe UI", 10, "bold"),
                           bg=Colors.WARNING, fg="white", relief=tk.FLAT, padx=15, pady=5,
                           cursor="hand2", command=self._add_expense)
        add_btn.pack(side=tk.RIGHT)
        
        # Summary
        self.expense_summary = ttk.Label(tab, text="Loading...", style="Subtitle.TLabel")
        self.expense_summary.pack(anchor=tk.W, pady=5)
        
        # Category filter
        filter_f = ttk.Frame(tab)
        filter_f.pack(fill=tk.X, pady=5)
        ttk.Label(filter_f, text="Category:").pack(side=tk.LEFT)
        self.expense_filter = ttk.Combobox(filter_f, values=["All"] + [c.value for c in ExpenseCategory],
                                          state="readonly", width=15)
        self.expense_filter.set("All")
        self.expense_filter.pack(side=tk.LEFT, padx=5)
        self.expense_filter.bind('<<ComboboxSelected>>', lambda e: self._load_expenses())
        
        # Expenses list
        cols = ("Date", "Category", "Name", "Qty", "Amount", "Total", "Supplier")
        self.expenses_tree = ttk.Treeview(tab, columns=cols, show="headings", height=12)
        for col, w in zip(cols, [90, 100, 180, 40, 80, 80, 120]):
            self.expenses_tree.heading(col, text=col)
            self.expenses_tree.column(col, width=w)
        self.expenses_tree.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Buttons
        btn_f = ttk.Frame(tab)
        btn_f.pack(fill=tk.X, pady=5)
        ttk.Button(btn_f, text="🔄 Refresh", command=self._load_expenses).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_f, text="✏️ Edit", command=self._edit_expense).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_f, text="🗑️ Delete", command=self._delete_expense).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_f, text="📊 Summary", command=self._show_expense_summary).pack(side=tk.LEFT, padx=3)
    
    def _build_stats_tab(self):
        """Statistics tab - Admin only"""
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="📊 Statistics")
        
        ttk.Label(tab, text="Business Dashboard", style="Title.TLabel").pack(anchor=tk.W, pady=(0, 10))
        
        self.stat_lbls = {}
        
        # Revenue section - expanded to show filament cost
        rev_f = ttk.LabelFrame(tab, text="💵 Revenue & Profit Breakdown", padding=10)
        rev_f.pack(fill=tk.X, pady=5)
        
        # First row - main metrics
        rev_cards = ttk.Frame(rev_f)
        rev_cards.pack(fill=tk.X)
        
        rev_stats = [("Revenue", "revenue", Colors.PRIMARY), ("- Filament Cost", "filament_cost", Colors.DANGER),
                    ("= Gross Profit", "gross_profit", Colors.SUCCESS), ("- All Deductions", "total_deductions", Colors.WARNING),
                    ("= NET PROFIT", "profit", Colors.SUCCESS)]
        
        for i, (label, key, color) in enumerate(rev_stats):
            frame = tk.Frame(rev_cards, bg=Colors.CARD, relief=tk.RIDGE, bd=1)
            frame.grid(row=0, column=i, padx=5, pady=5, sticky="nsew")
            tk.Label(frame, text=label, bg=Colors.CARD, fg=Colors.TEXT_LIGHT, font=("Segoe UI", 9)).pack(pady=(8, 0))
            lbl = tk.Label(frame, text="0", bg=Colors.CARD, fg=color, font=("Segoe UI", 14, "bold"))
            lbl.pack(pady=(0, 8))
            self.stat_lbls[key] = lbl
        for i in range(5):
            rev_cards.columnconfigure(i, weight=1)
        
        # Profit margin display
        margin_f = ttk.Frame(rev_f)
        margin_f.pack(fill=tk.X, pady=(5, 0))
        self.stat_lbls['profit_formula'] = ttk.Label(margin_f, text="", font=("Segoe UI", 9), foreground=Colors.TEXT_LIGHT)
        self.stat_lbls['profit_formula'].pack()
        
        # Orders section
        ord_f = ttk.LabelFrame(tab, text="📦 Orders & Production", padding=10)
        ord_f.pack(fill=tk.X, pady=5)
        ord_cards = ttk.Frame(ord_f)
        ord_cards.pack(fill=tk.X)
        
        ord_stats = [("Orders", "orders"), ("Completed", "completed"), ("R&D", "rd"), 
                    ("Weight", "weight"), ("Margin %", "margin")]
        
        for i, (label, key) in enumerate(ord_stats):
            frame = tk.Frame(ord_cards, bg=Colors.CARD, relief=tk.RIDGE, bd=1)
            frame.grid(row=0, column=i, padx=5, pady=5, sticky="nsew")
            tk.Label(frame, text=label, bg=Colors.CARD, fg=Colors.TEXT_LIGHT).pack(pady=(8, 0))
            lbl = tk.Label(frame, text="0", bg=Colors.CARD, fg=Colors.PRIMARY, font=("Segoe UI", 12, "bold"))
            lbl.pack(pady=(0, 8))
            self.stat_lbls[key] = lbl
        for i in range(5):
            ord_cards.columnconfigure(i, weight=1)
        
        # Costs section
        cost_f = ttk.LabelFrame(tab, text="📉 Costs Breakdown", padding=10)
        cost_f.pack(fill=tk.X, pady=5)
        cost_cards = ttk.Frame(cost_f)
        cost_cards.pack(fill=tk.X)
        
        cost_stats = [("Material", "material"), ("Electricity", "electricity"), ("Nozzle", "nozzle"),
                     ("Shipping", "shipping"), ("Fees", "fees"), ("Rounding", "rounding"),
                     ("Waste", "waste"), ("Spools", "spool_purchase")]
        
        for i, (label, key) in enumerate(cost_stats):
            row, col = i // 4, i % 4
            frame = tk.Frame(cost_cards, bg=Colors.CARD, relief=tk.RIDGE, bd=1)
            frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            tk.Label(frame, text=label, bg=Colors.CARD, fg=Colors.TEXT_LIGHT).pack(pady=(5, 0))
            lbl = tk.Label(frame, text="0", bg=Colors.CARD, fg=Colors.TEXT_SECONDARY, font=("Segoe UI", 11, "bold"))
            lbl.pack(pady=(0, 5))
            self.stat_lbls[key] = lbl
        for i in range(4):
            cost_cards.columnconfigure(i, weight=1)
        
        # Customers stat
        self.stat_lbls['custs'] = ttk.Label(tab, text="")
        
        btn_f = ttk.Frame(tab)
        btn_f.pack(pady=10)
        ttk.Button(btn_f, text="🔄 Refresh", command=self._load_stats).pack(side=tk.LEFT, padx=5)
        
        if self.auth.has_permission(Permission.EXPORT_DATA):
            ttk.Button(btn_f, text="📤 Export CSV", command=self._export_csv).pack(side=tk.LEFT, padx=5)
    
    def _build_analytics_tab(self):
        """Analytics tab with visual charts - Admin only"""
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="📈 Analytics")
        
        # Header
        header = ttk.Frame(tab)
        header.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header, text="📈 Business Analytics", style="Title.TLabel").pack(side=tk.LEFT)
        
        refresh_btn = tk.Button(header, text="🔄 Refresh Charts", font=("Segoe UI", 10),
                               bg=Colors.PRIMARY, fg="white", relief=tk.FLAT, padx=15, pady=5,
                               cursor="hand2", command=self._refresh_charts)
        refresh_btn.pack(side=tk.RIGHT)
        
        # Create a scrollable frame for charts
        canvas_frame = ttk.Frame(tab)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        # Store chart area for updates
        self.charts_frame = canvas_frame
        
        # Initial chart load
        self._load_charts()
    
    def _load_charts(self):
        """Load all analytics charts"""
        if not MATPLOTLIB_AVAILABLE:
            ttk.Label(self.charts_frame, text="📊 Install matplotlib for charts: pip install matplotlib").pack()
            return
        
        # Clear existing charts
        for widget in self.charts_frame.winfo_children():
            widget.destroy()
        
        # Get data
        monthly_stats = self.db.get_monthly_stats()
        color_stats = self.db.get_color_usage_stats()
        profit_breakdown = self.db.get_profit_breakdown()
        
        # Create figure with subplots
        fig = Figure(figsize=(14, 10), dpi=100, facecolor='#f8fafc')
        
        # Chart 1: Monthly Revenue & Profit (top left)
        ax1 = fig.add_subplot(2, 2, 1)
        if monthly_stats['months']:
            months = [m[-5:] for m in monthly_stats['months']]  # Show MM-YY
            x = range(len(months))
            width = 0.35
            
            bars1 = ax1.bar([i - width/2 for i in x], monthly_stats['revenue'], width, 
                           label='Revenue', color='#3b82f6', alpha=0.8)
            bars2 = ax1.bar([i + width/2 for i in x], monthly_stats['profit'], width,
                           label='Profit', color='#22c55e', alpha=0.8)
            
            ax1.set_xlabel('Month')
            ax1.set_ylabel('EGP')
            ax1.set_title('📊 Monthly Revenue vs Profit', fontweight='bold', fontsize=11)
            ax1.set_xticks(x)
            ax1.set_xticklabels(months, rotation=45)
            ax1.legend()
            ax1.grid(axis='y', alpha=0.3)
            
            # Add value labels
            for bar in bars1:
                height = bar.get_height()
                ax1.annotate(f'{int(height)}',
                            xy=(bar.get_x() + bar.get_width()/2, height),
                            ha='center', va='bottom', fontsize=8)
        else:
            ax1.text(0.5, 0.5, 'No data yet', ha='center', va='center', fontsize=12)
            ax1.set_title('📊 Monthly Revenue vs Profit', fontweight='bold')
        
        # Chart 2: Profit Breakdown (top right)
        ax2 = fig.add_subplot(2, 2, 2)
        costs = [
            ('Per-Order Material', profit_breakdown['filament_cost'], '#ef4444'),
            ('Spool Purchases', profit_breakdown.get('spool_purchase_total', 0), '#f87171'),
            ('Electricity', profit_breakdown['electricity_cost'], '#f59e0b'),
            ('Depreciation', profit_breakdown['depreciation_cost'], '#8b5cf6'),
            ('Fees & Loss', profit_breakdown['payment_fees'] + profit_breakdown['rounding_loss'], '#6b7280'),
            ('Failures', profit_breakdown['failures_cost'], '#dc2626'),
            ('Expenses', profit_breakdown['expenses'], '#f97316'),
        ]
        
        labels = [c[0] for c in costs if c[1] > 0]
        values = [c[1] for c in costs if c[1] > 0]
        colors_pie = [c[2] for c in costs if c[1] > 0]
        
        if values:
            wedges, texts, autotexts = ax2.pie(values, labels=labels, autopct='%1.1f%%',
                                               colors=colors_pie, startangle=90)
            ax2.set_title('💸 Cost Breakdown (incl. Spool Purchases)', fontweight='bold', fontsize=10)
        else:
            ax2.text(0.5, 0.5, 'No costs yet', ha='center', va='center', fontsize=12)
            ax2.set_title('💸 Cost Breakdown', fontweight='bold')
        
        # Chart 3: Filament Usage by Color (bottom left)
        ax3 = fig.add_subplot(2, 2, 3)
        if color_stats:
            color_names = list(color_stats.keys())
            usage = list(color_stats.values())
            
            # Color mapping
            color_map = {
                'Black': '#1f2937', 'White': '#e5e7eb', 'Red': '#ef4444',
                'Blue': '#3b82f6', 'Light Blue': '#60a5fa', 'Green': '#22c55e',
                'Yellow': '#eab308', 'Orange': '#f97316', 'Purple': '#a855f7',
                'Silver': '#9ca3af', 'Beige': '#d4a574', 'Pink': '#ec4899'
            }
            bar_colors = [color_map.get(c, '#6b7280') for c in color_names]
            
            bars = ax3.barh(color_names, usage, color=bar_colors, edgecolor='white')
            ax3.set_xlabel('Grams Used')
            ax3.set_title('🎨 Filament Usage by Color', fontweight='bold', fontsize=11)
            ax3.grid(axis='x', alpha=0.3)
            
            # Add value labels
            for bar, val in zip(bars, usage):
                ax3.text(val + max(usage)*0.02, bar.get_y() + bar.get_height()/2,
                        f'{int(val)}g', va='center', fontsize=9)
        else:
            ax3.text(0.5, 0.5, 'No filament data', ha='center', va='center', fontsize=12)
            ax3.set_title('🎨 Filament Usage by Color', fontweight='bold')
        
        # Chart 4: Orders & Weight Trend (bottom right)
        ax4 = fig.add_subplot(2, 2, 4)
        if monthly_stats['months']:
            months = [m[-5:] for m in monthly_stats['months']]
            x = range(len(months))
            
            # Primary axis - Orders
            ax4.bar(x, monthly_stats['orders'], color='#6366f1', alpha=0.7, label='Orders')
            ax4.set_xlabel('Month')
            ax4.set_ylabel('Orders', color='#6366f1')
            ax4.tick_params(axis='y', labelcolor='#6366f1')
            ax4.set_xticks(x)
            ax4.set_xticklabels(months, rotation=45)
            
            # Secondary axis - Filament
            ax4b = ax4.twinx()
            ax4b.plot(x, monthly_stats['filament'], 'o-', color='#f59e0b', linewidth=2, 
                     markersize=6, label='Filament (g)')
            ax4b.set_ylabel('Filament (g)', color='#f59e0b')
            ax4b.tick_params(axis='y', labelcolor='#f59e0b')
            
            ax4.set_title('📦 Orders & Filament Trend', fontweight='bold', fontsize=11)
            ax4.legend(loc='upper left')
            ax4b.legend(loc='upper right')
        else:
            ax4.text(0.5, 0.5, 'No trend data', ha='center', va='center', fontsize=12)
            ax4.set_title('📦 Orders & Filament Trend', fontweight='bold')
        
        # Adjust layout
        fig.tight_layout(pad=3.0)
        
        # Embed in tkinter
        canvas = FigureCanvasTkAgg(fig, master=self.charts_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Summary stats below charts
        summary_frame = ttk.Frame(self.charts_frame)
        summary_frame.pack(fill=tk.X, pady=10)
        
        summary_text = (
            f"💰 Revenue: {profit_breakdown['revenue']:,.0f} EGP  |  "
            f"📈 Gross: {profit_breakdown['gross_profit']:,.0f} EGP  |  "
            f"🛒 Spools: -{profit_breakdown.get('spool_purchase_total', 0):,.0f} EGP  |  "
            f"✨ Net: {profit_breakdown['net_profit']:,.0f} EGP  |  "
            f"📊 Margin: {profit_breakdown['profit_margin']:.1f}%"
        )
        
        ttk.Label(summary_frame, text=summary_text, font=("Segoe UI", 10, "bold"),
                 foreground=Colors.PRIMARY).pack()
        
        # Show pending loans warning if any
        if profit_breakdown.get('pending_loans', 0) > 0:
            loan_warning = f"⚠️ Pending Loans: {profit_breakdown['pending_loans']:,.0f} EGP (not yet deducted from profit)"
            ttk.Label(summary_frame, text=loan_warning, font=("Segoe UI", 9),
                     foreground=Colors.WARNING).pack()
    
    def _refresh_charts(self):
        """Refresh analytics charts"""
        if MATPLOTLIB_AVAILABLE:
            self._load_charts()
            messagebox.showinfo("Refreshed", "Charts updated with latest data!")
    
    def _build_trash_tab(self):
        """Trash/Deleted Orders tab - Access deleted orders"""
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="🗑️ Trash")
        
        # Header
        header = ttk.Frame(tab)
        header.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header, text="🗑️ Deleted Orders", style="Title.TLabel").pack(side=tk.LEFT)
        
        empty_btn = tk.Button(header, text="🧹 Empty Trash", font=("Segoe UI", 10),
                             bg=Colors.DANGER, fg="white", relief=tk.FLAT, padx=15, pady=5,
                             cursor="hand2", command=self._empty_trash)
        empty_btn.pack(side=tk.RIGHT)
        
        refresh_btn = tk.Button(header, text="🔄 Refresh", font=("Segoe UI", 10),
                               bg=Colors.INFO, fg="white", relief=tk.FLAT, padx=15, pady=5,
                               cursor="hand2", command=self._load_trash)
        refresh_btn.pack(side=tk.RIGHT, padx=5)
        
        # Info label
        self.trash_info = ttk.Label(tab, text="", style="Subtitle.TLabel")
        self.trash_info.pack(anchor=tk.W, pady=5)
        
        # Deleted orders list
        cols = ("Order#", "Customer", "Items", "Total", "Status", "Deleted Date")
        self.trash_tree = ttk.Treeview(tab, columns=cols, show="headings", height=15)
        for col, w in zip(cols, [70, 150, 50, 80, 90, 130]):
            self.trash_tree.heading(col, text=col)
            self.trash_tree.column(col, width=w, anchor=tk.CENTER if col != "Customer" else tk.W)
        
        scroll = ttk.Scrollbar(tab, command=self.trash_tree.yview)
        self.trash_tree.configure(yscrollcommand=scroll.set)
        self.trash_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Action buttons
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="♻️ Restore Selected", command=self._restore_order).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🗑️ Permanently Delete", command=self._permanent_delete_order).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="👁️ View Details", command=self._view_deleted_order).pack(side=tk.LEFT, padx=5)
        
        # Load trash on creation
        self._load_trash()
    
    def _load_trash(self):
        """Load deleted orders into trash tab"""
        if not hasattr(self, 'trash_tree'):
            return
        
        for item in self.trash_tree.get_children():
            self.trash_tree.delete(item)
        
        deleted_orders = self.db.get_deleted_orders()
        
        for order in deleted_orders:
            self.trash_tree.insert("", tk.END, iid=order.id, values=(
                order.order_number,
                order.customer_name or "Walk-in",
                order.item_count,
                f"{order.total:.0f}",
                order.status,
                order.deleted_date.split()[0] if order.deleted_date else "Unknown"
            ))
        
        self.trash_info.config(text=f"📋 {len(deleted_orders)} deleted orders in trash")
    
    def _restore_order(self):
        """Restore selected order from trash"""
        sel = self.trash_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select an order to restore")
            return
        
        if messagebox.askyesno("Restore", "Restore this order?\n\nIt will appear back in the Orders list."):
            if self.db.restore_order(sel[0]):
                self._load_trash()
                self._load_orders()
                messagebox.showinfo("Restored", "Order restored successfully!")
            else:
                messagebox.showerror("Error", "Failed to restore order")
    
    def _permanent_delete_order(self):
        """Permanently delete order from trash"""
        sel = self.trash_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select an order to delete")
            return
        
        if messagebox.askyesno("⚠️ Permanent Delete", 
                              "This will PERMANENTLY delete the order!\n\n"
                              "This action cannot be undone.\n\nContinue?"):
            if self.db.permanently_delete_order(sel[0]):
                self._load_trash()
                messagebox.showinfo("Deleted", "Order permanently deleted")
            else:
                messagebox.showerror("Error", "Failed to delete order")
    
    def _view_deleted_order(self):
        """View details of deleted order"""
        sel = self.trash_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select an order to view")
            return
        
        # Find order in deleted orders
        deleted_orders = self.db.get_deleted_orders()
        order = None
        for o in deleted_orders:
            if o.id == sel[0]:
                order = o
                break
        
        if not order:
            messagebox.showerror("Error", "Order not found")
            return
        
        # Show details dialog
        dlg = tk.Toplevel(self.root)
        dlg.title(f"Deleted Order #{order.order_number}")
        dlg.geometry("500x400")
        dlg.transient(self.root)
        
        main = ttk.Frame(dlg, padding=15)
        main.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main, text=f"📦 Order #{order.order_number}", 
                 font=("Segoe UI", 14, "bold")).pack(anchor=tk.W)
        
        info_text = f"""
Customer: {order.customer_name or 'Walk-in'}
Phone: {order.customer_phone or '-'}
Status: {order.status}
Created: {order.created_date}
Deleted: {order.deleted_date}

Items: {order.item_count}
Total Weight: {order.total_weight:.0f}g
Total: {order.total:.2f} EGP
Profit: {order.profit:.2f} EGP

Notes: {order.notes or 'None'}
        """
        
        text = tk.Text(main, height=15, font=("Segoe UI", 10))
        text.pack(fill=tk.BOTH, expand=True, pady=10)
        text.insert("1.0", info_text)
        text.config(state=tk.DISABLED)
        
        ttk.Button(main, text="Close", command=dlg.destroy).pack(pady=5)
    
    def _empty_trash(self):
        """Empty all items from trash"""
        deleted_orders = self.db.get_deleted_orders()
        if not deleted_orders:
            messagebox.showinfo("Empty", "Trash is already empty!")
            return
        
        if messagebox.askyesno("⚠️ Empty Trash", 
                              f"This will PERMANENTLY delete {len(deleted_orders)} orders!\n\n"
                              "This action cannot be undone.\n\nContinue?"):
            for order in deleted_orders:
                self.db.permanently_delete_order(order.id)
            self._load_trash()
            messagebox.showinfo("Done", "Trash emptied successfully!")
    
    def _build_settings_tab(self):
        """Settings tab - Admin only"""
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="⚙️ Settings")
        
        ttk.Label(tab, text="Application Settings", style="Title.TLabel").pack(anchor=tk.W, pady=(0, 15))
        
        company_f = ttk.LabelFrame(tab, text="Company Information", padding=10)
        company_f.pack(fill=tk.X, pady=5)
        
        settings = self.db.get_settings()
        
        for i, (lbl, attr, key, default) in enumerate([
            ("Company Name:", "set_company", "company_name", "Abaad"),
            ("Phone:", "set_phone", "company_phone", ""),
            ("Rate (EGP/g):", "set_rate", "default_rate_per_gram", "4.0"),
            ("Deposit %:", "set_deposit", "deposit_percent", "50")
        ]):
            ttk.Label(company_f, text=lbl).grid(row=i, column=0, sticky=tk.W, pady=3)
            e = ttk.Entry(company_f, width=30)
            e.insert(0, str(settings.get(key, default)))
            e.grid(row=i, column=1, pady=3, padx=5)
            setattr(self, attr, e)
        
        status_f = ttk.LabelFrame(tab, text="Feature Status", padding=10)
        status_f.pack(fill=tk.X, pady=10)
        
        for i, (name, avail, hint) in enumerate([
            ("PDF Generation", REPORTLAB_AVAILABLE, "pip install reportlab"),
            ("Cura Vision AI", CURA_VISION_AVAILABLE, "Pillow + Tesseract")
        ]):
            icon = "✅" if avail else "❌"
            text = f"{icon} {name}" + ("" if avail else f" ({hint})")
            ttk.Label(status_f, text=text).grid(row=i, column=0, sticky=tk.W, pady=2)
        
        btn_f = ttk.Frame(tab)
        btn_f.pack(fill=tk.X, pady=10)
        ttk.Button(btn_f, text="💾 Save Settings", command=self._save_settings).pack(side=tk.LEFT, padx=5)
        
        if self.auth.has_permission(Permission.SYSTEM_BACKUP):
            ttk.Button(btn_f, text="📦 Backup", command=self._backup).pack(side=tk.LEFT, padx=5)

    # === DATA LOADING ===
    def _load_all_data(self):
        self._load_orders()
        self._load_customers()
        self._load_spools()
        self._load_printers()
        self._load_failures()
        self._load_expenses()
        if hasattr(self, 'stat_lbls'):
            self._load_stats()
        if hasattr(self, 'trash_tree'):
            self._load_trash()
        if MATPLOTLIB_AVAILABLE and hasattr(self, 'charts_frame'):
            self._load_charts()
    
    def _load_orders(self):
        for i in self.orders_tree.get_children():
            self.orders_tree.delete(i)
        for o in self.db.get_all_orders():
            rd = "🔬" if o.is_rd_project else ""
            self.orders_tree.insert("", tk.END, iid=o.id, values=(
                o.order_number, o.customer_name or "Walk-in", o.item_count,
                f"{o.total:.0f}", o.status, o.created_date.split()[0], rd
            ))
    
    def _filter_orders(self):
        q = self.order_search.get().lower()
        status = self.status_filter.get()
        for i in self.orders_tree.get_children():
            self.orders_tree.delete(i)
        for o in self.db.get_all_orders():
            if status != "All" and o.status != status:
                continue
            if q and q not in o.customer_name.lower() and q not in str(o.order_number):
                continue
            rd = "🔬" if o.is_rd_project else ""
            self.orders_tree.insert("", tk.END, iid=o.id, values=(
                o.order_number, o.customer_name or "Walk-in", o.item_count,
                f"{o.total:.0f}", o.status, o.created_date.split()[0], rd
            ))
    
    def _load_customers(self):
        for i in self.custs_tree.get_children():
            self.custs_tree.delete(i)
        for c in self.db.get_all_customers():
            self.custs_tree.insert("", tk.END, iid=c.id, values=(
                c.name, c.phone, f"{c.discount_percent}%", c.total_orders, f"{c.total_spent:.2f}"
            ))
    
    def _filter_customers(self):
        q = self.cust_search.get().lower()
        for i in self.custs_tree.get_children():
            self.custs_tree.delete(i)
        for c in self.db.get_all_customers():
            if q and q not in c.name.lower() and q not in c.phone:
                continue
            self.custs_tree.insert("", tk.END, iid=c.id, values=(
                c.name, c.phone, f"{c.discount_percent}%", c.total_orders, f"{c.total_spent:.2f}"
            ))
    
    def _load_spools(self):
        for i in self.spools_tree.get_children():
            self.spools_tree.delete(i)
        spools = self.db.get_all_spools()
        
        # Calculate totals
        total_initial = sum(s.initial_weight_grams for s in spools)
        total_r = sum(s.current_weight_grams for s in spools if s.is_active)
        total_p = sum(s.pending_weight_grams for s in spools)
        total_u = sum(s.used_weight_grams for s in spools)
        active = len([s for s in spools if s.is_active and s.current_weight_grams > 50])
        low_count = len([s for s in spools if s.should_show_trash_button])
        
        # Calculate filament value
        total_value = sum(s.purchase_price_egp for s in spools if s.is_active and s.category != SpoolCategory.REMAINING.value)
        used_value = (total_u / total_initial * total_value) if total_initial > 0 else 0
        
        # Loan/Payment tracking
        loan_stats = self.db.get_loan_stats()
        spool_costs = self.db.get_spool_cost_for_profit()
        
        for s in spools:
            if s.status == SpoolStatus.TRASH.value:
                status = "🗑️ Trash"
                tag = 'trash'
            elif s.current_weight_grams <= 0:
                status = "Empty"
                tag = 'empty'
            elif s.should_show_trash_button:
                status = "⚠️ Low"
                tag = 'low'
            else:
                status = "Active"
                tag = ''
            
            # Payment status with color coding
            if s.is_loan_unpaid:
                payment = f"🔴 Loan: {s.loan_provider}"
                tag = 'loan_unpaid'
            elif s.is_loan and s.loan_paid:
                payment = f"✅ Loan PAID"
                tag = 'loan_paid' if not tag else tag
            elif s.payment_source == PaymentSource.PROFIT.value:
                payment = "💰 From Profit"
            elif s.payment_source == PaymentSource.POCKET.value:
                payment = "👤 From Pocket"
            elif s.category == SpoolCategory.REMAINING.value:
                payment = "♻️ Remaining"
            else:
                payment = s.payment_source
            
            category = "Remain" if s.category == SpoolCategory.REMAINING.value else "Std"
            cost_per_g = f"{s.cost_per_gram:.2f}" if s.cost_per_gram > 0 else "FREE"
            used_pct = f"{100 - s.remaining_percent:.0f}%"
            self.spools_tree.insert("", tk.END, iid=s.id, values=(
                s.display_name, s.color, category, f"{s.initial_weight_grams:.0f}g",
                f"{s.current_weight_grams:.0f}g", used_pct, cost_per_g, payment, status
            ), tags=(tag,))
        
        # Update summary
        self.spool_summary.config(
            text=f"📦 {len(spools)} spools | ✅ {active} active | ⚠️ {low_count} low | "
                 f"🎨 {total_r:.0f}g remaining | 📌 {total_p:.0f}g pending"
        )
        
        # Update stats
        if hasattr(self, 'filament_stats'):
            self.filament_stats.config(
                text=f"💰 Inventory Value: ~{total_value:,.0f} EGP | "
                     f"📊 Total Used: {total_u:,.0f}g (~{used_value:,.0f} EGP worth)"
            )
        
        # Update loan summary
        if hasattr(self, 'loan_summary'):
            if loan_stats['unpaid_loan_count'] > 0:
                loan_text = (f"⚠️ Unpaid Loans: {loan_stats['unpaid_loan_count']} spool(s) = "
                            f"{loan_stats['unpaid_loan_amount']:,.0f} EGP | ")
            else:
                loan_text = "✅ No unpaid loans | "
            
            loan_text += (f"💳 From Profit: {spool_costs['profit_cost']:,.0f} EGP | "
                         f"🔄 Loans Repaid: {spool_costs['loan_repaid_cost']:,.0f} EGP | "
                         f"📉 Affects Profit: {spool_costs['total_affects_profit']:,.0f} EGP")
            self.loan_summary.config(text=loan_text)
        
        # Update visual usage bar
        if hasattr(self, 'usage_bar'):
            self.usage_bar.delete("all")
            usage_percent = (total_u / total_initial * 100) if total_initial > 0 else 0
            
            # Draw background
            self.usage_bar.create_rectangle(0, 0, 300, 20, fill='#e5e7eb', outline='')
            
            # Draw usage bar (green for used, blue for remaining, orange for pending)
            remaining_width = int(300 * (total_r / total_initial)) if total_initial > 0 else 0
            pending_width = int(300 * (total_p / total_initial)) if total_initial > 0 else 0
            used_width = 300 - remaining_width - pending_width
            
            # Used (blue)
            if used_width > 0:
                self.usage_bar.create_rectangle(0, 0, used_width, 20, fill='#3b82f6', outline='')
            # Pending (orange)
            if pending_width > 0:
                self.usage_bar.create_rectangle(used_width, 0, used_width + pending_width, 20, fill='#f59e0b', outline='')
            # Remaining (green)
            if remaining_width > 0:
                self.usage_bar.create_rectangle(used_width + pending_width, 0, 300, 20, fill='#22c55e', outline='')
            
            self.usage_label.config(text=f"{usage_percent:.1f}% used")
    
    def _load_printers(self):
        for i in self.printers_tree.get_children():
            self.printers_tree.delete(i)
        for p in self.db.get_all_printers():
            self.printers_tree.insert("", tk.END, iid=p.id, values=(
                p.name, p.model, f"{p.total_printed_grams:.0f}g",
                format_time(p.total_print_time_minutes), p.nozzle_changes, f"{p.total_electricity_cost:.2f}",
                "Active" if p.is_active else "Inactive"
            ))
    
    def _load_stats(self):
        s = self.db.get_statistics()
        breakdown = self.db.get_profit_breakdown()
        
        # Revenue & Profit with filament cost breakdown
        self.stat_lbls['revenue'].config(text=f"{s.total_revenue:.0f}")
        self.stat_lbls['filament_cost'].config(text=f"{s.total_material_cost:.0f}")
        self.stat_lbls['gross_profit'].config(text=f"{breakdown['gross_profit']:.0f}")
        
        # Total deductions now includes spool purchases
        total_deductions = s.total_failure_cost + s.total_expenses + breakdown['spool_purchase_total']
        self.stat_lbls['total_deductions'].config(text=f"{total_deductions:.0f}")
        self.stat_lbls['profit'].config(text=f"{breakdown['net_profit']:.0f}")
        
        # Profit formula explanation - now includes spool purchases
        if 'profit_formula' in self.stat_lbls:
            formula = (f"Revenue ({s.total_revenue:.0f}) - Material ({s.total_material_cost:.0f}) - "
                      f"Electricity ({s.total_electricity_cost:.1f}) - Depreciation ({s.total_depreciation_cost:.0f}) "
                      f"= Gross ({breakdown['gross_profit']:.0f})\n"
                      f"  - Failures ({s.total_failure_cost:.0f}) - Expenses ({s.total_expenses:.0f}) "
                      f"- Spool Purchases ({breakdown['spool_purchase_total']:.0f}) = Net Profit ({breakdown['net_profit']:.0f})")
            if breakdown['pending_loans'] > 0:
                formula += f"\n⚠️ Pending Loans: {breakdown['pending_loans']:.0f} EGP (not yet deducted)"
            self.stat_lbls['profit_formula'].config(text=formula)
        
        # Update spool purchase info
        if 'spool_purchase' in self.stat_lbls:
            spool_text = f"{breakdown['spool_purchase_total']:.0f}"
            if breakdown['pending_loans'] > 0:
                spool_text += f" (+{breakdown['pending_loans']:.0f})"
            self.stat_lbls['spool_purchase'].config(text=spool_text)
        
        # Orders
        self.stat_lbls['orders'].config(text=str(s.total_orders))
        self.stat_lbls['completed'].config(text=str(s.completed_orders))
        self.stat_lbls['rd'].config(text=str(s.rd_orders))
        self.stat_lbls['weight'].config(text=f"{s.total_weight_printed:.0f}g")
        self.stat_lbls['margin'].config(text=f"{breakdown['profit_margin']:.1f}%")
        # Costs
        self.stat_lbls['material'].config(text=f"{s.total_material_cost:.0f}")
        self.stat_lbls['electricity'].config(text=f"{s.total_electricity_cost:.1f}")
        self.stat_lbls['nozzle'].config(text=f"{s.total_nozzle_cost:.0f}")
        self.stat_lbls['shipping'].config(text=f"{s.total_shipping:.0f}")
        self.stat_lbls['fees'].config(text=f"{s.total_payment_fees:.1f}")
        self.stat_lbls['rounding'].config(text=f"{s.total_rounding_loss:.1f}")
        self.stat_lbls['waste'].config(text=f"{s.total_filament_waste:.0f}g")
        self.stat_lbls['tolerance'].config(text=f"{s.total_tolerance_discounts:.1f}")

    # === ORDER OPERATIONS ===
    def _new_order(self):
        self.current_order = Order()
        self._clear_order_form()
        self.order_title.config(text="New Order")
    
    def _clear_order_form(self):
        self.cust_name.delete(0, tk.END)
        self.cust_phone.delete(0, tk.END)
        self.order_status.set("Draft")
        self.rd_var.set(False)
        self.payment_method.set(PaymentMethod.CASH.value)
        self.shipping_entry.delete(0, tk.END)
        self.shipping_entry.insert(0, "0")
        self.order_discount_entry.delete(0, tk.END)
        self.order_discount_entry.insert(0, "0")
        self.amount_received_entry.delete(0, tk.END)
        self.amount_received_entry.insert(0, "0")
        self.order_notes.delete("1.0", tk.END)
        for i in self.items_tree.get_children():
            self.items_tree.delete(i)
        self._update_totals_display()
    
    def _on_order_select(self, event):
        sel = self.orders_tree.selection()
        if not sel:
            return
        o = self.db.get_order(sel[0])
        if o:
            self.current_order = o
            self._load_order_to_form(o)
    
    def _load_order_to_form(self, o):
        self._clear_order_form()
        self.order_title.config(text=f"Order #{o.order_number}" + (" [R&D]" if o.is_rd_project else ""))
        self.cust_name.insert(0, o.customer_name)
        self.cust_phone.insert(0, o.customer_phone)
        self.order_status.set(o.status)
        self.rd_var.set(o.is_rd_project)
        self.payment_method.set(o.payment_method)
        self.shipping_entry.delete(0, tk.END)
        self.shipping_entry.insert(0, str(o.shipping_cost))
        self.order_discount_entry.delete(0, tk.END)
        self.order_discount_entry.insert(0, str(o.order_discount_percent))
        self.amount_received_entry.delete(0, tk.END)
        self.amount_received_entry.insert(0, str(o.amount_received))
        if o.notes:
            self.order_notes.insert("1.0", o.notes)
        for item in o.items:
            wt = f"{item.weight:.0f}g"
            if item.actual_weight_grams > 0 and item.actual_weight_grams != item.estimated_weight_grams:
                wt = f"{item.estimated_weight_grams:.0f}→{item.actual_weight_grams:.0f}g"
            self.items_tree.insert("", tk.END, iid=item.id, values=(
                item.name, item.color, wt, item.time_formatted,
                str(item.settings), item.quantity, f"{item.rate_per_gram:.2f}", f"{item.print_cost:.2f}"
            ))
        self._calc_totals()
    
    def _on_rd_toggle(self):
        if self.current_order:
            self.current_order.is_rd_project = self.rd_var.get()
            self._calc_totals()
    
    def _find_customer(self):
        q = simpledialog.askstring("Find Customer", "Enter name or phone:")
        if not q:
            return
        results = self.db.search_customers(q)
        if not results:
            messagebox.showinfo("Not Found", "No customer found")
            return
        c = results[0]
        self.cust_name.delete(0, tk.END)
        self.cust_name.insert(0, c.name)
        self.cust_phone.delete(0, tk.END)
        self.cust_phone.insert(0, c.phone)
        if self.current_order:
            self.current_order.customer_id = c.id
    
    def _add_item(self):
        if not self.current_order:
            self.current_order = Order()
        self._show_item_dialog()
    
    def _edit_item(self):
        sel = self.items_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select an item to edit")
            return
        item = self.current_order.get_item(sel[0])
        if item:
            self._show_item_dialog(item)
    
    def _remove_item(self):
        sel = self.items_tree.selection()
        if not sel:
            return
        if messagebox.askyesno("Confirm", "Remove item?"):
            item = self.current_order.get_item(sel[0])
            if item and item.filament_pending and item.spool_id:
                self.db.release_pending_filament(item.spool_id, item.total_weight)
            self.current_order.remove_item(sel[0])
            self.items_tree.delete(sel[0])
            self._calc_totals()
            self._load_spools()
    
    def _set_actual_weight(self):
        sel = self.items_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select an item first")
            return
        item = self.current_order.get_item(sel[0])
        if not item:
            return
        current = item.actual_weight_grams if item.actual_weight_grams > 0 else item.estimated_weight_grams
        result = simpledialog.askfloat("Actual Weight", f"Enter measured weight for '{item.name}':", initialvalue=current)
        if result and result > 0:
            item.actual_weight_grams = result
            item.calculate_tolerance_discount()
            wt = f"{item.estimated_weight_grams:.0f}→{item.actual_weight_grams:.0f}g"
            self.items_tree.item(item.id, values=(
                item.name, item.color, wt, item.time_formatted,
                str(item.settings), item.quantity, f"{item.rate_per_gram:.2f}", f"{item.print_cost:.2f}"
            ))
            self._calc_totals()
            if item.tolerance_discount_applied:
                messagebox.showinfo("Tolerance", f"Discount applied: {item.tolerance_discount_amount:.2f} EGP")
    
    def _calc_totals(self):
        if not self.current_order:
            return
        try:
            self.current_order.shipping_cost = float(self.shipping_entry.get() or 0)
            self.current_order.payment_method = self.payment_method.get()
            self.current_order.order_discount_percent = float(self.order_discount_entry.get() or 0)
            self.current_order.amount_received = float(self.amount_received_entry.get() or 0)
            self.current_order.is_rd_project = self.rd_var.get()
        except:
            pass
        self.current_order.calculate_totals()
        self._update_totals_display()
    
    def _update_totals_display(self):
        if not self.current_order:
            return
        o = self.current_order
        self.base_total_lbl.config(text=f"{o.subtotal:.2f}")
        self.actual_total_lbl.config(text=f"{o.actual_total:.2f}")
        self.discount_lbl.config(text=f"{o.discount_percent:.1f}%")
        self.order_discount_amt_lbl.config(text=f"(-{o.order_discount_amount:.2f})")
        self.payment_fee_lbl.config(text=f"{o.payment_fee:.2f}")
        self.total_lbl.config(text=f"{o.total:.2f} EGP")
        self.profit_lbl.config(text=f"{o.profit:.2f}")
        self.rounding_loss_lbl.config(text=f"Rounding: {o.rounding_loss:.2f}")
        self.tolerance_lbl.config(text=f"Tol: -{o.tolerance_discount_total:.2f}" if o.tolerance_discount_total > 0 else "")
        self.rd_cost_lbl.config(text=f"[R&D: {o.rd_cost:.2f}]" if o.is_rd_project else "")
        if o.is_rd_project:
            self.profit_lbl.config(text="0 (R&D)")

    def _save_order(self):
        if not self.current_order:
            messagebox.showwarning("Error", "No order to save")
            return
        name = self.cust_name.get().strip()
        phone = self.cust_phone.get().strip()
        if name or phone:
            cust = self.db.find_or_create_customer(name, phone)
            self.current_order.customer_id = cust.id
            self.current_order.customer_name = cust.name
            self.current_order.customer_phone = cust.phone
        
        old_order = self.db.get_order(self.current_order.id)
        old_status = old_order.status if old_order else OrderStatus.DRAFT.value
        
        self.current_order.status = self.order_status.get()
        self.current_order.payment_method = self.payment_method.get()
        self.current_order.notes = self.order_notes.get("1.0", tk.END).strip()
        self.current_order.is_rd_project = self.rd_var.get()
        self._calc_totals()
        
        confirm_filament = (old_status in [OrderStatus.DRAFT.value, OrderStatus.QUOTE.value] and self.current_order.is_confirmed)
        
        if self.current_order.status == OrderStatus.DELIVERED.value:
            printer = self.db.get_default_printer()
            if printer:
                for item in self.current_order.items:
                    if not item.is_printed:
                        self.db.add_print_to_printer(printer.id, item.total_weight, item.time_minutes * item.quantity)
                        item.is_printed = True
        
        if self.db.save_order(self.current_order, confirm_filament=confirm_filament):
            msg = f"Order #{self.current_order.order_number} saved!"
            if confirm_filament:
                msg += "\nFilament committed from inventory."
            messagebox.showinfo("Success", msg)
            self._load_all_data()
            self._load_order_to_form(self.current_order)
        else:
            messagebox.showerror("Error", "Failed to save")
    
    def _delete_order(self):
        if not self.current_order or not self.current_order.id:
            return
        if messagebox.askyesno("Confirm", f"Delete Order #{self.current_order.order_number}?"):
            self.db.delete_order(self.current_order.id, return_filament=True)
            self._load_all_data()
            self._new_order()
    
    def _gen_receipt(self):
        if not self.current_order or not self.current_order.items:
            messagebox.showwarning("Error", "Add items first")
            return
        o = self.current_order
        settings = self.db.get_settings()
        lines = ["=" * 50, settings.get('company_name', 'Abaad')]
        if o.is_rd_project:
            lines.append("[R&D PROJECT]")
        lines.extend([settings.get('company_phone', ''), "=" * 50, "", f"Order #{o.order_number}", f"Date: {o.created_date}",
                     f"Customer: {o.customer_name or 'Walk-in'}", f"Phone: {o.customer_phone or '-'}", "", "-" * 50, "ITEMS:"])
        for item in o.items:
            lines.extend(["", item.name, f"  {item.color} | {item.weight:.0f}g x {item.quantity}",
                         f"  {item.settings}", f"  Rate: {item.rate_per_gram:.2f} | Total: {item.print_cost:.2f}"])
        lines.extend(["", "-" * 50, f"Base: {o.subtotal:.2f} | Actual: {o.actual_total:.2f}",
                     f"Shipping: {o.shipping_cost:.2f} | Payment Fee: {o.payment_fee:.2f}",
                     "-" * 50, f"{'R&D COST' if o.is_rd_project else 'TOTAL'}: {o.total:.2f} EGP", "=" * 50, "Thank you!"])
        receipt = "\n".join(lines)
        dlg = tk.Toplevel(self.root)
        dlg.title(f"Receipt #{o.order_number}")
        dlg.geometry("500x600")
        text = tk.Text(dlg, font=("Courier New", 10))
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text.insert("1.0", receipt)
        text.config(state=tk.DISABLED)
        ttk.Button(dlg, text="Copy", command=lambda: self.root.clipboard_append(receipt)).pack(side=tk.LEFT, padx=10, pady=5)
        ttk.Button(dlg, text="Close", command=dlg.destroy).pack(side=tk.LEFT, padx=10, pady=5)
    
    def _gen_quote_pdf(self):
        if not self.current_order or not self.current_order.items:
            messagebox.showwarning("Error", "Add items first")
            return
        if not REPORTLAB_AVAILABLE:
            messagebox.showerror("Error", "Install reportlab: pip install reportlab")
            return
        try:
            exports_dir = Path(__file__).parent / "exports"
            exports_dir.mkdir(exist_ok=True)
            pdf_path = generate_quote(self.current_order, output_dir=exports_dir)
            if messagebox.askyesno("Success", f"Quote saved!\n{pdf_path}\n\nOpen?"):
                os.startfile(pdf_path)
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def _gen_receipt_pdf(self):
        if not self.current_order or not self.current_order.items:
            messagebox.showwarning("Error", "Add items first")
            return
        if not REPORTLAB_AVAILABLE:
            messagebox.showerror("Error", "Install reportlab: pip install reportlab")
            return
        try:
            exports_dir = Path(__file__).parent / "exports"
            exports_dir.mkdir(exist_ok=True)
            pdf_path = generate_receipt(self.current_order, output_dir=exports_dir)
            if messagebox.askyesno("Success", f"Receipt saved!\n{pdf_path}\n\nOpen?"):
                os.startfile(pdf_path)
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def _show_item_dialog(self, item=None):
        dlg = tk.Toplevel(self.root)
        dlg.title("Add/Edit Item")
        dlg.geometry("550x550")
        dlg.transient(self.root)
        dlg.grab_set()
        
        is_edit = item is not None
        if not item:
            item = PrintItem()
        
        main = ttk.Frame(dlg, padding=15)
        main.pack(fill=tk.BOTH, expand=True)
        spool_data = {'ids': [], 'spools': []}
        
        ttk.Label(main, text="Name:*").grid(row=0, column=0, sticky=tk.W, pady=3)
        name_e = ttk.Entry(main, width=30)
        name_e.insert(0, item.name)
        name_e.grid(row=0, column=1, columnspan=2, pady=3, padx=5)
        
        # Cura Vision AI buttons
        if CURA_VISION_AVAILABLE:
            ai_frame = ttk.Frame(main)
            ai_frame.grid(row=0, column=3, padx=5)
            
            def paste_cura():
                r = extract_from_cura_screenshot()
                if r:
                    if r.get('weight_grams'):
                        weight_e.delete(0, tk.END)
                        weight_e.insert(0, str(r['weight_grams']))
                    if r.get('time_minutes'):
                        hours_e.delete(0, tk.END)
                        hours_e.insert(0, str(r['time_minutes'] // 60))
                        mins_e.delete(0, tk.END)
                        mins_e.insert(0, str(r['time_minutes'] % 60))
                    messagebox.showinfo("🤖 Cura AI", f"Extracted:\n• Weight: {r.get('weight_grams', 'N/A')}g\n• Time: {r.get('time_minutes', 'N/A')}min")
                else:
                    messagebox.showwarning("🤖 Cura AI", "Could not extract data from clipboard.\nMake sure you copied a Cura screenshot.")
            
            ttk.Button(ai_frame, text="📷 Paste from Cura", command=paste_cura).pack()
        
        ttk.Label(main, text="Weight (g):*").grid(row=1, column=0, sticky=tk.W, pady=3)
        weight_e = ttk.Entry(main, width=12)
        weight_e.insert(0, str(item.estimated_weight_grams) if item.estimated_weight_grams else "")
        weight_e.grid(row=1, column=1, sticky=tk.W, pady=3, padx=5)
        
        ttk.Label(main, text="Time:").grid(row=2, column=0, sticky=tk.W, pady=3)
        time_f = ttk.Frame(main)
        time_f.grid(row=2, column=1, sticky=tk.W, pady=3, padx=5)
        hours_e = ttk.Entry(time_f, width=5)
        hours_e.insert(0, str(item.estimated_time_minutes // 60))
        hours_e.pack(side=tk.LEFT)
        ttk.Label(time_f, text="h").pack(side=tk.LEFT, padx=2)
        mins_e = ttk.Entry(time_f, width=5)
        mins_e.insert(0, str(item.estimated_time_minutes % 60))
        mins_e.pack(side=tk.LEFT)
        ttk.Label(time_f, text="m").pack(side=tk.LEFT, padx=2)
        
        ttk.Label(main, text="Color:").grid(row=3, column=0, sticky=tk.W, pady=3)
        colors = self.db.get_colors()
        color_c = ttk.Combobox(main, values=colors, width=15, state="readonly")
        color_c.set(item.color if item.color in colors else (colors[0] if colors else "Black"))
        color_c.grid(row=3, column=1, sticky=tk.W, pady=3, padx=5)
        
        ttk.Label(main, text="Spool:").grid(row=4, column=0, sticky=tk.W, pady=3)
        spool_c = ttk.Combobox(main, width=30, state="readonly")
        spool_c.grid(row=4, column=1, columnspan=2, sticky=tk.W, pady=3, padx=5)
        
        def update_spools(*args):
            spools = self.db.get_spools_by_color(color_c.get())
            spool_data['ids'] = [s.id for s in spools]
            spool_data['spools'] = spools
            spool_c['values'] = [f"{s.display_name} ({s.available_weight_grams:.0f}g)" for s in spools]
            if spool_c['values']:
                if item.spool_id in spool_data['ids']:
                    spool_c.current(spool_data['ids'].index(item.spool_id))
                else:
                    spool_c.current(0)
        color_c.bind('<<ComboboxSelected>>', update_spools)
        update_spools()
        
        ttk.Label(main, text="Nozzle:").grid(row=5, column=0, sticky=tk.W, pady=3)
        nozzle_c = ttk.Combobox(main, values=["0.2", "0.4", "0.6", "0.8", "1.0"], width=8)
        nozzle_c.set(str(item.settings.nozzle_size))
        nozzle_c.grid(row=5, column=1, sticky=tk.W, pady=3, padx=5)
        
        ttk.Label(main, text="Layer:").grid(row=6, column=0, sticky=tk.W, pady=3)
        layer_c = ttk.Combobox(main, values=["0.08", "0.12", "0.16", "0.2", "0.28", "0.32"], width=8)
        layer_c.set(str(item.settings.layer_height))
        layer_c.grid(row=6, column=1, sticky=tk.W, pady=3, padx=5)
        
        ttk.Label(main, text="Support:").grid(row=7, column=0, sticky=tk.W, pady=3)
        support_c = ttk.Combobox(main, values=[s.value for s in SupportType], width=12, state="readonly")
        support_c.set(item.settings.support_type)
        support_c.grid(row=7, column=1, sticky=tk.W, pady=3, padx=5)
        
        ttk.Label(main, text="Quantity:").grid(row=8, column=0, sticky=tk.W, pady=3)
        qty_e = ttk.Entry(main, width=8)
        qty_e.insert(0, str(item.quantity))
        qty_e.grid(row=8, column=1, sticky=tk.W, pady=3, padx=5)
        
        ttk.Label(main, text="Rate:").grid(row=9, column=0, sticky=tk.W, pady=3)
        rate_e = ttk.Entry(main, width=8)
        rate_e.insert(0, str(item.rate_per_gram))
        rate_e.grid(row=9, column=1, sticky=tk.W, pady=3, padx=5)
        
        cost_lbl = ttk.Label(main, text="0.00 EGP", font=("Segoe UI", 12, "bold"))
        cost_lbl.grid(row=10, column=0, columnspan=3, pady=10)
        
        def update_cost(*args):
            try:
                cost_lbl.config(text=f"{float(weight_e.get() or 0) * int(qty_e.get() or 1) * float(rate_e.get() or 4):.2f} EGP")
            except:
                cost_lbl.config(text="-- EGP")
        for e in [weight_e, qty_e, rate_e]:
            e.bind('<KeyRelease>', update_cost)
        update_cost()
        
        def save():
            try:
                n = name_e.get().strip()
                w = float(weight_e.get() or 0)
                if not n or w <= 0:
                    messagebox.showwarning("Error", "Enter name and weight")
                    return
                
                # Get new values
                new_qty = int(qty_e.get() or 1)
                new_spool_id = spool_data['ids'][spool_c.current()] if spool_data['ids'] and spool_c.current() >= 0 else ""
                new_total_weight = w * new_qty
                
                # Store old values for comparison
                old_spool_id = item.spool_id
                old_total_weight = item.total_weight
                
                # Handle spool/weight changes for existing items
                if is_edit:
                    spool_changed = old_spool_id != new_spool_id
                    weight_changed = abs(old_total_weight - new_total_weight) > 0.01
                    
                    if spool_changed or weight_changed:
                        # Return filament to old spool
                        if old_spool_id:
                            old_spool = self.db.get_spool(old_spool_id)
                            if old_spool:
                                if item.filament_deducted:
                                    # Filament was already used - return it
                                    old_spool.current_weight_grams += old_total_weight
                                    self.db.save_spool(old_spool)
                                    item.filament_deducted = False
                                elif item.filament_pending:
                                    # Filament was pending - release it
                                    old_spool.pending_weight_grams = max(0, old_spool.pending_weight_grams - old_total_weight)
                                    self.db.save_spool(old_spool)
                                    item.filament_pending = False
                        
                        # Reserve filament from new spool
                        if new_spool_id:
                            new_spool = self.db.get_spool(new_spool_id)
                            if new_spool:
                                if new_spool.available_weight_grams < new_total_weight:
                                    messagebox.showwarning("Warning", 
                                        f"Not enough filament in {new_spool.display_name}!\n"
                                        f"Available: {new_spool.available_weight_grams:.1f}g\n"
                                        f"Required: {new_total_weight:.1f}g")
                                    return
                                # Reserve the new amount
                                new_spool.pending_weight_grams += new_total_weight
                                self.db.save_spool(new_spool)
                                item.filament_pending = True
                                
                                # Record consumption history
                                self.db.record_spool_consumption(
                                    new_spool_id, new_total_weight,
                                    self.current_order.order_number if hasattr(self, 'current_order') else 0,
                                    n
                                )
                
                # Update item values
                item.name = n
                item.estimated_weight_grams = w
                item.estimated_time_minutes = int(hours_e.get() or 0) * 60 + int(mins_e.get() or 0)
                item.color = color_c.get()
                item.quantity = new_qty
                item.rate_per_gram = float(rate_e.get() or 4.0)
                item.spool_id = new_spool_id
                item.settings = PrintSettings(
                    nozzle_size=float(nozzle_c.get() or 0.4), 
                    layer_height=float(layer_c.get() or 0.2),
                    infill_density=20, 
                    support_type=support_c.get()
                )
                
                # New item - reserve filament and add to order
                if not is_edit:
                    if item.spool_id:
                        if not self.db.reserve_filament(item.spool_id, item.total_weight):
                            messagebox.showwarning("Warning", "Not enough filament!")
                            return
                        item.filament_pending = True
                        # Record consumption
                        self.db.record_spool_consumption(
                            item.spool_id, item.total_weight,
                            self.current_order.order_number if hasattr(self, 'current_order') else 0,
                            n
                        )
                    self.current_order.add_item(item)
                
                wt = f"{item.weight:.0f}g"
                if is_edit:
                    self.items_tree.item(item.id, values=(item.name, item.color, wt, item.time_formatted, str(item.settings),
                                                         item.quantity, f"{item.rate_per_gram:.2f}", f"{item.print_cost:.2f}"))
                else:
                    self.items_tree.insert("", tk.END, iid=item.id, values=(item.name, item.color, wt, item.time_formatted,
                                                                            str(item.settings), item.quantity,
                                                                            f"{item.rate_per_gram:.2f}", f"{item.print_cost:.2f}"))
                self._calc_totals()
                self._load_spools()
                dlg.destroy()
            except Exception as e:
                messagebox.showerror("Error", str(e))
                
        btn_f = ttk.Frame(main)
        btn_f.grid(row=11, column=0, columnspan=3, pady=10)
        ttk.Button(btn_f, text="💾 Save", command=save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_f, text="Cancel", command=dlg.destroy).pack(side=tk.LEFT, padx=5)
        
    def _move_to_trash(self):
        sel = self.spools_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select a spool to trash")
            return
        
        spool = self.db.get_spool(sel[0])
        if not spool:
            return

        if spool.current_weight_grams > TRASH_THRESHOLD_GRAMS:
            if not messagebox.askyesno("Warning", 
                f"This spool still has {spool.current_weight_grams:.0f}g.\n"
                f"The trash threshold is <{TRASH_THRESHOLD_GRAMS}g.\n\n"
                "Do you really want to trash it?"):
                return

        reason = simpledialog.askstring("Trash Spool", "Reason for trashing (e.g., Empty, Tangled):")
        if reason is None: return
        
        if self.db.move_spool_to_trash(spool.id, reason or "End of life"):
            self._load_spools()
            if hasattr(self, 'stat_lbls'):
                self._load_stats()
            messagebox.showinfo("Trashed", f"Spool moved to trash history.")

    def _show_color_chart(self):
        """Show filament usage by color chart"""
        dlg = tk.Toplevel(self.root)
        dlg.title("Filament Usage by Color")
        dlg.geometry("600x500")
        dlg.transient(self.root)
        
        if MATPLOTLIB_AVAILABLE:
            color_stats = self.db.get_color_usage_stats()
            
            if not color_stats:
                ttk.Label(dlg, text="No filament usage data yet", font=("Segoe UI", 14)).pack(expand=True)
                return
            
            fig = Figure(figsize=(6, 5), dpi=100, facecolor='#f8fafc')
            ax = fig.add_subplot(111)
            
            color_names = list(color_stats.keys())
            usage = list(color_stats.values())
            
            # Color mapping
            color_map = {
                'Black': '#1f2937', 'White': '#9ca3af', 'Red': '#ef4444',
                'Blue': '#3b82f6', 'Light Blue': '#60a5fa', 'Green': '#22c55e',
                'Yellow': '#eab308', 'Orange': '#f97316', 'Purple': '#a855f7',
                'Silver': '#6b7280', 'Beige': '#d4a574', 'Pink': '#ec4899'
            }
            bar_colors = [color_map.get(c, '#6b7280') for c in color_names]
            
            # Create pie chart
            wedges, texts, autotexts = ax.pie(
                usage, labels=color_names, autopct='%1.1f%%',
                colors=bar_colors, startangle=90,
                explode=[0.02] * len(usage)
            )
            
            ax.set_title('🎨 Filament Usage by Color', fontweight='bold', fontsize=12)
            
            # Add legend with grams
            legend_labels = [f"{c}: {u:.0f}g" for c, u in zip(color_names, usage)]
            ax.legend(wedges, legend_labels, title="Colors", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))
            
            fig.tight_layout()
            
            canvas = FigureCanvasTkAgg(fig, master=dlg)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        else:
            # Fallback to text display
            main = ttk.Frame(dlg, padding=15)
            main.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(main, text="🎨 Filament Usage by Color", font=("Segoe UI", 14, "bold")).pack(anchor=tk.W)
            
            color_stats = self.db.get_color_usage_stats()
            total = sum(color_stats.values())
            
            for color, usage in sorted(color_stats.items(), key=lambda x: -x[1]):
                percent = (usage / total * 100) if total > 0 else 0
                frame = ttk.Frame(main)
                frame.pack(fill=tk.X, pady=2)
                ttk.Label(frame, text=f"{color}:", width=15).pack(side=tk.LEFT)
                ttk.Label(frame, text=f"{usage:.0f}g ({percent:.1f}%)").pack(side=tk.LEFT)
        
        ttk.Button(dlg, text="Close", command=dlg.destroy).pack(pady=10)
    
    def _view_filament_history(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Filament Waste History")
        dlg.geometry("700x500")
        
        cols = ("Spool", "Color", "Used", "Wasted", "Date", "Reason")
        tree = ttk.Treeview(dlg, columns=cols, show="headings")
        
        for col, w in zip(cols, [150, 80, 60, 60, 90, 150]):
            tree.heading(col, text=col)
            tree.column(col, width=w)
        
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        history = self.db.get_filament_history()
        total_waste = 0
        
        for h in history:
            tree.insert("", tk.END, values=(
                h.spool_name, h.color, 
                f"{h.used_weight:.0f}g", 
                f"{h.waste_weight:.0f}g", 
                h.archived_date.split()[0], 
                h.reason
            ))
            total_waste += h.waste_weight
            
        ttk.Label(dlg, text=f"Total Wasted Filament: {total_waste:.0f}g", 
                 font=("Segoe UI", 12, "bold"), foreground=Colors.DANGER).pack(pady=10)
        
        ttk.Button(dlg, text="Close", command=dlg.destroy).pack(pady=5)
    
    def _show_spool_dialog(self, spool=None, is_remaining=False):
        dlg = tk.Toplevel(self.root)
        dlg.title("Add Remaining" if is_remaining else "Add Spool")
        dlg.geometry("400x280")
        dlg.transient(self.root)
        dlg.grab_set()
        
        is_edit = spool is not None
        if not spool:
            spool = FilamentSpool()
            if is_remaining:
                spool.category = SpoolCategory.REMAINING.value
                spool.brand = "Mixed"
                spool.purchase_price_egp = 0
        
        main = ttk.Frame(dlg, padding=15)
        main.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main, text="🎁 Remaining (FREE)" if is_remaining else "🆕 New Spool (840 EGP)", font=("Segoe UI", 12, "bold")).pack(anchor=tk.W)
        
        form = ttk.Frame(main)
        form.pack(fill=tk.X, pady=10)
        
        colors = self.db.get_colors()
        ttk.Label(form, text="Color:").grid(row=0, column=0, sticky=tk.W, pady=3)
        color_c = ttk.Combobox(form, values=colors, width=20, state="readonly")
        color_c.set(spool.color if spool.color in colors else colors[0])
        color_c.grid(row=0, column=1, sticky=tk.W, pady=3, padx=5)
        
        brand_c = None
        if not is_remaining:
            ttk.Label(form, text="Brand:").grid(row=1, column=0, sticky=tk.W, pady=3)
            settings = self.db.get_settings()
            brands = settings.get('filament_brands', ["eSUN", "Sunlu", "Creality", "Other"])
            brand_c = ttk.Combobox(form, values=brands, width=20)
            brand_c.set(spool.brand)
            brand_c.grid(row=1, column=1, sticky=tk.W, pady=3, padx=5)
        
        ttk.Label(form, text="Weight (g):").grid(row=2, column=0, sticky=tk.W, pady=3)
        weight_e = ttk.Entry(form, width=15)
        weight_e.insert(0, str(spool.current_weight_grams))
        weight_e.grid(row=2, column=1, sticky=tk.W, pady=3, padx=5)
        
        def save():
            try:
                w = float(weight_e.get() or 0)
                if w <= 0:
                    messagebox.showwarning("Error", "Enter weight")
                    return
                spool.color = color_c.get()
                spool.current_weight_grams = w
                spool.initial_weight_grams = w
                if is_remaining:
                    spool.category = SpoolCategory.REMAINING.value
                    spool.brand = "Mixed"
                    spool.purchase_price_egp = 0
                    spool.name = f"Remaining - {spool.color}"
                else:
                    spool.category = SpoolCategory.STANDARD.value
                    spool.brand = brand_c.get() if brand_c else "eSUN"
                    spool.purchase_price_egp = 840
                    spool.name = f"{spool.brand} PLA+ {spool.color}"
                if self.db.save_spool(spool):
                    if spool.color not in colors:
                        self.db.add_color(spool.color)
                    self._load_spools()
                    dlg.destroy()
            except Exception as e:
                messagebox.showerror("Error", str(e))
        
        btn_f = ttk.Frame(main)
        btn_f.pack(fill=tk.X, pady=10)
        ttk.Button(btn_f, text="💾 Save", command=save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_f, text="Cancel", command=dlg.destroy).pack(side=tk.LEFT, padx=5)
        
    # === CUSTOMER OPERATIONS ===
    
    def _add_customer(self):
        self.selected_customer = None
        self._clear_customer_form()
        self.cd_name.focus()
    
    def _clear_customer_form(self):
        self.cd_name.delete(0, tk.END)
        self.cd_phone.delete(0, tk.END)
        self.cd_email.delete(0, tk.END)
        self.cd_discount.delete(0, tk.END)
        self.cd_discount.insert(0, "0")
        self.cust_stats.config(text="")

    def _on_cust_select(self, event):
        sel = self.custs_tree.selection()
        if not sel:
            return
        c = self.db.get_customer(sel[0])
        if c:
            self.selected_customer = c
            self._load_customer_to_form(c)

    def _load_customer_to_form(self, c):
        self._clear_customer_form()
        self.cd_name.insert(0, c.name)
        self.cd_phone.insert(0, c.phone)
        self.cd_email.insert(0, c.email)
        self.cd_discount.delete(0, tk.END)
        self.cd_discount.insert(0, str(c.discount_percent))
        self.cust_stats.config(text=f"Orders: {c.total_orders} | Spent: {c.total_spent:.2f} EGP")

    def _save_customer(self):
        name = self.cd_name.get().strip()
        phone = self.cd_phone.get().strip()
        if not name:
            messagebox.showwarning("Error", "Name is required")
            return
        
        if self.selected_customer:
            c = self.selected_customer
            c.name = name
            c.phone = phone
            c.email = self.cd_email.get().strip()
            try:
                c.discount_percent = float(self.cd_discount.get() or 0)
            except:
                pass
            self.db.save_customer(c)
        else:
            c = Customer(name=name, phone=phone, email=self.cd_email.get().strip())
            try:
                c.discount_percent = float(self.cd_discount.get() or 0)
            except:
                pass
            self.db.save_customer(c)
        
        self._load_customers()
        self._clear_customer_form()
        messagebox.showinfo("Success", "Customer saved")

    def _del_customer(self):
        if not self.selected_customer:
            return
        if messagebox.askyesno("Confirm", f"Delete {self.selected_customer.name}?"):
            self.db.delete_customer(self.selected_customer.id)
            self._load_customers()
            self._clear_customer_form()
            self.selected_customer = None

    def _order_for_cust(self):
        if not self.selected_customer:
            messagebox.showwarning("Select", "Select a customer first")
            return
        self.notebook.select(0)
        self._new_order()
        self.cust_name.delete(0, tk.END)
        self.cust_name.insert(0, self.selected_customer.name)
        self.cust_phone.delete(0, tk.END)
        self.cust_phone.insert(0, self.selected_customer.phone)
        if self.current_order:
            self.current_order.customer_id = self.selected_customer.id
            self.current_order.customer_name = self.selected_customer.name
            self.current_order.customer_phone = self.selected_customer.phone
            self.current_order.order_discount_percent = self.selected_customer.discount_percent
            self.order_discount_entry.delete(0, tk.END)
            self.order_discount_entry.insert(0, str(self.selected_customer.discount_percent))

    # === FILAMENT BUTTON HANDLERS ===
    
    def _add_new_spool(self):
        self._show_spool_dialog()

    def _add_remaining_spool(self):
        self._show_spool_dialog(is_remaining=True)

    def _edit_spool(self):
        sel = self.spools_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select a spool to edit")
            return
        s = self.db.get_spool(sel[0])
        if s:
            self._show_spool_dialog(spool=s, is_remaining=(s.category == SpoolCategory.REMAINING.value))

    def _del_spool(self):
        sel = self.spools_tree.selection()
        if not sel:
            return
        if messagebox.askyesno("Confirm", "Delete this spool?"):
            self.db.delete_spool(sel[0])
            self._load_spools()
    
    def _edit_spool_payment(self):
        """Edit payment/loan information for a spool"""
        sel = self.spools_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select a spool to edit payment info")
            return
        
        spool = self.db.get_spool(sel[0])
        if not spool:
            return
        
        # Skip remaining spools
        if spool.category == SpoolCategory.REMAINING.value:
            messagebox.showinfo("Info", "Remaining spools have no cost, no payment tracking needed.")
            return
        
        dlg = tk.Toplevel(self.root)
        dlg.title(f"Payment/Loan Info - {spool.display_name}")
        dlg.geometry("450x350")
        dlg.transient(self.root)
        dlg.grab_set()
        
        ttk.Label(dlg, text=f"Spool: {spool.display_name}", font=("Segoe UI", 12, "bold")).pack(pady=10)
        ttk.Label(dlg, text=f"Price: {spool.purchase_price_egp:,.0f} EGP").pack()
        
        frame = ttk.Frame(dlg, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Payment source
        ttk.Label(frame, text="Payment Source:").grid(row=0, column=0, sticky=tk.W, pady=5)
        source_var = tk.StringVar(value=spool.payment_source)
        source_cb = ttk.Combobox(frame, textvariable=source_var, 
                                 values=[PaymentSource.PROFIT.value, PaymentSource.POCKET.value, 
                                        PaymentSource.LOAN.value, PaymentSource.GIFT.value],
                                 state="readonly", width=20)
        source_cb.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # Loan provider
        ttk.Label(frame, text="Loan Provider:").grid(row=1, column=0, sticky=tk.W, pady=5)
        provider_var = tk.StringVar(value=spool.loan_provider)
        provider_entry = ttk.Entry(frame, textvariable=provider_var, width=25)
        provider_entry.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Loan paid checkbox
        paid_var = tk.BooleanVar(value=spool.loan_paid)
        paid_cb = ttk.Checkbutton(frame, text="Loan has been PAID back", variable=paid_var)
        paid_cb.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Loan paid amount
        ttk.Label(frame, text="Amount Paid:").grid(row=3, column=0, sticky=tk.W, pady=5)
        amount_var = tk.StringVar(value=str(spool.loan_paid_amount or spool.purchase_price_egp))
        amount_entry = ttk.Entry(frame, textvariable=amount_var, width=15)
        amount_entry.grid(row=3, column=1, sticky=tk.W, pady=5)
        
        # Info label
        info_text = ("💡 Payment affects profit calculation:\n"
                    "• From Profit: Deducted from profit\n"
                    "• Loan (PAID): Deducted when repaid\n"
                    "• Loan (UNPAID): Not deducted yet\n"
                    "• From Pocket/Gift: Never affects profit")
        info_lbl = ttk.Label(frame, text=info_text, foreground=Colors.TEXT_SECONDARY)
        info_lbl.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=10)
        
        def save():
            source = source_var.get()
            provider = provider_var.get().strip()
            paid = paid_var.get()
            try:
                amount = float(amount_var.get() or spool.purchase_price_egp)
            except:
                amount = spool.purchase_price_egp
            
            # Validation
            if source == PaymentSource.LOAN.value and not provider:
                messagebox.showwarning("Validation", "Please enter the loan provider name")
                return
            
            self.db.update_spool_payment(spool.id, source, provider, paid, amount)
            self._load_spools()
            dlg.destroy()
            messagebox.showinfo("Success", "Payment information updated!")
        
        btn_frame = ttk.Frame(dlg)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="💾 Save", command=save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dlg.destroy).pack(side=tk.LEFT, padx=5)
    
    def _show_consumption_chart(self):
        """Show filament consumption chart"""
        if not MATPLOTLIB_AVAILABLE:
            messagebox.showinfo("Not Available", "Matplotlib is not installed. Install it with: pip install matplotlib")
            return
        
        dlg = tk.Toplevel(self.root)
        dlg.title("📈 Filament Consumption Chart")
        dlg.geometry("800x600")
        dlg.transient(self.root)
        
        # Get spools data
        spools = self.db.get_all_spools()
        
        # Filter to standard spools only
        std_spools = [s for s in spools if s.category != SpoolCategory.REMAINING.value]
        
        if not std_spools:
            ttk.Label(dlg, text="No standard spools to display", font=("Segoe UI", 12)).pack(pady=50)
            return
        
        # Create figure with subplots
        fig = Figure(figsize=(10, 7), dpi=100)
        
        # Subplot 1: Consumption per spool (bar chart)
        ax1 = fig.add_subplot(2, 1, 1)
        names = [s.display_name[:20] for s in std_spools]
        used = [s.used_weight_grams for s in std_spools]
        remaining = [s.current_weight_grams for s in std_spools]
        
        x = range(len(names))
        width = 0.35
        ax1.bar([i - width/2 for i in x], used, width, label='Used', color='#3b82f6')
        ax1.bar([i + width/2 for i in x], remaining, width, label='Remaining', color='#22c55e')
        ax1.set_ylabel('Grams')
        ax1.set_title('Spool Consumption Overview')
        ax1.set_xticks(x)
        ax1.set_xticklabels(names, rotation=45, ha='right')
        ax1.legend()
        
        # Subplot 2: Cost breakdown
        ax2 = fig.add_subplot(2, 1, 2)
        spool_costs = self.db.get_spool_cost_for_profit()
        
        labels = ['From Profit', 'Loans Repaid', 'Pending Loans', 'From Pocket']
        values = [
            spool_costs['profit_cost'],
            spool_costs['loan_repaid_cost'],
            spool_costs['pending_loan_cost'],
            spool_costs['pocket_cost']
        ]
        colors = ['#f59e0b', '#22c55e', '#ef4444', '#3b82f6']
        
        # Filter out zero values
        non_zero = [(l, v, c) for l, v, c in zip(labels, values, colors) if v > 0]
        if non_zero:
            labels, values, colors = zip(*non_zero)
            ax2.pie(values, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            ax2.set_title('Spool Purchase Cost Breakdown')
        else:
            ax2.text(0.5, 0.5, 'No purchase data', ha='center', va='center')
        
        fig.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, dlg)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    # === PRINTER OPERATIONS ===
    def _add_printer(self):
        name = simpledialog.askstring("Add Printer", "Enter printer name:")
        if name:
            self.db.save_printer(Printer(name=name))
            self._load_printers()
    
    def _on_printer_select(self, event):
        sel = self.printers_tree.selection()
        if not sel:
            return
        p = self.db.get_printer(sel[0])
        if p:
            self.printer_detail.config(text=f"Name: {p.name}\nModel: {p.model}\nPrinted: {p.total_printed_grams:.0f}g\nTime: {format_time(p.total_print_time_minutes)}\nNozzles: {p.nozzle_changes}\nElectricity: {p.total_electricity_cost:.2f} EGP")
    
    def _edit_printer(self):
        sel = self.printers_tree.selection()
        if not sel:
            return
        p = self.db.get_printer(sel[0])
        if p:
            name = simpledialog.askstring("Edit Printer", "Enter name:", initialvalue=p.name)
            if name:
                p.name = name
                self.db.save_printer(p)
                self._load_printers()
    
    def _reset_nozzle(self):
        sel = self.printers_tree.selection()
        if sel and messagebox.askyesno("Reset Nozzle", "Record nozzle change?"):
            p = self.db.get_printer(sel[0])
            if p:
                p.nozzle_changes += 1
                p.current_nozzle_grams = 0
                self.db.save_printer(p)
                self._load_printers()
    
    # === SETTINGS ===
    def _save_settings(self):
        settings = {
            'company_name': self.set_company.get().strip(),
            'company_phone': self.set_phone.get().strip(),
            'default_rate_per_gram': float(self.set_rate.get() or 4.0),
            'deposit_percent': float(self.set_deposit.get() or 50),
        }
        if self.db.save_settings(settings):
            messagebox.showinfo("Success", "Settings saved!")
    
    def _backup(self):
        path = self.db.backup_database()
        messagebox.showinfo("Backup", f"Backup created:\n{path}")
    
    def _export_csv(self):
        try:
            files = self.db.export_to_csv()
            messagebox.showinfo("Export", f"Exported:\n" + "\n".join(f"{k}: {v}" for k, v in files.items()))
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    # === FAILURES ===
    def _load_failures(self):
        """Load failures into the tree"""
        if not hasattr(self, 'failures_tree'):
            return
        for i in self.failures_tree.get_children():
            self.failures_tree.delete(i)
        
        source_filter = self.failure_filter.get() if hasattr(self, 'failure_filter') else "All"
        failures = self.db.get_all_failures()
        if source_filter != "All":
            failures = [f for f in failures if f.source == source_filter]
        
        total_cost = sum(f.total_loss for f in failures)
        total_filament = sum(f.filament_wasted_grams for f in failures)
        
        self.failure_summary.config(
            text=f"📊 {len(failures)} failures | 💸 {total_cost:.0f} EGP lost | 🎨 {total_filament:.0f}g wasted"
        )
        
        for f in failures:
            # Show order info or item name
            if f.source == FailureSource.CUSTOMER_ORDER.value and f.order_number:
                order_item = f"#{f.order_number} - {f.customer_name or f.item_name}"
            elif f.source == FailureSource.RD_PROJECT.value:
                order_item = f"🔬 {f.item_name or 'R&D'}"
            else:
                order_item = f.item_name or "Unknown"
            
            self.failures_tree.insert("", tk.END, iid=f.id, values=(
                f.date.split()[0], f.source,
                order_item, f.reason, 
                f"{f.filament_wasted_grams:.0f}g", f"{f.total_loss:.0f}"
            ))
    
    def _on_failure_select(self, event):
        """Show failure details"""
        sel = self.failures_tree.selection()
        if not sel:
            return
        f = self.db.get_failure(sel[0])
        if f:
            details = f"Source: {f.source}\n"
            if f.order_number:
                details += f"Order: #{f.order_number} ({f.customer_name})\n"
            details += f"Item: {f.item_name}\nReason: {f.reason}\n"
            details += f"Filament: {f.filament_wasted_grams}g ({f.color})\n"
            details += f"Time: {f.time_wasted_minutes} minutes\n"
            details += f"Cost: {f.total_loss:.2f} EGP (Material: {f.filament_cost:.2f} + Elec: {f.electricity_cost:.2f})\n"
            if f.printer_name:
                details += f"Printer: {f.printer_name}\n"
            if f.description:
                details += f"Notes: {f.description}"
            self.failure_detail.config(text=details)
    
    def _add_failure(self):
        """Add new failure dialog"""
        dlg = tk.Toplevel(self.root)
        dlg.title("Log Print Failure")
        dlg.geometry("500x620")
        dlg.transient(self.root)
        dlg.grab_set()
        
        # Center dialog
        dlg.update_idletasks()
        x = (dlg.winfo_screenwidth() - 500) // 2
        y = (dlg.winfo_screenheight() - 620) // 2
        dlg.geometry(f"500x620+{x}+{y}")
        
        main = ttk.Frame(dlg, padding=15)
        main.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main, text="⚠️ Log Print Failure", font=("Segoe UI", 14, "bold")).pack(anchor=tk.W, pady=(0, 10))
        
        # Source selection
        source_f = ttk.LabelFrame(main, text="Failure Source", padding=10)
        source_f.pack(fill=tk.X, pady=(0, 10))
        
        source_var = tk.StringVar(value=FailureSource.OTHER.value)
        order_data = {'id': '', 'number': 0, 'customer': ''}
        
        # Get orders for dropdown
        orders = self.db.get_all_orders()
        order_list = [f"#{o.order_number} - {o.customer_name or 'Walk-in'}" for o in orders[:50]]
        order_ids = {f"#{o.order_number} - {o.customer_name or 'Walk-in'}": o for o in orders[:50]}
        
        ttk.Radiobutton(source_f, text="📦 Customer Order", variable=source_var, 
                       value=FailureSource.CUSTOMER_ORDER.value).pack(anchor=tk.W)
        
        order_frame = ttk.Frame(source_f)
        order_frame.pack(fill=tk.X, padx=20, pady=5)
        order_c = ttk.Combobox(order_frame, values=order_list, width=40, state="readonly")
        order_c.pack(side=tk.LEFT)
        
        ttk.Radiobutton(source_f, text="🔬 R&D Project", variable=source_var,
                       value=FailureSource.RD_PROJECT.value).pack(anchor=tk.W)
        ttk.Radiobutton(source_f, text="🧪 Personal/Test", variable=source_var,
                       value=FailureSource.PERSONAL.value).pack(anchor=tk.W)
        ttk.Radiobutton(source_f, text="❓ Other", variable=source_var,
                       value=FailureSource.OTHER.value).pack(anchor=tk.W)
        
        # Item name
        ttk.Label(main, text="What was printing:").pack(anchor=tk.W)
        item_e = ttk.Entry(main, width=45)
        item_e.pack(fill=tk.X, pady=(0, 8))
        
        # Auto-fill item name when order selected
        def on_order_select(e):
            source_var.set(FailureSource.CUSTOMER_ORDER.value)
            sel = order_c.get()
            if sel in order_ids:
                order = order_ids[sel]
                order_data['id'] = order.id
                order_data['number'] = order.order_number
                order_data['customer'] = order.customer_name
                if order.items:
                    item_e.delete(0, tk.END)
                    item_e.insert(0, order.items[0].name)
        order_c.bind('<<ComboboxSelected>>', on_order_select)
        
        # Reason
        ttk.Label(main, text="Failure Reason:").pack(anchor=tk.W)
        reason_c = ttk.Combobox(main, values=[r.value for r in FailureReason], state="readonly", width=35)
        reason_c.set(FailureReason.OTHER.value)
        reason_c.pack(anchor=tk.W, pady=(0, 8))
        
        # Filament and Time row
        ft_frame = ttk.Frame(main)
        ft_frame.pack(fill=tk.X, pady=(0, 8))
        
        ttk.Label(ft_frame, text="Filament (g):").pack(side=tk.LEFT)
        filament_e = ttk.Entry(ft_frame, width=10)
        filament_e.insert(0, "0")
        filament_e.pack(side=tk.LEFT, padx=(5, 20))
        
        ttk.Label(ft_frame, text="Time (min):").pack(side=tk.LEFT)
        time_e = ttk.Entry(ft_frame, width=10)
        time_e.insert(0, "0")
        time_e.pack(side=tk.LEFT, padx=5)
        
        # Color and Printer row
        cp_frame = ttk.Frame(main)
        cp_frame.pack(fill=tk.X, pady=(0, 8))
        
        ttk.Label(cp_frame, text="Color:").pack(side=tk.LEFT)
        colors = self.db.get_colors()
        color_c = ttk.Combobox(cp_frame, values=colors, width=12)
        color_c.set(colors[0] if colors else "")
        color_c.pack(side=tk.LEFT, padx=(5, 20))
        
        ttk.Label(cp_frame, text="Printer:").pack(side=tk.LEFT)
        printers = self.db.get_all_printers()
        printer_c = ttk.Combobox(cp_frame, values=[p.name for p in printers], width=15)
        if printers:
            printer_c.set(printers[0].name)
        printer_c.pack(side=tk.LEFT, padx=5)
        
        # Description
        ttk.Label(main, text="Description/Notes:").pack(anchor=tk.W)
        desc_e = tk.Text(main, height=3, width=45)
        desc_e.pack(fill=tk.X, pady=(0, 8))
        
        # Cost preview
        cost_lbl = ttk.Label(main, text="Estimated Loss: 0 EGP", font=("Segoe UI", 11, "bold"),
                            foreground=Colors.DANGER)
        cost_lbl.pack(anchor=tk.W, pady=5)
        
        def update_cost(*args):
            try:
                grams = float(filament_e.get() or 0)
                mins = int(time_e.get() or 0)
                filament_cost = grams * 0.84  # 840 EGP per 1000g
                elec_cost = (mins / 60) * 0.31
                total = filament_cost + elec_cost
                cost_lbl.config(text=f"Estimated Loss: {total:.2f} EGP (Material: {filament_cost:.2f} + Elec: {elec_cost:.2f})")
            except:
                pass
        
        filament_e.bind('<KeyRelease>', update_cost)
        time_e.bind('<KeyRelease>', update_cost)
        
        def save():
            try:
                failure = PrintFailure(
                    source=source_var.get(),
                    order_id=order_data['id'] if source_var.get() == FailureSource.CUSTOMER_ORDER.value else '',
                    order_number=order_data['number'] if source_var.get() == FailureSource.CUSTOMER_ORDER.value else 0,
                    customer_name=order_data['customer'] if source_var.get() == FailureSource.CUSTOMER_ORDER.value else '',
                    item_name=item_e.get().strip() or "Unknown",
                    reason=reason_c.get(),
                    filament_wasted_grams=float(filament_e.get() or 0),
                    time_wasted_minutes=int(time_e.get() or 0),
                    color=color_c.get(),
                    description=desc_e.get("1.0", tk.END).strip(),
                    printer_name=printer_c.get()
                )
                
                # Find spool to deduct from
                spools = self.db.get_spools_by_color(color_c.get())
                if spools and failure.filament_wasted_grams > 0:
                    failure.spool_id = spools[0].id
                
                self.db.save_failure(failure)
                self._load_failures()
                self._load_spools()
                if hasattr(self, 'stat_lbls'):
                    self._load_stats()
                dlg.destroy()
                messagebox.showinfo("Logged", f"Failure logged: {failure.total_loss:.2f} EGP loss")
            except Exception as e:
                messagebox.showerror("Error", str(e))
        
        btn_f = ttk.Frame(main)
        btn_f.pack(fill=tk.X, pady=10)
        ttk.Button(btn_f, text="💾 Save Failure", command=save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_f, text="Cancel", command=dlg.destroy).pack(side=tk.LEFT, padx=5)
    
    def _delete_failure(self):
        """Delete selected failure"""
        sel = self.failures_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select a failure to delete")
            return
        if messagebox.askyesno("Confirm", "Delete this failure record?"):
            self.db.delete_failure(sel[0])
            self._load_failures()
            if hasattr(self, 'stat_lbls'):
                self._load_stats()
    
    def _show_failure_stats(self):
        """Show failure statistics popup"""
        stats = self.db.get_failure_stats()
        msg = f"📊 Failure Statistics\n\n"
        msg += f"Total Failures: {stats['total_failures']}\n"
        msg += f"Total Cost: {stats['total_cost']:.0f} EGP\n"
        msg += f"Filament Wasted: {stats['total_filament_wasted']:.0f}g\n"
        msg += f"Time Wasted: {stats['total_time_wasted']} minutes\n\n"
        msg += "By Reason:\n"
        for reason, count in stats['by_reason'].items():
            msg += f"  • {reason}: {count}\n"
        messagebox.showinfo("Failure Statistics", msg)
    
    # === EXPENSES ===
    def _load_expenses(self):
        """Load expenses into the tree"""
        if not hasattr(self, 'expenses_tree'):
            return
        for i in self.expenses_tree.get_children():
            self.expenses_tree.delete(i)
        
        category = self.expense_filter.get() if hasattr(self, 'expense_filter') else "All"
        expenses = self.db.get_all_expenses()
        if category != "All":
            expenses = [e for e in expenses if e.category == category]
        
        total = sum(e.total_cost for e in expenses)
        self.expense_summary.config(
            text=f"📊 {len(expenses)} expenses | 💰 {total:.0f} EGP total"
        )
        
        for e in expenses:
            self.expenses_tree.insert("", tk.END, iid=e.id, values=(
                e.date.split()[0], e.category, e.name,
                e.quantity, f"{e.amount:.0f}", f"{e.total_cost:.0f}",
                e.supplier or "-"
            ))
    
    def _add_expense(self):
        """Add new expense dialog"""
        dlg = tk.Toplevel(self.root)
        dlg.title("Add Expense")
        dlg.geometry("450x520")
        dlg.transient(self.root)
        dlg.grab_set()
        
        # Center dialog
        dlg.update_idletasks()
        x = (dlg.winfo_screenwidth() - 450) // 2
        y = (dlg.winfo_screenheight() - 520) // 2
        dlg.geometry(f"450x520+{x}+{y}")
        
        main = ttk.Frame(dlg, padding=15)
        main.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main, text="💰 Add Business Expense", font=("Segoe UI", 14, "bold")).pack(anchor=tk.W, pady=(0, 10))
        
        # Category with icons
        cat_f = ttk.LabelFrame(main, text="Category", padding=10)
        cat_f.pack(fill=tk.X, pady=(0, 10))
        
        category_icons = {
            ExpenseCategory.BILLS.value: "📄 Bills (Electricity, Internet, Rent)",
            ExpenseCategory.ENGINEER.value: "👨‍🔧 Engineer/Operator Salary",
            ExpenseCategory.TOOLS.value: "🔧 Tools (Nozzles, Spatulas)",
            ExpenseCategory.CONSUMABLES.value: "🧴 Consumables (Glue, Tape, Alcohol)",
            ExpenseCategory.MAINTENANCE.value: "🔩 Maintenance & Repairs",
            ExpenseCategory.FILAMENT.value: "🎨 Filament Purchases",
            ExpenseCategory.PACKAGING.value: "📦 Packaging Materials",
            ExpenseCategory.SOFTWARE.value: "💻 Software & Subscriptions",
            ExpenseCategory.OTHER.value: "📌 Other Expenses",
        }
        
        category_c = ttk.Combobox(cat_f, values=list(category_icons.values()), state="readonly", width=40)
        category_c.set(category_icons[ExpenseCategory.BILLS.value])
        category_c.pack(fill=tk.X)
        
        # Name
        ttk.Label(main, text="Description/Item Name:").pack(anchor=tk.W, pady=(5, 0))
        name_e = ttk.Entry(main, width=45)
        name_e.pack(fill=tk.X, pady=(0, 8))
        
        # Common items suggestions based on category
        suggestions = {
            "Bills": ["Electricity Bill", "Internet Bill", "Rent", "Water Bill", "Phone Bill"],
            "Engineer": ["Monthly Salary", "Weekly Wages", "Overtime", "Bonus"],
            "Tools": ["Nozzle 0.4mm", "Spatula", "Pliers", "Scraper", "Cutting Mat"],
            "Consumables": ["3D Glue Stick", "Masking Tape", "IPA Alcohol", "Lubricant", "Cleaning Cloth"],
        }
        
        # Amount and Quantity row
        aq_frame = ttk.Frame(main)
        aq_frame.pack(fill=tk.X, pady=(0, 8))
        
        ttk.Label(aq_frame, text="Amount (EGP):").pack(side=tk.LEFT)
        amount_e = ttk.Entry(aq_frame, width=12)
        amount_e.insert(0, "0")
        amount_e.pack(side=tk.LEFT, padx=(5, 20))
        
        ttk.Label(aq_frame, text="Quantity:").pack(side=tk.LEFT)
        qty_e = ttk.Entry(aq_frame, width=8)
        qty_e.insert(0, "1")
        qty_e.pack(side=tk.LEFT, padx=5)
        
        # Recurring option
        recurring_var = tk.BooleanVar(value=False)
        recurring_cb = ttk.Checkbutton(main, text="📅 Recurring expense (monthly)", variable=recurring_var)
        recurring_cb.pack(anchor=tk.W, pady=(5, 8))
        
        # Supplier
        ttk.Label(main, text="Supplier/Vendor (optional):").pack(anchor=tk.W)
        supplier_e = ttk.Entry(main, width=35)
        supplier_e.pack(anchor=tk.W, pady=(0, 8))
        
        # Description
        ttk.Label(main, text="Notes:").pack(anchor=tk.W)
        desc_e = tk.Text(main, height=2, width=45)
        desc_e.pack(fill=tk.X, pady=(0, 8))
        
        # Total display
        total_lbl = ttk.Label(main, text="Total: 0 EGP", font=("Segoe UI", 12, "bold"),
                             foreground=Colors.WARNING)
        total_lbl.pack(anchor=tk.W, pady=5)
        
        def update_total(*args):
            try:
                amt = float(amount_e.get() or 0)
                qty = int(qty_e.get() or 1)
                total_lbl.config(text=f"Total: {amt * qty:.0f} EGP")
            except:
                pass
        
        amount_e.bind('<KeyRelease>', update_total)
        qty_e.bind('<KeyRelease>', update_total)
        
        def save():
            try:
                name = name_e.get().strip()
                if not name:
                    messagebox.showwarning("Error", "Enter description/name")
                    return
                
                # Extract category from display text
                cat_display = category_c.get()
                category = ExpenseCategory.OTHER.value
                for cat, display in category_icons.items():
                    if display == cat_display:
                        category = cat
                        break
                
                expense = Expense(
                    category=category,
                    name=name,
                    amount=float(amount_e.get() or 0),
                    quantity=int(qty_e.get() or 1),
                    supplier=supplier_e.get().strip(),
                    description=desc_e.get("1.0", tk.END).strip(),
                    is_recurring=recurring_var.get(),
                    recurring_period="monthly" if recurring_var.get() else ""
                )
                expense.calculate_total()
                
                self.db.save_expense(expense)
                self._load_expenses()
                if hasattr(self, 'stat_lbls'):
                    self._load_stats()
                dlg.destroy()
                messagebox.showinfo("Added", f"Expense added: {expense.total_cost:.0f} EGP")
            except Exception as e:
                messagebox.showerror("Error", str(e))
        
        btn_f = ttk.Frame(main)
        btn_f.pack(fill=tk.X, pady=10)
        ttk.Button(btn_f, text="💾 Save Expense", command=save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_f, text="Cancel", command=dlg.destroy).pack(side=tk.LEFT, padx=5)
    
    def _edit_expense(self):
        """Edit selected expense"""
        sel = self.expenses_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select an expense to edit")
            return
        # For simplicity, just delete and re-add
        messagebox.showinfo("Edit", "Delete and re-add to edit expense")
    
    def _delete_expense(self):
        """Delete selected expense"""
        sel = self.expenses_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select an expense to delete")
            return
        if messagebox.askyesno("Confirm", "Delete this expense?"):
            self.db.delete_expense(sel[0])
            self._load_expenses()
            if hasattr(self, 'stat_lbls'):
                self._load_stats()
    
    def _show_expense_summary(self):
        """Show expense summary popup"""
        stats = self.db.get_expense_stats()
        msg = f"📊 Expense Summary\n\n"
        msg += f"Total Expenses: {stats['total_expenses']:.0f} EGP\n"
        msg += f"Number of Items: {stats['expense_count']}\n\n"
        msg += "By Category:\n"
        for cat, total in stats['by_category'].items():
            msg += f"  • {cat}: {total:.0f} EGP\n"
        messagebox.showinfo("Expense Summary", msg)


def main():
    """Main entry point with role selection"""
    import tkinter.simpledialog as simpledialog
    
    # Create hidden root
    root = tk.Tk()
    root.withdraw()
    
    # Simple role selection popup
    auth = get_auth_manager()
    
    # Create selection window
    select_win = tk.Toplevel(root)
    select_win.title("Abaad ERP v4.0")
    select_win.geometry("400x350")
    select_win.resizable(False, False)
    select_win.configure(bg="#f0f4f8")
    
    # Center on screen
    select_win.update_idletasks()
    x = (select_win.winfo_screenwidth() - 400) // 2
    y = (select_win.winfo_screenheight() - 350) // 2
    select_win.geometry(f"400x350+{x}+{y}")
    
    selected_user = [None]  # Use list to modify in nested function
    
    def select_admin():
        user = auth.users.get('admin_default')
        if not user:
            from src.logic.auth import User, UserRole
            user = User(
                id='admin_default',
                username='admin', 
                role=UserRole.ADMIN.value,
                display_name='Administrator'
            )
            user.set_password('admin')
            auth.users[user.id] = user
            auth._save_users()
        auth._current_user = user
        selected_user[0] = user
        select_win.destroy()
    
    def select_user():
        user = auth.users.get('user_default')
        if not user:
            from src.logic.auth import User, UserRole
            user = User(
                id='user_default',
                username='user',
                role=UserRole.USER.value, 
                display_name='Staff User'
            )
            user.set_password('user')
            auth.users[user.id] = user
            auth._save_users()
        auth._current_user = user
        selected_user[0] = user
        select_win.destroy()
    
    def on_close():
        select_win.destroy()
        root.destroy()
    
    select_win.protocol("WM_DELETE_WINDOW", on_close)
    
    # Header
    header = tk.Frame(select_win, bg="#2563eb", height=70)
    header.pack(fill=tk.X)
    header.pack_propagate(False)
    tk.Label(header, text="🖨️ Abaad ERP v4.0", font=("Arial", 18, "bold"),
             bg="#2563eb", fg="white").pack(expand=True)
    
    # Content
    content = tk.Frame(select_win, bg="#f0f4f8")
    content.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)
    
    tk.Label(content, text="Select Your Role:", font=("Arial", 14, "bold"),
             bg="#f0f4f8", fg="#333").pack(pady=(0, 20))
    
    # Admin button
    admin_btn = tk.Button(content, text="👑 Administrator\n(Full Access)", 
                         font=("Arial", 12), bg="#7c3aed", fg="white",
                         activebackground="#6d28d9", activeforeground="white",
                         width=25, height=3, relief=tk.FLAT, cursor="hand2",
                         command=select_admin)
    admin_btn.pack(pady=8)
    
    # User button  
    user_btn = tk.Button(content, text="👤 Staff User\n(Orders & Customers)",
                        font=("Arial", 12), bg="#0891b2", fg="white",
                        activebackground="#0e7490", activeforeground="white",
                        width=25, height=3, relief=tk.FLAT, cursor="hand2",
                        command=select_user)
    user_btn.pack(pady=8)
    
    # Footer
    tk.Label(content, text="Abaad 3D Printing • Ismailia", font=("Arial", 9),
             bg="#f0f4f8", fg="#888").pack(side=tk.BOTTOM, pady=10)
    
    # Focus and wait
    select_win.focus_force()
    select_win.grab_set()
    root.wait_window(select_win)
    
    # After selection
    if selected_user[0]:
        root.deiconify()
        app = App(root, selected_user[0])
        root.mainloop()
    else:
        root.destroy()


if __name__ == "__main__":
    main()
