"""
Abaad ERP v4.0 - Logic Module
Business logic, AI integration, and authentication
"""
from .cura_ai import (
    CuraVision, get_cura_vision, extract_from_cura_screenshot,
    PILLOW_AVAILABLE, TESSERACT_AVAILABLE
)

from .auth import (
    User, UserRole, Permission, AuthManager, get_auth_manager,
    hash_password, verify_password, require_admin, require_login,
    ROLE_PERMISSIONS
)

__all__ = [
    # Cura Vision AI
    'CuraVision', 'get_cura_vision', 'extract_from_cura_screenshot',
    'PILLOW_AVAILABLE', 'TESSERACT_AVAILABLE',
    
    # Authentication & Authorization
    'User', 'UserRole', 'Permission', 'AuthManager', 'get_auth_manager',
    'hash_password', 'verify_password', 'require_admin', 'require_login',
    'ROLE_PERMISSIONS',
]
