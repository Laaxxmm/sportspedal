from flask import send_file
from app.services.pdf_base import SafeFPDF as FPDF
from num2words import num2words
import io
import os


def amount_in_words(amount):
    rupees = int(amount)
    paise = int(round((amount - rupees) * 100))
    words = num2words(rupees, lang='en_IN').title()
    if paise > 0:
        paise_words = num2words(paise, lang='en_IN').title()
        return f"Rupees {words} and {paise_words} Paise Only"
    return f"Rupees {words} Only"


def generate_invoice(sale, profile):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Title
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 10, 'TAX INVOICE', 0, 1, 'C')
    pdf.ln(2)

    # Business details
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(0, 6, profile.name if profile else 'Sportspedal', 0, 1)
    pdf.set_font('Helvetica', '', 9)
    if profile and profile.address:
        pdf.cell(0, 5, f"{profile.address}, {profile.city or ''}, {profile.state or ''}", 0, 1)
    if profile and profile.gstin:
        pdf.cell(0, 5, f"GSTIN: {profile.gstin}", 0, 1)
    if profile and profile.phone:
        pdf.cell(0, 5, f"Phone: {profile.phone}", 0, 1)
    pdf.ln(3)

    # Invoice info
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(95, 5, f"Invoice No: {sale.invoice_number}", 0, 0)
    pdf.cell(95, 5, f"Date: {sale.sale_date}", 0, 1)
    pdf.ln(2)

    # Bill To
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(0, 6, 'Bill To:', 0, 1)
    pdf.set_font('Helvetica', '', 9)
    customer = sale.customer
    pdf.cell(0, 5, customer.name, 0, 1)
    if customer.address:
        pdf.multi_cell(0, 5, customer.address)
    if customer.city:
        pdf.cell(0, 5, f"{customer.city}, {customer.state or ''}", 0, 1)
    if customer.gstin:
        pdf.cell(0, 5, f"GSTIN: {customer.gstin}", 0, 1)
    if customer.phone:
        pdf.cell(0, 5, f"Phone: {customer.phone}", 0, 1)
    pdf.ln(3)

    # Items table header
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(8, 7, '#', 1, 0, 'C', True)
    pdf.cell(52, 7, 'Description', 1, 0, 'L', True)
    pdf.cell(15, 7, 'HSN', 1, 0, 'C', True)
    pdf.cell(12, 7, 'Qty', 1, 0, 'C', True)
    pdf.cell(22, 7, 'Rate', 1, 0, 'R', True)
    pdf.cell(18, 7, 'Disc', 1, 0, 'R', True)
    pdf.cell(15, 7, 'GST%', 1, 0, 'C', True)
    pdf.cell(20, 7, 'GST Amt', 1, 0, 'R', True)
    pdf.cell(28, 7, 'Total', 1, 1, 'R', True)

    # Items
    pdf.set_font('Helvetica', '', 9)
    subtotal = 0
    total_gst = 0
    for idx, item in enumerate(sale.items, 1):
        variant = item.variant
        desc = variant.display_name
        hsn = variant.product.hsn_code or ''
        line_disc = item.discount_amount or 0
        taxable = item.unit_price * item.quantity - line_disc
        subtotal += taxable
        total_gst += item.gst_amount or 0

        pdf.cell(8, 6, str(idx), 1, 0, 'C')
        pdf.cell(52, 6, desc[:30], 1, 0, 'L')
        pdf.cell(15, 6, hsn[:8], 1, 0, 'C')
        pdf.cell(12, 6, str(item.quantity), 1, 0, 'C')
        pdf.cell(22, 6, f"{item.unit_price:,.2f}", 1, 0, 'R')
        pdf.cell(18, 6, f"{line_disc:,.2f}" if line_disc else '-', 1, 0, 'R')
        pdf.cell(15, 6, f"{item.gst_percent:g}%", 1, 0, 'C')
        pdf.cell(20, 6, f"{(item.gst_amount or 0):,.2f}", 1, 0, 'R')
        pdf.cell(28, 6, f"{(item.total_amount or 0):,.2f}", 1, 1, 'R')

    pdf.ln(2)

    # Totals
    x_label = 125
    w_label = 40
    w_val = 25

    pdf.set_font('Helvetica', '', 9)
    pdf.set_x(x_label)
    pdf.cell(w_label, 6, 'Taxable value:', 0, 0, 'R')
    pdf.cell(w_val, 6, f"{subtotal:,.2f}", 0, 1, 'R')

    # GST breakdown
    home_state = ((profile.state if profile else None) or 'Karnataka').strip().lower()
    buyer_state = (customer.state or '').strip().lower()
    is_intrastate = buyer_state in (home_state, '')
    if is_intrastate:
        half_gst = total_gst / 2
        pdf.set_x(x_label)
        pdf.cell(w_label, 6, 'CGST:', 0, 0, 'R')
        pdf.cell(w_val, 6, f"{half_gst:,.2f}", 0, 1, 'R')
        pdf.set_x(x_label)
        pdf.cell(w_label, 6, 'SGST:', 0, 0, 'R')
        pdf.cell(w_val, 6, f"{half_gst:,.2f}", 0, 1, 'R')
    else:
        pdf.set_x(x_label)
        pdf.cell(w_label, 6, 'IGST:', 0, 0, 'R')
        pdf.cell(w_val, 6, f"{total_gst:,.2f}", 0, 1, 'R')

    if sale.transport_charge:
        pdf.set_x(x_label)
        pdf.cell(w_label, 6, 'Transport:', 0, 0, 'R')
        pdf.cell(w_val, 6, f"{sale.transport_charge:,.2f}", 0, 1, 'R')

    if sale.discount_amount:
        pdf.set_x(x_label)
        pdf.cell(w_label, 6, 'Order discount:', 0, 0, 'R')
        pdf.cell(w_val, 6, f"-{sale.discount_amount:,.2f}", 0, 1, 'R')

    if sale.is_package and sale.package_type:
        pdf.set_x(x_label)
        pdf.set_font('Helvetica', 'I', 8)
        pdf.cell(w_label + w_val, 6, f"({sale.package_type} applied)", 0, 1, 'R')

    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_x(x_label)
    pdf.cell(w_label, 8, 'GRAND TOTAL:', 0, 0, 'R')
    pdf.cell(w_val, 8, f"{sale.grand_total:,.2f}", 0, 1, 'R')

    # Amount in words
    pdf.ln(2)
    pdf.set_font('Helvetica', 'I', 9)
    pdf.cell(0, 6, amount_in_words(sale.grand_total), 0, 1)

    # Bank details
    if profile and profile.bank_name:
        pdf.ln(3)
        pdf.set_font('Helvetica', 'B', 9)
        pdf.cell(0, 5, 'Bank Details:', 0, 1)
        pdf.set_font('Helvetica', '', 9)
        pdf.cell(0, 5, f"Bank: {profile.bank_name}", 0, 1)
        pdf.cell(0, 5, f"A/C No: {profile.bank_account}", 0, 1)
        pdf.cell(0, 5, f"IFSC: {profile.bank_ifsc}", 0, 1)

    # Signature
    pdf.ln(10)
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(95, 5, 'Terms: Goods once sold will not be taken back.', 0, 0)
    pdf.cell(95, 5, f"For {profile.name if profile else 'Sportspedal'}", 0, 1, 'R')
    pdf.ln(10)
    pdf.cell(95, 5, '', 0, 0)
    pdf.cell(95, 5, 'Authorized Signatory', 0, 1, 'R')

    buf = io.BytesIO()
    pdf.output(buf)
    buf.seek(0)
    return send_file(buf, mimetype='application/pdf',
                     download_name=f"Invoice_{sale.invoice_number.replace('/', '-')}.pdf",
                     as_attachment=True)
