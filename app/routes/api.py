from flask import Blueprint, jsonify, request
from flask_login import login_required
from app.models import Location, Product, ProductVariant
from app.services.stock import get_stock_map
from app.data.india_locations import INDIA_STATES_DISTRICTS

bp = Blueprint('api', __name__, url_prefix='/api')


@bp.route('/districts')
@login_required
def get_districts():
    state = request.args.get('state', '')
    data = INDIA_STATES_DISTRICTS.get(state, {})
    districts = data.get('districts', [])
    return jsonify(districts)


@bp.route('/variants')
@login_required
def get_variants():
    product_id = request.args.get('product_id', type=int)
    if not product_id:
        return jsonify([])
    variants = ProductVariant.query.filter_by(product_id=product_id, is_active=True).all()
    colors = sorted(set(v.color for v in variants if v.color))
    sizes = sorted(set(v.size for v in variants if v.size))
    result = []
    for v in variants:
        result.append({
            'id': v.id, 'color': v.color or '', 'size': v.size or '',
            'sku': v.sku_code, 'cost': v.effective_cost,
            'coach': v.effective_coach_price, 'mrp': v.effective_mrp,
        })
    return jsonify({'variants': result, 'colors': colors, 'sizes': sizes})


@bp.route('/stock')
@login_required
def get_stock():
    variant_id = request.args.get('variant_id', type=int)
    location_id = request.args.get('location_id', type=int)
    stock_map = get_stock_map(location_id=location_id)
    stock = stock_map.get(variant_id, 0) if variant_id else stock_map
    return jsonify({'stock': stock})


@bp.route('/products')
@login_required
def get_products():
    """Return products grouped for cascading selection."""
    products = Product.query.filter_by(is_active=True).order_by(Product.category, Product.name).all()
    result = []
    for p in products:
        variants = ProductVariant.query.filter_by(product_id=p.id, is_active=True).all()
        colors = sorted(set(v.color for v in variants if v.color))
        sizes = sorted(set(v.size for v in variants if v.size))
        result.append({
            'id': p.id, 'name': p.name, 'category': p.category,
            'gst': p.gst_percent, 'cost': p.cost_price,
            'coach': p.coach_price, 'mrp': p.mrp,
            'colors': colors, 'sizes': sizes,
            'variants': [{'id': v.id, 'color': v.color, 'size': v.size, 'sku': v.sku_code,
                          'cost': v.effective_cost, 'coach': v.effective_coach_price, 'mrp': v.effective_mrp}
                         for v in variants],
        })
    return jsonify(result)


@bp.route('/locations')
@login_required
def get_locations():
    locations = Location.query.filter_by(is_active=True).order_by(Location.state, Location.district).all()
    return jsonify([{'id': l.id, 'state': l.state, 'district': l.district, 'display': l.display_name} for l in locations])
