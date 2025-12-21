"""
Authentication and Authorization Module for Abaad ERP v4.0
Role-Based Access Control (RBAC) Implementation
"""
import hashlib
import secrets
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime
import json
from pathlib import Path


class UserRole(str, Enum):
    """User roles with different permission levels"""
    ADMIN = "Admin"
    USER = "User"


class Permission(str, Enum):
    """Granular permissions for RBAC"""
    # Order permissions
    CREATE_ORDER = "create_order"
    VIEW_ORDER = "view_order"
    EDIT_ORDER = "edit_order"
    DELETE_ORDER = "delete_order"
    UPDATE_STATUS = "update_status"
    
    # Customer permissions
    VIEW_CUSTOMERS = "view_customers"
    MANAGE_CUSTOMERS = "manage_customers"
    
    # Inventory permissions
    VIEW_INVENTORY = "view_inventory"
    MANAGE_INVENTORY = "manage_inventory"
    
    # Printer permissions
    VIEW_PRINTERS = "view_printers"
    MANAGE_PRINTERS = "manage_printers"
    
    # Financial permissions
    VIEW_STATISTICS = "view_statistics"
    VIEW_FINANCIAL = "view_financial"
    EXPORT_DATA = "export_data"
    
    # Admin permissions
    MANAGE_USERS = "manage_users"
    MANAGE_SETTINGS = "manage_settings"
    SYSTEM_BACKUP = "system_backup"
    
    # PDF permissions
    GENERATE_QUOTE = "generate_quote"
    GENERATE_RECEIPT = "generate_receipt"


# Role-Permission mapping
ROLE_PERMISSIONS = {
    UserRole.ADMIN: [p for p in Permission],  # Admin has all permissions
    UserRole.USER: [
        # Limited permissions for regular users
        Permission.CREATE_ORDER,
        Permission.VIEW_ORDER,
        Permission.EDIT_ORDER,
        Permission.UPDATE_STATUS,
        Permission.VIEW_CUSTOMERS,
        Permission.VIEW_INVENTORY,
        Permission.VIEW_PRINTERS,
        Permission.GENERATE_QUOTE,
        Permission.GENERATE_RECEIPT,
    ]
}


def generate_id() -> str:
    """Generate a unique ID"""
    return secrets.token_hex(4)


def now_str() -> str:
    """Get current timestamp as string"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def hash_password(password: str, salt: Optional[str] = None) -> tuple:
    """
    Hash a password using SHA-256 with salt.
    
    Args:
        password: Plain text password
        salt: Optional salt (generated if not provided)
        
    Returns:
        Tuple of (password_hash, salt)
    """
    if salt is None:
        salt = secrets.token_hex(16)
    
    # Combine password with salt and hash
    salted = f"{salt}{password}".encode('utf-8')
    password_hash = hashlib.sha256(salted).hexdigest()
    
    return password_hash, salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        password: Plain text password to verify
        password_hash: Stored hash
        salt: Stored salt
        
    Returns:
        True if password matches, False otherwise
    """
    computed_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(computed_hash, password_hash)


@dataclass
class User:
    """User model for authentication and authorization"""
    id: str = field(default_factory=generate_id)
    username: str = ""
    password_hash: str = ""
    password_salt: str = ""
    role: str = UserRole.USER.value
    display_name: str = ""
    email: str = ""
    is_active: bool = True
    created_date: str = field(default_factory=now_str)
    last_login: str = ""
    login_count: int = 0
    notes: str = ""
    
    @property
    def permissions(self) -> List[Permission]:
        """Get list of permissions for this user's role"""
        role = UserRole(self.role) if self.role in [r.value for r in UserRole] else UserRole.USER
        return ROLE_PERMISSIONS.get(role, [])
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a specific permission"""
        return permission in self.permissions
    
    def can_access_tab(self, tab_name: str) -> bool:
        """Check if user can access a specific UI tab"""
        tab_permissions = {
            'orders': Permission.VIEW_ORDER,
            'customers': Permission.VIEW_CUSTOMERS,
            'filament': Permission.VIEW_INVENTORY,
            'printers': Permission.VIEW_PRINTERS,
            'statistics': Permission.VIEW_STATISTICS,
            'settings': Permission.MANAGE_SETTINGS,
            'admin': Permission.MANAGE_USERS,
        }
        required_permission = tab_permissions.get(tab_name.lower())
        if required_permission is None:
            return True  # Default to allow if not defined
        return self.has_permission(required_permission)
    
    def set_password(self, plain_password: str):
        """Set password with automatic hashing"""
        self.password_hash, self.password_salt = hash_password(plain_password)
    
    def check_password(self, plain_password: str) -> bool:
        """Verify password"""
        return verify_password(plain_password, self.password_hash, self.password_salt)
    
    def record_login(self):
        """Record a successful login"""
        self.last_login = now_str()
        self.login_count += 1
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'username': self.username,
            'password_hash': self.password_hash,
            'password_salt': self.password_salt,
            'role': self.role,
            'display_name': self.display_name,
            'email': self.email,
            'is_active': self.is_active,
            'created_date': self.created_date,
            'last_login': self.last_login,
            'login_count': self.login_count,
            'notes': self.notes,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        user = cls()
        user.id = data.get('id', generate_id())
        user.username = data.get('username', '')
        user.password_hash = data.get('password_hash', '')
        user.password_salt = data.get('password_salt', '')
        user.role = data.get('role', UserRole.USER.value)
        user.display_name = data.get('display_name', '')
        user.email = data.get('email', '')
        user.is_active = data.get('is_active', True)
        user.created_date = data.get('created_date', now_str())
        user.last_login = data.get('last_login', '')
        user.login_count = data.get('login_count', 0)
        user.notes = data.get('notes', '')
        return user


class AuthManager:
    """
    Authentication Manager - handles user login, session, and permissions.
    Singleton pattern ensures consistent auth state across the application.
    """
    _instance = None
    _current_user: Optional[User] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.users_file = Path("data/users.json")
        self.users: Dict[str, User] = {}
        self._load_users()
        self._ensure_default_admin()
        self._initialized = True
    
    def _load_users(self):
        """Load users from JSON file"""
        if self.users_file.exists():
            try:
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for user_data in data.get('users', []):
                        user = User.from_dict(user_data)
                        self.users[user.id] = user
                print(f"✓ Loaded {len(self.users)} users")
            except Exception as e:
                print(f"✗ Error loading users: {e}")
    
    def _save_users(self) -> bool:
        """Save users to JSON file"""
        try:
            self.users_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                'users': [user.to_dict() for user in self.users.values()]
            }
            temp_path = self.users_file.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            temp_path.replace(self.users_file)
            return True
        except Exception as e:
            print(f"✗ Error saving users: {e}")
            return False
    
    def _ensure_default_admin(self):
        """Ensure at least one admin user exists"""
        # Check if any admin exists
        admins = [u for u in self.users.values() if u.role == UserRole.ADMIN.value]
        
        if not admins:
            # Create default admin
            admin = User(
                id='admin_default',
                username='admin',
                role=UserRole.ADMIN.value,
                display_name='Administrator',
                notes='Default admin account'
            )
            admin.set_password('admin123')  # Default password - should be changed!
            self.users[admin.id] = admin
            self._save_users()
            print("✓ Created default admin (username: admin, password: admin123)")
    
    def login(self, username: str, password: str) -> tuple:
        """
        Authenticate user.
        
        Args:
            username: Username
            password: Plain text password
            
        Returns:
            Tuple of (success: bool, message: str, user: Optional[User])
        """
        # Find user by username
        user = None
        for u in self.users.values():
            if u.username.lower() == username.lower():
                user = u
                break
        
        if user is None:
            return False, "User not found", None
        
        if not user.is_active:
            return False, "Account is disabled", None
        
        if not user.check_password(password):
            return False, "Incorrect password", None
        
        # Successful login
        user.record_login()
        self._save_users()
        self._current_user = user
        
        return True, f"Welcome, {user.display_name or user.username}!", user
    
    def logout(self):
        """Log out current user"""
        self._current_user = None
    
    @property
    def current_user(self) -> Optional[User]:
        """Get currently logged in user"""
        return self._current_user
    
    @property
    def is_logged_in(self) -> bool:
        """Check if a user is logged in"""
        return self._current_user is not None
    
    @property
    def is_admin(self) -> bool:
        """Check if current user is admin"""
        return self._current_user is not None and self._current_user.role == UserRole.ADMIN.value
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if current user has a permission"""
        if self._current_user is None:
            return False
        return self._current_user.has_permission(permission)
    
    def require_permission(self, permission: Permission) -> bool:
        """
        Check permission and return False if not allowed.
        Use this in UI to conditionally show/hide elements.
        """
        return self.has_permission(permission)
    
    # User Management (Admin only)
    def create_user(self, username: str, password: str, role: str = UserRole.USER.value,
                    display_name: str = "", email: str = "") -> tuple:
        """Create a new user (admin only)"""
        if not self.is_admin:
            return False, "Permission denied", None
        
        # Check if username exists
        for u in self.users.values():
            if u.username.lower() == username.lower():
                return False, "Username already exists", None
        
        user = User(
            username=username,
            role=role,
            display_name=display_name or username,
            email=email,
        )
        user.set_password(password)
        
        self.users[user.id] = user
        self._save_users()
        
        return True, f"User '{username}' created successfully", user
    
    def update_user(self, user_id: str, **kwargs) -> tuple:
        """Update user details (admin only)"""
        if not self.is_admin:
            return False, "Permission denied"
        
        user = self.users.get(user_id)
        if not user:
            return False, "User not found"
        
        # Update allowed fields
        allowed_fields = ['display_name', 'email', 'role', 'is_active', 'notes']
        for field in allowed_fields:
            if field in kwargs:
                setattr(user, field, kwargs[field])
        
        # Handle password change separately
        if 'password' in kwargs and kwargs['password']:
            user.set_password(kwargs['password'])
        
        self._save_users()
        return True, "User updated successfully"
    
    def delete_user(self, user_id: str) -> tuple:
        """Delete a user (admin only)"""
        if not self.is_admin:
            return False, "Permission denied"
        
        user = self.users.get(user_id)
        if not user:
            return False, "User not found"
        
        # Don't allow deleting yourself
        if self._current_user and user_id == self._current_user.id:
            return False, "Cannot delete yourself"
        
        # Don't allow deleting the last admin
        if user.role == UserRole.ADMIN.value:
            admins = [u for u in self.users.values() if u.role == UserRole.ADMIN.value]
            if len(admins) <= 1:
                return False, "Cannot delete the last admin"
        
        del self.users[user_id]
        self._save_users()
        return True, "User deleted successfully"
    
    def get_all_users(self) -> List[User]:
        """Get all users (admin only)"""
        if not self.is_admin:
            return []
        return list(self.users.values())
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get a specific user"""
        return self.users.get(user_id)
    
    def change_password(self, old_password: str, new_password: str) -> tuple:
        """Allow user to change their own password"""
        if not self._current_user:
            return False, "Not logged in"
        
        if not self._current_user.check_password(old_password):
            return False, "Current password is incorrect"
        
        self._current_user.set_password(new_password)
        self._save_users()
        return True, "Password changed successfully"


# Singleton accessor
_auth_manager = None

def get_auth_manager() -> AuthManager:
    """Get the AuthManager singleton instance"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager


# Convenience decorators for permission checking
def require_admin(func):
    """Decorator to require admin role"""
    def wrapper(*args, **kwargs):
        auth = get_auth_manager()
        if not auth.is_admin:
            raise PermissionError("Admin access required")
        return func(*args, **kwargs)
    return wrapper


def require_login(func):
    """Decorator to require logged in user"""
    def wrapper(*args, **kwargs):
        auth = get_auth_manager()
        if not auth.is_logged_in:
            raise PermissionError("Login required")
        return func(*args, **kwargs)
    return wrapper
