"""
Data models for Abaad 3D Print Manager v3
With payment methods, multiple printers, and improved cost tracking
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
import uuid


# === CONSTANTS ===
DEFAULT_RATE_PER_GRAM = 4.0
DEFAULT_COST_PER_GRAM = 0.84  # eSUN spool 840 EGP / 1000g
SPOOL_PRICE_FIXED = 840.0  # Fixed price regardless of weight
DEFAULT_NOZZLE = 0.4
DEFAULT_LAYER_HEIGHT = 0.2


class OrderStatus(str, Enum):
    DRAFT = "Draft"
    CONFIRMED = "Confirmed"
    IN_PROGRESS = "In Progress"
    READY = "Ready"
    DELIVERED = "Delivered"
    CANCELLED = "Cancelled"


class PaymentMethod(str, Enum):
    CASH = "Cash"
    VODAFONE_CASH = "Vodafone Cash"
    INSTAPAY = "InstaPay"


class SupportType(str, Enum):
    NONE = "None"
    NORMAL = "Normal"
    TREE = "Tree"


class SpoolCategory(str, Enum):
    STANDARD = "standard"
    REMAINING = "remaining"


def generate_id() -> str:
    return str(uuid.uuid4())[:8]


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def format_time(minutes: int) -> str:
    if minutes <= 0:
        return "0m"
    days = minutes // (24 * 60)
    remaining = minutes % (24 * 60)
    hours = remaining // 60
    mins = remaining % 60
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if mins > 0 or not parts:
        parts.append(f"{mins}m")
    return " ".join(parts)


def calculate_payment_fee(amount: float, method: str) -> float:
    """Calculate payment method fee"""
    if method == PaymentMethod.CASH.value:
        return 0.0
    elif method == PaymentMethod.VODAFONE_CASH.value:
        # 0.5% of amount, min 1 EGP, max 15 EGP
        fee = amount * 0.005
        return max(1.0, min(15.0, fee))
    elif method == PaymentMethod.INSTAPAY.value:
        # 0.1% of amount, min 0.50 EGP, max 20 EGP
        fee = amount * 0.001
        return max(0.50, min(20.0, fee))
    return 0.0


# === MODELS ===

@dataclass
class PrintSettings:
    """Print settings from slicer"""
    nozzle_size: float = DEFAULT_NOZZLE
    layer_height: float = DEFAULT_LAYER_HEIGHT
    infill_density: int = 20
    support_type: str = SupportType.NONE.value
    scale_ratio: float = 1.0
    
    def to_dict(self) -> dict:
        return {
            'nozzle_size': self.nozzle_size,
            'layer_height': self.layer_height,
            'infill_density': self.infill_density,
            'support_type': self.support_type,
            'scale_ratio': self.scale_ratio,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PrintSettings':
        return cls(
            nozzle_size=float(data.get('nozzle_size', DEFAULT_NOZZLE)),
            layer_height=float(data.get('layer_height', DEFAULT_LAYER_HEIGHT)),
            infill_density=int(data.get('infill_density', 20)),
            support_type=data.get('support_type', SupportType.NONE.value),
            scale_ratio=float(data.get('scale_ratio', 1.0)),
        )
    
    def __str__(self):
        parts = [f"N{self.nozzle_size}", f"L{self.layer_height}"]
        if self.support_type != SupportType.NONE.value:
            parts.append(f"Sup:{self.support_type}")
        return " | ".join(parts)


@dataclass
class Printer:
    """3D Printer with tracking"""
    id: str = field(default_factory=generate_id)
    name: str = "HIVE 0.1"
    model: str = "Creality Ender-3 Max"
    purchase_price: float = 25000.0
    lifetime_kg: float = 500.0  # Expected lifetime in kg printed
    total_printed_grams: float = 0.0
    total_print_time_minutes: int = 0
    nozzle_changes: int = 0
    nozzle_cost: float = 100.0  # Cost per nozzle
    nozzle_lifetime_grams: float = 1500.0  # Grams per nozzle
    current_nozzle_grams: float = 0.0  # Grams printed on current nozzle
    electricity_rate_per_hour: float = 0.31  # EGP per hour
    is_active: bool = True
    notes: str = ""
    created_date: str = field(default_factory=now_str)
    
    @property
    def depreciation_per_gram(self) -> float:
        """Machine depreciation per gram"""
        return self.purchase_price / (self.lifetime_kg * 1000)
    
    @property
    def total_depreciation(self) -> float:
        return self.total_printed_grams * self.depreciation_per_gram
    
    @property
    def total_electricity_cost(self) -> float:
        return (self.total_print_time_minutes / 60) * self.electricity_rate_per_hour
    
    @property
    def total_nozzle_cost(self) -> float:
        return self.nozzle_changes * self.nozzle_cost
    
    @property
    def nozzle_usage_percent(self) -> float:
        if self.nozzle_lifetime_grams <= 0:
            return 0
        return (self.current_nozzle_grams / self.nozzle_lifetime_grams) * 100
    
    def add_print(self, grams: float, minutes: int):
        """Record a print job"""
        self.total_printed_grams += grams
        self.total_print_time_minutes += minutes
        self.current_nozzle_grams += grams
        
        # Auto nozzle change tracking
        if self.current_nozzle_grams >= self.nozzle_lifetime_grams:
            self.nozzle_changes += 1
            self.current_nozzle_grams = self.current_nozzle_grams - self.nozzle_lifetime_grams
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'model': self.model,
            'purchase_price': self.purchase_price,
            'lifetime_kg': self.lifetime_kg,
            'total_printed_grams': self.total_printed_grams,
            'total_print_time_minutes': self.total_print_time_minutes,
            'nozzle_changes': self.nozzle_changes,
            'nozzle_cost': self.nozzle_cost,
            'nozzle_lifetime_grams': self.nozzle_lifetime_grams,
            'current_nozzle_grams': self.current_nozzle_grams,
            'electricity_rate_per_hour': self.electricity_rate_per_hour,
            'is_active': self.is_active,
            'notes': self.notes,
            'created_date': self.created_date,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Printer':
        p = cls()
        p.id = data.get('id', generate_id())
        p.name = data.get('name', 'HIVE 0.1')
        p.model = data.get('model', 'Creality Ender-3 Max')
        p.purchase_price = data.get('purchase_price', 25000.0)
        p.lifetime_kg = data.get('lifetime_kg', 500.0)
        p.total_printed_grams = data.get('total_printed_grams', 0.0)
        p.total_print_time_minutes = data.get('total_print_time_minutes', 0)
        p.nozzle_changes = data.get('nozzle_changes', 0)
        p.nozzle_cost = data.get('nozzle_cost', 100.0)
        p.nozzle_lifetime_grams = data.get('nozzle_lifetime_grams', 1500.0)
        p.current_nozzle_grams = data.get('current_nozzle_grams', 0.0)
        p.electricity_rate_per_hour = data.get('electricity_rate_per_hour', 0.31)
        p.is_active = data.get('is_active', True)
        p.notes = data.get('notes', '')
        p.created_date = data.get('created_date', now_str())
        return p


@dataclass
class FilamentSpool:
    """Filament spool inventory"""
    id: str = field(default_factory=generate_id)
    name: str = ""
    filament_type: str = "PLA+"
    brand: str = "eSUN"
    color: str = "Black"
    category: str = SpoolCategory.STANDARD.value
    initial_weight_grams: float = 1000.0
    current_weight_grams: float = 1000.0
    purchase_price_egp: float = SPOOL_PRICE_FIXED
    purchase_date: str = field(default_factory=now_str)
    notes: str = ""
    is_active: bool = True
    
    @property
    def used_weight_grams(self) -> float:
        return self.initial_weight_grams - self.current_weight_grams
    
    @property
    def remaining_percent(self) -> float:
        if self.initial_weight_grams <= 0:
            return 0
        return (self.current_weight_grams / self.initial_weight_grams) * 100
    
    @property
    def cost_per_gram(self) -> float:
        """Cost per gram - 0 for remaining (already paid)"""
        if self.category == SpoolCategory.REMAINING.value:
            return 0.0  # Remaining filament has no cost (already paid)
        # Standard spools: fixed 840 EGP regardless of weight
        if self.initial_weight_grams <= 0:
            return DEFAULT_COST_PER_GRAM
        return SPOOL_PRICE_FIXED / self.initial_weight_grams
    
    @property
    def display_name(self) -> str:
        if self.name:
            return self.name
        return f"{self.brand} {self.filament_type} {self.color}"
    
    def use_filament(self, grams: float) -> bool:
        """Deduct filament. Returns True if successful."""
        if grams <= 0:
            return True
        if grams > self.current_weight_grams:
            return False
        self.current_weight_grams -= grams
        if self.current_weight_grams < 1:
            self.is_active = False
        return True
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name or self.display_name,
            'filament_type': self.filament_type,
            'brand': self.brand,
            'color': self.color,
            'category': self.category,
            'initial_weight_grams': self.initial_weight_grams,
            'current_weight_grams': self.current_weight_grams,
            'purchase_price_egp': self.purchase_price_egp,
            'purchase_date': self.purchase_date,
            'notes': self.notes,
            'is_active': self.is_active,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'FilamentSpool':
        spool = cls()
        spool.id = data.get('id', generate_id())
        spool.name = data.get('name', '')
        spool.filament_type = data.get('filament_type', 'PLA+')
        spool.brand = data.get('brand', 'eSUN')
        spool.color = data.get('color', 'Black')
        spool.category = data.get('category', SpoolCategory.STANDARD.value)
        spool.initial_weight_grams = data.get('initial_weight_grams', 1000.0)
        spool.current_weight_grams = data.get('current_weight_grams', 1000.0)
        spool.purchase_price_egp = data.get('purchase_price_egp', SPOOL_PRICE_FIXED)
        spool.purchase_date = data.get('purchase_date', now_str())
        spool.notes = data.get('notes', '')
        spool.is_active = data.get('is_active', True)
        return spool


@dataclass
class PrintItem:
    """Single print item in an order"""
    id: str = field(default_factory=generate_id)
    name: str = ""
    estimated_weight_grams: float = 0
    actual_weight_grams: float = 0
    estimated_time_minutes: int = 0
    actual_time_minutes: int = 0
    filament_type: str = "PLA+"
    color: str = "Black"
    spool_id: str = ""
    settings: PrintSettings = field(default_factory=PrintSettings)
    quantity: int = 1
    rate_per_gram: float = DEFAULT_RATE_PER_GRAM
    notes: str = ""
    is_printed: bool = False
    filament_deducted: bool = False
    printer_id: str = ""  # Which printer is used
    
    @property
    def weight(self) -> float:
        return self.actual_weight_grams if self.actual_weight_grams > 0 else self.estimated_weight_grams
    
    @property
    def time_minutes(self) -> int:
        return self.actual_time_minutes if self.actual_time_minutes > 0 else self.estimated_time_minutes
    
    @property
    def time_formatted(self) -> str:
        return format_time(self.time_minutes)
    
    @property
    def print_cost(self) -> float:
        """Cost = weight × quantity × rate"""
        return self.weight * self.quantity * self.rate_per_gram
    
    @property
    def discount_from_base(self) -> float:
        """Calculate discount % from base rate (4.0 EGP/g)"""
        if self.rate_per_gram >= DEFAULT_RATE_PER_GRAM:
            return 0.0
        return ((DEFAULT_RATE_PER_GRAM - self.rate_per_gram) / DEFAULT_RATE_PER_GRAM) * 100
    
    @property
    def total_weight(self) -> float:
        return self.weight * self.quantity
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'estimated_weight_grams': self.estimated_weight_grams,
            'actual_weight_grams': self.actual_weight_grams,
            'estimated_time_minutes': self.estimated_time_minutes,
            'actual_time_minutes': self.actual_time_minutes,
            'filament_type': self.filament_type,
            'color': self.color,
            'spool_id': self.spool_id,
            'settings': self.settings.to_dict(),
            'quantity': self.quantity,
            'rate_per_gram': self.rate_per_gram,
            'notes': self.notes,
            'is_printed': self.is_printed,
            'filament_deducted': self.filament_deducted,
            'printer_id': self.printer_id,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PrintItem':
        item = cls()
        item.id = data.get('id', generate_id())
        item.name = data.get('name', '')
        item.estimated_weight_grams = data.get('estimated_weight_grams', 0)
        item.actual_weight_grams = data.get('actual_weight_grams', 0)
        item.estimated_time_minutes = data.get('estimated_time_minutes', 0)
        item.actual_time_minutes = data.get('actual_time_minutes', 0)
        item.filament_type = data.get('filament_type', 'PLA+')
        item.color = data.get('color', 'Black')
        item.spool_id = data.get('spool_id', '')
        item.settings = PrintSettings.from_dict(data.get('settings', {}))
        item.quantity = data.get('quantity', 1)
        item.rate_per_gram = data.get('rate_per_gram', DEFAULT_RATE_PER_GRAM)
        item.notes = data.get('notes', '')
        item.is_printed = data.get('is_printed', False)
        item.filament_deducted = data.get('filament_deducted', False)
        item.printer_id = data.get('printer_id', '')
        return item


@dataclass
class Customer:
    """Customer information"""
    id: str = field(default_factory=generate_id)
    name: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""
    notes: str = ""
    created_date: str = field(default_factory=now_str)
    total_orders: int = 0
    total_spent: float = 0
    discount_percent: float = 0
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'email': self.email,
            'address': self.address,
            'notes': self.notes,
            'created_date': self.created_date,
            'total_orders': self.total_orders,
            'total_spent': self.total_spent,
            'discount_percent': self.discount_percent,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Customer':
        c = cls()
        c.id = data.get('id', generate_id())
        c.name = data.get('name', '')
        c.phone = data.get('phone', '')
        c.email = data.get('email', '')
        c.address = data.get('address', '')
        c.notes = data.get('notes', '')
        c.created_date = data.get('created_date', now_str())
        c.total_orders = data.get('total_orders', 0)
        c.total_spent = data.get('total_spent', 0)
        c.discount_percent = data.get('discount_percent', 0)
        return c


@dataclass
class Order:
    """Customer order with multiple items"""
    id: str = field(default_factory=generate_id)
    order_number: int = 0
    customer_id: str = ""
    customer_name: str = ""
    customer_phone: str = ""
    status: str = OrderStatus.DRAFT.value
    items: List[PrintItem] = field(default_factory=list)
    
    # Pricing
    subtotal: float = 0  # Sum of items at base rate (4 EGP/g)
    actual_total: float = 0  # Sum of items at actual rates
    discount_percent: float = 0  # Auto-calculated from rates
    discount_amount: float = 0
    order_discount_percent: float = 0  # Manual order-level discount (on top of rate discount)
    order_discount_amount: float = 0
    shipping_cost: float = 0
    total: float = 0
    
    # Payment
    payment_method: str = PaymentMethod.CASH.value
    payment_fee: float = 0
    
    # Cost tracking (internal)
    material_cost: float = 0
    electricity_cost: float = 0
    depreciation_cost: float = 0
    profit: float = 0
    
    # Dates
    created_date: str = field(default_factory=now_str)
    updated_date: str = field(default_factory=now_str)
    delivered_date: str = ""
    deleted_date: str = ""
    
    notes: str = ""
    is_deleted: bool = False
    
    @property
    def item_count(self) -> int:
        return sum(item.quantity for item in self.items)
    
    @property
    def total_weight(self) -> float:
        return sum(item.total_weight for item in self.items)
    
    @property
    def total_time(self) -> int:
        return sum(item.time_minutes * item.quantity for item in self.items)
    
    @property
    def total_time_formatted(self) -> str:
        return format_time(self.total_time)
    
    def add_item(self, item: PrintItem):
        self.items.append(item)
        self.calculate_totals()
        self.updated_date = now_str()
    
    def remove_item(self, item_id: str):
        self.items = [i for i in self.items if i.id != item_id]
        self.calculate_totals()
        self.updated_date = now_str()
    
    def get_item(self, item_id: str) -> Optional[PrintItem]:
        for item in self.items:
            if item.id == item_id:
                return item
        return None
    
    def calculate_totals(self):
        """Calculate all totals with auto-discount and manual order discount"""
        # Subtotal at base rate (4 EGP/g)
        self.subtotal = sum(item.weight * item.quantity * DEFAULT_RATE_PER_GRAM for item in self.items)
        
        # Actual total at item rates
        self.actual_total = sum(item.print_cost for item in self.items)
        
        # Auto-calculate discount from subtotal vs actual (rate discount)
        if self.subtotal > 0:
            self.discount_amount = self.subtotal - self.actual_total
            self.discount_percent = (self.discount_amount / self.subtotal) * 100
        else:
            self.discount_amount = 0
            self.discount_percent = 0
        
        # Apply manual order discount (on top of rate discount)
        after_rate_discount = self.actual_total
        if self.order_discount_percent > 0:
            self.order_discount_amount = after_rate_discount * (self.order_discount_percent / 100)
        else:
            self.order_discount_amount = 0
        
        final_subtotal = after_rate_discount - self.order_discount_amount
        
        # Calculate payment fee
        subtotal_with_shipping = final_subtotal + self.shipping_cost
        self.payment_fee = calculate_payment_fee(subtotal_with_shipping, self.payment_method)
        
        # Final total (fee is added to receipt for customer)
        self.total = final_subtotal + self.shipping_cost + self.payment_fee
        
        # Cost tracking (for statistics)
        self.material_cost = sum(item.total_weight for item in self.items) * DEFAULT_COST_PER_GRAM
        hours = self.total_time / 60
        self.electricity_cost = hours * 0.31  # EGP per hour
        self.depreciation_cost = self.total_weight * (25000 / 500000)  # 25000 EGP / 500kg lifetime
        
        # Profit (based on final_subtotal, not total which includes shipping/fees)
        total_costs = self.material_cost + self.electricity_cost + self.depreciation_cost
        self.profit = final_subtotal - total_costs
        
        self.updated_date = now_str()
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'order_number': self.order_number,
            'customer_id': self.customer_id,
            'customer_name': self.customer_name,
            'customer_phone': self.customer_phone,
            'status': self.status,
            'items': [item.to_dict() for item in self.items],
            'subtotal': self.subtotal,
            'actual_total': self.actual_total,
            'discount_percent': self.discount_percent,
            'discount_amount': self.discount_amount,
            'order_discount_percent': self.order_discount_percent,
            'order_discount_amount': self.order_discount_amount,
            'shipping_cost': self.shipping_cost,
            'total': self.total,
            'payment_method': self.payment_method,
            'payment_fee': self.payment_fee,
            'material_cost': self.material_cost,
            'electricity_cost': self.electricity_cost,
            'depreciation_cost': self.depreciation_cost,
            'profit': self.profit,
            'created_date': self.created_date,
            'updated_date': self.updated_date,
            'delivered_date': self.delivered_date,
            'deleted_date': self.deleted_date,
            'notes': self.notes,
            'is_deleted': self.is_deleted,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Order':
        order = cls()
        order.id = data.get('id', generate_id())
        order.order_number = data.get('order_number', 0)
        order.customer_id = data.get('customer_id', '')
        order.customer_name = data.get('customer_name', '')
        order.customer_phone = data.get('customer_phone', '')
        order.status = data.get('status', OrderStatus.DRAFT.value)
        order.items = [PrintItem.from_dict(i) for i in data.get('items', [])]
        order.subtotal = data.get('subtotal', 0)
        order.actual_total = data.get('actual_total', 0)
        order.discount_percent = data.get('discount_percent', 0)
        order.discount_amount = data.get('discount_amount', 0)
        order.order_discount_percent = data.get('order_discount_percent', 0)
        order.order_discount_amount = data.get('order_discount_amount', 0)
        order.shipping_cost = data.get('shipping_cost', 0)
        order.total = data.get('total', 0)
        order.payment_method = data.get('payment_method', PaymentMethod.CASH.value)
        order.payment_fee = data.get('payment_fee', 0)
        order.material_cost = data.get('material_cost', 0)
        order.electricity_cost = data.get('electricity_cost', 0)
        order.depreciation_cost = data.get('depreciation_cost', 0)
        order.profit = data.get('profit', 0)
        order.created_date = data.get('created_date', now_str())
        order.updated_date = data.get('updated_date', now_str())
        order.delivered_date = data.get('delivered_date', '')
        order.deleted_date = data.get('deleted_date', '')
        order.notes = data.get('notes', '')
        order.is_deleted = data.get('is_deleted', False)
        return order


@dataclass
class Statistics:
    """Business statistics"""
    # Orders
    total_orders: int = 0
    completed_orders: int = 0
    
    # Revenue
    total_revenue: float = 0
    total_shipping: float = 0
    total_payment_fees: float = 0
    
    # Costs
    total_material_cost: float = 0
    total_electricity_cost: float = 0
    total_depreciation_cost: float = 0
    total_nozzle_cost: float = 0
    
    # Profit
    total_profit: float = 0
    
    # Production
    total_weight_printed: float = 0
    total_time_printed: int = 0
    total_filament_used: float = 0
    
    # Inventory
    active_spools: int = 0
    remaining_filament: float = 0
    
    # Customers
    total_customers: int = 0
    
    # Printers
    total_printers: int = 0
    
    @property
    def profit_margin(self) -> float:
        if self.total_revenue <= 0:
            return 0
        return (self.total_profit / self.total_revenue) * 100
    
    @property
    def total_costs(self) -> float:
        return (self.total_material_cost + self.total_electricity_cost + 
                self.total_depreciation_cost + self.total_nozzle_cost)
