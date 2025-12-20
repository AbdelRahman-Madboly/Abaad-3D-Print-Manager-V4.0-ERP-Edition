"""
PDF Generator for Abaad 3D Print Manager v4.0
Two-stage PDF generation: Initial Quote and Final Invoice
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
        Spacer, Image, HRFlowable
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
}

COLORS = {
    'primary': '#1e3a8a',
    'success': '#22c55e',
    'warning': '#f59e0b',
    'text': '#1f2937',
    'text_light': '#6b7280',
    'border': '#e5e7eb',
    'rd_badge': '#7c3aed',
}

DISCLAIMERS = {
    'quote': "ESTIMATE - Final pricing may vary ±100 EGP based on actual print results.",
    'invoice': "Supports removed for recycling. Design tolerances are customer's responsibility.",
    'rd': "R&D Project - Cost-only pricing (no profit margin).",
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
            ('SectionHeader', {'fontName': 'Helvetica-Bold', 'fontSize': 12, 'textColor': self._hex_to_color(self.colors['primary'])}),
            ('NormalText', {'fontName': 'Helvetica', 'fontSize': 10, 'textColor': self._hex_to_color(self.colors['text'])}),
            ('SmallText', {'fontName': 'Helvetica', 'fontSize': 8, 'textColor': self._hex_to_color(self.colors['text_light'])}),
            ('Footer', {'fontName': 'Helvetica-Oblique', 'fontSize': 10, 'textColor': self._hex_to_color(self.colors['text_light']), 'alignment': TA_CENTER}),
            ('Disclaimer', {'fontName': 'Helvetica-Oblique', 'fontSize': 8, 'textColor': self._hex_to_color(self.colors['warning']), 'alignment': TA_CENTER}),
        ]:
            self.styles.add(ParagraphStyle(name=name, **config))
    
    def _build_header(self, order, doc_type="RECEIPT"):
        elements = []
        logo_cell = ""
        logo_path = Path(self.company['logo_path'])
        if logo_path.exists():
            try:
                logo_cell = Image(str(logo_path), width=35*mm, height=35*mm)
            except:
                pass
        
        company_text = f"<b>{self.company['name']}</b><br/><font size='9'>{self.company['subtitle']}<br/>{self.company['address']}<br/>Tel: {self.company['phone']}</font>"
        company_para = Paragraph(company_text, self.styles['NormalText'])
        
        order_date = order.created_date.split()[0] if order.created_date else datetime.now().strftime('%Y-%m-%d')
        rd_text = "<font color='#7c3aed'><b>[R&D]</b></font><br/>" if order.is_rd_project else ""
        doc_info = f"<b>{doc_type}</b><br/>{rd_text}<font size='9'>Order #: <b>{order.order_number}</b><br/>Date: {order_date}<br/>Status: {order.status}</font>"
        doc_para = Paragraph(doc_info, self.styles['NormalText'])
        
        header_table = Table([[logo_cell, company_para, doc_para]], colWidths=[40*mm, 75*mm, 65*mm])
        header_table.setStyle(TableStyle([
            ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.extend([header_table, Spacer(1, 5*mm), HRFlowable(width="100%", thickness=1, color=self._hex_to_color(self.colors['primary'])), Spacer(1, 5*mm)])
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
        elements = [Paragraph("Order Items", self.styles['SectionHeader'])]
        headers = ["#", "Item Description", "Qty", "Weight", "Rate", "Total"]
        data = [headers]
        
        for i, item in enumerate(order.items, 1):
            desc_text = f"{item.name}\n{item.color} | {item.settings}"
            if item.tolerance_discount_applied:
                desc_text += f"\n[Tolerance Discount: -{item.tolerance_discount_amount:.2f}]"
            weight_text = f"{item.weight:.0f}g"
            if show_actual and item.actual_weight_grams > 0:
                weight_text = f"{item.estimated_weight_grams:.0f}g → {item.actual_weight_grams:.0f}g"
            data.append([str(i), desc_text, str(item.quantity), weight_text, f"{item.rate_per_gram:.2f}", f"{item.print_cost:.2f}"])
        
        table = Table(data, colWidths=[10*mm, 75*mm, 15*mm, 30*mm, 25*mm, 25*mm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self._hex_to_color(self.colors['primary'])),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, self._hex_to_color(self.colors['border'])),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self._hex_to_color('#f3f4f6')]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.extend([table, Spacer(1, 5*mm)])
        return elements
    
    def _build_totals(self, order, is_quote=False):
        elements = []
        currency = "EGP"
        totals_data = [["Base Total (4 EGP/g):", f"{order.subtotal:.2f} {currency}"]]
        
        if order.discount_percent > 0:
            totals_data.append([f"Rate Discount ({order.discount_percent:.1f}%):", f"-{order.discount_amount:.2f} {currency}"])
        totals_data.append(["Subtotal:", f"{order.actual_total:.2f} {currency}"])
        
        if order.order_discount_percent > 0:
            totals_data.append([f"Order Discount ({order.order_discount_percent:.1f}%):", f"-{order.order_discount_amount:.2f} {currency}"])
        if order.tolerance_discount_total > 0:
            totals_data.append(["Tolerance Discounts:", f"-{order.tolerance_discount_total:.2f} {currency}"])
        if order.shipping_cost > 0:
            totals_data.append(["Shipping:", f"{order.shipping_cost:.2f} {currency}"])
        
        totals_data.append(["Payment Method:", order.payment_method])
        if order.payment_fee > 0:
            totals_data.append(["Payment Fee:", f"{order.payment_fee:.2f} {currency}"])
        
        totals_data.append(["", ""])
        
        if is_quote:
            totals_data.append(["ESTIMATED TOTAL:", f"{order.total:.2f} {currency}"])
            deposit = order.total * 0.5
            totals_data.append(["Deposit Required (50%):", f"{deposit:.2f} {currency}"])
        else:
            totals_data.append(["TOTAL:", f"{order.total:.2f} {currency}"])
            if order.rounding_loss > 0:
                totals_data.append(["Rounding Adjustment:", f"-{order.rounding_loss:.2f} {currency}"])
                totals_data.append(["Amount Received:", f"{order.amount_received:.2f} {currency}"])
        
        table = Table(totals_data, colWidths=[100*mm, 50*mm])
        style = [
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -3), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, -2), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -2), (-1, -1), 12 if not is_quote else 11),
            ('TEXTCOLOR', (0, -2), (-1, -1), self._hex_to_color(self.colors['primary'])),
            ('LINEABOVE', (0, -2), (-1, -2), 2, self._hex_to_color(self.colors['primary'])),
        ]
        # Color discounts green
        for i, row in enumerate(totals_data):
            if 'Discount' in row[0]:
                style.append(('TEXTCOLOR', (1, i), (1, i), self._hex_to_color(self.colors['success'])))
        
        table.setStyle(TableStyle(style))
        elements.extend([table, Spacer(1, 10*mm)])
        return elements
    
    def _build_footer(self, order, is_quote=False):
        elements = []
        elements.append(HRFlowable(width="100%", thickness=0.5, color=self._hex_to_color(self.colors['border'])))
        elements.append(Spacer(1, 3*mm))
        
        if is_quote:
            elements.append(Paragraph(DISCLAIMERS['quote'], self.styles['Disclaimer']))
        else:
            elements.append(Paragraph(DISCLAIMERS['invoice'], self.styles['SmallText']))
        
        if order.is_rd_project:
            elements.append(Paragraph(DISCLAIMERS['rd'], self.styles['Disclaimer']))
        
        elements.append(Spacer(1, 5*mm))
        elements.append(Paragraph("Thank you for your business!", self.styles['Footer']))
        elements.append(Paragraph(self.company['tagline'], self.styles['SmallText']))
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
