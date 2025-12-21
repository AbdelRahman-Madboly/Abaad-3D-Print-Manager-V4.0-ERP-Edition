"""
Admin Panel for Abaad ERP v4.0
User management, inventory configuration, and system settings
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Optional, Callable
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.logic.auth import get_auth_manager, User, UserRole, Permission


class Colors:
    """Application color scheme"""
    PRIMARY = "#1e3a8a"
    PRIMARY_LIGHT = "#3b82f6"
    SUCCESS = "#22c55e"
    DANGER = "#ef4444"
    WARNING = "#f59e0b"
    INFO = "#06b6d4"
    PURPLE = "#7c3aed"
    BG = "#f8fafc"
    CARD = "#ffffff"
    TEXT = "#1e293b"
    TEXT_LIGHT = "#64748b"
    BORDER = "#e2e8f0"


class UserManagementFrame(ttk.Frame):
    """Frame for managing users - Admin only"""
    
    def __init__(self, parent, db_manager):
        super().__init__(parent, padding=10)
        self.db = db_manager
        self.auth = get_auth_manager()
        self.selected_user = None
        
        self._build_ui()
        self._load_users()
    
    def _build_ui(self):
        """Build the user management UI"""
        # Header
        header = ttk.Frame(self)
        header.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(
            header, 
            text="👥 User Management",
            font=("Segoe UI", 14, "bold")
        ).pack(side=tk.LEFT)
        
        ttk.Button(
            header,
            text="+ Add User",
            command=self._add_user
        ).pack(side=tk.RIGHT)
        
        # Main content - split into list and details
        content = ttk.Frame(self)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Users list (left side)
        list_frame = ttk.LabelFrame(content, text="Users", padding=10)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Treeview for users
        columns = ("Username", "Display Name", "Role", "Status", "Last Login")
        self.users_tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show="headings",
            height=15
        )
        
        for col, width in zip(columns, [100, 120, 80, 70, 120]):
            self.users_tree.heading(col, text=col)
            self.users_tree.column(col, width=width, minwidth=50)
        
        scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.users_tree.yview)
        self.users_tree.configure(yscrollcommand=scroll.set)
        
        self.users_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.users_tree.bind('<<TreeviewSelect>>', self._on_user_select)
        
        # User details (right side)
        details_frame = ttk.LabelFrame(content, text="User Details", padding=15)
        details_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 0), ipadx=10)
        
        # Form fields
        fields = [
            ("Username:", "username_entry"),
            ("Display Name:", "display_entry"),
            ("Email:", "email_entry"),
            ("Password:", "password_entry"),
        ]
        
        for i, (label, attr) in enumerate(fields):
            ttk.Label(details_frame, text=label).grid(row=i, column=0, sticky=tk.W, pady=5)
            entry = ttk.Entry(details_frame, width=25)
            entry.grid(row=i, column=1, sticky=tk.EW, pady=5, padx=5)
            if attr == "password_entry":
                entry.configure(show="●")
            setattr(self, attr, entry)
        
        # Role dropdown
        ttk.Label(details_frame, text="Role:").grid(row=len(fields), column=0, sticky=tk.W, pady=5)
        self.role_combo = ttk.Combobox(
            details_frame,
            values=[r.value for r in UserRole],
            state="readonly",
            width=22
        )
        self.role_combo.grid(row=len(fields), column=1, sticky=tk.EW, pady=5, padx=5)
        
        # Active checkbox
        self.active_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            details_frame,
            text="Account Active",
            variable=self.active_var
        ).grid(row=len(fields)+1, column=0, columnspan=2, sticky=tk.W, pady=10)
        
        # Notes
        ttk.Label(details_frame, text="Notes:").grid(row=len(fields)+2, column=0, sticky=tk.NW, pady=5)
        self.notes_text = tk.Text(details_frame, width=25, height=4, font=("Segoe UI", 9))
        self.notes_text.grid(row=len(fields)+2, column=1, sticky=tk.EW, pady=5, padx=5)
        
        # Action buttons
        btn_frame = ttk.Frame(details_frame)
        btn_frame.grid(row=len(fields)+3, column=0, columnspan=2, pady=15)
        
        ttk.Button(btn_frame, text="💾 Save", command=self._save_user).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="🗑️ Delete", command=self._delete_user).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="Clear", command=self._clear_form).pack(side=tk.LEFT, padx=3)
        
        # User info label
        self.info_label = ttk.Label(details_frame, text="", foreground=Colors.TEXT_LIGHT)
        self.info_label.grid(row=len(fields)+4, column=0, columnspan=2, pady=5)
    
    def _load_users(self):
        """Load users into the treeview"""
        for item in self.users_tree.get_children():
            self.users_tree.delete(item)
        
        for user in self.auth.get_all_users():
            status = "✅ Active" if user.is_active else "❌ Disabled"
            last_login = user.last_login.split()[0] if user.last_login else "Never"
            
            self.users_tree.insert("", tk.END, iid=user.id, values=(
                user.username,
                user.display_name or user.username,
                user.role,
                status,
                last_login
            ))
    
    def _on_user_select(self, event):
        """Handle user selection"""
        selection = self.users_tree.selection()
        if not selection:
            return
        
        user = self.auth.get_user(selection[0])
        if user:
            self.selected_user = user
            self._load_user_to_form(user)
    
    def _load_user_to_form(self, user: User):
        """Load user data into form"""
        self._clear_form()
        
        self.username_entry.insert(0, user.username)
        self.display_entry.insert(0, user.display_name)
        self.email_entry.insert(0, user.email)
        # Don't show password
        self.role_combo.set(user.role)
        self.active_var.set(user.is_active)
        self.notes_text.insert("1.0", user.notes)
        
        self.info_label.config(text=f"Login count: {user.login_count} | Created: {user.created_date.split()[0]}")
    
    def _clear_form(self):
        """Clear all form fields"""
        self.selected_user = None
        self.username_entry.delete(0, tk.END)
        self.display_entry.delete(0, tk.END)
        self.email_entry.delete(0, tk.END)
        self.password_entry.delete(0, tk.END)
        self.role_combo.set(UserRole.USER.value)
        self.active_var.set(True)
        self.notes_text.delete("1.0", tk.END)
        self.info_label.config(text="")
    
    def _add_user(self):
        """Add new user"""
        self._clear_form()
        self.username_entry.focus_set()
    
    def _save_user(self):
        """Save user (create or update)"""
        username = self.username_entry.get().strip()
        display_name = self.display_entry.get().strip()
        email = self.email_entry.get().strip()
        password = self.password_entry.get()
        role = self.role_combo.get()
        is_active = self.active_var.get()
        notes = self.notes_text.get("1.0", tk.END).strip()
        
        if not username:
            messagebox.showwarning("Validation", "Username is required")
            return
        
        if self.selected_user:
            # Update existing user
            kwargs = {
                'display_name': display_name,
                'email': email,
                'role': role,
                'is_active': is_active,
                'notes': notes,
            }
            if password:  # Only update password if provided
                kwargs['password'] = password
            
            success, message = self.auth.update_user(self.selected_user.id, **kwargs)
            if success:
                messagebox.showinfo("Success", message)
                self._load_users()
            else:
                messagebox.showerror("Error", message)
        else:
            # Create new user
            if not password:
                messagebox.showwarning("Validation", "Password is required for new users")
                return
            
            success, message, user = self.auth.create_user(
                username=username,
                password=password,
                role=role,
                display_name=display_name,
                email=email
            )
            
            if success:
                # Update notes separately if any
                if notes and user:
                    self.auth.update_user(user.id, notes=notes)
                
                messagebox.showinfo("Success", message)
                self._load_users()
                self._clear_form()
            else:
                messagebox.showerror("Error", message)
    
    def _delete_user(self):
        """Delete selected user"""
        if not self.selected_user:
            messagebox.showwarning("Select User", "Please select a user to delete")
            return
        
        if not messagebox.askyesno("Confirm Delete", 
                                   f"Delete user '{self.selected_user.username}'?\n\nThis cannot be undone."):
            return
        
        success, message = self.auth.delete_user(self.selected_user.id)
        if success:
            messagebox.showinfo("Success", message)
            self._load_users()
            self._clear_form()
        else:
            messagebox.showerror("Error", message)


class FilamentConfigFrame(ttk.Frame):
    """Frame for configuring filament brands, colors, and types - Admin only"""
    
    def __init__(self, parent, db_manager):
        super().__init__(parent, padding=10)
        self.db = db_manager
        
        self._build_ui()
        self._load_data()
    
    def _build_ui(self):
        """Build the filament configuration UI"""
        # Header
        ttk.Label(
            self,
            text="🎨 Filament Configuration",
            font=("Segoe UI", 14, "bold")
        ).pack(anchor=tk.W, pady=(0, 15))
        
        # Horizontal layout for lists
        lists_frame = ttk.Frame(self)
        lists_frame.pack(fill=tk.BOTH, expand=True)
        
        # Colors management
        colors_frame = ttk.LabelFrame(lists_frame, text="Available Colors", padding=10)
        colors_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        self.colors_listbox = tk.Listbox(
            colors_frame,
            font=("Segoe UI", 10),
            height=15,
            selectmode=tk.SINGLE
        )
        self.colors_listbox.pack(fill=tk.BOTH, expand=True)
        
        colors_btn = ttk.Frame(colors_frame)
        colors_btn.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(colors_btn, text="+ Add", command=self._add_color).pack(side=tk.LEFT, padx=2)
        ttk.Button(colors_btn, text="Remove", command=self._remove_color).pack(side=tk.LEFT, padx=2)
        
        # Brands management
        brands_frame = ttk.LabelFrame(lists_frame, text="Filament Brands", padding=10)
        brands_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        self.brands_listbox = tk.Listbox(
            brands_frame,
            font=("Segoe UI", 10),
            height=15,
            selectmode=tk.SINGLE
        )
        self.brands_listbox.pack(fill=tk.BOTH, expand=True)
        
        brands_btn = ttk.Frame(brands_frame)
        brands_btn.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(brands_btn, text="+ Add", command=self._add_brand).pack(side=tk.LEFT, padx=2)
        ttk.Button(brands_btn, text="Remove", command=self._remove_brand).pack(side=tk.LEFT, padx=2)
        
        # Types management
        types_frame = ttk.LabelFrame(lists_frame, text="Filament Types", padding=10)
        types_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.types_listbox = tk.Listbox(
            types_frame,
            font=("Segoe UI", 10),
            height=15,
            selectmode=tk.SINGLE
        )
        self.types_listbox.pack(fill=tk.BOTH, expand=True)
        
        types_btn = ttk.Frame(types_frame)
        types_btn.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(types_btn, text="+ Add", command=self._add_type).pack(side=tk.LEFT, padx=2)
        ttk.Button(types_btn, text="Remove", command=self._remove_type).pack(side=tk.LEFT, padx=2)
        
        # Pricing section
        pricing_frame = ttk.LabelFrame(self, text="Default Pricing", padding=15)
        pricing_frame.pack(fill=tk.X, pady=(15, 0))
        
        pricing_grid = ttk.Frame(pricing_frame)
        pricing_grid.pack(fill=tk.X)
        
        ttk.Label(pricing_grid, text="Standard Spool Price:").grid(row=0, column=0, sticky=tk.W, pady=3)
        self.spool_price_entry = ttk.Entry(pricing_grid, width=15)
        self.spool_price_entry.grid(row=0, column=1, pady=3, padx=5)
        ttk.Label(pricing_grid, text="EGP").grid(row=0, column=2, sticky=tk.W)
        
        ttk.Label(pricing_grid, text="Rate per Gram:").grid(row=1, column=0, sticky=tk.W, pady=3)
        self.rate_entry = ttk.Entry(pricing_grid, width=15)
        self.rate_entry.grid(row=1, column=1, pady=3, padx=5)
        ttk.Label(pricing_grid, text="EGP/g").grid(row=1, column=2, sticky=tk.W)
        
        ttk.Button(pricing_grid, text="💾 Save Pricing", command=self._save_pricing).grid(
            row=2, column=0, columnspan=3, pady=10
        )
    
    def _load_data(self):
        """Load configuration data"""
        # Colors
        self.colors_listbox.delete(0, tk.END)
        for color in self.db.get_colors():
            self.colors_listbox.insert(tk.END, color)
        
        # Brands - get from settings or defaults
        settings = self.db.get_settings()
        brands = settings.get('filament_brands', ["eSUN", "Sunlu", "Creality", "Polymaker", "Other"])
        self.brands_listbox.delete(0, tk.END)
        for brand in brands:
            self.brands_listbox.insert(tk.END, brand)
        
        # Types
        types = settings.get('filament_types', ["PLA+", "PLA", "PETG", "ABS", "TPU"])
        self.types_listbox.delete(0, tk.END)
        for t in types:
            self.types_listbox.insert(tk.END, t)
        
        # Pricing
        self.spool_price_entry.delete(0, tk.END)
        self.spool_price_entry.insert(0, str(settings.get('spool_price', 840)))
        
        self.rate_entry.delete(0, tk.END)
        self.rate_entry.insert(0, str(settings.get('default_rate_per_gram', 4.0)))
    
    def _add_color(self):
        color = simpledialog.askstring("Add Color", "Enter color name:")
        if color and color.strip():
            if self.db.add_color(color.strip()):
                self._load_data()
    
    def _remove_color(self):
        selection = self.colors_listbox.curselection()
        if selection:
            color = self.colors_listbox.get(selection[0])
            if messagebox.askyesno("Confirm", f"Remove color '{color}'?"):
                colors = self.db.get_colors()
                if color in colors:
                    colors.remove(color)
                    self.db.data['colors'] = colors
                    self.db._save()
                    self._load_data()
    
    def _add_brand(self):
        brand = simpledialog.askstring("Add Brand", "Enter brand name:")
        if brand and brand.strip():
            settings = self.db.get_settings()
            brands = settings.get('filament_brands', [])
            if brand.strip() not in brands:
                brands.append(brand.strip())
                self.db.save_settings({'filament_brands': brands})
                self._load_data()
    
    def _remove_brand(self):
        selection = self.brands_listbox.curselection()
        if selection:
            brand = self.brands_listbox.get(selection[0])
            if messagebox.askyesno("Confirm", f"Remove brand '{brand}'?"):
                settings = self.db.get_settings()
                brands = settings.get('filament_brands', [])
                if brand in brands:
                    brands.remove(brand)
                    self.db.save_settings({'filament_brands': brands})
                    self._load_data()
    
    def _add_type(self):
        ftype = simpledialog.askstring("Add Type", "Enter filament type:")
        if ftype and ftype.strip():
            settings = self.db.get_settings()
            types = settings.get('filament_types', [])
            if ftype.strip() not in types:
                types.append(ftype.strip())
                self.db.save_settings({'filament_types': types})
                self._load_data()
    
    def _remove_type(self):
        selection = self.types_listbox.curselection()
        if selection:
            ftype = self.types_listbox.get(selection[0])
            if messagebox.askyesno("Confirm", f"Remove type '{ftype}'?"):
                settings = self.db.get_settings()
                types = settings.get('filament_types', [])
                if ftype in types:
                    types.remove(ftype)
                    self.db.save_settings({'filament_types': types})
                    self._load_data()
    
    def _save_pricing(self):
        try:
            spool_price = float(self.spool_price_entry.get())
            rate = float(self.rate_entry.get())
            
            self.db.save_settings({
                'spool_price': spool_price,
                'default_rate_per_gram': rate
            })
            messagebox.showinfo("Success", "Pricing settings saved!")
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers")


class PrinterProfilesFrame(ttk.Frame):
    """Frame for managing printer profiles - Admin only"""
    
    def __init__(self, parent, db_manager):
        super().__init__(parent, padding=10)
        self.db = db_manager
        self.selected_printer = None
        
        self._build_ui()
        self._load_printers()
    
    def _build_ui(self):
        """Build printer profiles UI"""
        # Header
        header = ttk.Frame(self)
        header.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(
            header,
            text="🖨️ Printer Profiles",
            font=("Segoe UI", 14, "bold")
        ).pack(side=tk.LEFT)
        
        ttk.Button(header, text="+ Add Printer", command=self._add_printer).pack(side=tk.RIGHT)
        
        # Content
        content = ttk.Frame(self)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Printers list
        list_frame = ttk.LabelFrame(content, text="Printers", padding=10)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        columns = ("Name", "Model", "Nozzle", "Printed", "Status")
        self.printers_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=12)
        
        for col, width in zip(columns, [100, 120, 60, 80, 70]):
            self.printers_tree.heading(col, text=col)
            self.printers_tree.column(col, width=width, minwidth=50)
        
        self.printers_tree.pack(fill=tk.BOTH, expand=True)
        self.printers_tree.bind('<<TreeviewSelect>>', self._on_printer_select)
        
        # Details form
        details = ttk.LabelFrame(content, text="Printer Details", padding=15)
        details.pack(side=tk.LEFT, fill=tk.BOTH, ipadx=10)
        
        fields = [
            ("Name:", "name_entry"),
            ("Model:", "model_entry"),
            ("Purchase Price:", "price_entry"),
            ("Lifetime (kg):", "lifetime_entry"),
            ("Nozzle Size:", "nozzle_entry"),
            ("Nozzle Cost:", "nozzle_cost_entry"),
            ("Nozzle Lifetime (g):", "nozzle_life_entry"),
            ("Elec Rate (EGP/h):", "elec_entry"),
        ]
        
        for i, (label, attr) in enumerate(fields):
            ttk.Label(details, text=label).grid(row=i, column=0, sticky=tk.W, pady=3)
            entry = ttk.Entry(details, width=20)
            entry.grid(row=i, column=1, pady=3, padx=5)
            setattr(self, attr, entry)
        
        # Active checkbox
        self.active_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            details,
            text="Active",
            variable=self.active_var
        ).grid(row=len(fields), column=0, columnspan=2, sticky=tk.W, pady=10)
        
        # Buttons
        btn_frame = ttk.Frame(details)
        btn_frame.grid(row=len(fields)+1, column=0, columnspan=2, pady=10)
        
        ttk.Button(btn_frame, text="💾 Save", command=self._save_printer).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="🗑️ Delete", command=self._delete_printer).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="Reset Nozzle", command=self._reset_nozzle).pack(side=tk.LEFT, padx=3)
    
    def _load_printers(self):
        """Load printers into treeview"""
        for item in self.printers_tree.get_children():
            self.printers_tree.delete(item)
        
        for printer in self.db.get_all_printers():
            status = "✅ Active" if printer.is_active else "❌ Inactive"
            self.printers_tree.insert("", tk.END, iid=printer.id, values=(
                printer.name,
                printer.model,
                f"{printer.nozzle_cost:.1f}",
                f"{printer.total_printed_grams:.0f}g",
                status
            ))
    
    def _on_printer_select(self, event):
        selection = self.printers_tree.selection()
        if not selection:
            return
        
        printer = self.db.get_printer(selection[0])
        if printer:
            self.selected_printer = printer
            self._load_printer_to_form(printer)
    
    def _load_printer_to_form(self, printer):
        self._clear_form()
        
        self.name_entry.insert(0, printer.name)
        self.model_entry.insert(0, printer.model)
        self.price_entry.insert(0, str(printer.purchase_price))
        self.lifetime_entry.insert(0, str(printer.lifetime_kg))
        self.nozzle_entry.insert(0, "0.4")  # Default nozzle size
        self.nozzle_cost_entry.insert(0, str(printer.nozzle_cost))
        self.nozzle_life_entry.insert(0, str(printer.nozzle_lifetime_grams))
        self.elec_entry.insert(0, str(printer.electricity_rate_per_hour))
        self.active_var.set(printer.is_active)
    
    def _clear_form(self):
        self.selected_printer = None
        for attr in ['name_entry', 'model_entry', 'price_entry', 'lifetime_entry',
                     'nozzle_entry', 'nozzle_cost_entry', 'nozzle_life_entry', 'elec_entry']:
            getattr(self, attr).delete(0, tk.END)
        self.active_var.set(True)
    
    def _add_printer(self):
        self._clear_form()
        self.name_entry.focus_set()
    
    def _save_printer(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("Validation", "Printer name is required")
            return
        
        try:
            from src.models import Printer
            
            if self.selected_printer:
                printer = self.selected_printer
            else:
                printer = Printer()
            
            printer.name = name
            printer.model = self.model_entry.get().strip() or "Unknown"
            printer.purchase_price = float(self.price_entry.get() or 25000)
            printer.lifetime_kg = float(self.lifetime_entry.get() or 500)
            printer.nozzle_cost = float(self.nozzle_cost_entry.get() or 100)
            printer.nozzle_lifetime_grams = float(self.nozzle_life_entry.get() or 1500)
            printer.electricity_rate_per_hour = float(self.elec_entry.get() or 0.31)
            printer.is_active = self.active_var.get()
            
            self.db.save_printer(printer)
            messagebox.showinfo("Success", "Printer saved!")
            self._load_printers()
            
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid number: {e}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def _delete_printer(self):
        if not self.selected_printer:
            messagebox.showwarning("Select", "Select a printer to delete")
            return
        
        if messagebox.askyesno("Confirm", f"Delete printer '{self.selected_printer.name}'?"):
            # Don't actually delete, just deactivate
            self.selected_printer.is_active = False
            self.db.save_printer(self.selected_printer)
            self._load_printers()
            self._clear_form()
    
    def _reset_nozzle(self):
        if not self.selected_printer:
            messagebox.showwarning("Select", "Select a printer first")
            return
        
        if messagebox.askyesno("Reset Nozzle", "Record nozzle change?"):
            self.selected_printer.nozzle_changes += 1
            self.selected_printer.current_nozzle_grams = 0
            self.db.save_printer(self.selected_printer)
            messagebox.showinfo("Success", "Nozzle change recorded")
            self._load_printers()


class AdminPanel(ttk.Frame):
    """Main Admin Panel with tabbed interface"""
    
    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.db = db_manager
        self.auth = get_auth_manager()
        
        # Check admin access
        if not self.auth.is_admin:
            ttk.Label(
                self,
                text="🔒 Admin access required",
                font=("Segoe UI", 16)
            ).pack(expand=True)
            return
        
        self._build_ui()
    
    def _build_ui(self):
        """Build the admin panel UI"""
        # Header
        header = tk.Frame(self, bg=Colors.PURPLE, height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(
            header,
            text="⚙️ Admin Panel",
            font=("Segoe UI", 14, "bold"),
            bg=Colors.PURPLE,
            fg="white"
        ).pack(side=tk.LEFT, padx=15, pady=10)
        
        tk.Label(
            header,
            text=f"Logged in as: {self.auth.current_user.display_name or self.auth.current_user.username}",
            font=("Segoe UI", 9),
            bg=Colors.PURPLE,
            fg="white"
        ).pack(side=tk.RIGHT, padx=15)
        
        # Admin sub-tabs
        self.admin_notebook = ttk.Notebook(self)
        self.admin_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # User Management tab
        self.users_frame = UserManagementFrame(self.admin_notebook, self.db)
        self.admin_notebook.add(self.users_frame, text="👥 Users")
        
        # Filament Configuration tab
        self.filament_frame = FilamentConfigFrame(self.admin_notebook, self.db)
        self.admin_notebook.add(self.filament_frame, text="🎨 Filament")
        
        # Printer Profiles tab
        self.printers_frame = PrinterProfilesFrame(self.admin_notebook, self.db)
        self.admin_notebook.add(self.printers_frame, text="🖨️ Printers")
        
        # System Settings tab
        self.settings_frame = self._create_settings_frame()
        self.admin_notebook.add(self.settings_frame, text="⚙️ System")
    
    def _create_settings_frame(self):
        """Create system settings frame"""
        frame = ttk.Frame(self.admin_notebook, padding=10)
        
        ttk.Label(
            frame,
            text="🏢 System Settings",
            font=("Segoe UI", 14, "bold")
        ).pack(anchor=tk.W, pady=(0, 15))
        
        # Company info
        company_frame = ttk.LabelFrame(frame, text="Company Information", padding=15)
        company_frame.pack(fill=tk.X, pady=(0, 15))
        
        settings = self.db.get_settings()
        
        fields = [
            ("Company Name:", "company_name", settings.get('company_name', 'Abaad')),
            ("Phone:", "company_phone", settings.get('company_phone', '')),
            ("Address:", "company_address", settings.get('company_address', '')),
        ]
        
        self.settings_entries = {}
        for i, (label, key, default) in enumerate(fields):
            ttk.Label(company_frame, text=label).grid(row=i, column=0, sticky=tk.W, pady=3)
            entry = ttk.Entry(company_frame, width=40)
            entry.insert(0, default)
            entry.grid(row=i, column=1, pady=3, padx=5)
            self.settings_entries[key] = entry
        
        # Quote settings
        quote_frame = ttk.LabelFrame(frame, text="Quote/Invoice Settings", padding=15)
        quote_frame.pack(fill=tk.X, pady=(0, 15))
        
        quote_fields = [
            ("Deposit %:", "deposit_percent", str(settings.get('deposit_percent', 50))),
            ("Quote Validity (days):", "quote_validity_days", str(settings.get('quote_validity_days', 7))),
        ]
        
        for i, (label, key, default) in enumerate(quote_fields):
            ttk.Label(quote_frame, text=label).grid(row=i, column=0, sticky=tk.W, pady=3)
            entry = ttk.Entry(quote_frame, width=15)
            entry.insert(0, default)
            entry.grid(row=i, column=1, sticky=tk.W, pady=3, padx=5)
            self.settings_entries[key] = entry
        
        # Save button
        ttk.Button(
            frame,
            text="💾 Save All Settings",
            command=self._save_all_settings
        ).pack(pady=15)
        
        # Backup section
        backup_frame = ttk.LabelFrame(frame, text="Data Management", padding=15)
        backup_frame.pack(fill=tk.X)
        
        btn_row = ttk.Frame(backup_frame)
        btn_row.pack(fill=tk.X)
        
        ttk.Button(btn_row, text="📦 Backup Database", command=self._backup).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_row, text="📤 Export to CSV", command=self._export_csv).pack(side=tk.LEFT, padx=5)
        
        return frame
    
    def _save_all_settings(self):
        settings = {}
        for key, entry in self.settings_entries.items():
            value = entry.get().strip()
            if key in ['deposit_percent', 'quote_validity_days']:
                try:
                    value = float(value)
                except:
                    value = 50 if key == 'deposit_percent' else 7
            settings[key] = value
        
        self.db.save_settings(settings)
        messagebox.showinfo("Success", "Settings saved!")
    
    def _backup(self):
        try:
            path = self.db.backup_database()
            messagebox.showinfo("Backup", f"Backup created:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def _export_csv(self):
        try:
            files = self.db.export_to_csv()
            messagebox.showinfo("Export", "Exported:\n" + "\n".join(f"• {k}: {v}" for k, v in files.items()))
        except Exception as e:
            messagebox.showerror("Error", str(e))
