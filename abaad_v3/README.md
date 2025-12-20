# Abaad 3D Print Manager v3.0

A complete Windows desktop application for managing 3D printing orders with advanced features.

## 🌟 New Features in v3.0

### ✅ Auto-Discount Calculation
- When you set a rate below 4.0 EGP/g, discount is automatically calculated
- Example: 182g at 2.7-2.8 EGP/g = 30.46% discount automatically
- Discount shown in item dialog and order totals

### ✅ Correct Filament Pricing
- **New Spools**: 840 EGP fixed (regardless of weight > 1000g)
- **Remaining Spools**: FREE (already paid for)
- Cost per gram: 0.84 EGP for new, 0 for remaining

### ✅ Payment Methods with Auto Fees
- **Cash**: FREE
- **Vodafone Cash**: 0.5% (Min 1 EGP, Max 15 EGP)
- **InstaPay**: 0.1% (Min 0.50 EGP, Max 20 EGP)
- Fees automatically calculated and shown on receipt

### ✅ Shipping Cost Tracking
- Enter shipping cost per order
- Included in receipt total

### ✅ Multiple Printers Support
- Default printer: HIVE 0.1 (Creality Ender-3 Max)
- Track per-printer: Print time, filament used, nozzle changes
- Automatic nozzle wear tracking
- Depreciation and electricity cost calculation

### ✅ Color-Based Spool Filtering
- When selecting color, only matching spools appear
- Auto-selects spool with most remaining filament

### ✅ Immediate Filament Deduction
- Filament deducted when item is added to order
- Real-time spool quantities

### ✅ Comprehensive Statistics
- Revenue, Profit, Material Cost
- Electricity Cost, Nozzle Cost
- Shipping, Payment Fees
- Profit Margin %

## 📦 Installation

1. Extract to: `D:\Abad\Print3D_Manager\`
2. Run: `python run_app.py`

No external dependencies required (uses only Python standard library)!

## 💰 Pricing Logic

### Order Discount Calculation
```
Base Total = Weight × Quantity × 4.0 EGP/g
Actual Total = Weight × Quantity × Item Rate
Discount % = (Base - Actual) / Base × 100
```

### Payment Fees
```
InstaPay: 0.1% × Amount (Min 0.50, Max 20 EGP)
Vodafone: 0.5% × Amount (Min 1.00, Max 15 EGP)
Cash: FREE
```

### Profit Calculation
```
Material Cost = Weight × 0.84 EGP/g
Electricity = Hours × 0.31 EGP/h
Depreciation = Kg × 50 EGP/kg (25000/500kg)
Profit = Actual Total - Material - Electricity - Depreciation
```

## 📱 Receipt Shows
- Items with color, weight, settings, rate
- Base total vs actual total
- Discount amount and percentage
- Shipping cost
- Payment method and fee
- Final total

## 🖨️ Printer Tracking
- Total print time (hours)
- Total filament used (g/kg)
- Nozzle changes
- Electricity cost
- Depreciation cost

## 📂 File Structure
```
abaad_v3/
├── run_app.py          # Main application
├── core/
│   ├── __init__.py
│   ├── models.py       # Data models
│   └── database.py     # JSON database
├── data/
│   └── abaad_print_manager.db.json
└── requirements.txt
```

## 🎨 Available Colors
Black, Light Blue, Silver, White, Red, Beige, Purple

---

**Abaad 3D Printing Services**  
Ismailia, Egypt  
01070750477
