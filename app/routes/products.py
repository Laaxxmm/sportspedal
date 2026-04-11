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
