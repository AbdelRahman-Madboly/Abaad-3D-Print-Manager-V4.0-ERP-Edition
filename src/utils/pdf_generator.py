"""
PDF Generator for Abaad 3D Print Manager v4.0
Enhanced PDF generation with detailed cost breakdown and professional formatting
"""
from pathlib import Path
from datetime import datetime, timedelta
import os

REPORTLAB_AVAILABLE = False
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, 
        Spacer, Image, HRFlowable, PageBreak
    )
    REPORTLAB_AVAILABLE = True
except ImportError:
    pass

COMPANY_INFO = {
    'name': 'Abaad',
    'subtitle': '3D Printing Services',
    'phone': '01070750477',
    'address': 'Ismailia, Egypt',
    'logo_path': 'assets/Abaad.png',
    'tagline': 'Quality 3D Printing Solutions',
    'website': 'Ismailia, Egypt',
    'social': '@abaad3d',
}

COLORS = {
    'primary': '#1e3a8a',
    'primary_light': '#3b82f6',
    'success': '#22c55e',
    'warning': '#f59e0b',
    'danger': '#ef4444',
    'text': '#1f2937',
    'text_light': '#6b7280',
    'border': '#e5e7eb',
    'rd_badge': '#7c3aed',
    'background': '#f8fafc',
}

DISCLAIMERS = {
    'quote': "📋 ESTIMATE - Final pricing may vary ±100 EGP based on actual print results.",
    'invoice': "✓ Supports removed for recycling. Design tolerances are customer's responsibility.",
    'rd': "🔬 R&D Project - Cost-only pricing (no profit margin).",
    'terms': "Payment due upon delivery. All sales are final. Files retained for 30 days.",
}


class PDFGenerator:
    def __init__(self, company_info=None, colors_config=None):
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab not installed. Run: pip install reportlab")
        self.company = {**COMPANY_INFO, **(company_info or {})}
        self.colors = {**COLORS, **(colors_config or {})}
        self._setup_styles()
    
    def _hex_to_color(self, hex_color):
        if isinstance(hex_color, str) and hex_color.startswith('#'):
            hex_color = hex_color.lstrip('#')
            r, g, b = int(hex_color[0:2], 16)/255, int(hex_color[2:4], 16)/255, int(hex_color[4:6], 16)/255
            return colors.Color(r, g, b)
        return hex_color
    
    def _setup_styles(self):
        self.styles = getSampleStyleSheet()
        for name, config in [
            ('SectionHeader', {'fontName': 'Helvetica-Bold', 'fontSize': 12, 'textColor': self._hex_to_color(self.colors['primary']), 'spaceAfter': 6}),
            ('NormalText', {'fontName': 'Helvetica', 'fontSize': 10, 'textColor': self._hex_to_color(self.colors['text'])}),
            ('SmallText', {'fontName': 'Helvetica', 'fontSize': 8, 'textColor': self._hex_to_color(self.colors['text_light'])}),
            ('Footer', {'fontName': 'Helvetica-Oblique', 'fontSize': 10, 'textColor': self._hex_to_color(self.colors['text_light']), 'alignment': TA_CENTER}),
            ('Disclaimer', {'fontName': 'Helvetica-Oblique', 'fontSize': 8, 'textColor': self._hex_to_color(self.colors['warning']), 'alignment': TA_CENTER}),
            ('TotalText', {'fontName': 'Helvetica-Bold', 'fontSize': 14, 'textColor': self._hex_to_color(self.colors['primary'])}),
            ('SuccessText', {'fontName': 'Helvetica', 'fontSize': 10, 'textColor': self._hex_to_color(self.colors['success'])}),
        ]:
            self.styles.add(ParagraphStyle(name=name, **config))
    
    def _build_header(self, order, doc_type="RECEIPT"):
        elements = []
        logo_cell = ""
        logo_path = Path(self.company['logo_path'])
        if logo_path.exists():
            try:
                logo_cell = Image(str(logo_path), width=40*mm, height=40*mm)
            except:
                pass
        
        company_text = f"""<b><font size='16' color='{self.colors['primary']}'>{self.company['name']}</font></b><br/>
        <font size='10' color='{self.colors['text_light']}'>{self.company['subtitle']}</font><br/>
        <font size='9'>{self.company['address']}</font><br/>
        <font size='9'>📞 {self.company['phone']}</font>"""
        company_para = Paragraph(company_text, self.styles['NormalText'])
        
        order_date = order.created_date.split()[0] if order.created_date else datetime.now().strftime('%Y-%m-%d')
        rd_badge = f"<font color='{self.colors['rd_badge']}'><b>🔬 R&D PROJECT</b></font><br/>" if order.is_rd_project else ""
        
        # Document type with colored badge
        doc_color = self.colors['primary'] if doc_type == "RECEIPT" else self.colors['warning'] if doc_type == "QUOTE" else self.colors['success']
        doc_info = f"""<font size='14' color='{doc_color}'><b>{doc_type}</b></font><br/>
        {rd_badge}
        <font size='10'>Order #: <b>{order.order_number}</b></font><br/>
        <font size='9'>Date: {order_date}</font><br/>
        <font size='9'>Status: <b>{order.status}</b></font>"""
        doc_para = Paragraph(doc_info, self.styles['NormalText'])
        
        header_table = Table([[logo_cell, company_para, doc_para]], colWidths=[45*mm, 70*mm, 65*mm])
        header_table.setStyle(TableStyle([
            ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.extend([header_table, Spacer(1, 5*mm), 
                        HRFlowable(width="100%", thickness=2, color=self._hex_to_color(self.colors['primary'])), 
                        Spacer(1, 5*mm)])
        return elements
    
    def _build_customer_section(self, order):
        elements = [Paragraph("Customer Information", self.styles['SectionHeader'])]
        cust_table = Table([["Name:", order.customer_name or "Walk-in"], ["Phone:", order.customer_phone or "-"]], colWidths=[25*mm, 100*mm])
        cust_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ]))
        elements.extend([cust_table, Spacer(1, 5*mm)])
        return elements
    
    def _build_items_table(self, order, show_actual=False):
        elements = [Paragraph("📦 Order Items", self.styles['SectionHeader'])]
        headers = ["#", "Item Description", "Qty", "Weight", "Rate/g", "Total"]
        data = [headers]
        
        total_weight = 0
        total_time = 0
        
        for i, item in enumerate(order.items, 1):
            # Rich item description
            desc_text = f"<b>{item.name}</b>\n"
            desc_text += f"<font size='8' color='{self.colors['text_light']}'>"
            desc_text += f"🎨 {item.color} | ⚙️ {item.settings}"
            if item.tolerance_discount_applied:
                desc_text += f"\n<font color='{self.colors['success']}'>✓ Tolerance Discount: -{item.tolerance_discount_amount:.2f}</font>"
            desc_text += "</font>"
            
            weight_text = f"{item.weight:.0f}g"
            if show_actual and item.actual_weight_grams > 0:
                diff = item.actual_weight_grams - item.estimated_weight_grams
                diff_color = self.colors['success'] if diff <= 0 else self.colors['warning']
                weight_text = f"{item.estimated_weight_grams:.0f}g → {item.actual_weight_grams:.0f}g"
            
            total_weight += item.total_weight
            total_time += item.time_minutes * item.quantity
            
            data.append([str(i), Paragraph(desc_text, self.styles['SmallText']), 
                        str(item.quantity), weight_text, f"{item.rate_per_gram:.2f}", f"{item.print_cost:.2f}"])
        
        # Add summary row
        hours = total_time // 60
        mins = total_time % 60
        data.append(["", f"<b>Total: {len(order.items)} items</b>", "", f"<b>{total_weight:.0f}g</b>", f"<b>{hours}h {mins}m</b>", ""])
        
        table = Table(data, colWidths=[10*mm, 80*mm, 15*mm, 25*mm, 20*mm, 30*mm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self._hex_to_color(self.colors['primary'])),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -2), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -2), 0.5, self._hex_to_color(self.colors['border'])),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, self._hex_to_color('#f8fafc')]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            # Summary row styling
            ('BACKGROUND', (0, -1), (-1, -1), self._hex_to_color('#e5e7eb')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('LINEABOVE', (0, -1), (-1, -1), 1.5, self._hex_to_color(self.colors['primary'])),
        ]))
        elements.extend([table, Spacer(1, 8*mm)])
        return elements
    
    def _build_totals(self, order, is_quote=False):
        elements = [Paragraph("💰 Payment Summary", self.styles['SectionHeader'])]
        currency = "EGP"
        
        # Build totals data
        totals_data = []
        
        # Pricing breakdown
        totals_data.append(["Base Total (4 EGP/g):", f"{order.subtotal:.2f} {currency}"])
        
        if order.discount_percent > 0:
            totals_data.append([f"✓ Rate Discount ({order.discount_percent:.1f}%):", f"-{order.discount_amount:.2f} {currency}"])
        
        if order.order_discount_percent > 0:
            totals_data.append([f"✓ Order Discount ({order.order_discount_percent:.1f}%):", f"-{order.order_discount_amount:.2f} {currency}"])
        
        if order.tolerance_discount_total > 0:
            totals_data.append(["✓ Tolerance Discounts:", f"-{order.tolerance_discount_total:.2f} {currency}"])
        
        totals_data.append(["Subtotal:", f"{order.actual_total:.2f} {currency}"])
        
        if order.shipping_cost > 0:
            totals_data.append(["🚚 Shipping:", f"+{order.shipping_cost:.2f} {currency}"])
        
        totals_data.append(["Payment Method:", f"💳 {order.payment_method}"])
        if order.payment_fee > 0:
            totals_data.append(["Payment Fee:", f"+{order.payment_fee:.2f} {currency}"])
        
        totals_data.append(["", ""])
        
        if is_quote:
            totals_data.append(["📋 ESTIMATED TOTAL:", f"{order.total:.2f} {currency}"])
            deposit = order.total * 0.5
            totals_data.append(["", ""])
            totals_data.append(["💵 Deposit Required (50%):", f"{deposit:.2f} {currency}"])
            totals_data.append(["💵 Balance on Delivery:", f"{order.total - deposit:.2f} {currency}"])
        else:
            totals_data.append(["📋 TOTAL:", f"{order.total:.2f} {currency}"])
            if order.rounding_loss > 0:
                totals_data.append(["Rounding Adjustment:", f"-{order.rounding_loss:.2f} {currency}"])
            if order.amount_received > 0:
                totals_data.append(["✓ Amount Received:", f"{order.amount_received:.2f} {currency}"])
                balance = order.total - order.amount_received
                if balance > 0.5:
                    totals_data.append(["⚠️ Balance Due:", f"{balance:.2f} {currency}"])
                elif balance < -0.5:
                    totals_data.append(["Change Given:", f"{-balance:.2f} {currency}"])
        
        # Create right-aligned table
        table = Table(totals_data, colWidths=[100*mm, 55*mm])
        style = [
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]
        
        # Find and style key rows
        for i, row in enumerate(totals_data):
            if 'Discount' in row[0] or row[0].startswith('✓'):
                style.append(('TEXTCOLOR', (1, i), (1, i), self._hex_to_color(self.colors['success'])))
            if 'TOTAL' in row[0]:
                style.append(('FONTNAME', (0, i), (-1, i), 'Helvetica-Bold'))
                style.append(('FONTSIZE', (0, i), (-1, i), 13))
                style.append(('TEXTCOLOR', (0, i), (-1, i), self._hex_to_color(self.colors['primary'])))
                style.append(('LINEABOVE', (0, i), (-1, i), 2, self._hex_to_color(self.colors['primary'])))
            if 'Deposit' in row[0] or 'Balance' in row[0]:
                style.append(('FONTNAME', (0, i), (-1, i), 'Helvetica-Bold'))
                style.append(('BACKGROUND', (0, i), (-1, i), self._hex_to_color('#fef3c7')))
            if '⚠️' in row[0]:
                style.append(('TEXTCOLOR', (1, i), (1, i), self._hex_to_color(self.colors['warning'])))
        
        table.setStyle(TableStyle(style))
        elements.extend([table, Spacer(1, 10*mm)])
        return elements
    
    def _build_footer(self, order, is_quote=False):
        elements = []
        elements.append(HRFlowable(width="100%", thickness=1, color=self._hex_to_color(self.colors['border'])))
        elements.append(Spacer(1, 5*mm))
        
        # Disclaimers
        if is_quote:
            elements.append(Paragraph(DISCLAIMERS['quote'], self.styles['Disclaimer']))
            validity_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
            elements.append(Paragraph(f"📅 Quote valid until: {validity_date}", self.styles['SmallText']))
        else:
            elements.append(Paragraph(DISCLAIMERS['invoice'], self.styles['SmallText']))
        
        if order.is_rd_project:
            elements.append(Paragraph(DISCLAIMERS['rd'], self.styles['Disclaimer']))
        
        elements.append(Spacer(1, 3*mm))
        elements.append(Paragraph(DISCLAIMERS['terms'], self.styles['SmallText']))
        
        elements.append(Spacer(1, 8*mm))
        
        # Thank you message with styling
        thank_you = f"""<font size='12' color='{self.colors['primary']}'><b>Thank you for choosing {self.company['name']}!</b></font>"""
        elements.append(Paragraph(thank_you, self.styles['Footer']))
        elements.append(Spacer(1, 3*mm))
        
        # Contact info footer
        footer_text = f"""<font size='9' color='{self.colors['text_light']}'>
        {self.company['tagline']} | 📞 {self.company['phone']} | 📍 {self.company['address']}
        </font>"""
        elements.append(Paragraph(footer_text, self.styles['Footer']))
        
        # Generation timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        elements.append(Spacer(1, 5*mm))
        elements.append(Paragraph(f"<font size='7' color='{self.colors['text_light']}'>Generated: {timestamp}</font>", 
                                 self.styles['Footer']))
        
        return elements
    
    def generate_quote(self, order, output_path=None, output_dir=None):
        """Generate initial quote PDF"""
        return self._generate_pdf(order, "QUOTE", output_path, output_dir, is_quote=True)
    
    def generate_invoice(self, order, output_path=None, output_dir=None):
        """Generate final invoice PDF"""
        return self._generate_pdf(order, "INVOICE", output_path, output_dir, is_quote=False)
    
    def generate_receipt(self, order, output_path=None, output_dir=None):
        """Generate receipt PDF (alias for invoice)"""
        return self._generate_pdf(order, "RECEIPT", output_path, output_dir, is_quote=False)
    
    def _generate_pdf(self, order, doc_type, output_path, output_dir, is_quote=False):
        if not output_path:
            if not output_dir:
                output_dir = Path("exports")
            else:
                output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{doc_type}_{order.order_number}_{timestamp}.pdf"
            output_path = output_dir / filename
        
        output_path = str(output_path)
        
        doc = SimpleDocTemplate(output_path, pagesize=A4, topMargin=15*mm, bottomMargin=15*mm, leftMargin=15*mm, rightMargin=15*mm)
        
        elements = []
        elements.extend(self._build_header(order, doc_type))
        elements.extend(self._build_customer_section(order))
        elements.extend(self._build_items_table(order, show_actual=not is_quote))
        elements.extend(self._build_totals(order, is_quote))
        elements.extend(self._build_footer(order, is_quote))
        
        doc.build(elements)
        return output_path


def generate_quote(order, output_path=None, output_dir=None, **kwargs):
    """Quick function to generate a quote"""
    generator = PDFGenerator(**kwargs)
    return generator.generate_quote(order, output_path, output_dir)

def generate_invoice(order, output_path=None, output_dir=None, **kwargs):
    """Quick function to generate an invoice"""
    generator = PDFGenerator(**kwargs)
    return generator.generate_invoice(order, output_path, output_dir)

def generate_receipt(order, output_path=None, output_dir=None, **kwargs):
    """Quick function to generate a receipt"""
    generator = PDFGenerator(**kwargs)
    return generator.generate_receipt(order, output_path, output_dir)
