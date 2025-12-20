"""
Abaad 3D Print Manager v3.0
With auto-discount, payment methods, multiple printers, and improved cost tracking
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime
from pathlib import Path
import sys
import os

sys.path.insert(0, str(Path(__file__).parent))

from core import (
    get_database, Order, PrintItem, FilamentSpool, Customer, Printer,
    PrintSettings, OrderStatus, PaymentMethod, SupportType, SpoolCategory,
    format_time, DEFAULT_RATE_PER_GRAM, DEFAULT_COST_PER_GRAM,
    calculate_payment_fee
)

# Import PDF generator
try:
    from pdf_generator import generate_receipt, REPORTLAB_AVAILABLE
except ImportError:
    REPORTLAB_AVAILABLE = False


class Colors:
    PRIMARY = "#2563eb"
    SUCCESS = "#22c55e"
    DANGER = "#ef4444"
    WARNING = "#f59e0b"
    BG = "#f8fafc"
    CARD = "#ffffff"
    TEXT = "#1e293b"
    TEXT_LIGHT = "#64748b"


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Abaad 3D Print Manager v3.0")
        self.root.geometry("1400x850")
        self.root.configure(bg=Colors.BG)
        
        self.db = get_database()
        self.current_order = None
        self.selected_customer = None
        
        self._setup_styles()
        self._build_ui()
        self._load_all_data()
    
    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background=Colors.BG)
        style.configure("TLabel", background=Colors.BG)
        style.configure("TNotebook.Tab", padding=[15, 8], font=("Arial", 10))
        style.configure("Title.TLabel", font=("Arial", 14, "bold"))
    
    def _build_ui(self):
        header = tk.Frame(self.root, bg=Colors.PRIMARY, height=55)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text="Abaad 3D Print Manager v3.0", font=("Arial", 16, "bold"),
                fg="white", bg=Colors.PRIMARY).pack(side=tk.LEFT, padx=15, pady=10)
        
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self._build_orders_tab()
        self._build_customers_tab()
        self._build_filament_tab()
        self._build_printers_tab()
        self._build_stats_tab()
        self._build_settings_tab()

    def _build_orders_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Orders")
        
        left = ttk.Frame(tab)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        ttk.Label(left, text="All Orders", style="Title.TLabel").pack(anchor=tk.W)
        
        search_f = ttk.Frame(left)
        search_f.pack(fill=tk.X, pady=5)
        self.order_search = ttk.Entry(search_f, width=25)
        self.order_search.pack(side=tk.LEFT, padx=5)
        self.order_search.bind('<KeyRelease>', lambda e: self._filter_orders())
        
        self.status_filter = ttk.Combobox(search_f, values=["All"] + [s.value for s in OrderStatus], 
                                          state="readonly", width=12)
        self.status_filter.set("All")
        self.status_filter.pack(side=tk.LEFT, padx=5)
        self.status_filter.bind('<<ComboboxSelected>>', lambda e: self._filter_orders())
        
        ttk.Button(search_f, text="+ New Order", command=self._new_order).pack(side=tk.RIGHT)
        
        cols = ("Order#", "Customer", "Items", "Total", "Status", "Date")
        self.orders_tree = ttk.Treeview(left, columns=cols, show="headings", height=25)
        for col, w in zip(cols, [60, 140, 50, 80, 90, 90]):
            self.orders_tree.heading(col, text=col)
            self.orders_tree.column(col, width=w)
        
        scroll = ttk.Scrollbar(left, command=self.orders_tree.yview)
        self.orders_tree.configure(yscrollcommand=scroll.set)
        self.orders_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.orders_tree.bind('<<TreeviewSelect>>', self._on_order_select)
        
        right = ttk.Frame(tab)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.order_title = ttk.Label(right, text="New Order", style="Title.TLabel")
        self.order_title.pack(anchor=tk.W)
        
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
        ttk.Button(row1, text="Find", command=self._find_customer).pack(side=tk.LEFT, padx=5)
        
        row2 = ttk.Frame(cust_f)
        row2.pack(fill=tk.X, pady=(5, 0))
        ttk.Label(row2, text="Status:").pack(side=tk.LEFT)
        self.order_status = ttk.Combobox(row2, values=[s.value for s in OrderStatus], 
                                         state="readonly", width=12)
        self.order_status.set("Draft")
        self.order_status.pack(side=tk.LEFT, padx=5)
        
        items_f = ttk.LabelFrame(right, text="Print Items", padding=8)
        items_f.pack(fill=tk.BOTH, expand=True, pady=5)
        
        items_tb = ttk.Frame(items_f)
        items_tb.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(items_tb, text="+ Add Item", command=self._add_item).pack(side=tk.LEFT, padx=2)
        ttk.Button(items_tb, text="Edit", command=self._edit_item).pack(side=tk.LEFT, padx=2)
        ttk.Button(items_tb, text="Remove", command=self._remove_item).pack(side=tk.LEFT, padx=2)
        
        cols = ("Name", "Color", "Weight", "Time", "Settings", "Qty", "Rate", "Total")
        self.items_tree = ttk.Treeview(items_f, columns=cols, show="headings", height=8)
        for col, w in zip(cols, [120, 70, 55, 50, 90, 35, 45, 70]):
            self.items_tree.heading(col, text=col)
            self.items_tree.column(col, width=w)
        self.items_tree.pack(fill=tk.BOTH, expand=True)
        
        totals_f = ttk.LabelFrame(right, text="Payment & Totals", padding=8)
        totals_f.pack(fill=tk.X, pady=5)
        
        row_t1 = ttk.Frame(totals_f)
        row_t1.pack(fill=tk.X)
        ttk.Label(row_t1, text="Base (4 EGP/g):").pack(side=tk.LEFT)
        self.base_total_lbl = ttk.Label(row_t1, text="0.00")
        self.base_total_lbl.pack(side=tk.LEFT, padx=5)
        ttk.Label(row_t1, text="Actual:").pack(side=tk.LEFT, padx=(15, 0))
        self.actual_total_lbl = ttk.Label(row_t1, text="0.00", font=("Arial", 10, "bold"), foreground=Colors.PRIMARY)
        self.actual_total_lbl.pack(side=tk.LEFT, padx=5)
        ttk.Label(row_t1, text="Rate Disc:").pack(side=tk.LEFT, padx=(15, 0))
        self.discount_lbl = ttk.Label(row_t1, text="0%", foreground=Colors.SUCCESS)
        self.discount_lbl.pack(side=tk.LEFT, padx=5)
        
        # NEW: Manual order discount row
        row_t1b = ttk.Frame(totals_f)
        row_t1b.pack(fill=tk.X, pady=(3, 0))
        ttk.Label(row_t1b, text="Order Discount %:").pack(side=tk.LEFT)
        self.order_discount_entry = ttk.Entry(row_t1b, width=6)
        self.order_discount_entry.insert(0, "0")
        self.order_discount_entry.pack(side=tk.LEFT, padx=5)
        self.order_discount_entry.bind('<KeyRelease>', lambda e: self._calc_totals())
        self.order_discount_amt_lbl = ttk.Label(row_t1b, text="(-0.00)", foreground=Colors.SUCCESS)
        self.order_discount_amt_lbl.pack(side=tk.LEFT, padx=5)
        ttk.Label(row_t1b, text="(Manual discount on top of rate discount)", 
                 foreground=Colors.TEXT_LIGHT, font=("Arial", 8)).pack(side=tk.LEFT, padx=10)
        
        row_t2 = ttk.Frame(totals_f)
        row_t2.pack(fill=tk.X, pady=(5, 0))
        ttk.Label(row_t2, text="Payment:").pack(side=tk.LEFT)
        self.payment_method = ttk.Combobox(row_t2, values=[p.value for p in PaymentMethod], 
                                            state="readonly", width=14)
        self.payment_method.set(PaymentMethod.CASH.value)
        self.payment_method.pack(side=tk.LEFT, padx=5)
        self.payment_method.bind('<<ComboboxSelected>>', lambda e: self._calc_totals())
        
        ttk.Label(row_t2, text="Fee:").pack(side=tk.LEFT, padx=(10, 0))
        self.payment_fee_lbl = ttk.Label(row_t2, text="0.00")
        self.payment_fee_lbl.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(row_t2, text="Shipping:").pack(side=tk.LEFT, padx=(10, 0))
        self.shipping_entry = ttk.Entry(row_t2, width=8)
        self.shipping_entry.insert(0, "0")
        self.shipping_entry.pack(side=tk.LEFT, padx=5)
        self.shipping_entry.bind('<KeyRelease>', lambda e: self._calc_totals())
        
        row_t3 = ttk.Frame(totals_f)
        row_t3.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(row_t3, text="TOTAL:", font=("Arial", 12, "bold")).pack(side=tk.LEFT)
        self.total_lbl = ttk.Label(row_t3, text="0.00 EGP", font=("Arial", 14, "bold"), foreground=Colors.PRIMARY)
        self.total_lbl.pack(side=tk.LEFT, padx=10)
        ttk.Label(row_t3, text="Profit:").pack(side=tk.LEFT, padx=(20, 0))
        self.profit_lbl = ttk.Label(row_t3, text="0.00", foreground=Colors.SUCCESS)
        self.profit_lbl.pack(side=tk.LEFT, padx=5)
        
        actions = ttk.Frame(right)
        actions.pack(fill=tk.X, pady=5)
        ttk.Button(actions, text="Save Order", command=self._save_order).pack(side=tk.LEFT, padx=3)
        ttk.Button(actions, text="PDF Receipt", command=self._gen_pdf_receipt).pack(side=tk.LEFT, padx=3)
        ttk.Button(actions, text="Text Receipt", command=self._gen_receipt).pack(side=tk.LEFT, padx=3)
        ttk.Button(actions, text="Delete", command=self._delete_order).pack(side=tk.LEFT, padx=3)
        ttk.Button(actions, text="New", command=self._new_order).pack(side=tk.LEFT, padx=3)
        
        ttk.Label(right, text="Notes:").pack(anchor=tk.W, pady=(5, 0))
        self.order_notes = tk.Text(right, height=2, font=("Arial", 9))
        self.order_notes.pack(fill=tk.X)

    def _build_customers_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Customers")
        
        left = ttk.Frame(tab)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        header = ttk.Frame(left)
        header.pack(fill=tk.X)
        ttk.Label(header, text="Customer Archive", style="Title.TLabel").pack(side=tk.LEFT)
        ttk.Button(header, text="+ Add", command=self._add_customer).pack(side=tk.RIGHT)
        
        self.cust_search = ttk.Entry(left, width=30)
        self.cust_search.pack(fill=tk.X, pady=5)
        self.cust_search.bind('<KeyRelease>', lambda e: self._filter_customers())
        
        cols = ("Name", "Phone", "Discount", "Orders", "Spent")
        self.custs_tree = ttk.Treeview(left, columns=cols, show="headings", height=20)
        for col, w in zip(cols, [140, 100, 60, 50, 80]):
            self.custs_tree.heading(col, text=col)
            self.custs_tree.column(col, width=w)
        self.custs_tree.pack(fill=tk.BOTH, expand=True)
        self.custs_tree.bind('<<TreeviewSelect>>', self._on_cust_select)
        
        right = ttk.Frame(tab)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        ttk.Label(right, text="Customer Details", style="Title.TLabel").pack(anchor=tk.W)
        
        form = ttk.LabelFrame(right, text="Info", padding=10)
        form.pack(fill=tk.X, pady=5)
        
        for i, (lbl, attr) in enumerate([("Name:", "cd_name"), ("Phone:", "cd_phone"), 
                                         ("Email:", "cd_email"), ("Discount %:", "cd_discount")]):
            ttk.Label(form, text=lbl).grid(row=i, column=0, sticky=tk.W, pady=2)
            e = ttk.Entry(form, width=35)
            e.grid(row=i, column=1, sticky=tk.EW, pady=2, padx=5)
            setattr(self, attr, e)
        
        self.cust_stats = ttk.Label(right, text="")
        self.cust_stats.pack(anchor=tk.W, pady=5)
        
        btn_f = ttk.Frame(right)
        btn_f.pack(fill=tk.X, pady=5)
        ttk.Button(btn_f, text="Save", command=self._save_customer).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_f, text="New Order", command=self._order_for_cust).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_f, text="Delete", command=self._del_customer).pack(side=tk.LEFT, padx=3)

    def _build_filament_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Filament")
        
        header = ttk.Frame(tab)
        header.pack(fill=tk.X)
        ttk.Label(header, text="Filament Inventory", style="Title.TLabel").pack(side=tk.LEFT)
        ttk.Button(header, text="+ New Spool (840 EGP)", command=self._add_new_spool).pack(side=tk.RIGHT, padx=5)
        ttk.Button(header, text="+ Remaining (FREE)", command=self._add_remaining_spool).pack(side=tk.RIGHT, padx=5)
        
        self.spool_summary = ttk.Label(tab, text="")
        self.spool_summary.pack(anchor=tk.W, pady=5)
        
        cols = ("Name", "Color", "Type", "Initial", "Current", "Used", "Cost/g", "Status")
        self.spools_tree = ttk.Treeview(tab, columns=cols, show="headings", height=20)
        for col, w in zip(cols, [150, 80, 80, 70, 80, 70, 60, 70]):
            self.spools_tree.heading(col, text=col)
            self.spools_tree.column(col, width=w)
        self.spools_tree.pack(fill=tk.BOTH, expand=True)
        
        btn_f = ttk.Frame(tab)
        btn_f.pack(fill=tk.X, pady=5)
        ttk.Button(btn_f, text="Edit", command=self._edit_spool).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_f, text="Delete", command=self._del_spool).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_f, text="Finish & Delete (< 20g)", command=self._finish_spool).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_f, text="Refresh", command=self._load_spools).pack(side=tk.LEFT, padx=3)

    def _build_printers_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Printers")
        
        header = ttk.Frame(tab)
        header.pack(fill=tk.X)
        ttk.Label(header, text="Printer Management", style="Title.TLabel").pack(side=tk.LEFT)
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
        ttk.Button(btn_f, text="Edit", command=self._edit_printer).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_f, text="Reset Nozzle", command=self._reset_nozzle).pack(side=tk.LEFT, padx=3)

    def _build_stats_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Statistics")
        
        ttk.Label(tab, text="Business Dashboard", style="Title.TLabel").pack(anchor=tk.W, pady=(0, 15))
        
        self.stat_lbls = {}
        cards = ttk.Frame(tab)
        cards.pack(fill=tk.X)
        
        stats = [
            ("Orders", "orders"), ("Completed", "completed"),
            ("Revenue", "revenue"), ("Profit", "profit"),
            ("Material Cost", "material"), ("Electricity", "electricity"),
            ("Nozzle Cost", "nozzle"), ("Shipping", "shipping"),
            ("Payment Fees", "fees"), ("Weight", "weight"),
            ("Customers", "custs"), ("Margin", "margin"),
        ]
        
        for i, (label, key) in enumerate(stats):
            row = i // 4
            col = i % 4
            frame = tk.Frame(cards, bg=Colors.CARD, relief=tk.RIDGE, bd=1)
            frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            tk.Label(frame, text=label, bg=Colors.CARD, fg=Colors.TEXT_LIGHT).pack(pady=(8, 0))
            lbl = tk.Label(frame, text="0", bg=Colors.CARD, fg=Colors.PRIMARY, font=("Arial", 16, "bold"))
            lbl.pack(pady=(0, 8))
            self.stat_lbls[key] = lbl
        
        for i in range(4):
            cards.columnconfigure(i, weight=1)
        
        ttk.Button(tab, text="Refresh", command=self._load_stats).pack(pady=20)

    def _build_settings_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Settings")
        
        ttk.Label(tab, text="Settings", style="Title.TLabel").pack(anchor=tk.W, pady=(0, 15))
        
        form = ttk.LabelFrame(tab, text="Company", padding=10)
        form.pack(fill=tk.X, pady=5)
        
        settings = self.db.get_settings()
        
        ttk.Label(form, text="Company Name:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.set_company = ttk.Entry(form, width=35)
        self.set_company.insert(0, settings.get('company_name', 'Abaad'))
        self.set_company.grid(row=0, column=1, sticky=tk.W, pady=5, padx=10)
        
        ttk.Label(form, text="Phone:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.set_phone = ttk.Entry(form, width=35)
        self.set_phone.insert(0, settings.get('company_phone', ''))
        self.set_phone.grid(row=1, column=1, sticky=tk.W, pady=5, padx=10)
        
        ttk.Label(form, text="Default Rate (EGP/g):").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.set_rate = ttk.Entry(form, width=15)
        self.set_rate.insert(0, str(settings.get('default_rate_per_gram', 4.0)))
        self.set_rate.grid(row=2, column=1, sticky=tk.W, pady=5, padx=10)
        
        ttk.Button(form, text="Save", command=self._save_settings).grid(row=3, column=1, sticky=tk.W, pady=10)
        
        fee_f = ttk.LabelFrame(tab, text="Payment Fees (Auto-calculated)", padding=10)
        fee_f.pack(fill=tk.X, pady=10)
        ttk.Label(fee_f, text="Cash: FREE").pack(anchor=tk.W)
        ttk.Label(fee_f, text="Vodafone Cash: 0.5% (Min 1 EGP, Max 15 EGP)").pack(anchor=tk.W)
        ttk.Label(fee_f, text="InstaPay: 0.1% (Min 0.50 EGP, Max 20 EGP)").pack(anchor=tk.W)
        
        data_f = ttk.LabelFrame(tab, text="Data", padding=10)
        data_f.pack(fill=tk.X, pady=10)
        ttk.Button(data_f, text="Backup", command=self._backup).pack(side=tk.LEFT, padx=5)

    def _load_all_data(self):
        self._load_orders()
        self._load_customers()
        self._load_spools()
        self._load_printers()
        self._load_stats()
        self._new_order()

    def _load_orders(self):
        for i in self.orders_tree.get_children():
            self.orders_tree.delete(i)
        for o in self.db.get_all_orders():
            self.orders_tree.insert("", tk.END, iid=o.id, values=(
                o.order_number, o.customer_name or "Walk-in", o.item_count,
                f"{o.total:.2f}", o.status, o.created_date.split()[0] if o.created_date else ""
            ))

    def _filter_orders(self):
        q = self.order_search.get().lower()
        status = self.status_filter.get()
        for i in self.orders_tree.get_children():
            self.orders_tree.delete(i)
        for o in self.db.get_all_orders():
            if status != "All" and o.status != status:
                continue
            if q and q not in o.customer_name.lower() and q not in o.customer_phone and q not in str(o.order_number):
                continue
            self.orders_tree.insert("", tk.END, iid=o.id, values=(
                o.order_number, o.customer_name or "Walk-in", o.item_count,
                f"{o.total:.2f}", o.status, o.created_date.split()[0] if o.created_date else ""
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
        total_r = sum(s.current_weight_grams for s in spools)
        total_u = sum(s.used_weight_grams for s in spools)
        active = len([s for s in spools if s.current_weight_grams > 50])
        
        for s in spools:
            status = "Empty" if s.current_weight_grams <= 0 else "Low" if s.remaining_percent < 15 else "Active"
            category = "Remaining" if s.category == SpoolCategory.REMAINING.value else "Standard"
            cost_per_g = f"{s.cost_per_gram:.2f}" if s.cost_per_gram > 0 else "FREE"
            self.spools_tree.insert("", tk.END, iid=s.id, values=(
                s.display_name, s.color, category,
                f"{s.initial_weight_grams:.0f}g",
                f"{s.current_weight_grams:.0f}g ({s.remaining_percent:.0f}%)",
                f"{s.used_weight_grams:.0f}g", cost_per_g, status
            ))
        
        self.spool_summary.config(text=f"{len(spools)} spools | {active} active | {total_r:.0f}g remaining | {total_u:.0f}g used")

    def _load_printers(self):
        for i in self.printers_tree.get_children():
            self.printers_tree.delete(i)
        for p in self.db.get_all_printers():
            status = "Active" if p.is_active else "Inactive"
            self.printers_tree.insert("", tk.END, iid=p.id, values=(
                p.name, p.model, f"{p.total_printed_grams:.0f}g",
                format_time(p.total_print_time_minutes),
                p.nozzle_changes, f"{p.total_electricity_cost:.2f}", status
            ))

    def _load_stats(self):
        s = self.db.get_statistics()
        self.stat_lbls['orders'].config(text=str(s.total_orders))
        self.stat_lbls['completed'].config(text=str(s.completed_orders))
        self.stat_lbls['revenue'].config(text=f"{s.total_revenue:.0f}")
        self.stat_lbls['profit'].config(text=f"{s.total_profit:.0f}")
        self.stat_lbls['material'].config(text=f"{s.total_material_cost:.0f}")
        self.stat_lbls['electricity'].config(text=f"{s.total_electricity_cost:.1f}")
        self.stat_lbls['nozzle'].config(text=f"{s.total_nozzle_cost:.0f}")
        self.stat_lbls['shipping'].config(text=f"{s.total_shipping:.0f}")
        self.stat_lbls['fees'].config(text=f"{s.total_payment_fees:.1f}")
        self.stat_lbls['weight'].config(text=f"{s.total_weight_printed:.0f}g")
        self.stat_lbls['custs'].config(text=str(s.total_customers))
        self.stat_lbls['margin'].config(text=f"{s.profit_margin:.1f}%")

    def _new_order(self):
        self.current_order = Order()
        self._clear_order_form()
        self.order_title.config(text="New Order")

    def _clear_order_form(self):
        self.cust_name.delete(0, tk.END)
        self.cust_phone.delete(0, tk.END)
        self.order_status.set("Draft")
        self.payment_method.set(PaymentMethod.CASH.value)
        self.shipping_entry.delete(0, tk.END)
        self.shipping_entry.insert(0, "0")
        self.order_discount_entry.delete(0, tk.END)
        self.order_discount_entry.insert(0, "0")
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
        self.order_title.config(text=f"Order #{o.order_number}")
        self.cust_name.insert(0, o.customer_name)
        self.cust_phone.insert(0, o.customer_phone)
        self.order_status.set(o.status)
        self.payment_method.set(o.payment_method)
        self.shipping_entry.delete(0, tk.END)
        self.shipping_entry.insert(0, str(o.shipping_cost))
        self.order_discount_entry.delete(0, tk.END)
        self.order_discount_entry.insert(0, str(o.order_discount_percent))
        if o.notes:
            self.order_notes.insert("1.0", o.notes)
        
        for item in o.items:
            self.items_tree.insert("", tk.END, iid=item.id, values=(
                item.name, item.color, f"{item.weight:.0f}g", item.time_formatted,
                str(item.settings), item.quantity, f"{item.rate_per_gram:.2f}", f"{item.print_cost:.2f}"
            ))
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
            self.current_order.remove_item(sel[0])
            self.items_tree.delete(sel[0])
            self._calc_totals()

    def _calc_totals(self):
        if not self.current_order:
            return
        try:
            self.current_order.shipping_cost = float(self.shipping_entry.get() or 0)
            self.current_order.payment_method = self.payment_method.get()
            self.current_order.order_discount_percent = float(self.order_discount_entry.get() or 0)
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
        
        self.current_order.status = self.order_status.get()
        self.current_order.payment_method = self.payment_method.get()
        self.current_order.notes = self.order_notes.get("1.0", tk.END).strip()
        self._calc_totals()
        
        if self.current_order.status == OrderStatus.DELIVERED.value:
            printer = self.db.get_default_printer()
            if printer:
                for item in self.current_order.items:
                    if not item.is_printed:
                        self.db.add_print_to_printer(printer.id, item.total_weight, item.time_minutes * item.quantity)
                        item.is_printed = True
        
        if self.db.save_order(self.current_order):
            messagebox.showinfo("Success", f"Order #{self.current_order.order_number} saved!")
            self._load_all_data()
            self._load_order_to_form(self.current_order)
        else:
            messagebox.showerror("Error", "Failed to save")

    def _delete_order(self):
        if not self.current_order or not self.current_order.id:
            return
        if messagebox.askyesno("Confirm", f"Delete Order #{self.current_order.order_number}?"):
            self.db.delete_order(self.current_order.id)
            self._load_all_data()
            self._new_order()

    def _gen_receipt(self):
        if not self.current_order or not self.current_order.items:
            messagebox.showwarning("Error", "Add items first")
            return
        
        o = self.current_order
        settings = self.db.get_settings()
        
        lines = []
        lines.append("=" * 50)
        lines.append(settings.get('company_name', 'Abaad'))
        lines.append(settings.get('company_phone', ''))
        lines.append(settings.get('company_address', ''))
        lines.append("=" * 50)
        lines.append("")
        lines.append(f"Order #{o.order_number}")
        lines.append(f"Date: {o.created_date}")
        lines.append(f"Customer: {o.customer_name or 'Walk-in'}")
        lines.append(f"Phone: {o.customer_phone or '-'}")
        lines.append("")
        lines.append("-" * 50)
        lines.append("ITEMS:")
        
        for item in o.items:
            lines.append("")
            lines.append(item.name)
            lines.append(f"  {item.color} | {item.weight:.0f}g x {item.quantity}")
            lines.append(f"  Settings: {item.settings}")
            lines.append(f"  Rate: {item.rate_per_gram:.2f} EGP/g")
            lines.append(f"  Total: {item.print_cost:.2f} EGP")
        
        lines.append("")
        lines.append("-" * 50)
        lines.append(f"Base Total (4 EGP/g): {o.subtotal:.2f} EGP")
        lines.append(f"Rate Discount: -{o.discount_amount:.2f} EGP ({o.discount_percent:.1f}%)")
        lines.append(f"Subtotal: {o.actual_total:.2f} EGP")
        if o.order_discount_percent > 0:
            lines.append(f"Order Discount: -{o.order_discount_amount:.2f} EGP ({o.order_discount_percent:.1f}%)")
        lines.append(f"Shipping: {o.shipping_cost:.2f} EGP")
        lines.append(f"Payment Method: {o.payment_method}")
        lines.append(f"Payment Fee: {o.payment_fee:.2f} EGP")
        lines.append("-" * 50)
        lines.append(f"TOTAL: {o.total:.2f} EGP")
        lines.append("=" * 50)
        lines.append("")
        lines.append("Thank you for your business!")
        
        receipt = "\n".join(lines)
        
        dlg = tk.Toplevel(self.root)
        dlg.title(f"Receipt - Order #{o.order_number}")
        dlg.geometry("500x600")
        
        text = tk.Text(dlg, font=("Courier", 10))
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text.insert("1.0", receipt)
        text.config(state=tk.DISABLED)
        
        ttk.Button(dlg, text="Close", command=dlg.destroy).pack(pady=10)

    def _gen_pdf_receipt(self):
        """Generate professional PDF receipt"""
        if not self.current_order or not self.current_order.items:
            messagebox.showwarning("Error", "Add items first")
            return
        
        if not REPORTLAB_AVAILABLE:
            messagebox.showerror("Error", "PDF generation requires reportlab.\n\nInstall with:\npip install reportlab")
            return
        
        try:
            # Create exports directory
            exports_dir = Path(__file__).parent / "exports"
            exports_dir.mkdir(exist_ok=True)
            
            # Generate PDF
            pdf_path = generate_receipt(self.current_order, output_dir=exports_dir)
            
            if messagebox.askyesno("Success", f"PDF Receipt saved!\n\n{pdf_path}\n\nOpen the file?"):
                os.startfile(pdf_path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate PDF:\n{str(e)}")

    def _show_item_dialog(self, item=None):
        dlg = tk.Toplevel(self.root)
        dlg.title("Add/Edit Item")
        dlg.geometry("550x500")
        dlg.transient(self.root)
        dlg.grab_set()
        
        is_edit = item is not None
        if not item:
            item = PrintItem()
        
        main = ttk.Frame(dlg, padding=15)
        main.pack(fill=tk.BOTH, expand=True)
        
        spool_data = {'ids': [], 'spools': []}
        
        row = 0
        ttk.Label(main, text="Name:*").grid(row=row, column=0, sticky=tk.W, pady=3)
        name_e = ttk.Entry(main, width=35)
        name_e.insert(0, item.name)
        name_e.grid(row=row, column=1, columnspan=2, pady=3, padx=5)
        
        row += 1
        ttk.Label(main, text="Weight (g):*").grid(row=row, column=0, sticky=tk.W, pady=3)
        weight_e = ttk.Entry(main, width=12)
        weight_e.insert(0, str(item.estimated_weight_grams) if item.estimated_weight_grams else "")
        weight_e.grid(row=row, column=1, sticky=tk.W, pady=3, padx=5)
        
        row += 1
        ttk.Label(main, text="Time:").grid(row=row, column=0, sticky=tk.W, pady=3)
        time_f = ttk.Frame(main)
        time_f.grid(row=row, column=1, sticky=tk.W, pady=3, padx=5)
        hours_e = ttk.Entry(time_f, width=5)
        hours_e.insert(0, str(item.estimated_time_minutes // 60))
        hours_e.pack(side=tk.LEFT)
        ttk.Label(time_f, text="h").pack(side=tk.LEFT, padx=(2, 8))
        mins_e = ttk.Entry(time_f, width=5)
        mins_e.insert(0, str(item.estimated_time_minutes % 60))
        mins_e.pack(side=tk.LEFT)
        ttk.Label(time_f, text="m").pack(side=tk.LEFT, padx=2)
        
        row += 1
        ttk.Label(main, text="Color:").grid(row=row, column=0, sticky=tk.W, pady=3)
        colors = self.db.get_colors()
        color_c = ttk.Combobox(main, values=colors, width=15, state="readonly")
        color_c.set(item.color if item.color in colors else (colors[0] if colors else "Black"))
        color_c.grid(row=row, column=1, sticky=tk.W, pady=3, padx=5)
        
        row += 1
        ttk.Label(main, text="Spool:").grid(row=row, column=0, sticky=tk.W, pady=3)
        spool_c = ttk.Combobox(main, width=35, state="readonly")
        spool_c.grid(row=row, column=1, columnspan=2, sticky=tk.W, pady=3, padx=5)
        
        def update_spools_for_color(*args):
            selected_color = color_c.get()
            matching = self.db.get_spools_by_color(selected_color)
            spool_data['spools'] = matching
            spool_data['ids'] = [s.id for s in matching]
            
            if matching:
                names = [f"{s.display_name} ({s.current_weight_grams:.0f}g)" for s in matching]
                spool_c['values'] = names
                best = max(range(len(matching)), key=lambda i: matching[i].current_weight_grams)
                spool_c.current(best)
            else:
                spool_c['values'] = [f"No {selected_color} spools available"]
                spool_c.current(0)
        
        color_c.bind('<<ComboboxSelected>>', update_spools_for_color)
        update_spools_for_color()
        
        row += 1
        ttk.Label(main, text="Settings:").grid(row=row, column=0, sticky=tk.W, pady=3)
        settings_f = ttk.Frame(main)
        settings_f.grid(row=row, column=1, columnspan=2, sticky=tk.W, pady=3, padx=5)
        
        ttk.Label(settings_f, text="Nozzle:").pack(side=tk.LEFT)
        nozzle_c = ttk.Combobox(settings_f, values=["0.2", "0.4", "0.6", "0.8"], width=5, state="readonly")
        nozzle_c.set(str(item.settings.nozzle_size))
        nozzle_c.pack(side=tk.LEFT, padx=(2, 10))
        
        ttk.Label(settings_f, text="Layer:").pack(side=tk.LEFT)
        layer_c = ttk.Combobox(settings_f, values=["0.12", "0.16", "0.2", "0.28", "0.32"], width=5, state="readonly")
        layer_c.set(str(item.settings.layer_height))
        layer_c.pack(side=tk.LEFT, padx=(2, 10))
        
        ttk.Label(settings_f, text="Support:").pack(side=tk.LEFT)
        support_c = ttk.Combobox(settings_f, values=["None", "Normal", "Tree"], width=8, state="readonly")
        support_c.set(item.settings.support_type)
        support_c.pack(side=tk.LEFT, padx=2)
        
        row += 1
        ttk.Label(main, text="Infill %:").grid(row=row, column=0, sticky=tk.W, pady=3)
        infill_e = ttk.Entry(main, width=8)
        infill_e.insert(0, str(item.settings.infill_density))
        infill_e.grid(row=row, column=1, sticky=tk.W, pady=3, padx=5)
        
        row += 1
        ttk.Label(main, text="Quantity:").grid(row=row, column=0, sticky=tk.W, pady=3)
        qty_e = ttk.Entry(main, width=8)
        qty_e.insert(0, str(item.quantity))
        qty_e.grid(row=row, column=1, sticky=tk.W, pady=3, padx=5)
        
        row += 1
        ttk.Label(main, text="Rate (EGP/g):").grid(row=row, column=0, sticky=tk.W, pady=3)
        rate_f = ttk.Frame(main)
        rate_f.grid(row=row, column=1, columnspan=2, sticky=tk.W, pady=3, padx=5)
        rate_e = ttk.Entry(rate_f, width=8)
        rate_e.insert(0, str(item.rate_per_gram))
        rate_e.pack(side=tk.LEFT)
        discount_lbl = ttk.Label(rate_f, text="", foreground=Colors.SUCCESS)
        discount_lbl.pack(side=tk.LEFT, padx=10)
        
        def update_discount(*args):
            try:
                rate = float(rate_e.get() or 4.0)
                if rate < DEFAULT_RATE_PER_GRAM:
                    disc = ((DEFAULT_RATE_PER_GRAM - rate) / DEFAULT_RATE_PER_GRAM) * 100
                    discount_lbl.config(text=f"({disc:.0f}% discount)", foreground=Colors.SUCCESS)
                elif rate > DEFAULT_RATE_PER_GRAM:
                    prem = ((rate - DEFAULT_RATE_PER_GRAM) / DEFAULT_RATE_PER_GRAM) * 100
                    discount_lbl.config(text=f"(+{prem:.0f}% premium)", foreground=Colors.WARNING)
                else:
                    discount_lbl.config(text="(standard rate)")
            except:
                discount_lbl.config(text="")
        
        rate_e.bind('<KeyRelease>', update_discount)
        update_discount()
        
        row += 1
        cost_frame = ttk.LabelFrame(main, text="Cost Preview", padding=5)
        cost_frame.grid(row=row, column=0, columnspan=3, sticky=tk.EW, pady=10, padx=5)
        cost_lbl = ttk.Label(cost_frame, text="0.00 EGP", font=("Arial", 12, "bold"))
        cost_lbl.pack()
        
        def update_cost(*args):
            try:
                w = float(weight_e.get() or 0)
                q = int(qty_e.get() or 1)
                r = float(rate_e.get() or 4.0)
                total = w * q * r
                cost_lbl.config(text=f"{total:.2f} EGP")
            except:
                cost_lbl.config(text="-- EGP")
        
        weight_e.bind('<KeyRelease>', update_cost)
        qty_e.bind('<KeyRelease>', update_cost)
        rate_e.bind('<KeyRelease>', update_cost)
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
                
                new_spool_id = ""
                if spool_data['ids'] and spool_c.current() >= 0 and spool_c.current() < len(spool_data['ids']):
                    new_spool_id = spool_data['ids'][spool_c.current()]
                
                item.spool_id = new_spool_id
                item.settings = PrintSettings(
                    nozzle_size=float(nozzle_c.get() or 0.4),
                    layer_height=float(layer_c.get() or 0.2),
                    infill_density=int(infill_e.get() or 20),
                    support_type=support_c.get()
                )
                
                new_weight = item.total_weight
                
                if not is_edit:
                    if new_spool_id:
                        if not self.db.use_filament(new_spool_id, new_weight):
                            messagebox.showwarning("Warning", "Not enough filament in spool!")
                        item.filament_deducted = True
                    
                    self.current_order.add_item(item)
                
                if is_edit:
                    self.items_tree.item(item.id, values=(
                        item.name, item.color, f"{item.weight:.0f}g", item.time_formatted,
                        str(item.settings), item.quantity, f"{item.rate_per_gram:.2f}", f"{item.print_cost:.2f}"
                    ))
                else:
                    self.items_tree.insert("", tk.END, iid=item.id, values=(
                        item.name, item.color, f"{item.weight:.0f}g", item.time_formatted,
                        str(item.settings), item.quantity, f"{item.rate_per_gram:.2f}", f"{item.print_cost:.2f}"
                    ))
                
                self._calc_totals()
                self._load_spools()
                dlg.destroy()
            except Exception as e:
                messagebox.showerror("Error", str(e))
        
        row += 1
        btn_f = ttk.Frame(main)
        btn_f.grid(row=row, column=0, columnspan=3, pady=10)
        ttk.Button(btn_f, text="Save", command=save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_f, text="Cancel", command=dlg.destroy).pack(side=tk.LEFT, padx=5)

    def _on_cust_select(self, event):
        sel = self.custs_tree.selection()
        if not sel:
            return
        c = self.db.get_customer(sel[0])
        if c:
            self.selected_customer = c
            for e, v in [(self.cd_name, c.name), (self.cd_phone, c.phone),
                         (self.cd_email, c.email), (self.cd_discount, str(c.discount_percent))]:
                e.delete(0, tk.END)
                e.insert(0, v)
            self.cust_stats.config(text=f"{c.total_orders} orders | {c.total_spent:.2f} EGP total")

    def _add_customer(self):
        self.selected_customer = Customer()
        for e in [self.cd_name, self.cd_phone, self.cd_email, self.cd_discount]:
            e.delete(0, tk.END)
        self.cust_stats.config(text="New Customer")

    def _save_customer(self):
        if not self.selected_customer:
            self.selected_customer = Customer()
        self.selected_customer.name = self.cd_name.get().strip()
        self.selected_customer.phone = self.cd_phone.get().strip()
        self.selected_customer.email = self.cd_email.get().strip()
        try:
            self.selected_customer.discount_percent = float(self.cd_discount.get() or 0)
        except:
            pass
        if self.db.save_customer(self.selected_customer):
            messagebox.showinfo("Success", "Customer saved!")
            self._load_customers()

    def _del_customer(self):
        if not self.selected_customer:
            return
        if messagebox.askyesno("Confirm", f"Delete {self.selected_customer.name}?"):
            self.db.delete_customer(self.selected_customer.id)
            self._load_customers()
            self._add_customer()

    def _order_for_cust(self):
        if not self.selected_customer:
            return
        self._new_order()
        self.cust_name.insert(0, self.selected_customer.name)
        self.cust_phone.insert(0, self.selected_customer.phone)
        self.current_order.customer_id = self.selected_customer.id
        self.notebook.select(0)

    def _add_new_spool(self):
        self._show_spool_dialog(is_remaining=False)

    def _add_remaining_spool(self):
        self._show_spool_dialog(is_remaining=True)

    def _edit_spool(self):
        sel = self.spools_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select a spool")
            return
        s = self.db.get_spool(sel[0])
        if s:
            is_remaining = s.category == SpoolCategory.REMAINING.value
            self._show_spool_dialog(spool=s, is_remaining=is_remaining)

    def _del_spool(self):
        sel = self.spools_tree.selection()
        if not sel:
            return
        if messagebox.askyesno("Confirm", "Delete spool?"):
            self.db.delete_spool(sel[0])
            self._load_spools()

    def _finish_spool(self):
        """Mark spool as finished and delete it - for nearly empty spools (< 20g)"""
        sel = self.spools_tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select a spool to finish")
            return
        
        s = self.db.get_spool(sel[0])
        if not s:
            return
        
        # Check if spool is nearly empty
        if s.current_weight_grams > 20:
            if not messagebox.askyesno("Warning", 
                f"This spool still has {s.current_weight_grams:.0f}g remaining.\n\n"
                "This feature is meant for nearly empty spools (< 20g) that have\n"
                "leftover filament that can't be used for printing.\n\n"
                "Are you sure you want to mark it as finished and delete it?"):
                return
        
        # Confirm deletion
        msg = f"Finish and delete spool?\n\n"
        msg += f"Name: {s.display_name}\n"
        msg += f"Remaining: {s.current_weight_grams:.0f}g\n"
        msg += f"Used: {s.used_weight_grams:.0f}g\n\n"
        msg += "This filament will be counted as waste/leftover."
        
        if messagebox.askyesno("Finish Spool", msg):
            self.db.delete_spool(sel[0])
            self._load_spools()
            messagebox.showinfo("Done", f"Spool '{s.display_name}' has been finished and removed.")

    def _show_spool_dialog(self, spool=None, is_remaining=False):
        dlg = tk.Toplevel(self.root)
        dlg.title("Add Remaining Filament" if is_remaining else "Add New Spool")
        dlg.geometry("400x300")
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
        
        title = "Remaining Filament (FREE)" if is_remaining else "New Spool (840 EGP)"
        ttk.Label(main, text=title, font=("Arial", 12, "bold")).pack(anchor=tk.W)
        
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
            brand_c = ttk.Combobox(form, values=["eSUN", "Sunlu", "Creality", "Other"], width=20)
            brand_c.set(spool.brand)
            brand_c.grid(row=1, column=1, sticky=tk.W, pady=3, padx=5)
        
        ttk.Label(form, text="Weight (g):").grid(row=2, column=0, sticky=tk.W, pady=3)
        weight_e = ttk.Entry(form, width=15)
        weight_e.insert(0, str(spool.current_weight_grams))
        weight_e.grid(row=2, column=1, sticky=tk.W, pady=3, padx=5)
        
        if is_remaining:
            ttk.Label(form, text="Cost: FREE (already paid)", foreground=Colors.SUCCESS).grid(
                row=3, column=0, columnspan=2, sticky=tk.W, pady=10)
        else:
            ttk.Label(form, text="Price: 840 EGP (fixed)", foreground=Colors.TEXT_LIGHT).grid(
                row=3, column=0, columnspan=2, sticky=tk.W, pady=3)
        
        def save():
            try:
                w = float(weight_e.get() or 0)
                if w <= 0:
                    messagebox.showwarning("Error", "Enter weight")
                    return
                
                spool.color = color_c.get()
                spool.current_weight_grams = w
                
                if is_remaining:
                    spool.category = SpoolCategory.REMAINING.value
                    spool.brand = "Mixed"
                    spool.initial_weight_grams = w
                    spool.purchase_price_egp = 0
                    spool.name = f"Remaining - {spool.color}"
                else:
                    spool.category = SpoolCategory.STANDARD.value
                    spool.brand = brand_c.get() if brand_c else "eSUN"
                    spool.initial_weight_grams = w
                    spool.purchase_price_egp = 840
                    spool.name = f"{spool.brand} {spool.filament_type} {spool.color}"
                
                if self.db.save_spool(spool):
                    if spool.color not in colors:
                        self.db.add_color(spool.color)
                    self._load_spools()
                    dlg.destroy()
            except Exception as e:
                messagebox.showerror("Error", str(e))
        
        btn_f = ttk.Frame(main)
        btn_f.pack(fill=tk.X, pady=10)
        ttk.Button(btn_f, text="Save", command=save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_f, text="Cancel", command=dlg.destroy).pack(side=tk.LEFT, padx=5)

    def _add_printer(self):
        name = simpledialog.askstring("Add Printer", "Enter printer name:")
        if name:
            p = Printer(name=name)
            self.db.save_printer(p)
            self._load_printers()

    def _on_printer_select(self, event):
        sel = self.printers_tree.selection()
        if not sel:
            return
        p = self.db.get_printer(sel[0])
        if p:
            detail = f"""Name: {p.name}
Model: {p.model}
Total Printed: {p.total_printed_grams:.0f}g ({p.total_printed_grams/1000:.2f}kg)
Total Time: {format_time(p.total_print_time_minutes)}
Nozzle Changes: {p.nozzle_changes}
Current Nozzle Usage: {p.current_nozzle_grams:.0f}g / {p.nozzle_lifetime_grams:.0f}g ({p.nozzle_usage_percent:.0f}%)
Depreciation: {p.total_depreciation:.2f} EGP
Electricity Cost: {p.total_electricity_cost:.2f} EGP
Nozzle Cost: {p.total_nozzle_cost:.2f} EGP"""
            self.printer_detail.config(text=detail)

    def _edit_printer(self):
        sel = self.printers_tree.selection()
        if not sel:
            return
        p = self.db.get_printer(sel[0])
        if p:
            name = simpledialog.askstring("Edit Printer", "Enter new name:", initialvalue=p.name)
            if name:
                p.name = name
                self.db.save_printer(p)
                self._load_printers()

    def _reset_nozzle(self):
        sel = self.printers_tree.selection()
        if not sel:
            return
        if messagebox.askyesno("Reset Nozzle", "Record nozzle change?"):
            p = self.db.get_printer(sel[0])
            if p:
                p.nozzle_changes += 1
                p.current_nozzle_grams = 0
                self.db.save_printer(p)
                self._load_printers()
                self._on_printer_select(None)

    def _save_settings(self):
        settings = {
            'company_name': self.set_company.get().strip(),
            'company_phone': self.set_phone.get().strip(),
            'default_rate_per_gram': float(self.set_rate.get() or 4.0),
        }
        if self.db.save_settings(settings):
            messagebox.showinfo("Success", "Settings saved!")

    def _backup(self):
        path = self.db.backup_database()
        messagebox.showinfo("Backup", f"Backup created:\n{path}")


def main():
    root = tk.Tk()
    app = App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
