# 🖨️ Abaad 3D Print Manager v4.0 (ERP Edition)

<div align="center">

![Abaad Logo](assets/Abaad.png)

**Professional 3D Print Shop Management System**

*Orders • Customers • Inventory • Statistics*

</div>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📦 **Order Management** | Create, track, and manage print orders with detailed pricing |
| 👥 **Customer Database** | Store customer info with discount history |
| 🎨 **Filament Inventory** | Track spool usage, pending, and remaining weight |
| 🖨️ **Printer Tracking** | Monitor print time, material used, nozzle wear |
| 📊 **Business Statistics** | Revenue, profit, costs, margins dashboard |
| 📄 **PDF Generation** | Professional quotes and receipts |
| 🤖 **Cura Vision AI** | Extract print data from Cura screenshots (optional) |
| 👑 **Role-Based Access** | Admin & Staff user roles |

---

## 🚀 Quick Start (Windows)

### Step 1: Install Python

1. Download Python from: https://www.python.org/downloads/
2. **IMPORTANT**: Check ✅ "Add Python to PATH" during installation
3. Click "Install Now"

### Step 2: Setup the Project

**Option A: Automatic Setup (Recommended)**
```
Double-click SETUP.bat
```

**Option B: Manual Setup**
```cmd
# Open Command Prompt in project folder
cd D:\Abad\Print3D_Manager

# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Run the Application

**Option A: Double-click**
```
Double-click Launch_App.bat
```

**Option B: Manual Run**
```cmd
# Open Command Prompt in project folder
venv\Scripts\activate
python main.py
```

---

## 📁 Project Structure

```
Print3D_Manager/
├── 📄 main.py              # Main application entry
├── 📄 SETUP.bat            # One-click setup script
├── 📄 Launch_App.bat       # Run the application
├── 📄 requirements.txt     # Python dependencies
│
├── 📁 src/                 # Source code
│   ├── models.py           # Data models
│   ├── database.py         # Database operations
│   ├── 📁 logic/           # Business logic
│   │   ├── auth.py         # Authentication
│   │   └── cura_ai.py      # Cura screenshot OCR
│   ├── 📁 ui/              # User interface
│   │   ├── login.py        # Quick start dialog
│   │   └── admin_panel.py  # Admin panel
│   └── 📁 utils/           # Utilities
│       └── pdf_generator.py
│
├── 📁 data/                # Database files (JSON)
│   └── abaad_v4.db.json
│
├── 📁 exports/             # Generated PDFs
│
└── 📁 assets/              # Images & resources
```

---

## 🎯 How to Use

### Quick Start
1. **Double-click** `Launch_App.bat`
2. **Select your role**: Administrator or Staff User
3. Start managing your 3D print shop!

### User Roles

| Role | Access |
|------|--------|
| 👑 **Administrator** | Full access to all features including settings, statistics, and user management |
| 👤 **Staff User** | Create orders, manage customers, view inventory |

### Creating an Order
1. Go to **📦 Orders** tab
2. Click **+ New Order**
3. Enter customer name/phone
4. Click **+ Add** to add print items
5. Fill in item details (name, weight, color)
6. Click **💾 Save**
7. Generate **📄 Quote** or **🧾 Receipt**

---

## ⚙️ Configuration

### Company Settings (Admin Only)
- Go to **⚙️ Settings** tab
- Update company name, phone, default pricing
- Click **💾 Save Settings**

### Adding Filament Colors (Admin Only)
- Go to **👑 Admin Panel** tab
- Click **Filament Config** section
- Add new colors, brands, or types

---

## 🛠️ Troubleshooting

### "Python is not recognized"
→ Reinstall Python with "Add to PATH" checked

### "Module not found"
→ Run `venv\Scripts\activate` then `pip install -r requirements.txt`

### "Cannot open PDF"
→ Install a PDF viewer (Adobe Reader, Chrome, etc.)

### App crashes on start
→ Delete `data/abaad_v4.db.json` to reset the database

---

## 📞 Support

**Abaad 3D Printing Services**  
📍 Ismailia, Egypt  
📱 01070750477

---

<div align="center">

**Made with ❤️ for 3D Printing Community**

*v4.0 ERP Edition*

</div>
