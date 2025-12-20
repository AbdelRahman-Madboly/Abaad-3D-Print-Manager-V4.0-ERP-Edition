"""
PDF Receipt Generator for Abaad 3D Print Manager
=================================================
Professional, customizable PDF receipts using reportlab

Installation: pip install reportlab

CUSTOMIZATION GUIDE:
- Edit COMPANY_INFO dict for your business details
- Edit COLORS dict to change color scheme
- Edit FONTS dict to change fonts
- Modify generate_receipt() to change layout
- Add new sections in _build_* methods

Author: Abaad 3D Printing
Version: 1.0
"""
from pathlib import Path
from datetime import datetime
import os

# Check if reportlab is available
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.units import mm, cm, inch
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, 
        Spacer, Image, HRFlowable, PageBreak
    )
    from reportlab.graphics.shapes import Drawing, Line
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("=" * 60)
    print("  reportlab not installed!")
    print("  Run: pip install reportlab")
    print("=" * 60)


# =============================================================================
# ★★★ CUSTOMIZATION SECTION - EDIT THESE VALUES ★★★
# =============================================================================

# Company Information
COMPANY_INFO = {
    'name': 'Abaad',
    'subtitle': '3D Printing Services',
    'phone': '01070750477',
    'address': 'Ismailia, Egypt',
    'email': '',                              # Optional - leave empty to hide
    'website': '',                            # Optional - leave empty to hide
    'logo_path': 'D:/Abad/Logo/Abaad.png',   # Path to logo (PNG, 300x300 recommended)
    'tagline': 'Quality 3D Printing Solutions',  # Shown in footer
}

# Colors (use hex format like '#1e3a8a' or reportlab colors)
COLORS = {
    'primary': '#1e3a8a',       # Dark blue - headers, titles
    'secondary': '#3b82f6',     # Light blue - accents
    'success': '#22c55e',       # Green - profit, positive values
    'danger': '#ef4444',        # Red - negative values
    'warning': '#f59e0b',       # Orange - warnings
    'text': '#1f2937',          # Dark gray - main text
    'text_light': '#6b7280',    # Light gray - secondary text
    'background': '#f8fafc',    # Light background
    'border': '#e5e7eb',        # Border color
    'header_bg': '#1e3a8a',     # Header background
    'row_alt': '#f3f4f6',       # Alternating row color
}

# Page Settings
PAGE_SETTINGS = {
    'page_size': A4,            # A4 or letter
    'margin_top': 15 * mm,
    'margin_bottom': 15 * mm,
    'margin_left': 15 * mm,
    'margin_right': 15 * mm,
}

# Receipt Settings
RECEIPT_SETTINGS = {
    'show_logo': True,
    'logo_width': 35 * mm,
    'logo_height': 35 * mm,
    'show_qr_code': False,      # Future feature
    'show_internal_costs': False,  # Show material/electricity costs (internal only)
    'currency': 'EGP',
    'currency_symbol': '',      # Or use 'ج.م' for Arabic
    'date_format': '%Y-%m-%d %H:%M',
    'thank_you_message': 'Thank you for your business!',
    'terms_conditions': '',     # Optional terms at bottom
}


# =============================================================================
# PDF GENERATOR CLASS
# =============================================================================

class PDFReceiptGenerator:
    """
    Professional PDF Receipt Generator
    
    Usage:
        generator = PDFReceiptGenerator()
        pdf_path = generator.generate_receipt(order, output_path)
    """
    
    def __init__(self, company_info=None, colors=None, settings=None):
        """
        Initialize generator with optional custom settings
        
        Args:
            company_info: Dict overriding COMPANY_INFO
            colors: Dict overriding COLORS
            settings: Dict overriding RECEIPT_SETTINGS
        """
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab not installed. Run: pip install reportlab")
        
        self.company = {**COMPANY_INFO, **(company_info or {})}
        self.colors = {**COLORS, **(colors or {})}
        self.settings = {**RECEIPT_SETTINGS, **(settings or {})}
        self.page = PAGE_SETTINGS
        
        self._setup_styles()
    
    def _hex_to_color(self, hex_color):
        """Convert hex color to reportlab color"""
        if isinstance(hex_color, str) and hex_color.startswith('#'):
            hex_color = hex_color.lstrip('#')
            r = int(hex_color[0:2], 16) / 255.0
            g = int(hex_color[2:4], 16) / 255.0
            b = int(hex_color[4:6], 16) / 255.0
            return colors.Color(r, g, b)
        return hex_color
    
    def _setup_styles(self):
        """Setup paragraph styles"""
        self.styles = getSampleStyleSheet()
        
        # Title style
        self.styles.add(ParagraphStyle(
            name='CompanyName',
            fontName='Helvetica-Bold',
            fontSize=20,
            textColor=self._hex_to_color(self.colors['primary']),
            alignment=TA_LEFT,
            spaceAfter=2 * mm,
        ))
        
        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='Subtitle',
            fontName='Helvetica',
            fontSize=10,
            textColor=self._hex_to_color(self.colors['text_light']),
            alignment=TA_LEFT,
        ))
        
        # Section header
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            fontName='Helvetica-Bold',
            fontSize=12,
            textColor=self._hex_to_color(self.colors['primary']),
            spaceBefore=5 * mm,
            spaceAfter=3 * mm,
        ))
        
        # Normal text
        self.styles.add(ParagraphStyle(
            name='NormalText',
            fontName='Helvetica',
            fontSize=10,
            textColor=self._hex_to_color(self.colors['text']),
        ))
        
        # Small text
        self.styles.add(ParagraphStyle(
            name='SmallText',
            fontName='Helvetica',
            fontSize=8,
            textColor=self._hex_to_color(self.colors['text_light']),
        ))
        
        # Footer
        self.styles.add(ParagraphStyle(
            name='Footer',
            fontName='Helvetica-Oblique',
            fontSize=10,
            textColor=self._hex_to_color(self.colors['text_light']),
            alignment=TA_CENTER,
        ))
    
    def _build_header(self, order):
        """Build receipt header with logo and company info"""
        elements = []
        
        # Create header table with logo and company info
        header_data = []
        
        # Left side: Logo (if exists)
        logo_cell = ""
        if self.settings['show_logo'] and self.company['logo_path']:
            logo_path = Path(self.company['logo_path'])
            if logo_path.exists():
                try:
                    logo_cell = Image(
                        str(logo_path),
                        width=self.settings['logo_width'],
                        height=self.settings['logo_height']
                    )
                except:
                    logo_cell = ""
        
        # Right side: Company info
        company_text = f"""
        <b>{self.company['name']}</b><br/>
        <font size="9">{self.company['subtitle']}</font><br/>
        <font size="9">{self.company['address']}</font><br/>
        <font size="9">Tel: {self.company['phone']}</font>
        """
        if self.company.get('email'):
            company_text += f"<br/><font size='9'>{self.company['email']}</font>"
        
        company_para = Paragraph(company_text, self.styles['NormalText'])
        
        # Order info (right side)
        order_date = order.created_date.split()[0] if order.created_date else datetime.now().strftime('%Y-%m-%d')
        order_info = f"""
        <b>RECEIPT</b><br/>
        <font size="9">Order #: <b>{order.order_number}</b></font><br/>
        <font size="9">Date: {order_date}</font><br/>
        <font size="9">Status: {order.status}</font>
        """
        order_para = Paragraph(order_info, ParagraphStyle(
            'OrderInfo',
            parent=self.styles['NormalText'],
            alignment=TA_RIGHT
        ))
        
        header_data.append([logo_cell, company_para, order_para])
        
        header_table = Table(header_data, colWidths=[40*mm, 80*mm, 60*mm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
        ]))
        
        elements.append(header_table)
        elements.append(Spacer(1, 5 * mm))
        
        # Horizontal line
        elements.append(HRFlowable(
            width="100%",
            thickness=1,
            color=self._hex_to_color(self.colors['primary']),
            spaceBefore=2 * mm,
            spaceAfter=5 * mm
        ))
        
        return elements
    
    def _build_customer_section(self, order):
        """Build customer information section"""
        elements = []
        
        elements.append(Paragraph("Customer Information", self.styles['SectionHeader']))
        
        customer_data = [
            ["Name:", order.customer_name or "Walk-in Customer"],
            ["Phone:", order.customer_phone or "-"],
        ]
        
        customer_table = Table(customer_data, colWidths=[25*mm, 80*mm])
        customer_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), self._hex_to_color(self.colors['text_light'])),
            ('TEXTCOLOR', (1, 0), (1, -1), self._hex_to_color(self.colors['text'])),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        elements.append(customer_table)
        elements.append(Spacer(1, 5 * mm))
        
        return elements
    
    def _build_items_table(self, order):
        """Build items table"""
        elements = []
        
        elements.append(Paragraph("Order Items", self.styles['SectionHeader']))
        
        # Table header
        header = ["#", "Item Description", "Qty", "Weight", "Rate", "Total"]
        items_data = [header]
        
        # Table rows
        for i, item in enumerate(order.items, 1):
            # Build description with settings
            settings_str = f"{item.settings.nozzle_size}mm / {item.settings.layer_height}mm"
            if item.settings.support_type != "None":
                settings_str += f" / {item.settings.support_type}"
            
            description = f"{item.name}\n{item.color} | {settings_str}"
            
            row = [
                str(i),
                description,
                str(item.quantity),
                f"{item.weight:.0f}g",
                f"{item.rate_per_gram:.2f}",
                f"{item.print_cost:.2f}"
            ]
            items_data.append(row)
        
        # Create table
        items_table = Table(items_data, colWidths=[10*mm, 75*mm, 15*mm, 20*mm, 20*mm, 30*mm])
        
        # Style
        style = [
            # Header style
            ('BACKGROUND', (0, 0), (-1, 0), self._hex_to_color(self.colors['header_bg'])),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Body style
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # # column
            ('ALIGN', (2, 1), (-1, -1), 'CENTER'),  # Qty onwards
            ('ALIGN', (-1, 1), (-1, -1), 'RIGHT'),  # Total column
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, self._hex_to_color(self.colors['border'])),
            ('LINEBELOW', (0, 0), (-1, 0), 2, self._hex_to_color(self.colors['primary'])),
            
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            
            # Alternating row colors
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]
        
        # Add alternating row colors
        for i in range(1, len(items_data)):
            if i % 2 == 0:
                style.append(('BACKGROUND', (0, i), (-1, i), self._hex_to_color(self.colors['row_alt'])))
        
        items_table.setStyle(TableStyle(style))
        
        elements.append(items_table)
        elements.append(Spacer(1, 5 * mm))
        
        return elements
    
    def _build_totals_section(self, order):
        """Build totals and payment section"""
        elements = []
        
        currency = self.settings['currency']
        
        # Build totals data
        totals_data = []
        
        # Base total (at standard rate)
        totals_data.append([
            "Base Total (4 EGP/g):",
            f"{order.subtotal:.2f} {currency}"
        ])
        
        # Rate discount (from item rates)
        if order.discount_percent > 0:
            totals_data.append([
                f"Rate Discount ({order.discount_percent:.1f}%):",
                f"-{order.discount_amount:.2f} {currency}"
            ])
        
        # Subtotal after rate discount
        totals_data.append([
            "Subtotal:",
            f"{order.actual_total:.2f} {currency}"
        ])
        
        # Order discount (manual)
        if hasattr(order, 'order_discount_percent') and order.order_discount_percent > 0:
            order_disc_amount = order.actual_total * (order.order_discount_percent / 100)
            totals_data.append([
                f"Order Discount ({order.order_discount_percent:.1f}%):",
                f"-{order_disc_amount:.2f} {currency}"
            ])
        
        # Shipping
        if order.shipping_cost > 0:
            totals_data.append([
                "Shipping:",
                f"{order.shipping_cost:.2f} {currency}"
            ])
        
        # Payment method and fee
        totals_data.append([
            f"Payment Method:",
            order.payment_method
        ])
        
        if order.payment_fee > 0:
            totals_data.append([
                "Payment Fee:",
                f"{order.payment_fee:.2f} {currency}"
            ])
        
        # Separator row
        totals_data.append(["", ""])
        
        # Grand total
        totals_data.append([
            "TOTAL:",
            f"{order.total:.2f} {currency}"
        ])
        
        # Create table (right-aligned)
        totals_table = Table(totals_data, colWidths=[100*mm, 50*mm])
        
        style = [
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -2), 10),
            ('TEXTCOLOR', (0, 0), (-1, -2), self._hex_to_color(self.colors['text'])),
            
            # Total row styling
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 14),
            ('TEXTCOLOR', (0, -1), (-1, -1), self._hex_to_color(self.colors['primary'])),
            ('LINEABOVE', (0, -1), (-1, -1), 2, self._hex_to_color(self.colors['primary'])),
            
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]
        
        # Style discount rows in green
        for i, row in enumerate(totals_data):
            if 'Discount' in row[0]:
                style.append(('TEXTCOLOR', (1, i), (1, i), self._hex_to_color(self.colors['success'])))
        
        totals_table.setStyle(TableStyle(style))
        
        elements.append(totals_table)
        elements.append(Spacer(1, 10 * mm))
        
        return elements
    
    def _build_footer(self, order):
        """Build receipt footer"""
        elements = []
        
        # Horizontal line
        elements.append(HRFlowable(
            width="100%",
            thickness=0.5,
            color=self._hex_to_color(self.colors['border']),
            spaceBefore=5 * mm,
            spaceAfter=5 * mm
        ))
        
        # Thank you message
        elements.append(Paragraph(
            self.settings['thank_you_message'],
            self.styles['Footer']
        ))
        
        # Tagline
        if self.company.get('tagline'):
            elements.append(Spacer(1, 2 * mm))
            elements.append(Paragraph(
                self.company['tagline'],
                self.styles['SmallText']
            ))
        
        # Terms
        if self.settings.get('terms_conditions'):
            elements.append(Spacer(1, 5 * mm))
            elements.append(Paragraph(
                self.settings['terms_conditions'],
                self.styles['SmallText']
            ))
        
        return elements
    
    def generate_receipt(self, order, output_path=None, output_dir=None):
        """
        Generate PDF receipt for an order
        
        Args:
            order: Order object with items
            output_path: Full path for output file (optional)
            output_dir: Directory for output (optional, uses default if not specified)
        
        Returns:
            str: Path to generated PDF file
        """
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab not installed. Run: pip install reportlab")
        
        # Determine output path
        if not output_path:
            if not output_dir:
                output_dir = Path(__file__).parent / "exports"
            else:
                output_dir = Path(output_dir)
            
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"Receipt_{order.order_number}_{timestamp}.pdf"
            output_path = output_dir / filename
        
        output_path = str(output_path)
        
        # Create document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=self.page['page_size'],
            topMargin=self.page['margin_top'],
            bottomMargin=self.page['margin_bottom'],
            leftMargin=self.page['margin_left'],
            rightMargin=self.page['margin_right'],
        )
        
        # Build content
        elements = []
        
        # Header
        elements.extend(self._build_header(order))
        
        # Customer section
        elements.extend(self._build_customer_section(order))
        
        # Items table
        elements.extend(self._build_items_table(order))
        
        # Totals section
        elements.extend(self._build_totals_section(order))
        
        # Footer
        elements.extend(self._build_footer(order))
        
        # Build PDF
        doc.build(elements)
        
        return output_path


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

def generate_receipt(order, output_path=None, output_dir=None, **kwargs):
    """
    Quick function to generate a receipt
    
    Args:
        order: Order object
        output_path: Optional full output path for the PDF
        output_dir: Optional directory for output (used if output_path not specified)
        **kwargs: Additional settings to override (company_info, colors, settings)
    
    Returns:
        str: Path to generated PDF
    """
    generator = PDFReceiptGenerator(**kwargs)
    return generator.generate_receipt(order, output_path, output_dir)


# =============================================================================
# TEST / DEMO
# =============================================================================

if __name__ == "__main__":
    print("PDF Receipt Generator")
    print("=" * 50)
    
    if REPORTLAB_AVAILABLE:
        print("✓ reportlab is installed")
        print("\nUsage:")
        print("  from pdf_generator import generate_receipt")
        print("  pdf_path = generate_receipt(order)")
    else:
        print("✗ reportlab is NOT installed")
        print("\nInstall with:")
        print("  pip install reportlab")
