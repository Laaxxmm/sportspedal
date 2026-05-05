from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app import db
from app.models import Product, ProductVariant
from app.services.image import save_product_image, delete_product_image, allowed_file

bp = Blueprint('products', __name__)

COLORS = ['Blue', 'Pink', 'Grey', 'Black', 'White', 'Red']
SIZES = ['XS', 'S', 'M', 'L', 'XL']
CATEGORIES = ['skates', 'helmet', 'guards', 'bag', 'freebie']


def generate_sku(product_name, color, size):
    name_part = product_name[:4].upper().replace(' ', '')
    color_part = (color[:3].upper()) if color else ''
    size_part = size.upper() if size else ''
    parts = [name_part]
    if color_part:
        parts.append(color_part)
    if size_part:
        parts.append(size_part)
    return '-'.join(parts)


@bp.route('/')
@login_required
def list_products():
    products = Product.query.filter_by(is_active=True).order_by(Product.category, Product.name).all()
    return render_template('products/list.html', products=products)


@bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_product():
    if request.method == 'POST':
        product = Product(
            name=request.form['name'],
            category=request.form['category'],
            hsn_code=request.form.get('hsn_code', ''),
            gst_percent=float(request.form.get('gst_percent', 12.0)),
            cost_price=float(request.form.get('cost_price', 0)),
            coach_price=float(request.form.get('coach_price', 0)),
            mrp=float(request.form.get('mrp', 0)),
            coach_local=float(request.form.get('coach_local', 0) or 0),
            coach_direct=float(request.form.get('coach_direct', 0) or 0),
            coach_self=float(request.form.get('coach_self', 0) or 0),
            bulk_local=float(request.form.get('bulk_local', 0) or 0),
            bulk_direct=float(request.form.get('bulk_direct', 0) or 0),
            bulk_self=float(request.form.get('bulk_self', 0) or 0),
            dealer_price=float(request.form.get('dealer_price', 0) or 0),
        )

        # Handle image upload
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                product.image_path = save_product_image(file)

        db.session.add(product)
        db.session.flush()

        colors = request.form.getlist('colors')
        sizes = request.form.getlist('sizes')

        if colors and sizes:
            for color in colors:
                for size in sizes:
                    db.session.add(ProductVariant(
                        product_id=product.id, color=color, size=size,
                        sku_code=generate_sku(product.name, color, size)))
        elif colors:
            for color in colors:
                db.session.add(ProductVariant(
                    product_id=product.id, color=color,
                    sku_code=generate_sku(product.name, color, None)))
        else:
            db.session.add(ProductVariant(
                product_id=product.id, sku_code=generate_sku(product.name, None, None)))

        db.session.commit()
        flash(f'Product "{product.name}" created with {product.variants.count()} variant(s).', 'success')
        return redirect(url_for('products.list_products'))

    return render_template('products/form.html', product=None, colors=COLORS, sizes=SIZES, categories=CATEGORIES)


@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    product = Product.query.get_or_404(id)
    if request.method == 'POST':
        product.name = request.form['name']
        product.category = request.form['category']
        product.hsn_code = request.form.get('hsn_code', '')
        product.gst_percent = float(request.form.get('gst_percent', 12.0))
        product.cost_price = float(request.form.get('cost_price', 0))
        product.coach_price = float(request.form.get('coach_price', 0))
        product.mrp = float(request.form.get('mrp', 0))
        product.coach_local = float(request.form.get('coach_local', 0) or 0)
        product.coach_direct = float(request.form.get('coach_direct', 0) or 0)
        product.coach_self = float(request.form.get('coach_self', 0) or 0)
        product.bulk_local = float(request.form.get('bulk_local', 0) or 0)
        product.bulk_direct = float(request.form.get('bulk_direct', 0) or 0)
        product.bulk_self = float(request.form.get('bulk_self', 0) or 0)
        product.dealer_price = float(request.form.get('dealer_price', 0) or 0)

        # Handle image upload
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                # Delete old image
                if product.image_path:
                    delete_product_image(product.image_path)
                product.image_path = save_product_image(file)

        # Handle image removal
        if request.form.get('remove_image') == '1' and product.image_path:
            delete_product_image(product.image_path)
            product.image_path = None

        db.session.commit()
        flash(f'Product "{product.name}" updated.', 'success')
        return redirect(url_for('products.list_products'))

    return render_template('products/form.html', product=product, colors=COLORS, sizes=SIZES, categories=CATEGORIES)


@bp.route('/<int:id>/add-variant', methods=['POST'])
@login_required
def add_variant(id):
    product = Product.query.get_or_404(id)
    color = request.form.get('color') or None
    size = request.form.get('size') or None
    sku = generate_sku(product.name, color, size)

    existing = ProductVariant.query.filter_by(sku_code=sku).first()
    if existing:
        flash(f'Variant with SKU {sku} already exists.', 'warning')
    else:
        variant = ProductVariant(product_id=product.id, color=color, size=size, sku_code=sku)
        db.session.add(variant)
        db.session.commit()
        flash(f'Variant {sku} added.', 'success')

    return redirect(url_for('products.edit_product', id=id))


@bp.route('/variant/<int:vid>/edit', methods=['POST'])
@login_required
def edit_variant(vid):
    variant = ProductVariant.query.get_or_404(vid)
    variant.color = request.form.get('color') or None
    variant.size = request.form.get('size') or None
    variant.sku_code = generate_sku(variant.product.name, variant.color, variant.size)
    variant.cost_price_override = float(request.form.get('cost_override') or 0) or None
    variant.coach_price_override = float(request.form.get('coach_override') or 0) or None
    variant.mrp_override = float(request.form.get('mrp_override') or 0) or None
    db.session.commit()
    flash(f'Variant {variant.sku_code} updated.', 'success')
    return redirect(url_for('products.edit_product', id=variant.product_id))


@bp.route('/variant/<int:vid>/delete', methods=['POST'])
@login_required
def delete_variant(vid):
    variant = ProductVariant.query.get_or_404(vid)
    pid = variant.product_id
    sku = variant.sku_code
    # Check if variant has purchase or sale items
    from app.models import PurchaseItem, SaleItem
    has_purchases = PurchaseItem.query.filter_by(variant_id=vid).count() > 0
    has_sales = SaleItem.query.filter_by(variant_id=vid).count() > 0
    if has_purchases or has_sales:
        variant.is_active = False
        db.session.commit()
        flash(f'Variant {sku} deactivated (has order history).', 'warning')
    else:
        db.session.delete(variant)
        db.session.commit()
        flash(f'Variant {sku} deleted.', 'info')
    return redirect(url_for('products.edit_product', id=pid))


@bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_product(id):
    product = Product.query.get_or_404(id)
    product.is_active = False
    for v in product.variants:
        v.is_active = False
    db.session.commit()
    flash(f'Product "{product.name}" deactivated.', 'info')
    return redirect(url_for('products.list_products'))
