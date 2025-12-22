"""
Abaad 3D Print Manager v4.0 (ERP Edition)
Core module with AI integration and advanced features
"""
from .models import (
    PrintSettings, FilamentSpool, PrintItem, Customer, Order, 
    Statistics, Printer, FilamentHistory, OrderStatus, PaymentMethod, 
    SupportType, SpoolCategory, SpoolStatus, format_time, generate_id, now_str,
    DEFAULT_RATE_PER_GRAM, DEFAULT_COST_PER_GRAM, SPOOL_PRICE_FIXED,
    TRASH_THRESHOLD_GRAMS, TOLERANCE_THRESHOLD_GRAMS,
    calculate_payment_fee,
    # New models for failures and expenses
    PrintFailure, Expense, FailureReason, ExpenseCategory
)

from .database import DatabaseManager, get_database

__version__ = "4.0.0"
__author__ = "Abaad 3D Printing Services"

__all__ = [
    'PrintSettings', 'FilamentSpool', 'PrintItem', 'Customer', 'Order',
    'Statistics', 'Printer', 'FilamentHistory', 'OrderStatus', 'PaymentMethod', 
    'SupportType', 'SpoolCategory', 'SpoolStatus', 'format_time', 'generate_id', 
    'now_str', 'DEFAULT_RATE_PER_GRAM', 'DEFAULT_COST_PER_GRAM', 'SPOOL_PRICE_FIXED',
    'TRASH_THRESHOLD_GRAMS', 'TOLERANCE_THRESHOLD_GRAMS',
    'calculate_payment_fee', 'DatabaseManager', 'get_database',
    # New exports
    'PrintFailure', 'Expense', 'FailureReason', 'ExpenseCategory',
]
