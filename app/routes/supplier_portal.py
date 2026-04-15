"""Read-only supplier portal - shows what they've sent, costs, payments, stock across locations."""
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app import db
from app.models import (PurchaseOrder, PurchaseItem, ProductVariant, Product,
                        Location, SupplierPayment, Supplier)
from app.services.stock import get_inventory_data, get_stock_map
from sqlalchemy import func

bp = Blueprint('supplier_portal', __name__, url_prefix='/supplier-portal')


def supplier_required(f):
    from functools import wraps
    from flask import redirect, url_for, flash
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.is_supplier_user and not current_user.is_superadmin:
            flash('Access denied.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated


def get_supplier_id():
    """Get the supplier_id for the current user."""
    if current_user.is_superadmin:
        return Supplier.query.first().id if Supplier.query.first() else None
    return current_user.supplier_id


@bp.route('/')
@login_required
@supplier_required
def portal_dashboard():
    sid = get_supplier_id()
    if not sid:
        return render_template('supplier_portal/dashboard.html', supplier=None, data={})

    supplier = Supplier.query.get(sid)

    # What they sent us: all purchase orders for this supplier
    orders = (PurchaseOrder.query
              .filter_by(supplier_id=sid)
              .order_by(PurchaseOrder.order_date.desc()).all())

    # Total cost breakdown
    total_cost = sum(po.total_amount for po in orders)
    total_taxable = db.session.query(
        func.sum(PurchaseItem.unit_price * PurchaseItem.quantity_received)
    ).join(PurchaseOrder).filter(PurchaseOrder.supplier_id == sid).scalar() or 0
    total_gst = db.session.query(
        func.sum(PurchaseItem.gst_amount)
    ).join(PurchaseOrder).filter(PurchaseOrder.supplier_id == sid).scalar() or 0

    # Total units sent
    total_units = db.session.query(
        func.sum(PurchaseItem.quantity_received)
    ).join(PurchaseOrder).filter(PurchaseOrder.supplier_id == sid).scalar() or 0

    # Payments made
    total_paid = db.session.query(
        func.sum(SupplierPayment.amount)
    ).filter(SupplierPayment.supplier_id == sid).scalar() or 0
    payments = (SupplierPayment.query
                .filter_by(supplier_id=sid)
                .order_by(SupplierPayment.payment_date.desc()).all())

    # Shipping credits (supplier owes for shipping)
    from app.models import SaleOrder
    shipping_credit = db.session.query(func.sum(SaleOrder.shipping_cost)).filter(
        SaleOrder.shipping_paid_by == 'supplier', SaleOrder.shipping_cost > 0
    ).scalar() or 0

    shipping_settled = db.session.query(func.sum(SupplierPayment.shipping_deduction)).filter(
        SupplierPayment.supplier_id == sid
    ).scalar() or 0

    shipping_pending = shipping_credit - shipping_settled
    balance = total_cost - total_paid - shipping_pending

    # Stock by location
    locations = Location.query.filter_by(is_active=True).order_by(Location.state, Location.district).all()
    location_stock = []
    for loc in locations:
        inv = get_inventory_data(location_id=loc.id)
        total_stock = sum(item['stock'] for item in inv)
        total_value = sum(item['stock_value'] for item in inv)
        if total_stock > 0 or any(item['inward'] > 0 for item in inv):
            location_stock.append({
                'location': loc,
                'stock': total_stock,
                'value': total_value,
                'stock_items': [i for i in inv if i['stock'] > 0 or i['inward'] > 0],
            })

    # Items that need restocking (stock = 0 but were previously stocked)
    all_inv = get_inventory_data()
    restock_needed = [i for i in all_inv if i['stock'] <= 0 and i['inward'] > 0]

    # Per-product summary: what was sent, current stock across all locations
    product_summary = {}
    total_units_sold = 0
    total_cogs = 0
    for item in all_inv:
        name = item['product_name']
        if name not in product_summary:
            product_summary[name] = {'name': name, 'category': item['category'],
                                      'image_url': item.get('image_url'),
                                      'total_sent': 0, 'total_stock': 0, 'total_sold': 0,
                                      'cost_of_sold': 0}
        product_summary[name]['total_sent'] += item['inward']
        product_summary[name]['total_stock'] += item['stock']
        product_summary[name]['total_sold'] += item['outward']
        product_summary[name]['cost_of_sold'] += item['outward'] * item['cost_price']
        total_units_sold += item['outward']
        total_cogs += item['outward'] * item['cost_price']

    return render_template('supplier_portal/dashboard.html',
                           supplier=supplier, orders=orders,
                           total_cost=total_cost, total_taxable=total_taxable,
                           total_gst=total_gst, total_units=total_units,
                           total_units_sold=total_units_sold,
                           total_cogs=total_cogs,
                           total_paid=total_paid, balance=balance,
                           shipping_credit=shipping_credit,
                           shipping_pending=shipping_pending,
                           payments=payments,
                           location_stock=location_stock,
                           restock_needed=restock_needed,
                           product_summary=sorted(product_summary.values(), key=lambda x: x['name']))
