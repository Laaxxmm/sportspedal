from app import db
from app.models import (ProductVariant, Product, PurchaseItem, PurchaseOrder,
                        SaleItem, SaleOrder, StockTransferItem, StockTransfer)
from sqlalchemy import func


def get_stock_map(location_id=None):
    """Returns dict of {variant_id: current_stock}. If location_id is given, scoped to that location."""
    # Inward from purchases
    inward_q = (db.session.query(PurchaseItem.variant_id, func.sum(PurchaseItem.quantity_received))
                .join(PurchaseOrder)
                .filter(PurchaseOrder.status == 'delivered'))
    if location_id:
        inward_q = inward_q.filter(PurchaseOrder.location_id == location_id)
    inward = dict(inward_q.group_by(PurchaseItem.variant_id).all())

    # Outward from sales
    outward_q = db.session.query(SaleItem.variant_id, func.sum(SaleItem.quantity)).join(SaleOrder)
    if location_id:
        outward_q = outward_q.filter(SaleOrder.location_id == location_id)
    outward = dict(outward_q.group_by(SaleItem.variant_id).all())

    # Transfers in (completed transfers TO this location)
    transfers_in = {}
    transfers_out = {}
    if location_id:
        tin = dict(
            db.session.query(StockTransferItem.variant_id, func.sum(StockTransferItem.quantity))
            .join(StockTransfer)
            .filter(StockTransfer.to_location_id == location_id, StockTransfer.status == 'completed')
            .group_by(StockTransferItem.variant_id).all()
        )
        transfers_in = tin

        tout = dict(
            db.session.query(StockTransferItem.variant_id, func.sum(StockTransferItem.quantity))
            .join(StockTransfer)
            .filter(StockTransfer.from_location_id == location_id,
                    StockTransfer.status.in_(['completed', 'in_transit']))
            .group_by(StockTransferItem.variant_id).all()
        )
        transfers_out = tout

    all_variants = ProductVariant.query.filter_by(is_active=True).all()
    stock = {}
    for v in all_variants:
        s = (inward.get(v.id, 0) or 0) + (transfers_in.get(v.id, 0) or 0) \
            - (outward.get(v.id, 0) or 0) - (transfers_out.get(v.id, 0) or 0)
        stock[v.id] = s
    return stock


def get_inventory_data(location_id=None):
    """Returns list of dicts with full inventory details per variant."""
    stock_map = get_stock_map(location_id)

    inward_q = (db.session.query(PurchaseItem.variant_id, func.sum(PurchaseItem.quantity_received))
                .join(PurchaseOrder).filter(PurchaseOrder.status == 'delivered'))
    if location_id:
        inward_q = inward_q.filter(PurchaseOrder.location_id == location_id)
    inward_map = dict(inward_q.group_by(PurchaseItem.variant_id).all())

    outward_q = db.session.query(SaleItem.variant_id, func.sum(SaleItem.quantity)).join(SaleOrder)
    if location_id:
        outward_q = outward_q.filter(SaleOrder.location_id == location_id)
    outward_map = dict(outward_q.group_by(SaleItem.variant_id).all())

    variants = (db.session.query(ProductVariant, Product)
                .join(Product)
                .filter(ProductVariant.is_active == True, Product.is_active == True)
                .order_by(Product.category, Product.name, ProductVariant.color, ProductVariant.size)
                .all())

    # Weighted average purchase price per variant (excl GST)
    avg_cost_q = (db.session.query(
        PurchaseItem.variant_id,
        func.sum(PurchaseItem.unit_price * PurchaseItem.quantity_received),
        func.sum(PurchaseItem.quantity_received)
    ).join(PurchaseOrder).filter(PurchaseOrder.status == 'delivered'))
    if location_id:
        avg_cost_q = avg_cost_q.filter(PurchaseOrder.location_id == location_id)
    avg_cost_data = avg_cost_q.group_by(PurchaseItem.variant_id).all()
    avg_cost_map = {}
    for vid, total_cost, total_qty in avg_cost_data:
        avg_cost_map[vid] = total_cost / total_qty if total_qty else 0

    result = []
    for variant, product in variants:
        inward = inward_map.get(variant.id, 0) or 0
        outward = outward_map.get(variant.id, 0) or 0
        stock = stock_map.get(variant.id, 0)
        # Use actual purchase price if available, else product master price
        actual_cost = avg_cost_map.get(variant.id, variant.effective_cost or 0)
        result.append({
            'variant_id': variant.id,
            'product_name': product.name,
            'category': product.category,
            'color': variant.color or '-',
            'size': variant.size or '-',
            'sku': variant.sku_code,
            'image_url': product.image_url,
            'inward': inward,
            'outward': outward,
            'stock': stock,
            'cost_price': actual_cost,
            'stock_value': stock * actual_cost,
        })
    return result


def get_active_states():
    """Return list of states that have at least one location with stock or activity."""
    from app.models import Location
    locations = Location.query.filter_by(is_active=True).order_by(Location.state).all()
    states = sorted(set(l.state for l in locations))
    return states


def get_locations_for_state(state):
    """Return locations for a given state."""
    from app.models import Location
    return Location.query.filter_by(state=state, is_active=True).order_by(Location.district).all()
