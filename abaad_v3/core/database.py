"""
Database manager for Abaad 3D Print Manager v3
JSON-based persistent storage with auto-filament deduction
"""
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any

from .models import (
    Order, PrintItem, FilamentSpool, Customer, Statistics, Printer,
    OrderStatus, SpoolCategory, PaymentMethod, now_str,
    DEFAULT_COST_PER_GRAM, SPOOL_PRICE_FIXED
)


class DatabaseManager:
    """JSON-based database with auto-save and spool management"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.db_path = Path("data/abaad_print_manager.db.json")
        self.data = {
            'orders': {},
            'customers': {},
            'spools': {},
            'printers': {},
            'deleted_orders': {},
            'colors': ["Black", "Light Blue", "Silver", "White", "Red", "Beige", "Purple"],
            'settings': {
                'company_name': 'Abaad',
                'company_phone': '01070750477',
                'company_address': 'Ismailia, Egypt',
                'default_rate_per_gram': 4.0,
                'next_order_number': 1,
            },
        }
        self._load()
        self._ensure_default_printer()
        self._initialized = True
    
    def _load(self):
        """Load database from file"""
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    for key in self.data:
                        if key in loaded:
                            if isinstance(self.data[key], dict):
                                self.data[key].update(loaded[key])
                            else:
                                self.data[key] = loaded[key]
                print(f"Database loaded: {len(self.data['orders'])} orders")
            except Exception as e:
                print(f"Error loading database: {e}")
    
    def _save(self) -> bool:
        """Save database to file"""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = self.db_path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            temp_path.replace(self.db_path)
            return True
        except Exception as e:
            print(f"Error saving database: {e}")
            return False
    
    def _ensure_default_printer(self):
        """Ensure default printer exists"""
        if not self.data['printers']:
            default_printer = Printer(
                id='printer_default',
                name='HIVE 0.1',
                model='Creality Ender-3 Max'
            )
            self.data['printers']['printer_default'] = default_printer.to_dict()
            self._save()
    
    # === COLORS ===
    def get_colors(self) -> List[str]:
        return self.data.get('colors', [])
    
    def add_color(self, color: str) -> bool:
        if color and color not in self.data['colors']:
            self.data['colors'].append(color)
            return self._save()
        return False
    
    # === SPOOLS ===
    def save_spool(self, spool: FilamentSpool) -> bool:
        self.data['spools'][spool.id] = spool.to_dict()
        return self._save()
    
    def get_spool(self, spool_id: str) -> Optional[FilamentSpool]:
        data = self.data['spools'].get(spool_id)
        if data:
            return FilamentSpool.from_dict(data)
        return None
    
    def get_all_spools(self) -> List[FilamentSpool]:
        return [FilamentSpool.from_dict(d) for d in self.data['spools'].values()]
    
    def get_active_spools(self) -> List[FilamentSpool]:
        return [s for s in self.get_all_spools() if s.is_active and s.current_weight_grams > 0]
    
    def get_spools_by_color(self, color: str) -> List[FilamentSpool]:
        """Get active spools filtered by color"""
        return [s for s in self.get_active_spools() if s.color == color]
    
    def use_filament(self, spool_id: str, grams: float) -> bool:
        """Deduct filament from spool immediately"""
        spool = self.get_spool(spool_id)
        if spool and spool.use_filament(grams):
            return self.save_spool(spool)
        return False
    
    def delete_spool(self, spool_id: str) -> bool:
        if spool_id in self.data['spools']:
            del self.data['spools'][spool_id]
            return self._save()
        return False
    
    # === PRINTERS ===
    def save_printer(self, printer: Printer) -> bool:
        self.data['printers'][printer.id] = printer.to_dict()
        return self._save()
    
    def get_printer(self, printer_id: str) -> Optional[Printer]:
        data = self.data['printers'].get(printer_id)
        if data:
            return Printer.from_dict(data)
        return None
    
    def get_all_printers(self) -> List[Printer]:
        return [Printer.from_dict(d) for d in self.data['printers'].values()]
    
    def get_active_printers(self) -> List[Printer]:
        return [p for p in self.get_all_printers() if p.is_active]
    
    def get_default_printer(self) -> Optional[Printer]:
        printers = self.get_active_printers()
        return printers[0] if printers else None
    
    def add_print_to_printer(self, printer_id: str, grams: float, minutes: int) -> bool:
        """Record print job on printer"""
        printer = self.get_printer(printer_id)
        if printer:
            printer.add_print(grams, minutes)
            return self.save_printer(printer)
        return False
    
    # === ORDERS ===
    def get_next_order_number(self) -> int:
        num = self.data['settings'].get('next_order_number', 1)
        self.data['settings']['next_order_number'] = num + 1
        self._save()
        return num
    
    def save_order(self, order: Order) -> bool:
        if order.order_number == 0:
            order.order_number = self.get_next_order_number()
        
        order.updated_date = now_str()
        order.calculate_totals()
        
        self.data['orders'][order.id] = order.to_dict()
        
        if order.customer_id:
            self._update_customer_stats(order.customer_id)
        
        return self._save()
    
    def get_order(self, order_id: str) -> Optional[Order]:
        data = self.data['orders'].get(order_id)
        if data:
            return Order.from_dict(data)
        return None
    
    def get_all_orders(self) -> List[Order]:
        orders = [Order.from_dict(d) for d in self.data['orders'].values() 
                  if not d.get('is_deleted', False)]
        return sorted(orders, key=lambda o: o.created_date, reverse=True)
    
    def search_orders(self, query: str) -> List[Order]:
        query = query.lower().strip()
        results = []
        for data in self.data['orders'].values():
            if data.get('is_deleted', False):
                continue
            order = Order.from_dict(data)
            if (query in order.customer_name.lower() or
                query in order.customer_phone or
                query in str(order.order_number)):
                results.append(order)
        return sorted(results, key=lambda o: o.created_date, reverse=True)
    
    def delete_order(self, order_id: str, soft: bool = True) -> bool:
        if order_id in self.data['orders']:
            if soft:
                self.data['orders'][order_id]['is_deleted'] = True
                self.data['orders'][order_id]['deleted_date'] = now_str()
            else:
                del self.data['orders'][order_id]
            return self._save()
        return False
    
    # === CUSTOMERS ===
    def save_customer(self, customer: Customer) -> bool:
        self.data['customers'][customer.id] = customer.to_dict()
        return self._save()
    
    def get_customer(self, customer_id: str) -> Optional[Customer]:
        data = self.data['customers'].get(customer_id)
        if data:
            return Customer.from_dict(data)
        return None
    
    def get_all_customers(self) -> List[Customer]:
        return [Customer.from_dict(d) for d in self.data['customers'].values()]
    
    def search_customers(self, query: str) -> List[Customer]:
        query = query.lower().strip()
        results = []
        for data in self.data['customers'].values():
            customer = Customer.from_dict(data)
            if query in customer.name.lower() or query in customer.phone:
                results.append(customer)
        return results
    
    def find_or_create_customer(self, name: str, phone: str) -> Customer:
        if phone:
            for data in self.data['customers'].values():
                if data.get('phone') == phone:
                    return Customer.from_dict(data)
        if name:
            name_lower = name.lower().strip()
            for data in self.data['customers'].values():
                if data.get('name', '').lower().strip() == name_lower:
                    return Customer.from_dict(data)
        customer = Customer(name=name, phone=phone)
        self.save_customer(customer)
        return customer
    
    def get_customer_orders(self, customer_id: str) -> List[Order]:
        orders = []
        for data in self.data['orders'].values():
            if data.get('customer_id') == customer_id and not data.get('is_deleted', False):
                orders.append(Order.from_dict(data))
        return sorted(orders, key=lambda o: o.created_date, reverse=True)
    
    def _update_customer_stats(self, customer_id: str):
        orders = self.get_customer_orders(customer_id)
        data = self.data['customers'].get(customer_id)
        if data:
            data['total_orders'] = len(orders)
            data['total_spent'] = sum(o.total for o in orders if o.status != 'Cancelled')
    
    def delete_customer(self, customer_id: str) -> bool:
        if customer_id in self.data['customers']:
            del self.data['customers'][customer_id]
            return self._save()
        return False
    
    # === STATISTICS ===
    def get_statistics(self) -> Statistics:
        stats = Statistics()
        
        orders = self.get_all_orders()
        stats.total_orders = len(orders)
        stats.completed_orders = len([o for o in orders if o.status == 'Delivered'])
        stats.total_revenue = sum(o.total for o in orders if o.status != 'Cancelled')
        stats.total_shipping = sum(o.shipping_cost for o in orders if o.status != 'Cancelled')
        stats.total_payment_fees = sum(o.payment_fee for o in orders if o.status != 'Cancelled')
        stats.total_material_cost = sum(o.material_cost for o in orders if o.status != 'Cancelled')
        stats.total_electricity_cost = sum(o.electricity_cost for o in orders if o.status != 'Cancelled')
        stats.total_depreciation_cost = sum(o.depreciation_cost for o in orders if o.status != 'Cancelled')
        stats.total_profit = sum(o.profit for o in orders if o.status != 'Cancelled')
        stats.total_weight_printed = sum(o.total_weight for o in orders if o.status in ['Delivered', 'Ready'])
        stats.total_time_printed = sum(o.total_time for o in orders if o.status in ['Delivered', 'Ready'])
        
        spools = self.get_all_spools()
        stats.total_filament_used = sum(s.used_weight_grams for s in spools)
        stats.active_spools = len([s for s in spools if s.is_active and s.current_weight_grams > 50])
        stats.remaining_filament = sum(s.current_weight_grams for s in spools if s.is_active)
        
        printers = self.get_all_printers()
        stats.total_printers = len(printers)
        stats.total_nozzle_cost = sum(p.total_nozzle_cost for p in printers)
        
        stats.total_customers = len(self.data['customers'])
        
        return stats
    
    # === SETTINGS ===
    def get_settings(self) -> dict:
        return self.data['settings'].copy()
    
    def save_settings(self, settings: dict) -> bool:
        self.data['settings'].update(settings)
        return self._save()
    
    # === BACKUP ===
    def backup_database(self) -> str:
        backup_dir = self.db_path.parent / "backups"
        backup_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"backup_{timestamp}.json"
        shutil.copy2(self.db_path, backup_path)
        return str(backup_path)


# Singleton
_db_instance = None

def get_database() -> DatabaseManager:
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager()
    return _db_instance
