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
    PrintFailure, Expense, FailureReason, ExpenseCategory, PaymentSource,
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
            'filament_history': {},  # Archive for trashed spools
            'failures': {},  # NEW: Print failures tracking
            'expenses': {},  # NEW: Business expenses tracking
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
    
    # === SPOOL LOAN/PAYMENT TRACKING ===
    def update_spool_payment(self, spool_id: str, payment_source: str, 
                             loan_provider: str = "", loan_paid: bool = False,
                             loan_paid_amount: float = 0.0) -> bool:
        """Update spool payment/loan information"""
        spool = self.get_spool(spool_id)
        if not spool:
            return False
        
        spool.payment_source = payment_source
        spool.loan_provider = loan_provider
        spool.loan_paid = loan_paid
        if loan_paid and not spool.loan_paid_date:
            spool.loan_paid_date = now_str()
        spool.loan_paid_amount = loan_paid_amount or spool.purchase_price_egp
        return self.save_spool(spool)
    
    def mark_loan_paid(self, spool_id: str, amount: float = 0.0) -> bool:
        """Mark a spool loan as paid"""
        spool = self.get_spool(spool_id)
        if not spool or not spool.is_loan:
            return False
        
        spool.loan_paid = True
        spool.loan_paid_date = now_str()
        spool.loan_paid_amount = amount or spool.purchase_price_egp
        return self.save_spool(spool)
    
    def get_loan_stats(self) -> Dict[str, Any]:
        """Get loan statistics for all spools"""
        spools = self.get_all_spools()
        loan_spools = [s for s in spools if s.is_loan]
        
        total_loan_amount = sum(s.purchase_price_egp for s in loan_spools)
        paid_loans = [s for s in loan_spools if s.loan_paid]
        unpaid_loans = [s for s in loan_spools if not s.loan_paid]
        
        return {
            'total_loan_spools': len(loan_spools),
            'total_loan_amount': total_loan_amount,
            'paid_loan_count': len(paid_loans),
            'paid_loan_amount': sum(s.loan_paid_amount for s in paid_loans),
            'unpaid_loan_count': len(unpaid_loans),
            'unpaid_loan_amount': sum(s.purchase_price_egp for s in unpaid_loans),
            'loan_providers': list(set(s.loan_provider for s in loan_spools if s.loan_provider)),
            'paid_loans': paid_loans,
            'unpaid_loans': unpaid_loans,
        }
    
    def get_spool_cost_for_profit(self) -> Dict[str, Any]:
        """Calculate spool costs that affect profit"""
        spools = self.get_all_spools()
        
        # Costs that affect profit:
        # 1. Spools paid from profit (full price)
        # 2. Loans that have been repaid (repayment amount)
        
        profit_cost = 0.0
        pocket_cost = 0.0
        loan_repaid_cost = 0.0
        pending_loan_cost = 0.0
        
        details = []
        
        for spool in spools:
            if spool.category == SpoolCategory.REMAINING.value:
                continue  # Remaining spools have no cost
            
            if spool.payment_source == PaymentSource.PROFIT.value:
                profit_cost += spool.purchase_price_egp
                details.append({
                    'spool': spool.display_name,
                    'amount': spool.purchase_price_egp,
                    'source': 'Profit',
                    'affects_profit': True
                })
            elif spool.payment_source == PaymentSource.POCKET.value:
                pocket_cost += spool.purchase_price_egp
                details.append({
                    'spool': spool.display_name,
                    'amount': spool.purchase_price_egp,
                    'source': 'Pocket',
                    'affects_profit': False
                })
            elif spool.payment_source == PaymentSource.LOAN.value:
                if spool.loan_paid:
                    loan_repaid_cost += spool.loan_paid_amount
                    details.append({
                        'spool': spool.display_name,
                        'amount': spool.loan_paid_amount,
                        'source': f'Loan (PAID to {spool.loan_provider})',
                        'affects_profit': True
                    })
                else:
                    pending_loan_cost += spool.purchase_price_egp
                    details.append({
                        'spool': spool.display_name,
                        'amount': spool.purchase_price_egp,
                        'source': f'Loan from {spool.loan_provider} (UNPAID)',
                        'affects_profit': False
                    })
        
        return {
            'profit_cost': profit_cost,
            'pocket_cost': pocket_cost,
            'loan_repaid_cost': loan_repaid_cost,
            'pending_loan_cost': pending_loan_cost,
            'total_affects_profit': profit_cost + loan_repaid_cost,
            'details': details
        }
    
    def record_spool_consumption(self, spool_id: str, grams: float, 
                                  order_number: int = 0, item_name: str = "") -> bool:
        """Record filament consumption for tracking"""
        spool = self.get_spool(spool_id)
        if not spool:
            return False
        
        spool.add_consumption(grams, order_number, item_name)
        return self.save_spool(spool)
    
    # === FILAMENT HISTORY ===
    def get_filament_history(self) -> List[FilamentHistory]:
        return [FilamentHistory.from_dict(d) for d in self.data['filament_history'].values()]
    
    def get_total_waste(self) -> float:
        """Get total waste from all trashed spools"""
        return sum(h.waste_weight for h in self.get_filament_history())
    
    # === PRINT FAILURES ===
    def save_failure(self, failure: PrintFailure) -> bool:
        """Save a print failure record"""
        failure.calculate_costs()
        self.data['failures'][failure.id] = failure.to_dict()
        
        # Deduct wasted filament from spool if specified
        if failure.spool_id and failure.filament_wasted_grams > 0:
            spool = self.get_spool(failure.spool_id)
            if spool:
                spool.use_filament(failure.filament_wasted_grams)
                self.save_spool(spool)
        
        return self._save()
    
    def get_failure(self, failure_id: str) -> Optional[PrintFailure]:
        data = self.data.get('failures', {}).get(failure_id)
        if data:
            return PrintFailure.from_dict(data)
        return None
    
    def get_all_failures(self) -> List[PrintFailure]:
        """Get all print failures, sorted by date (newest first)"""
        failures = [PrintFailure.from_dict(d) for d in self.data.get('failures', {}).values()]
        return sorted(failures, key=lambda f: f.date, reverse=True)
    
    def get_failures_by_reason(self, reason: str) -> List[PrintFailure]:
        """Get failures filtered by reason"""
        return [f for f in self.get_all_failures() if f.reason == reason]
    
    def get_failure_stats(self) -> Dict[str, Any]:
        """Get failure statistics"""
        failures = self.get_all_failures()
        stats = {
            'total_failures': len(failures),
            'total_cost': sum(f.total_loss for f in failures),
            'total_filament_wasted': sum(f.filament_wasted_grams for f in failures),
            'total_time_wasted': sum(f.time_wasted_minutes for f in failures),
            'by_reason': {},
        }
        # Count by reason
        for reason in FailureReason:
            count = len([f for f in failures if f.reason == reason.value])
            if count > 0:
                stats['by_reason'][reason.value] = count
        return stats
    
    def delete_failure(self, failure_id: str) -> bool:
        if failure_id in self.data.get('failures', {}):
            del self.data['failures'][failure_id]
            return self._save()
        return False
    
    # === EXPENSES ===
    def save_expense(self, expense: Expense) -> bool:
        """Save a business expense"""
        expense.calculate_total()
        self.data['expenses'][expense.id] = expense.to_dict()
        return self._save()
    
    def get_expense(self, expense_id: str) -> Optional[Expense]:
        data = self.data.get('expenses', {}).get(expense_id)
        if data:
            return Expense.from_dict(data)
        return None
    
    def get_all_expenses(self) -> List[Expense]:
        """Get all expenses, sorted by date (newest first)"""
        expenses = [Expense.from_dict(d) for d in self.data.get('expenses', {}).values()]
        return sorted(expenses, key=lambda e: e.date, reverse=True)
    
    def get_expenses_by_category(self, category: str) -> List[Expense]:
        """Get expenses filtered by category"""
        return [e for e in self.get_all_expenses() if e.category == category]
    
    def get_expense_stats(self) -> Dict[str, Any]:
        """Get expense statistics"""
        expenses = self.get_all_expenses()
        
        # Separate filament purchases from regular expenses
        filament_expenses = [e for e in expenses if e.category == ExpenseCategory.FILAMENT.value]
        other_expenses = [e for e in expenses if e.category != ExpenseCategory.FILAMENT.value]
        
        stats = {
            'total_expenses': sum(e.total_cost for e in other_expenses),  # Exclude filament
            'total_filament_purchases': sum(e.total_cost for e in filament_expenses),
            'expense_count': len(other_expenses),
            'filament_count': len(filament_expenses),
            'by_category': {},
        }
        # Sum by category
        for category in ExpenseCategory:
            total = sum(e.total_cost for e in expenses if e.category == category.value)
            if total > 0:
                stats['by_category'][category.value] = total
        return stats
    
    def get_filament_expenses(self) -> List[Expense]:
        """Get all filament purchase expenses"""
        return self.get_expenses_by_category(ExpenseCategory.FILAMENT.value)
    
    def get_financial_summary(self) -> Dict[str, Any]:
        """Get comprehensive financial summary"""
        stats = self.get_statistics()
        profit_breakdown = self.get_profit_breakdown()
        expense_stats = self.get_expense_stats()
        loan_stats = self.get_loan_stats()
        
        # Calculate true profit
        revenue = stats.total_revenue
        
        # Operating costs (per order)
        operating_costs = (
            stats.total_material_cost +
            stats.total_electricity_cost +
            stats.total_depreciation_cost +
            stats.total_payment_fees +
            stats.total_rounding_loss
        )
        
        # Gross profit (before failures, expenses, spool purchases)
        gross_profit = revenue - operating_costs
        
        # Deductions
        failure_cost = stats.total_failure_cost
        other_expenses = expense_stats['total_expenses']  # Excludes filament
        spool_purchases = profit_breakdown['spool_purchase_total']
        
        # Net profit
        net_profit = gross_profit - failure_cost - other_expenses - spool_purchases
        
        return {
            'revenue': revenue,
            'operating_costs': operating_costs,
            'gross_profit': gross_profit,
            'failure_cost': failure_cost,
            'other_expenses': other_expenses,
            'spool_purchases': spool_purchases,
            'net_profit': net_profit,
            'profit_margin': (net_profit / revenue * 100) if revenue > 0 else 0,
            'pending_loans': loan_stats['unpaid_loan_amount'],
            # Filament details
            'filament_material_cost': stats.total_material_cost,
            'filament_spool_purchases': spool_purchases,
            'filament_total_cost': stats.total_material_cost + spool_purchases,
        }
    
    def delete_expense(self, expense_id: str) -> bool:
        if expense_id in self.data.get('expenses', {}):
            del self.data['expenses'][expense_id]
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
                # Also store in deleted_orders for easy access
                self.data['deleted_orders'][order_id] = self.data['orders'][order_id].copy()
            else:
                del self.data['orders'][order_id]
            return self._save()
        return False
    
    def get_deleted_orders(self) -> List[Order]:
        """Get all soft-deleted orders"""
        deleted = []
        for data in self.data['orders'].values():
            if data.get('is_deleted', False):
                deleted.append(Order.from_dict(data))
        # Also check deleted_orders dict
        for data in self.data.get('deleted_orders', {}).values():
            order = Order.from_dict(data)
            if order.id not in [o.id for o in deleted]:
                deleted.append(order)
        return sorted(deleted, key=lambda o: o.deleted_date or o.created_date, reverse=True)
    
    def restore_order(self, order_id: str) -> bool:
        """Restore a deleted order"""
        if order_id in self.data['orders']:
            self.data['orders'][order_id]['is_deleted'] = False
            self.data['orders'][order_id]['deleted_date'] = ''
            # Remove from deleted_orders if exists
            if order_id in self.data.get('deleted_orders', {}):
                del self.data['deleted_orders'][order_id]
            return self._save()
        # Check deleted_orders dict
        if order_id in self.data.get('deleted_orders', {}):
            order_data = self.data['deleted_orders'][order_id]
            order_data['is_deleted'] = False
            order_data['deleted_date'] = ''
            self.data['orders'][order_id] = order_data
            del self.data['deleted_orders'][order_id]
            return self._save()
        return False
    
    def permanently_delete_order(self, order_id: str) -> bool:
        """Permanently delete an order"""
        deleted = False
        if order_id in self.data['orders']:
            del self.data['orders'][order_id]
            deleted = True
        if order_id in self.data.get('deleted_orders', {}):
            del self.data['deleted_orders'][order_id]
            deleted = True
        if deleted:
            return self._save()
        return False
    
    def fix_order_numbering(self) -> bool:
        """Fix order numbering to start from 1 if there's no order #1"""
        orders = self.get_all_orders()
        order_numbers = [o.order_number for o in orders]
        
        if 1 not in order_numbers and order_numbers:
            # Find the minimum order number
            min_num = min(order_numbers)
            if min_num > 1:
                # Shift all order numbers down
                diff = min_num - 1
                for order_id, order_data in self.data['orders'].items():
                    if not order_data.get('is_deleted', False):
                        order_data['order_number'] = order_data['order_number'] - diff
                # Update next_order_number
                self.data['settings']['next_order_number'] = max(order_numbers) - diff + 1
                return self._save()
        return False
    
    def get_monthly_stats(self) -> Dict[str, Any]:
        """Get monthly statistics for charts"""
        from collections import defaultdict
        from datetime import datetime
        
        monthly_revenue = defaultdict(float)
        monthly_profit = defaultdict(float)
        monthly_orders = defaultdict(int)
        monthly_filament = defaultdict(float)
        
        for data in self.data['orders'].values():
            if data.get('is_deleted', False):
                continue
            order = Order.from_dict(data)
            if order.status == OrderStatus.CANCELLED.value:
                continue
            
            # Extract month-year from date
            try:
                date = datetime.strptime(order.created_date.split()[0], '%Y-%m-%d')
                month_key = date.strftime('%Y-%m')
                
                monthly_revenue[month_key] += order.total
                monthly_profit[month_key] += order.profit
                monthly_orders[month_key] += 1
                monthly_filament[month_key] += order.total_weight
            except:
                pass
        
        # Sort by date
        sorted_months = sorted(monthly_revenue.keys())
        
        return {
            'months': sorted_months,
            'revenue': [monthly_revenue[m] for m in sorted_months],
            'profit': [monthly_profit[m] for m in sorted_months],
            'orders': [monthly_orders[m] for m in sorted_months],
            'filament': [monthly_filament[m] for m in sorted_months],
        }
    
    def get_color_usage_stats(self) -> Dict[str, float]:
        """Get filament usage by color"""
        color_usage = {}
        for spool in self.get_all_spools():
            color = spool.color
            if color not in color_usage:
                color_usage[color] = 0
            color_usage[color] += spool.used_weight_grams
        return color_usage
    
    def get_profit_breakdown(self) -> Dict[str, Any]:
        """Get detailed profit breakdown including spool purchase costs"""
        stats = self.get_statistics()
        
        # Calculate filament cost from orders (per-gram cost)
        filament_cost = stats.total_material_cost
        
        # Get spool purchase costs that affect profit
        spool_costs = self.get_spool_cost_for_profit()
        
        # Get loan stats
        loan_stats = self.get_loan_stats()
        
        # Calculate TRUE profit: Revenue - All Costs - Spool Purchases - Loan Repayments
        total_costs = (
            filament_cost +
            stats.total_electricity_cost +
            stats.total_depreciation_cost +
            stats.total_payment_fees +
            stats.total_rounding_loss +
            stats.total_failure_cost +
            stats.total_expenses
        )
        
        gross_profit = stats.total_revenue - total_costs
        
        # Deduct spool purchases that affect profit
        spool_purchase_deduction = spool_costs['total_affects_profit']
        net_profit = gross_profit - spool_purchase_deduction
        
        return {
            'revenue': stats.total_revenue,
            'filament_cost': filament_cost,
            'electricity_cost': stats.total_electricity_cost,
            'depreciation_cost': stats.total_depreciation_cost,
            'payment_fees': stats.total_payment_fees,
            'rounding_loss': stats.total_rounding_loss,
            'failures_cost': stats.total_failure_cost,
            'expenses': stats.total_expenses,
            'tolerance_discounts': stats.total_tolerance_discounts,
            # Spool purchases
            'spool_from_profit': spool_costs['profit_cost'],
            'loan_repaid': spool_costs['loan_repaid_cost'],
            'spool_purchase_total': spool_purchase_deduction,
            'pending_loans': spool_costs['pending_loan_cost'],
            'spool_details': spool_costs['details'],
            # Loan info
            'unpaid_loan_count': loan_stats['unpaid_loan_count'],
            'unpaid_loan_amount': loan_stats['unpaid_loan_amount'],
            # Profits
            'gross_profit': gross_profit,
            'net_profit': net_profit,
            'profit_margin': (net_profit / stats.total_revenue * 100) if stats.total_revenue > 0 else 0,
        }
    
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
        
        # Orders
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
        stats.total_weight_printed = sum(o.total_weight for o in orders if o.status in [OrderStatus.DELIVERED.value, OrderStatus.READY.value])
        stats.total_time_printed = sum(o.total_time for o in orders if o.status in [OrderStatus.DELIVERED.value, OrderStatus.READY.value])
        stats.total_tolerance_discounts = sum(o.tolerance_discount_total for o in orders if o.status != OrderStatus.CANCELLED.value)
        
        # Gross profit from orders (before failures and expenses)
        stats.gross_profit = sum(o.profit for o in orders if o.status != OrderStatus.CANCELLED.value)
        
        # Failures
        failure_stats = self.get_failure_stats()
        stats.total_failures = failure_stats['total_failures']
        stats.total_failure_cost = failure_stats['total_cost']
        stats.failure_filament_wasted = failure_stats['total_filament_wasted']
        stats.failure_time_wasted = failure_stats['total_time_wasted']
        
        # Expenses
        expense_stats = self.get_expense_stats()
        stats.total_expenses = expense_stats['total_expenses']
        stats.expenses_tools = expense_stats['by_category'].get(ExpenseCategory.TOOLS.value, 0)
        stats.expenses_consumables = expense_stats['by_category'].get(ExpenseCategory.CONSUMABLES.value, 0)
        stats.expenses_maintenance = expense_stats['by_category'].get(ExpenseCategory.MAINTENANCE.value, 0)
        stats.expenses_other = (stats.total_expenses - stats.expenses_tools - 
                               stats.expenses_consumables - stats.expenses_maintenance)
        
        # TRUE PROFIT = Gross Profit - Failures - Expenses
        stats.total_profit = stats.gross_profit - stats.total_failure_cost - stats.total_expenses
        
        # Filament/Inventory
        spools = self.get_all_spools()
        stats.total_filament_used = sum(s.used_weight_grams for s in spools)
        stats.active_spools = len([s for s in spools if s.is_active and s.current_weight_grams > 50])
        stats.remaining_filament = sum(s.current_weight_grams for s in spools if s.is_active)
        stats.pending_filament = sum(s.pending_weight_grams for s in spools)
        stats.total_filament_waste = self.get_total_waste() + stats.failure_filament_wasted
        
        # Printers
        printers = self.get_all_printers()
        stats.total_printers = len(printers)
        stats.total_nozzle_cost = sum(p.total_nozzle_cost for p in printers)
        
        # Customers
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
