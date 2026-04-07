from flask import send_file
from fpdf import FPDF
import io


def generate_challan(sale, profile):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Title
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 10, 'DELIVERY CHALLAN', 0, 1, 'C')
    pdf.ln(2)

    # Business details
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(0, 6, profile.name if profile else 'Sportspedal', 0, 1)
    pdf.set_font('Helvetica', '', 9)
    if profile and profile.address:
        pdf.cell(0, 5, f"{profile.address}, {profile.city or ''}, {profile.state or ''}", 0, 1)
    if profile and profile.phone:
        pdf.cell(0, 5, f"Phone: {profile.phone}", 0, 1)
    pdf.ln(3)

    # Challan info
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(95, 5, f"Challan No: {sale.challan_number or '-'}", 0, 0)
    pdf.cell(95, 5, f"Date: {sale.sale_date}", 0, 1)
    if sale.invoice_number:
        pdf.cell(95, 5, f"Ref Invoice: {sale.invoice_number}", 0, 1)
    pdf.ln(2)

    # Deliver To
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(0, 6, 'Deliver To:', 0, 1)
    pdf.set_font('Helvetica', '', 9)
    customer = sale.customer
    pdf.cell(0, 5, customer.name, 0, 1)
    if customer.address:
        pdf.cell(0, 5, customer.address, 0, 1)
    if customer.city:
        pdf.cell(0, 5, f"{customer.city}, {customer.state or ''}", 0, 1)
    if customer.phone:
        pdf.cell(0, 5, f"Phone: {customer.phone}", 0, 1)
    pdf.ln(3)

    # Items table (no prices)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(10, 7, '#', 1, 0, 'C', True)
    pdf.cell(80, 7, 'Description', 1, 0, 'L', True)
    pdf.cell(15, 7, 'SKU', 1, 0, 'C', True)
    pdf.cell(20, 7, 'Qty', 1, 0, 'C', True)
    pdf.cell(65, 7, 'Remarks', 1, 1, 'L', True)

    pdf.set_font('Helvetica', '', 9)
    total_qty = 0
    for idx, item in enumerate(sale.items, 1):
        variant = item.variant
        total_qty += item.quantity
        pdf.cell(10, 6, str(idx), 1, 0, 'C')
        pdf.cell(80, 6, variant.display_name[:45], 1, 0, 'L')
        pdf.cell(15, 6, variant.sku_code or '', 1, 0, 'C')
        pdf.cell(20, 6, str(item.quantity), 1, 0, 'C')
        pdf.cell(65, 6, '', 1, 1, 'L')

    # Total items
    pdf.set_font('Helvetica', 'B', 9)
    pdf.cell(90, 6, 'Total Items:', 1, 0, 'R')
    pdf.cell(15, 6, '', 1, 0)
    pdf.cell(20, 6, str(total_qty), 1, 0, 'C')
    pdf.cell(65, 6, '', 1, 1)

    # Transport
    pdf.ln(5)
    pdf.set_font('Helvetica', '', 9)
    if sale.transport_mode:
        pdf.cell(0, 5, f"Transport Mode: {sale.transport_mode}", 0, 1)
    if sale.notes:
        pdf.cell(0, 5, f"Notes: {sale.notes}", 0, 1)

    # Signatures
    pdf.ln(15)
    pdf.cell(95, 5, 'Dispatched By: _______________', 0, 0)
    pdf.cell(95, 5, 'Received By: _______________', 0, 1, 'R')
    pdf.ln(10)
    pdf.cell(95, 5, 'Date: _______________', 0, 0)
    pdf.cell(95, 5, 'Date: _______________', 0, 1, 'R')

    buf = io.BytesIO()
    pdf.output(buf)
    buf.seek(0)
    challan_num = (sale.challan_number or str(sale.id)).replace('/', '-')
    return send_file(buf, mimetype='application/pdf',
                     download_name=f"Challan_{challan_num}.pdf",
                     as_attachment=True)
