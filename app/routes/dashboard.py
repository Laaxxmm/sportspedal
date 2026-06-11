from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from app import db
from app.models import (Product, ProductVariant, SaleOrder, SaleItem, PurchaseOrder,
                        PurchaseItem, Location, SupplierPayment, Customer,
                        StockAdjustment, StockAdjustmentItem)
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
    # Stock value derived from purchase cost - COGS to guarantee they balance
    stock_value = total_purchase_cost - total_cogs
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

    # Override overall profit to match: only public profit counts (coach is pass-through)
    gross_profit = public_data['profit']
    profit_margin = (gross_profit / public_data['revenue'] * 100) if public_data['revenue'] > 0 else 0

    # Supplier balance (global only, not scoped)
    supplier_balance = get_supplier_balance()

    # Buyer advances (global) - prepaid balances and overdrawn dues
    from app.services.customer_account import customer_advance_map
    adv = customer_advance_map()
    buyer_advance_held = sum(v for v in adv.values() if v > 0)
    buyer_advance_due = sum(-v for v in adv.values() if v < 0)

    # Transport costs (scoped) - by who bears them
    tq = db.session.query(func.sum(SaleOrder.shipping_cost)).filter(
        SaleOrder.shipping_paid_by == 'supplier', SaleOrder.shipping_cost > 0)
    tq_self = db.session.query(func.sum(SaleOrder.shipping_cost)).filter(
        SaleOrder.shipping_cost > 0,
        (SaleOrder.shipping_paid_by.is_(None)) | (SaleOrder.shipping_paid_by != 'supplier'))
    tq_cust = db.session.query(func.sum(SaleOrder.transport_charge)).filter(SaleOrder.transport_charge > 0)
    if location_id:
        tq = tq.filter(SaleOrder.location_id == location_id)
        tq_self = tq_self.filter(SaleOrder.location_id == location_id)
        tq_cust = tq_cust.filter(SaleOrder.location_id == location_id)
    transport_supplier = tq.scalar() or 0
    transport_self = tq_self.scalar() or 0
    transport_customer = tq_cust.scalar() or 0
    # Standalone transport expenses (not tied to a sale) - global, add on the all-locations view
    if not location_id:
        from app.models import TransportExpense
        transport_supplier += db.session.query(func.sum(TransportExpense.amount)).filter(
            TransportExpense.borne_by == 'supplier').scalar() or 0
        transport_self += db.session.query(func.sum(TransportExpense.amount)).filter(
            TransportExpense.borne_by == 'self').scalar() or 0
    transport_total = transport_supplier + transport_self + transport_customer

    # Bulk orders
    bulk_q = SaleOrder.query.filter_by(is_bulk=True)
    if location_id:
        bulk_q = bulk_q.filter_by(location_id=location_id)
    bulk_orders = bulk_q.all()
    bulk_data = {
        'count': len(bulk_orders),
        'qty': sum(sum(i.quantity for i in s.items) for s in bulk_orders),
        'revenue': sum(s.grand_total for s in bulk_orders),
    }

    # Adjustments breakdown
    adj_q = (db.session.query(StockAdjustment.adjustment_type,
                              func.sum(StockAdjustmentItem.quantity),
                              func.sum(StockAdjustmentItem.unit_cost * StockAdjustmentItem.quantity))
             .join(StockAdjustmentItem)
             .filter(StockAdjustment.status == 'completed'))
    if location_id:
        adj_q = adj_q.filter(StockAdjustment.location_id == location_id)
    adj_breakdown = adj_q.group_by(StockAdjustment.adjustment_type).all()

    promo_data = {'qty': 0, 'value': 0}
    damage_data = {'qty': 0, 'value': 0}
    for atype, qty, value in adj_breakdown:
        if atype == 'promotional':
            promo_data = {'qty': qty or 0, 'value': value or 0}
        elif atype in ('damaged', 'returned_to_supplier'):
            damage_data['qty'] += qty or 0
            damage_data['value'] += value or 0

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
        'buyer_advance_held': buyer_advance_held,
        'buyer_advance_due': buyer_advance_due,
        'transport_supplier': transport_supplier,
        'transport_self': transport_self,
        'transport_customer': transport_customer,
        'transport_total': transport_total,
        'bulk_data': bulk_data,
        'promo_data': promo_data,
        'damage_data': damage_data,
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
