# Abaad 3D Print Manager v4.0 (ERP Edition)

A complete Windows desktop application for managing 3D printing orders with advanced ERP features and AI integration.

## 🌟 What's New in v4.0

### ✅ Pending Filament Deduction
- Filament is **reserved (pending)** when added to an order
- Only **permanently deducted** when order status changes to "Confirmed" or "In Progress"
- If order is **cancelled or deleted**, filament is **returned** to the spool

### ✅ Filament Trash/Archive System
- Spools with < 20g remaining show "Move to Trash" button
- Archived spools are tracked in FilamentHistory
- Waste tracking for business statistics

### ✅ R&D Mode
- Toggle "R&D Project" checkbox for internal projects
- R&D Cost = Material + Electricity + Depreciation (actual cost)
- Zero profit calculation for R&D orders
- Purple badge on R&D orders

### ✅ Financial Rounding/Slippage
- Enter "Amount Received" when customer pays
- System calculates "Rounding Loss" automatically
- Example: Total 1007 EGP, Received 1000 EGP → Loss 7 EGP
- Tracked in statistics for business analysis

### ✅ Tolerance Discount
- Set "Actual Weight" after printing to compare with estimate
- If printed part is 1-5g heavier than estimated, automatic discount applies
- Discount = 1g × rate per part
- Shows in receipt and order totals

### ✅ Cura Vision AI (OCR)
- Click "Paste from Clipboard (Cura)" in Add Item dialog
- Screenshot Cura slicer after slicing, copy to clipboard
- AI extracts Time and Weight automatically
- Requires: Pillow + Tesseract OCR

### ✅ Two-Stage PDF Generation
- **Quote PDF**: Shows estimated costs, 50% deposit required, disclaimer
- **Invoice/Receipt PDF**: Shows final measured weights, tolerance discounts

### ✅ Enhanced Statistics Dashboard
- Revenue, Profit, Margin
- Material Cost, Electricity, Depreciation
- Rounding Loss tracking
- Waste from trashed spools
- Tolerance discounts total
- R&D orders count

## 📦 Installation

### Option 1: Run Directly (Windows)
1. Extract to: `D:\Abad\Print3D_Manager\abaad_v4\`
2. Run: `python main.py`

### Option 2: Create Virtual Environment
```bash
cd D:\Abad\Print3D_Manager\abaad_v4
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Installing Tesseract OCR (for Cura Vision AI)
1. Download from: https://github.com/UB-Mannheim/tesseract/wiki
2. Install to default location: `C:\Program Files\Tesseract-OCR\`
3. The app will auto-detect it

## 💰 Pricing Logic

### Pending Filament System
```
1. Item Added → Filament RESERVED (pending)
2. Order Confirmed → Filament COMMITTED (deducted)
3. Order Cancelled → Filament RETURNED
```

### R&D Mode Pricing
```
R&D Cost = Material Cost + Electricity Cost + Depreciation Cost
Profit = 0 (always)
```

### Tolerance Discount
```
If Actual Weight > Estimated by 1-5g:
    Discount = Rate × Quantity (1g cost per part)
```

### Rounding Loss
```
Rounding Loss = Total - Amount Received
(Only if Amount Received < Total)
```

## 📂 File Structure
```
abaad_v4/
├── main.py                 # Entry point
├── requirements.txt        # Dependencies
├── README.md              # This file
├── assets/                # Logo and icons
│   └── icon.ico
├── data/                  # Database storage
│   └── abaad_v4.db.json
├── exports/               # Generated PDFs
├── src/
│   ├── __init__.py
│   ├── models.py          # Data models
│   ├── database.py        # JSON database manager
│   ├── logic/
│   │   ├── __init__.py
│   │   └── cura_ai.py     # Cura Vision OCR
│   └── utils/
│       ├── __init__.py
│       └── pdf_generator.py
```

## 🎨 Available Colors
Black, Light Blue, Silver, White, Red, Beige, Purple

## 🔄 Migration from v3
The v4 database manager automatically migrates data from v3 if:
- v3 database exists at `data/abaad_print_manager.db.json`
- v4 database is empty

---

**Abaad 3D Printing Services**  
Ismailia, Egypt  
01070750477
