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
    SpoolCategory, SpoolStatus, format_time, generate_id, now_str,
    DEFAULT_RATE_PER_GRAM, DEFAULT_COST_PER_GRAM, TRASH_THRESHOLD_GRAMS,
    TOLERANCE_THRESHOLD_GRAMS, calculate_payment_fee
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


class App:
    def __init__(self, root, user):
        self.root = root
        self.user = user
        self.auth = get_auth_manager()
        self.root.title(f"Abaad ERP v4.0 - {user.display_name or user.username}")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 700)
        self.root.configure(bg=Colors.BG)
        
        # Try to set window icon
        try:
            icon_path = Path(__file__).parent / "assets" / "Abaad.png"
            if icon_path.exists():
                img = tk.PhotoImage(file=str(icon_path))
                self.root.iconphoto(True, img)
        except:
            pass
        
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
        
        # Admin-only tabs
        if self.auth.has_permission(Permission.VIEW_STATISTICS):
            self._build_stats_tab()
        
        if self.auth.has_permission(Permission.MANAGE_SETTINGS):
            self._build_settings_tab()
        
        if self.auth.has_permission(Permission.MANAGE_USERS):
            self._build_admin_tab()
        
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
        
        self.spool_summary = ttk.Label(tab, text="")
        self.spool_summary.pack(anchor=tk.W, pady=5)
        
        cols = ("Name", "Color", "Type", "Initial", "Available", "Pending", "Used", "Cost/g", "Status")
        self.spools_tree = ttk.Treeview(tab, columns=cols, show="headings", height=18)
        for col, w in zip(cols, [130, 70, 70, 60, 75, 55, 55, 50, 60]):
            self.spools_tree.heading(col, text=col)
            self.spools_tree.column(col, width=w)
        self.spools_tree.pack(fill=tk.BOTH, expand=True)
        
        btn_f = ttk.Frame(tab)
        btn_f.pack(fill=tk.X, pady=5)
        
        if self.auth.has_permission(Permission.MANAGE_INVENTORY):
            ttk.Button(btn_f, text="Edit", command=self._edit_spool).pack(side=tk.LEFT, padx=3)
            ttk.Button(btn_f, text="Delete", command=self._del_spool).pack(side=tk.LEFT, padx=3)
            ttk.Button(btn_f, text="🗑️ Trash", command=self._move_to_trash).pack(side=tk.LEFT, padx=3)
        
        ttk.Button(btn_f, text="📜 History", command=self._view_filament_history).pack(side=tk.LEFT, padx=3)
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
    
    def _build_stats_tab(self):
        """Statistics tab - Admin only"""
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="📊 Statistics")
        
        ttk.Label(tab, text="Business Dashboard", style="Title.TLabel").pack(anchor=tk.W, pady=(0, 15))
        
        self.stat_lbls = {}
        cards = ttk.Frame(tab)
        cards.pack(fill=tk.X)
        
        stats = [("Orders", "orders"), ("Completed", "completed"), ("R&D", "rd"), ("Revenue", "revenue"), 
                 ("Profit", "profit"), ("Margin", "margin"), ("Material", "material"), ("Electricity", "electricity"),
                 ("Nozzle", "nozzle"), ("Shipping", "shipping"), ("Fees", "fees"), ("Rounding", "rounding"),
                 ("Weight", "weight"), ("Waste", "waste"), ("Customers", "custs"), ("Tolerance", "tolerance")]
        
        for i, (label, key) in enumerate(stats):
            row, col = i // 4, i % 4
            frame = tk.Frame(cards, bg=Colors.CARD, relief=tk.RIDGE, bd=1)
            frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            tk.Label(frame, text=label, bg=Colors.CARD, fg=Colors.TEXT_LIGHT).pack(pady=(8, 0))
            lbl = tk.Label(frame, text="0", bg=Colors.CARD, fg=Colors.PRIMARY, font=("Segoe UI", 14, "bold"))
            lbl.pack(pady=(0, 8))
            self.stat_lbls[key] = lbl
        
        for i in range(4):
            cards.columnconfigure(i, weight=1)
        
        btn_f = ttk.Frame(tab)
        btn_f.pack(pady=20)
        ttk.Button(btn_f, text="🔄 Refresh", command=self._load_stats).pack(side=tk.LEFT, padx=5)
        
        if self.auth.has_permission(Permission.EXPORT_DATA):
            ttk.Button(btn_f, text="📤 Export CSV", command=self._export_csv).pack(side=tk.LEFT, padx=5)
    
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
        if hasattr(self, 'stat_lbls'):
            self._load_stats()
    
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
        total_r = sum(s.current_weight_grams for s in spools if s.is_active)
        total_p = sum(s.pending_weight_grams for s in spools)
        total_u = sum(s.used_weight_grams for s in spools)
        active = len([s for s in spools if s.is_active and s.current_weight_grams > 50])
        
        for s in spools:
            if s.status == SpoolStatus.TRASH.value:
                status = "🗑️ Trash"
            elif s.current_weight_grams <= 0:
                status = "Empty"
            elif s.should_show_trash_button:
                status = "⚠️ Low"
            else:
                status = "Active"
            category = "Remaining" if s.category == SpoolCategory.REMAINING.value else "Standard"
            cost_per_g = f"{s.cost_per_gram:.2f}" if s.cost_per_gram > 0 else "FREE"
            self.spools_tree.insert("", tk.END, iid=s.id, values=(
                s.display_name, s.color, category, f"{s.initial_weight_grams:.0f}g",
                f"{s.available_weight_grams:.0f}g ({s.remaining_percent:.0f}%)",
                f"{s.pending_weight_grams:.0f}g", f"{s.used_weight_grams:.0f}g", cost_per_g, status
            ))
        self.spool_summary.config(text=f"{len(spools)} spools | {active} active | {total_r:.0f}g remaining | {total_p:.0f}g pending | {total_u:.0f}g used")
    
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
        self.stat_lbls['orders'].config(text=str(s.total_orders))
        self.stat_lbls['completed'].config(text=str(s.completed_orders))
        self.stat_lbls['rd'].config(text=str(s.rd_orders))
        self.stat_lbls['revenue'].config(text=f"{s.total_revenue:.0f}")
        self.stat_lbls['profit'].config(text=f"{s.total_profit:.0f}")
        self.stat_lbls['material'].config(text=f"{s.total_material_cost:.0f}")
        self.stat_lbls['electricity'].config(text=f"{s.total_electricity_cost:.1f}")
        self.stat_lbls['nozzle'].config(text=f"{s.total_nozzle_cost:.0f}")
        self.stat_lbls['shipping'].config(text=f"{s.total_shipping:.0f}")
        self.stat_lbls['fees'].config(text=f"{s.total_payment_fees:.1f}")
        self.stat_lbls['rounding'].config(text=f"{s.total_rounding_loss:.1f}")
        self.stat_lbls['weight'].config(text=f"{s.total_weight_printed:.0f}g")
        self.stat_lbls['waste'].config(text=f"{s.total_filament_waste:.0f}g")
        self.stat_lbls['custs'].config(text=str(s.total_customers))
        self.stat_lbls['margin'].config(text=f"{s.profit_margin:.1f}%")
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
        layer_c = ttk.Combobox(main, values=["0.1", "0.15", "0.2", "0.25", "0.3"], width=8)
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
                item.name = n
                item.estimated_weight_grams = w
                item.estimated_time_minutes = int(hours_e.get() or 0) * 60 + int(mins_e.get() or 0)
                item.color = color_c.get()
                item.quantity = int(qty_e.get() or 1)
                item.rate_per_gram = float(rate_e.get() or 4.0)
                item.spool_id = spool_data['ids'][spool_c.current()] if spool_data['ids'] and spool_c.current() >= 0 else ""
                item.settings = PrintSettings(nozzle_size=float(nozzle_c.get() or 0.4), layer_height=float(layer_c.get() or 0.2),
                                              infill_density=20, support_type=support_c.get())
                if not is_edit:
                    if item.spool_id:
                        if not self.db.reserve_filament(item.spool_id, item.total_weight):
                            messagebox.showwarning("Warning", "Not enough filament!")
                            return
                        item.filament_pending = True
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


def main():
    """Main entry point with login"""
    root = tk.Tk()
    root.withdraw()  # Hide main window during login
    
    # Show login dialog
    login_dialog = LoginDialog(root)
    
    if login_dialog.result and login_dialog.user:
        # Login successful - show main app
        root.deiconify()  # Show main window
        app = App(root, login_dialog.user)
        root.mainloop()
    else:
        # Login failed or cancelled
        root.destroy()


if __name__ == "__main__":
    main()
