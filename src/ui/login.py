"""
Quick Start Dialog for Abaad ERP v4.0
Simple role selection - No password required
Professional, user-friendly design
"""
import tkinter as tk
from tkinter import ttk
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
    
    # Gradient-like pairs
    GRADIENT_START = "#4f46e5"
    GRADIENT_END = "#06b6d4"


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
        self.dialog.title("Abaad ERP v4.0")
        self.dialog.geometry("500x600")
        self.dialog.resizable(False, False)
        self.dialog.configure(bg=Colors.BG)
        
        # Center the dialog
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() - 500) // 2
        y = (self.dialog.winfo_screenheight() - 600) // 2
        self.dialog.geometry(f"500x600+{x}+{y}")
        
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_exit)
        
        self._build_ui()
        self.dialog.wait_window()
    
    def _build_ui(self):
        """Build the modern UI"""
        # Main container
        main = tk.Frame(self.dialog, bg=Colors.BG)
        main.pack(fill=tk.BOTH, expand=True, padx=40, pady=30)
        
        # === HEADER ===
        header = tk.Frame(main, bg=Colors.BG)
        header.pack(fill=tk.X, pady=(0, 30))
        
        # Logo
        logo_frame = tk.Frame(header, bg=Colors.PRIMARY, width=90, height=90)
        logo_frame.pack()
        logo_frame.pack_propagate(False)
        
        tk.Label(
            logo_frame,
            text="🖨️",
            font=("Segoe UI", 40),
            bg=Colors.PRIMARY,
            fg="white"
        ).pack(expand=True)
        
        # Title
        tk.Label(
            header,
            text="Abaad ERP",
            font=("Segoe UI", 28, "bold"),
            bg=Colors.BG,
            fg=Colors.TEXT
        ).pack(pady=(20, 5))
        
        tk.Label(
            header,
            text="3D Print Management System",
            font=("Segoe UI", 12),
            bg=Colors.BG,
            fg=Colors.TEXT_SECONDARY
        ).pack()
        
        # Version badge
        version_frame = tk.Frame(header, bg=Colors.SUCCESS, padx=12, pady=4)
        version_frame.pack(pady=(10, 0))
        tk.Label(
            version_frame,
            text="v4.0 ERP Edition",
            font=("Segoe UI", 9, "bold"),
            bg=Colors.SUCCESS,
            fg="white"
        ).pack()
        
        # === SELECT ROLE ===
        tk.Label(
            main,
            text="Select Your Role",
            font=("Segoe UI", 14, "bold"),
            bg=Colors.BG,
            fg=Colors.TEXT
        ).pack(pady=(20, 15))
        
        # Role cards container
        cards = tk.Frame(main, bg=Colors.BG)
        cards.pack(fill=tk.X, pady=10)
        
        # Admin Card
        self._create_role_card(
            cards,
            role=UserRole.ADMIN,
            icon="👑",
            title="Administrator",
            description="Full access to all features\nManage users, inventory & settings",
            color=Colors.ADMIN,
            hover_color=Colors.ADMIN_DARK
        )
        
        # Spacer
        tk.Frame(main, bg=Colors.BG, height=15).pack()
        
        # User Card
        self._create_role_card(
            cards,
            role=UserRole.USER,
            icon="👤",
            title="Staff User",
            description="Create orders & manage customers\nView inventory & print receipts",
            color=Colors.USER,
            hover_color=Colors.USER_DARK
        )
        
        # === FOOTER ===
        footer = tk.Frame(main, bg=Colors.BG)
        footer.pack(side=tk.BOTTOM, fill=tk.X, pady=(30, 0))
        
        tk.Label(
            footer,
            text="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            font=("Segoe UI", 8),
            bg=Colors.BG,
            fg=Colors.BORDER
        ).pack()
        
        tk.Label(
            footer,
            text="Abaad 3D Printing Services",
            font=("Segoe UI", 10, "bold"),
            bg=Colors.BG,
            fg=Colors.TEXT_SECONDARY
        ).pack(pady=(10, 2))
        
        tk.Label(
            footer,
            text="Ismailia, Egypt • 01070750477",
            font=("Segoe UI", 9),
            bg=Colors.BG,
            fg=Colors.TEXT_LIGHT
        ).pack()
    
    def _create_role_card(self, parent, role, icon, title, description, color, hover_color):
        """Create a clickable role card"""
        # Card frame
        card = tk.Frame(
            parent,
            bg=Colors.CARD,
            highlightbackground=Colors.BORDER,
            highlightthickness=2,
            cursor="hand2"
        )
        card.pack(fill=tk.X, pady=5, ipady=15)
        
        # Inner container
        inner = tk.Frame(card, bg=Colors.CARD)
        inner.pack(fill=tk.X, padx=20, pady=10)
        
        # Left: Icon
        icon_frame = tk.Frame(inner, bg=color, width=60, height=60)
        icon_frame.pack(side=tk.LEFT, padx=(0, 20))
        icon_frame.pack_propagate(False)
        
        icon_label = tk.Label(
            icon_frame,
            text=icon,
            font=("Segoe UI", 28),
            bg=color,
            fg="white"
        )
        icon_label.pack(expand=True)
        
        # Right: Text
        text_frame = tk.Frame(inner, bg=Colors.CARD)
        text_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        title_label = tk.Label(
            text_frame,
            text=title,
            font=("Segoe UI", 14, "bold"),
            bg=Colors.CARD,
            fg=Colors.TEXT,
            anchor=tk.W
        )
        title_label.pack(anchor=tk.W)
        
        desc_label = tk.Label(
            text_frame,
            text=description,
            font=("Segoe UI", 10),
            bg=Colors.CARD,
            fg=Colors.TEXT_SECONDARY,
            anchor=tk.W,
            justify=tk.LEFT
        )
        desc_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Arrow
        arrow_label = tk.Label(
            inner,
            text="→",
            font=("Segoe UI", 20),
            bg=Colors.CARD,
            fg=Colors.TEXT_LIGHT
        )
        arrow_label.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Hover effects
        def on_enter(e):
            card.configure(highlightbackground=color, highlightthickness=3)
            inner.configure(bg=Colors.CARD_HOVER)
            text_frame.configure(bg=Colors.CARD_HOVER)
            title_label.configure(bg=Colors.CARD_HOVER)
            desc_label.configure(bg=Colors.CARD_HOVER)
            arrow_label.configure(bg=Colors.CARD_HOVER, fg=color)
        
        def on_leave(e):
            card.configure(highlightbackground=Colors.BORDER, highlightthickness=2)
            inner.configure(bg=Colors.CARD)
            text_frame.configure(bg=Colors.CARD)
            title_label.configure(bg=Colors.CARD)
            desc_label.configure(bg=Colors.CARD)
            arrow_label.configure(bg=Colors.CARD, fg=Colors.TEXT_LIGHT)
        
        def on_click(e):
            self._select_role(role)
        
        # Bind events to all elements
        for widget in [card, inner, icon_frame, icon_label, text_frame, 
                       title_label, desc_label, arrow_label]:
            widget.bind('<Enter>', on_enter)
            widget.bind('<Leave>', on_leave)
            widget.bind('<Button-1>', on_click)
    
    def _select_role(self, role: UserRole):
        """Handle role selection"""
        # Create or get user for this role
        if role == UserRole.ADMIN:
            # Use default admin
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
            # Use or create default user
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
    
    def _on_exit(self):
        """Handle window close"""
        self.result = False
        self.dialog.destroy()
        self.parent.destroy()
        sys.exit(0)


class ChangePasswordDialog:
    """Dialog for users to change their password (kept for compatibility)"""
    
    def __init__(self, parent):
        self.parent = parent
        self.result = False
        self.auth = get_auth_manager()
        
        # Simple info dialog instead
        from tkinter import messagebox
        messagebox.showinfo(
            "Profile Settings",
            f"Logged in as: {self.auth.current_user.display_name}\n"
            f"Role: {self.auth.current_user.role}\n\n"
            "Password settings are disabled in quick-start mode."
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
    else:
        print("Cancelled")
    
    root.mainloop()
