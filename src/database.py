"""
Database manager for Abaad 3D Print Manager v4.0 (ERP Edition)
JSON-based persistent storage with pending filament, history tracking
"""
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any

from .models import (
    Order, PrintItem, FilamentSpool, Customer, Statistics, Printer,
    FilamentHistory, OrderStatus, SpoolCategory, SpoolStatus, PaymentMethod,
    now_str, DEFAULT_COST_PER_GRAM, SPOOL_PRICE_FIXED, TRASH_THRESHOLD_GRAMS
)


class DatabaseManager:
    """JSON-based database with pending filament and history tracking"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.db_path = Path("data/abaad_v4.db.json")
        self.data = {
            'orders': {},
            'customers': {},
            'spools': {},
            'printers': {},
            'filament_history': {},  # NEW: Archive for trashed spools
            'deleted_orders': {},
            'colors': ["Black", "Light Blue", "Silver", "White", "Red", "Beige", "Purple"],
            'settings': {
                'company_name': 'Abaad',
                'company_phone': '01070750477',
                'company_address': 'Ismailia, Egypt',
                'default_rate_per_gram': 4.0,
                'next_order_number': 1,
                'deposit_percent': 50,  # Default deposit percentage
                'quote_validity_days': 7,
            },
        }
        self._load()
        self._ensure_default_printer()
        self._migrate_v3_data()
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
                print(f"✓ Database loaded: {len(self.data['orders'])} orders, {len(self.data['spools'])} spools")
            except Exception as e:
                print(f"✗ Error loading database: {e}")
    
    def _migrate_v3_data(self):
        """Migrate v3 data if exists"""
        v3_path = Path("data/abaad_print_manager.db.json")
        if v3_path.exists() and not self.data['orders']:
            try:
                with open(v3_path, 'r', encoding='utf-8') as f:
                    v3_data = json.load(f)
                    # Migrate orders, customers, spools, printers
                    for key in ['orders', 'customers', 'spools', 'printers', 'colors']:
                        if key in v3_data and v3_data[key]:
                            self.data[key].update(v3_data[key])
                    if 'settings' in v3_data:
                        self.data['settings'].update(v3_data['settings'])
                    self._save()
                    print(f"✓ Migrated v3 data: {len(self.data['orders'])} orders")
            except Exception as e:
                print(f"✗ Migration error: {e}")
    
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
            print(f"✗ Error saving database: {e}")
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
        return [s for s in self.get_all_spools() 
                if s.is_active and s.current_weight_grams > 0 and s.status != SpoolStatus.TRASH.value]
    
    def get_spools_by_color(self, color: str) -> List[FilamentSpool]:
        """Get active spools filtered by color, sorted by available weight"""
        spools = [s for s in self.get_active_spools() if s.color == color]
        return sorted(spools, key=lambda s: s.available_weight_grams, reverse=True)
    
    def get_low_spools(self) -> List[FilamentSpool]:
        """Get spools that should show trash button"""
        return [s for s in self.get_active_spools() if s.should_show_trash_button]
    
    # Pending filament operations
    def reserve_filament(self, spool_id: str, grams: float) -> bool:
        """Reserve filament (pending) without deducting"""
        spool = self.get_spool(spool_id)
        if spool and spool.reserve_filament(grams):
            return self.save_spool(spool)
        return False
    
    def release_pending_filament(self, spool_id: str, grams: float) -> bool:
        """Release pending filament reservation"""
        spool = self.get_spool(spool_id)
        if spool and spool.release_pending(grams):
            return self.save_spool(spool)
        return False
    
    def commit_filament(self, spool_id: str, grams: float) -> bool:
        """Commit pending filament (actually deduct)"""
        spool = self.get_spool(spool_id)
        if spool and spool.commit_filament(grams):
            return self.save_spool(spool)
        return False
    
    def use_filament(self, spool_id: str, grams: float) -> bool:
        """Direct deduction (backward compatibility)"""
        return self.commit_filament(spool_id, grams)
    
    def move_spool_to_trash(self, spool_id: str, reason: str = "trash") -> bool:
        """Move spool to trash and create history record"""
        spool = self.get_spool(spool_id)
        if not spool:
            return False
        
        # Create history record
        history = FilamentHistory(
            spool_id=spool.id,
            spool_name=spool.display_name,
            color=spool.color,
            initial_weight=spool.initial_weight_grams,
            used_weight=spool.used_weight_grams,
            remaining_weight=spool.current_weight_grams,
            waste_weight=spool.current_weight_grams,  # Remaining = waste
            reason=reason
        )
        self.data['filament_history'][history.id] = history.to_dict()
        
        # Update spool
        spool.move_to_trash()
        self.save_spool(spool)
        
        return self._save()
    
    def delete_spool(self, spool_id: str) -> bool:
        if spool_id in self.data['spools']:
            del self.data['spools'][spool_id]
            return self._save()
        return False
    
    # === FILAMENT HISTORY ===
    def get_filament_history(self) -> List[FilamentHistory]:
        return [FilamentHistory.from_dict(d) for d in self.data['filament_history'].values()]
    
    def get_total_waste(self) -> float:
        """Get total waste from all trashed spools"""
        return sum(h.waste_weight for h in self.get_filament_history())
    
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
    
    def save_order(self, order: Order, confirm_filament: bool = False) -> bool:
        """
        Save order with optional filament confirmation.
        
        Args:
            order: The order to save
            confirm_filament: If True, commit pending filament when status changes to confirmed
        """
        if order.order_number == 0:
            order.order_number = self.get_next_order_number()
        
        order.updated_date = now_str()
        order.calculate_totals()
        
        # Handle filament commitment on confirmation
        if confirm_filament and order.is_confirmed:
            for item in order.items:
                if item.filament_pending and not item.filament_deducted and item.spool_id:
                    # Commit the pending filament
                    if self.commit_filament(item.spool_id, item.total_weight):
                        item.filament_pending = False
                        item.filament_deducted = True
            order.confirmed_date = now_str()
        
        # Handle order cancellation - return filament
        if order.status == OrderStatus.CANCELLED.value:
            for item in order.items:
                if item.filament_pending and item.spool_id:
                    # Release pending filament
                    self.release_pending_filament(item.spool_id, item.total_weight)
                    item.filament_pending = False
        
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
    
    def get_orders_by_status(self, status: str) -> List[Order]:
        return [o for o in self.get_all_orders() if o.status == status]
    
    def get_rd_orders(self) -> List[Order]:
        """Get all R&D project orders"""
        return [o for o in self.get_all_orders() if o.is_rd_project]
    
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
    
    def delete_order(self, order_id: str, soft: bool = True, return_filament: bool = True) -> bool:
        """
        Delete order with optional filament return.
        
        Args:
            order_id: Order to delete
            soft: If True, mark as deleted. If False, permanently delete.
            return_filament: If True, return reserved/deducted filament to spools
        """
        order = self.get_order(order_id)
        if not order:
            return False
        
        # Return filament if requested
        if return_filament:
            for item in order.items:
                if item.spool_id:
                    spool = self.get_spool(item.spool_id)
                    if spool:
                        # Return the filament
                        if item.filament_deducted:
                            spool.current_weight_grams += item.total_weight
                        elif item.filament_pending:
                            spool.pending_weight_grams -= item.total_weight
                        self.save_spool(spool)
        
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
            data['total_spent'] = sum(o.total for o in orders if o.status != OrderStatus.CANCELLED.value)
    
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
        stats.completed_orders = len([o for o in orders if o.status == OrderStatus.DELIVERED.value])
        stats.rd_orders = len([o for o in orders if o.is_rd_project])
        stats.total_revenue = sum(o.total for o in orders if o.status != OrderStatus.CANCELLED.value)
        stats.total_shipping = sum(o.shipping_cost for o in orders if o.status != OrderStatus.CANCELLED.value)
        stats.total_payment_fees = sum(o.payment_fee for o in orders if o.status != OrderStatus.CANCELLED.value)
        stats.total_rounding_loss = sum(o.rounding_loss for o in orders if o.status != OrderStatus.CANCELLED.value)
        stats.total_material_cost = sum(o.material_cost for o in orders if o.status != OrderStatus.CANCELLED.value)
        stats.total_electricity_cost = sum(o.electricity_cost for o in orders if o.status != OrderStatus.CANCELLED.value)
        stats.total_depreciation_cost = sum(o.depreciation_cost for o in orders if o.status != OrderStatus.CANCELLED.value)
        stats.total_profit = sum(o.profit for o in orders if o.status != OrderStatus.CANCELLED.value)
        stats.total_weight_printed = sum(o.total_weight for o in orders if o.status in [OrderStatus.DELIVERED.value, OrderStatus.READY.value])
        stats.total_time_printed = sum(o.total_time for o in orders if o.status in [OrderStatus.DELIVERED.value, OrderStatus.READY.value])
        stats.total_tolerance_discounts = sum(o.tolerance_discount_total for o in orders if o.status != OrderStatus.CANCELLED.value)
        
        spools = self.get_all_spools()
        stats.total_filament_used = sum(s.used_weight_grams for s in spools)
        stats.active_spools = len([s for s in spools if s.is_active and s.current_weight_grams > 50])
        stats.remaining_filament = sum(s.current_weight_grams for s in spools if s.is_active)
        stats.pending_filament = sum(s.pending_weight_grams for s in spools)
        stats.total_filament_waste = self.get_total_waste()
        
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
        backup_path = backup_dir / f"backup_v4_{timestamp}.json"
        shutil.copy2(self.db_path, backup_path)
        return str(backup_path)
    
    def export_to_csv(self, export_dir: str = "exports") -> Dict[str, str]:
        """Export data to CSV files for external analysis"""
        import csv
        export_path = Path(export_dir)
        export_path.mkdir(exist_ok=True)
        
        files = {}
        
        # Export orders
        orders_file = export_path / "orders.csv"
        with open(orders_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Order#', 'Customer', 'Status', 'Total', 'Profit', 'Date', 'R&D'])
            for o in self.get_all_orders():
                writer.writerow([o.order_number, o.customer_name, o.status, o.total, o.profit, o.created_date, o.is_rd_project])
        files['orders'] = str(orders_file)
        
        # Export customers
        customers_file = export_path / "customers.csv"
        with open(customers_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Name', 'Phone', 'Orders', 'Total Spent', 'Discount'])
            for c in self.get_all_customers():
                writer.writerow([c.name, c.phone, c.total_orders, c.total_spent, c.discount_percent])
        files['customers'] = str(customers_file)
        
        return files


# Singleton
_db_instance = None

def get_database() -> DatabaseManager:
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager()
    return _db_instance
