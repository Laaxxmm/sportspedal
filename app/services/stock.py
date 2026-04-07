from app import db
from app.models import ProductVariant, Product, PurchaseItem, PurchaseOrder, SaleItem
from sqlalchemy import func


def get_stock_map():
    """Returns dict of {variant_id: current_stock}."""
    inward = dict(
        db.session.query(PurchaseItem.variant_id, func.sum(PurchaseItem.quantity_received))
        .join(PurchaseOrder)
        .filter(PurchaseOrder.status == 'delivered')
        .group_by(PurchaseItem.variant_id)
        .all()
    )
    outward = dict(
        db.session.query(SaleItem.variant_id, func.sum(SaleItem.quantity))
        .group_by(SaleItem.variant_id)
        .all()
    )
    all_variants = ProductVariant.query.filter_by(is_active=True).all()
    stock = {}
    for v in all_variants:
        stock[v.id] = (inward.get(v.id, 0) or 0) - (outward.get(v.id, 0) or 0)
    return stock


def get_inventory_data():
    """Returns list of dicts with full inventory details per variant."""
    stock_map = get_stock_map()

    inward_map = dict(
        db.session.query(PurchaseItem.variant_id, func.sum(PurchaseItem.quantity_received))
        .join(PurchaseOrder)
        .filter(PurchaseOrder.status == 'delivered')
        .group_by(PurchaseItem.variant_id)
        .all()
    )
    outward_map = dict(
        db.session.query(SaleItem.variant_id, func.sum(SaleItem.quantity))
        .group_by(SaleItem.variant_id)
        .all()
    )

    variants = (db.session.query(ProductVariant, Product)
                .join(Product)
                .filter(ProductVariant.is_active == True, Product.is_active == True)
                .order_by(Product.category, Product.name, ProductVariant.color, ProductVariant.size)
                .all())

    result = []
    for variant, product in variants:
        inward = inward_map.get(variant.id, 0) or 0
        outward = outward_map.get(variant.id, 0) or 0
        stock = stock_map.get(variant.id, 0)
        result.append({
            'variant_id': variant.id,
            'product_name': product.name,
            'category': product.category,
            'color': variant.color or '-',
            'size': variant.size or '-',
            'sku': variant.sku_code,
            'inward': inward,
            'outward': outward,
            'stock': stock,
            'cost_price': variant.effective_cost,
            'stock_value': stock * (variant.effective_cost or 0),
        })
    return result
