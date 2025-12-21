"""
Login Dialog for Abaad ERP v4.0
Professional login UI with authentication
"""
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.logic.auth import get_auth_manager, UserRole


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
    BG_DARK = "#1e293b"
    CARD = "#ffffff"
    TEXT = "#1e293b"
    TEXT_LIGHT = "#64748b"
    BORDER = "#e2e8f0"


class LoginDialog:
    """
    Modern login dialog with role indicator.
    
    Usage:
        dialog = LoginDialog(root)
        if dialog.result:
            # User logged in successfully
            user = dialog.user
        else:
            # Login cancelled or failed
    """
    
    def __init__(self, parent):
        self.parent = parent
        self.result = False
        self.user = None
        self.auth = get_auth_manager()
        
        self._create_dialog()
    
    def _create_dialog(self):
        """Create the login dialog window"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Abaad ERP v4.0 - Login")
        self.dialog.geometry("420x520")
        self.dialog.resizable(False, False)
        self.dialog.configure(bg=Colors.BG)
        
        # Center the dialog
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center on screen
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() - 420) // 2
        y = (self.dialog.winfo_screenheight() - 520) // 2
        self.dialog.geometry(f"420x520+{x}+{y}")
        
        # Prevent closing without logging in
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)
        
        self._build_ui()
        
        # Focus username field
        self.username_entry.focus_set()
        
        # Bind Enter key
        self.dialog.bind('<Return>', lambda e: self._on_login())
        
        # Wait for dialog to close
        self.dialog.wait_window()
    
    def _build_ui(self):
        """Build the login UI"""
        # Main container
        main = tk.Frame(self.dialog, bg=Colors.BG)
        main.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Logo/Header section
        header = tk.Frame(main, bg=Colors.BG)
        header.pack(fill=tk.X, pady=(0, 30))
        
        # Logo placeholder (or actual logo if exists)
        logo_frame = tk.Frame(header, bg=Colors.PRIMARY, width=80, height=80)
        logo_frame.pack()
        logo_frame.pack_propagate(False)
        
        tk.Label(
            logo_frame, 
            text="🖨️", 
            font=("Segoe UI", 32),
            bg=Colors.PRIMARY,
            fg="white"
        ).pack(expand=True)
        
        # Title
        tk.Label(
            header,
            text="Abaad ERP",
            font=("Segoe UI", 24, "bold"),
            bg=Colors.BG,
            fg=Colors.TEXT
        ).pack(pady=(15, 0))
        
        tk.Label(
            header,
            text="3D Print Management System v4.0",
            font=("Segoe UI", 10),
            bg=Colors.BG,
            fg=Colors.TEXT_LIGHT
        ).pack()
        
        # Login form card
        form_card = tk.Frame(main, bg=Colors.CARD, relief=tk.FLAT, bd=0)
        form_card.pack(fill=tk.X, pady=10)
        
        # Add shadow effect (border)
        form_card.configure(highlightbackground=Colors.BORDER, highlightthickness=1)
        
        form_inner = tk.Frame(form_card, bg=Colors.CARD)
        form_inner.pack(fill=tk.X, padx=25, pady=25)
        
        # Username field
        tk.Label(
            form_inner,
            text="Username",
            font=("Segoe UI", 10, "bold"),
            bg=Colors.CARD,
            fg=Colors.TEXT,
            anchor=tk.W
        ).pack(fill=tk.X)
        
        self.username_entry = tk.Entry(
            form_inner,
            font=("Segoe UI", 12),
            relief=tk.FLAT,
            bg=Colors.BG,
            fg=Colors.TEXT,
            insertbackground=Colors.PRIMARY
        )
        self.username_entry.pack(fill=tk.X, pady=(5, 15), ipady=8)
        self.username_entry.configure(highlightbackground=Colors.BORDER, highlightthickness=1)
        
        # Password field
        tk.Label(
            form_inner,
            text="Password",
            font=("Segoe UI", 10, "bold"),
            bg=Colors.CARD,
            fg=Colors.TEXT,
            anchor=tk.W
        ).pack(fill=tk.X)
        
        self.password_entry = tk.Entry(
            form_inner,
            font=("Segoe UI", 12),
            relief=tk.FLAT,
            bg=Colors.BG,
            fg=Colors.TEXT,
            show="●",
            insertbackground=Colors.PRIMARY
        )
        self.password_entry.pack(fill=tk.X, pady=(5, 5), ipady=8)
        self.password_entry.configure(highlightbackground=Colors.BORDER, highlightthickness=1)
        
        # Show password checkbox
        self.show_password_var = tk.BooleanVar(value=False)
        show_pw_check = tk.Checkbutton(
            form_inner,
            text="Show password",
            variable=self.show_password_var,
            command=self._toggle_password_visibility,
            font=("Segoe UI", 9),
            bg=Colors.CARD,
            fg=Colors.TEXT_LIGHT,
            activebackground=Colors.CARD,
            selectcolor=Colors.CARD
        )
        show_pw_check.pack(anchor=tk.W, pady=(0, 15))
        
        # Error message label (hidden by default)
        self.error_label = tk.Label(
            form_inner,
            text="",
            font=("Segoe UI", 9),
            bg=Colors.CARD,
            fg=Colors.DANGER,
            anchor=tk.W
        )
        self.error_label.pack(fill=tk.X, pady=(0, 10))
        
        # Login button
        self.login_btn = tk.Button(
            form_inner,
            text="Sign In",
            font=("Segoe UI", 11, "bold"),
            bg=Colors.PRIMARY,
            fg="white",
            activebackground=Colors.PRIMARY_LIGHT,
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            command=self._on_login
        )
        self.login_btn.pack(fill=tk.X, ipady=10)
        
        # Hover effects for button
        self.login_btn.bind('<Enter>', lambda e: self.login_btn.configure(bg=Colors.PRIMARY_LIGHT))
        self.login_btn.bind('<Leave>', lambda e: self.login_btn.configure(bg=Colors.PRIMARY))
        
        # Footer
        footer = tk.Frame(main, bg=Colors.BG)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        
        tk.Label(
            footer,
            text="Default: admin / admin123",
            font=("Segoe UI", 8),
            bg=Colors.BG,
            fg=Colors.TEXT_LIGHT
        ).pack(pady=5)
        
        tk.Label(
            footer,
            text="© 2024 Abaad 3D Printing Services",
            font=("Segoe UI", 8),
            bg=Colors.BG,
            fg=Colors.TEXT_LIGHT
        ).pack()
    
    def _toggle_password_visibility(self):
        """Toggle password visibility"""
        if self.show_password_var.get():
            self.password_entry.configure(show="")
        else:
            self.password_entry.configure(show="●")
    
    def _show_error(self, message: str):
        """Show error message"""
        self.error_label.configure(text=f"⚠ {message}")
        # Shake effect
        x = self.dialog.winfo_x()
        for i in range(3):
            self.dialog.geometry(f"+{x+5}+{self.dialog.winfo_y()}")
            self.dialog.update()
            self.dialog.after(50)
            self.dialog.geometry(f"+{x-5}+{self.dialog.winfo_y()}")
            self.dialog.update()
            self.dialog.after(50)
        self.dialog.geometry(f"+{x}+{self.dialog.winfo_y()}")
    
    def _on_login(self):
        """Handle login attempt"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        
        if not username:
            self._show_error("Please enter your username")
            self.username_entry.focus_set()
            return
        
        if not password:
            self._show_error("Please enter your password")
            self.password_entry.focus_set()
            return
        
        # Disable button during auth
        self.login_btn.configure(text="Signing in...", state=tk.DISABLED)
        self.dialog.update()
        
        # Attempt login
        success, message, user = self.auth.login(username, password)
        
        if success:
            self.result = True
            self.user = user
            self.dialog.destroy()
        else:
            self._show_error(message)
            self.login_btn.configure(text="Sign In", state=tk.NORMAL)
            self.password_entry.delete(0, tk.END)
            self.password_entry.focus_set()
    
    def _on_cancel(self):
        """Handle dialog close/cancel"""
        if messagebox.askyesno("Exit", "Exit the application?"):
            self.result = False
            self.dialog.destroy()
            self.parent.destroy()
            sys.exit(0)


class ChangePasswordDialog:
    """Dialog for users to change their password"""
    
    def __init__(self, parent):
        self.parent = parent
        self.result = False
        self.auth = get_auth_manager()
        
        self._create_dialog()
    
    def _create_dialog(self):
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Change Password")
        self.dialog.geometry("350x280")
        self.dialog.resizable(False, False)
        self.dialog.configure(bg=Colors.CARD)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() - 350) // 2
        y = (self.dialog.winfo_screenheight() - 280) // 2
        self.dialog.geometry(f"350x280+{x}+{y}")
        
        main = tk.Frame(self.dialog, bg=Colors.CARD)
        main.pack(fill=tk.BOTH, expand=True, padx=25, pady=25)
        
        tk.Label(
            main,
            text="Change Password",
            font=("Segoe UI", 14, "bold"),
            bg=Colors.CARD,
            fg=Colors.TEXT
        ).pack(anchor=tk.W, pady=(0, 15))
        
        # Current password
        tk.Label(main, text="Current Password:", font=("Segoe UI", 10), 
                bg=Colors.CARD, fg=Colors.TEXT, anchor=tk.W).pack(fill=tk.X)
        self.current_pw = tk.Entry(main, font=("Segoe UI", 11), show="●")
        self.current_pw.pack(fill=tk.X, pady=(3, 10), ipady=5)
        
        # New password
        tk.Label(main, text="New Password:", font=("Segoe UI", 10),
                bg=Colors.CARD, fg=Colors.TEXT, anchor=tk.W).pack(fill=tk.X)
        self.new_pw = tk.Entry(main, font=("Segoe UI", 11), show="●")
        self.new_pw.pack(fill=tk.X, pady=(3, 10), ipady=5)
        
        # Confirm password
        tk.Label(main, text="Confirm New Password:", font=("Segoe UI", 10),
                bg=Colors.CARD, fg=Colors.TEXT, anchor=tk.W).pack(fill=tk.X)
        self.confirm_pw = tk.Entry(main, font=("Segoe UI", 11), show="●")
        self.confirm_pw.pack(fill=tk.X, pady=(3, 15), ipady=5)
        
        # Buttons
        btn_frame = tk.Frame(main, bg=Colors.CARD)
        btn_frame.pack(fill=tk.X)
        
        tk.Button(
            btn_frame, text="Cancel", font=("Segoe UI", 10),
            command=self.dialog.destroy, width=10
        ).pack(side=tk.RIGHT, padx=(5, 0))
        
        tk.Button(
            btn_frame, text="Change", font=("Segoe UI", 10, "bold"),
            bg=Colors.PRIMARY, fg="white",
            command=self._on_change, width=10
        ).pack(side=tk.RIGHT)
        
        self.current_pw.focus_set()
        self.dialog.bind('<Return>', lambda e: self._on_change())
        
        self.dialog.wait_window()
    
    def _on_change(self):
        current = self.current_pw.get()
        new = self.new_pw.get()
        confirm = self.confirm_pw.get()
        
        if not all([current, new, confirm]):
            messagebox.showwarning("Error", "Please fill all fields")
            return
        
        if new != confirm:
            messagebox.showwarning("Error", "New passwords don't match")
            return
        
        if len(new) < 4:
            messagebox.showwarning("Error", "Password must be at least 4 characters")
            return
        
        success, message = self.auth.change_password(current, new)
        if success:
            messagebox.showinfo("Success", message)
            self.result = True
            self.dialog.destroy()
        else:
            messagebox.showerror("Error", message)


def show_login(parent) -> tuple:
    """
    Show login dialog and return result.
    
    Args:
        parent: Parent window
        
    Returns:
        Tuple of (success: bool, user: Optional[User])
    """
    dialog = LoginDialog(parent)
    return dialog.result, dialog.user


if __name__ == "__main__":
    # Test the login dialog
    root = tk.Tk()
    root.withdraw()  # Hide main window
    
    dialog = LoginDialog(root)
    
    if dialog.result:
        print(f"Logged in as: {dialog.user.username} ({dialog.user.role})")
    else:
        print("Login cancelled")
    
    root.mainloop()
