from flask import Blueprint, render_template
from app import db
from app.models import Product, ProductVariant, SaleOrder, SaleItem, PurchaseOrder, PurchaseItem
from app.services.stock import get_inventory_data
from sqlalchemy import func
from datetime import datetime

bp = Blueprint('dashboard', __name__)


@bp.route('/')
def index():
    total_products = Product.query.filter_by(is_active=True).count()
    total_variants = ProductVariant.query.filter_by(is_active=True).count()
    recent_purchases = PurchaseOrder.query.order_by(PurchaseOrder.created_at.desc()).limit(5).all()
    recent_sales = SaleOrder.query.order_by(SaleOrder.created_at.desc()).limit(5).all()

    # Financial metrics
    # Total purchase cost (what we paid to suppliers, incl GST)
    total_purchase_cost = db.session.query(func.sum(PurchaseItem.total_amount)).scalar() or 0

    # Total purchase cost (excl GST) - this is what we owe/paid
    purchase_taxable = db.session.query(
        func.sum(PurchaseItem.unit_price * PurchaseItem.quantity_received)
    ).scalar() or 0
    purchase_gst = db.session.query(func.sum(PurchaseItem.gst_amount)).scalar() or 0

    # Revenue from sales (what customers paid us)
    total_revenue = 0
    total_sale_gst = 0
    for sale in SaleOrder.query.all():
        total_revenue += sale.grand_total
        total_sale_gst += sale.total_gst

    # Cost of goods sold (cost price of items we sold)
    total_cogs = 0
    for si in SaleItem.query.all():
        cost = si.variant.effective_cost or 0
        total_cogs += cost * si.quantity

    gross_profit = total_revenue - total_cogs
    profit_margin = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0

    # Inventory value (stock on hand at cost)
    inventory = get_inventory_data()
    stock_value = sum(item['stock_value'] for item in inventory)
    total_stock_units = sum(item['stock'] for item in inventory)

    # Low stock items
    low_stock = [item for item in inventory if 0 < item['stock'] < 3]
    zero_stock = [item for item in inventory if item['stock'] <= 0 and item['inward'] > 0]

    # Coach vs Public split
    coach_data = {'orders': 0, 'revenue': 0, 'qty': 0, 'cogs': 0}
    public_data = {'orders': 0, 'revenue': 0, 'qty': 0, 'cogs': 0}
    for sale in SaleOrder.query.all():
        bucket = coach_data if sale.customer.customer_type == 'coach' else public_data
        bucket['orders'] += 1
        bucket['revenue'] += sale.grand_total
        for item in sale.items:
            bucket['qty'] += item.quantity
            bucket['cogs'] += (item.variant.effective_cost or 0) * item.quantity
    coach_data['profit'] = coach_data['revenue'] - coach_data['cogs']
    public_data['profit'] = public_data['revenue'] - public_data['cogs']

    return render_template('dashboard.html',
                           now=datetime.now(),
                           total_products=total_products,
                           total_variants=total_variants,
                           recent_purchases=recent_purchases,
                           recent_sales=recent_sales,
                           total_purchase_cost=total_purchase_cost,
                           purchase_taxable=purchase_taxable,
                           purchase_gst=purchase_gst,
                           total_revenue=total_revenue,
                           total_sale_gst=total_sale_gst,
                           total_cogs=total_cogs,
                           gross_profit=gross_profit,
                           profit_margin=profit_margin,
                           stock_value=stock_value,
                           total_stock_units=total_stock_units,
                           low_stock=low_stock,
                           zero_stock=zero_stock,
                           coach_data=coach_data,
                           public_data=public_data)
