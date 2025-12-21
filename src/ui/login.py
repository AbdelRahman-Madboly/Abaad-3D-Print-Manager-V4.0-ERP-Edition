"""
Quick Start Dialog for Abaad ERP v4.0
Simple role selection - No password required
"""
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.logic.auth import get_auth_manager, User, UserRole


class Colors:
    """Modern color scheme for Abaad ERP"""
    # Primary colors (Blue)
    PRIMARY = "#2563eb"
    PRIMARY_DARK = "#1d4ed8"
    PRIMARY_LIGHT = "#3b82f6"
    PRIMARY_LIGHTER = "#60a5fa"
    
    # Status colors
    SUCCESS = "#10b981"
    SUCCESS_DARK = "#059669"
    SUCCESS_LIGHT = "#34d399"
    
    DANGER = "#ef4444"
    DANGER_DARK = "#dc2626"
    DANGER_LIGHT = "#f87171"
    
    WARNING = "#f59e0b"
    WARNING_DARK = "#d97706"
    WARNING_LIGHT = "#fbbf24"
    
    INFO = "#06b6d4"
    INFO_DARK = "#0891b2"
    INFO_LIGHT = "#22d3ee"
    
    # Role colors
    ADMIN = "#7c3aed"
    ADMIN_DARK = "#6d28d9"
    USER = "#0891b2"
    USER_DARK = "#0e7490"
    
    # Neutral colors
    BG = "#f8fafc"
    BG_DARK = "#1e293b"
    BG_DARKER = "#0f172a"
    
    CARD = "#ffffff"
    CARD_HOVER = "#f1f5f9"
    CARD_DARK = "#334155"
    
    TEXT = "#0f172a"
    TEXT_SECONDARY = "#64748b"
    TEXT_LIGHT = "#94a3b8"
    TEXT_MUTED = "#cbd5e1"
    
    BORDER = "#e2e8f0"
    BORDER_DARK = "#475569"
    
    # Accent colors
    PURPLE = "#7c3aed"
    PURPLE_LIGHT = "#a78bfa"
    CYAN = "#06b6d4"
    ORANGE = "#f97316"
    PINK = "#ec4899"


class QuickStartDialog:
    """
    Simple role selection dialog.
    No password - just click Admin or User to start.
    """
    
    def __init__(self, parent):
        self.parent = parent
        self.result = False
        self.user = None
        self.auth = get_auth_manager()
        
        self._create_dialog()
    
    def _create_dialog(self):
        """Create the quick start dialog"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Abaad ERP v4.0 - Select Role")
        self.dialog.geometry("450x500")
        self.dialog.resizable(False, False)
        self.dialog.configure(bg="#f0f4f8")
        
        # Center the dialog on screen
        self.dialog.update_idletasks()
        width = 450
        height = 500
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # Make modal
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_exit)
        
        self._build_ui()
        
        # Wait for dialog to close
        self.parent.wait_window(self.dialog)
    
    def _build_ui(self):
        """Build the UI"""
        bg = "#f0f4f8"
        
        # Header
        header = tk.Frame(self.dialog, bg=Colors.PRIMARY, height=100)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(
            header,
            text="🖨️ Abaad ERP v4.0",
            font=("Arial", 22, "bold"),
            bg=Colors.PRIMARY,
            fg="white"
        ).pack(expand=True)
        
        # Main content
        main = tk.Frame(self.dialog, bg=bg)
        main.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)
        
        tk.Label(
            main,
            text="Welcome! Select your role:",
            font=("Arial", 14, "bold"),
            bg=bg,
            fg="#333"
        ).pack(pady=(10, 20))
        
        # Admin Button
        admin_btn = tk.Button(
            main,
            text="👑  Administrator\n\nFull access to all features",
            font=("Arial", 12),
            bg=Colors.ADMIN,
            fg="white",
            activebackground=Colors.ADMIN_DARK,
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            width=30,
            height=4,
            command=lambda: self._select_role(UserRole.ADMIN)
        )
        admin_btn.pack(pady=10, ipady=10)
        
        # User Button
        user_btn = tk.Button(
            main,
            text="👤  Staff User\n\nCreate orders & manage customers",
            font=("Arial", 12),
            bg=Colors.USER,
            fg="white",
            activebackground=Colors.USER_DARK,
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            width=30,
            height=4,
            command=lambda: self._select_role(UserRole.USER)
        )
        user_btn.pack(pady=10, ipady=10)
        
        # Footer
        tk.Label(
            main,
            text="─" * 40,
            font=("Arial", 8),
            bg=bg,
            fg="#ccc"
        ).pack(pady=(30, 5))
        
        tk.Label(
            main,
            text="Abaad 3D Printing Services\nIsmailia, Egypt",
            font=("Arial", 9),
            bg=bg,
            fg="#888"
        ).pack()
    
    def _select_role(self, role: UserRole):
        """Handle role selection"""
        try:
            # Create or get user for this role
            if role == UserRole.ADMIN:
                user = self.auth.users.get('admin_default')
                if not user:
                    user = User(
                        id='admin_default',
                        username='admin',
                        role=UserRole.ADMIN.value,
                        display_name='Administrator'
                    )
                    user.set_password('admin')
                    self.auth.users[user.id] = user
                    self.auth._save_users()
            else:
                user = self.auth.users.get('user_default')
                if not user:
                    user = User(
                        id='user_default',
                        username='user',
                        role=UserRole.USER.value,
                        display_name='Staff User'
                    )
                    user.set_password('user')
                    self.auth.users[user.id] = user
                    self.auth._save_users()
            
            # Set as current user
            user.record_login()
            self.auth._save_users()
            self.auth._current_user = user
            
            self.result = True
            self.user = user
            self.dialog.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to login: {e}")
    
    def _on_exit(self):
        """Handle window close"""
        self.result = False
        self.dialog.destroy()


class ChangePasswordDialog:
    """Dialog for profile info (kept for compatibility)"""
    
    def __init__(self, parent):
        self.parent = parent
        self.auth = get_auth_manager()
        
        if self.auth.current_user:
            messagebox.showinfo(
                "Profile",
                f"Logged in as: {self.auth.current_user.display_name}\n"
                f"Role: {self.auth.current_user.role}\n\n"
                "Use Switch button to change roles."
            )


# Compatibility alias
LoginDialog = QuickStartDialog


def show_login(parent) -> tuple:
    """Show login dialog and return result."""
    dialog = QuickStartDialog(parent)
    return dialog.result, dialog.user


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    
    dialog = QuickStartDialog(root)
    
    if dialog.result:
        print(f"Selected: {dialog.user.display_name} ({dialog.user.role})")
        root.deiconify()
        root.mainloop()
    else:
        print("Cancelled")
        root.destroy()
