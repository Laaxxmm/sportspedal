from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import SaleOrder, SaleItem, Customer, ProductVariant, Product, BusinessProfile, PackagePrice
from app.services.stock import get_stock_map
from datetime import date

bp = Blueprint('sales', __name__)


def generate_invoice_number():
    profile = BusinessProfile.query.first()
    prefix = profile.invoice_prefix if profile else 'SP'
    fy = profile.current_fy if profile else '2025-26'
    last = SaleOrder.query.filter(SaleOrder.invoice_number.isnot(None)).order_by(SaleOrder.id.desc()).first()
    if last and last.invoice_number:
        try:
            seq = int(last.invoice_number.split('/')[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1
    return f"{prefix}/{fy}/{seq:03d}"


def generate_challan_number():
    profile = BusinessProfile.query.first()
    prefix = profile.challan_prefix if profile else 'DC'
    fy = profile.current_fy if profile else '2025-26'
    last = SaleOrder.query.filter(SaleOrder.challan_number.isnot(None)).order_by(SaleOrder.id.desc()).first()
    if last and last.challan_number:
        try:
            seq = int(last.challan_number.split('/')[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1
    return f"{prefix}/{fy}/{seq:03d}"


def detect_package(items_data, customer_type):
    """Check if items form a complete package (skate + helmet + guards + bag)."""
    categories = {}
    for item in items_data:
        variant = ProductVariant.query.get(item['variant_id'])
        if variant:
            cat = variant.product.category
            if cat not in categories:
                categories[cat] = variant.product
    has_skate = 'skates' in categories
    has_helmet = 'helmet' in categories
    has_guards = 'guards' in categories
    has_bag = 'bag' in categories

    if has_skate and has_helmet and has_guards and has_bag:
        skate_product = categories['skates']
        pkg = PackagePrice.query.filter_by(skate_product_id=skate_product.id).first()
        if pkg:
            price = pkg.coach_price if customer_type == 'coach' else pkg.public_price
            return pkg, price
    return None, 0


@bp.route('/')
@login_required
def list_sales():
    sales = SaleOrder.query.order_by(SaleOrder.sale_date.desc()).all()
    return render_template('sales/list.html', sales=sales)


@bp.route('/download')
@login_required
def download_sales():
    from app.services.excel_export import export_sales
    sales = SaleOrder.query.order_by(SaleOrder.sale_date.desc()).all()
    return export_sales(sales)


@bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_sale():
    if request.method == 'POST':
        customer = Customer.query.get(int(request.form['customer_id']))
        sale = SaleOrder(
            invoice_number=generate_invoice_number(),
            challan_number=generate_challan_number(),
            customer_id=customer.id,
            sale_date=request.form.get('sale_date', date.today().isoformat()),
            status=request.form.get('status', 'confirmed'),
            payment_status=request.form.get('payment_status', 'paid'),
            transport_mode=request.form.get('transport_mode', ''),
            transport_charge=float(request.form.get('transport_charge', 0)),
            discount_amount=float(request.form.get('discount_amount', 0)),
            notes=request.form.get('notes', ''),
        )
        db.session.add(sale)
        db.session.flush()

        variant_ids = request.form.getlist('variant_id[]')
        qtys = request.form.getlist('qty[]')
        unit_prices = request.form.getlist('unit_price[]')
        gst_percents = request.form.getlist('gst_percent[]')

        items_data = []
        for i in range(len(variant_ids)):
            if not variant_ids[i]:
                continue
            items_data.append({
                'variant_id': int(variant_ids[i]),
                'quantity': int(qtys[i] or 1),
                'unit_price': float(unit_prices[i] or 0),
                'gst_percent': float(gst_percents[i] or 12.0),
            })

        # Check for package pricing
        use_package = request.form.get('apply_package') == '1'
        if use_package:
            pkg, pkg_price = detect_package(items_data, customer.customer_type)
            if pkg:
                sale.is_package = True
                sale.package_type = pkg.name
                # Distribute package price proportionally across items
                individual_total = sum(d['unit_price'] * d['quantity'] for d in items_data)
                ratio = pkg_price / individual_total if individual_total > 0 else 1

                for d in items_data:
                    adjusted_price = round(d['unit_price'] * ratio, 2)
                    taxable = adjusted_price * d['quantity']
                    gst_amt = taxable * d['gst_percent'] / 100
                    item = SaleItem(
                        sale_order_id=sale.id,
                        variant_id=d['variant_id'],
                        quantity=d['quantity'],
                        unit_price=adjusted_price,
                        gst_percent=d['gst_percent'],
                        gst_amount=gst_amt,
                        total_amount=taxable + gst_amt,
                    )
                    db.session.add(item)
            else:
                use_package = False

        if not use_package:
            for d in items_data:
                taxable = d['unit_price'] * d['quantity']
                gst_amt = taxable * d['gst_percent'] / 100
                item = SaleItem(
                    sale_order_id=sale.id,
                    variant_id=d['variant_id'],
                    quantity=d['quantity'],
                    unit_price=d['unit_price'],
                    gst_percent=d['gst_percent'],
                    gst_amount=gst_amt,
                    total_amount=taxable + gst_amt,
                )
                db.session.add(item)

        db.session.commit()
        flash(f'Sale {sale.invoice_number} created.', 'success')
        return redirect(url_for('sales.list_sales'))

    customers = Customer.query.order_by(Customer.name).all()
    variants = (db.session.query(ProductVariant, Product)
                .join(Product)
                .filter(ProductVariant.is_active == True, Product.is_active == True)
                .order_by(Product.name, ProductVariant.color, ProductVariant.size)
                .all())
    stock_map = get_stock_map()
    packages = PackagePrice.query.all()
    return render_template('sales/form.html', sale=None, customers=customers,
                           variants=variants, stock_map=stock_map, packages=packages)


@bp.route('/<int:id>')
@login_required
def view_sale(id):
    sale = SaleOrder.query.get_or_404(id)
    profile = BusinessProfile.query.first()
    return render_template('sales/detail.html', sale=sale, profile=profile)


@bp.route('/<int:id>/invoice')
@login_required
def download_invoice(id):
    from app.services.invoice_pdf import generate_invoice
    sale = SaleOrder.query.get_or_404(id)
    profile = BusinessProfile.query.first()
    return generate_invoice(sale, profile)


@bp.route('/<int:id>/challan')
@login_required
def download_challan(id):
    from app.services.challan_pdf import generate_challan
    sale = SaleOrder.query.get_or_404(id)
    profile = BusinessProfile.query.first()
    return generate_challan(sale, profile)
