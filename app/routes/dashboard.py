from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from app import db
from app.models import (Product, ProductVariant, SaleOrder, SaleItem, PurchaseOrder,
                        PurchaseItem, Location, SupplierPayment)
from app.services.stock import get_inventory_data
from app.routes.payments import get_supplier_balance
from sqlalchemy import func
from datetime import datetime

bp = Blueprint('dashboard', __name__)


def compute_dashboard_data(location_id=None):
    """Compute all dashboard metrics, optionally scoped to a location."""
    total_products = Product.query.filter_by(is_active=True).count()
    total_variants = ProductVariant.query.filter_by(is_active=True).count()

    # Recent activity (scoped)
    po_query = PurchaseOrder.query
    so_query = SaleOrder.query
    if location_id:
        po_query = po_query.filter_by(location_id=location_id)
        so_query = so_query.filter_by(location_id=location_id)
    recent_purchases = po_query.order_by(PurchaseOrder.created_at.desc()).limit(5).all()
    recent_sales = so_query.order_by(SaleOrder.created_at.desc()).limit(5).all()

    # Purchase cost (scoped)
    pi_query = db.session.query(func.sum(PurchaseItem.total_amount)).join(PurchaseOrder)
    pt_query = db.session.query(func.sum(PurchaseItem.unit_price * PurchaseItem.quantity_received)).join(PurchaseOrder)
    pg_query = db.session.query(func.sum(PurchaseItem.gst_amount)).join(PurchaseOrder)
    if location_id:
        pi_query = pi_query.filter(PurchaseOrder.location_id == location_id)
        pt_query = pt_query.filter(PurchaseOrder.location_id == location_id)
        pg_query = pg_query.filter(PurchaseOrder.location_id == location_id)
    total_purchase_cost = pi_query.scalar() or 0
    purchase_taxable = pt_query.scalar() or 0
    purchase_gst = pg_query.scalar() or 0

    # Revenue (scoped)
    all_sales = so_query.all() if location_id else SaleOrder.query.all()
    total_revenue = sum(s.grand_total for s in all_sales)
    total_sale_gst = sum(s.total_gst for s in all_sales)

    # Units sold
    si_query = db.session.query(func.sum(SaleItem.quantity)).join(SaleOrder)
    if location_id:
        si_query = si_query.filter(SaleOrder.location_id == location_id)
    total_units_sold = si_query.scalar() or 0

    # COGS (scoped)
    total_cogs = 0
    sale_items_query = SaleItem.query.join(SaleOrder)
    if location_id:
        sale_items_query = sale_items_query.filter(SaleOrder.location_id == location_id)
    for si in sale_items_query.all():
        total_cogs += si.effective_cost * si.quantity

    gross_profit = total_revenue - total_cogs
    profit_margin = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0

    # Inventory (scoped)
    inventory = get_inventory_data(location_id)
    stock_value = sum(item['stock_value'] for item in inventory)
    total_stock_units = sum(item['stock'] for item in inventory)
    low_stock = [item for item in inventory if 0 < item['stock'] < 3]
    zero_stock = [item for item in inventory if item['stock'] <= 0 and item['inward'] > 0]

    # Coach vs Public (scoped)
    coach_data = {'orders': 0, 'revenue': 0, 'qty': 0, 'cogs': 0}
    public_data = {'orders': 0, 'revenue': 0, 'qty': 0, 'cogs': 0}
    for sale in all_sales:
        bucket = coach_data if sale.customer.customer_type == 'coach' else public_data
        bucket['orders'] += 1
        bucket['revenue'] += sale.grand_total
        for item in sale.items:
            bucket['qty'] += item.quantity
            bucket['cogs'] += item.effective_cost * item.quantity
    # Coach = pass-through (zero profit), Public = actual margin
    coach_data['profit'] = 0
    public_data['profit'] = public_data['revenue'] - public_data['cogs']

    # Supplier balance (global only, not scoped)
    supplier_balance = get_supplier_balance()

    return {
        'total_products': total_products, 'total_variants': total_variants,
        'recent_purchases': recent_purchases, 'recent_sales': recent_sales,
        'total_purchase_cost': total_purchase_cost,
        'purchase_taxable': purchase_taxable, 'purchase_gst': purchase_gst,
        'total_revenue': total_revenue, 'total_sale_gst': total_sale_gst,
        'total_units_sold': total_units_sold,
        'total_cogs': total_cogs, 'gross_profit': gross_profit, 'profit_margin': profit_margin,
        'stock_value': stock_value, 'total_stock_units': total_stock_units,
        'low_stock': low_stock, 'zero_stock': zero_stock,
        'coach_data': coach_data, 'public_data': public_data,
        'supplier_balance': supplier_balance,
    }


@bp.route('/')
@login_required
def index():
    # Determine location scope
    location_id = None
    selected_location = None

    if current_user.is_superadmin:
        # Superadmin can drill down by location
        loc_param = request.args.get('location_id', type=int)
        if loc_param:
            location_id = loc_param
            selected_location = Location.query.get(loc_param)
    else:
        # Admin sees only their location
        location_id = current_user.location_id

    data = compute_dashboard_data(location_id)

    # Available locations for drill-down (superadmin only)
    locations = []
    if current_user.is_superadmin:
        locations = Location.query.filter_by(is_active=True).order_by(Location.state, Location.district).all()

    return render_template('dashboard.html',
                           now=datetime.now(),
                           selected_location=selected_location,
                           locations=locations,
                           **data)
