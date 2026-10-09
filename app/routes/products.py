from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.decorators import permission_required
from flask_login import login_required
from app import db
from app.models import Product, ProductVariant
from app.services.image import save_product_image, delete_product_image, allowed_file
from app.form_utils import form_float, form_int, form_opt_float, form_opt_int

bp = Blueprint('products', __name__)

COLORS = ['Blue', 'Pink', 'Grey', 'Black', 'White', 'Red']
SIZES = ['XS', 'S', 'M', 'L', 'XL']
CATEGORIES = ['skates', 'helmet', 'guards', 'bag', 'freebie']


def generate_sku(product_name, color, size, exclude_id=None):
    name_part = product_name[:4].upper().replace(' ', '')
    color_part = (color[:3].upper()) if color else ''
    size_part = size.upper() if size else ''
    parts = [name_part]
    if color_part:
        parts.append(color_part)
    if size_part:
        parts.append(size_part)
    base_sku = '-'.join(parts)

    # Ensure uniqueness - append counter if SKU exists
    sku = base_sku
    counter = 2
    def taken(code):
        q = ProductVariant.query.filter_by(sku_code=code)
        if exclude_id:
            q = q.filter(ProductVariant.id != exclude_id)
        return q.first() is not None

    while taken(sku):
        sku = f"{base_sku}-{counter}"
        counter += 1
    return sku


@bp.route('/')
@login_required
@permission_required('view_products')
def list_products():
    products = Product.query.filter_by(is_active=True).order_by(Product.category, Product.name).all()
    return render_template('products/list.html', products=products)


@bp.route('/new', methods=['GET', 'POST'])
@login_required
@permission_required('view_products')
def new_product():
    if request.method == 'POST':
      try:
        def fnum(key, default=0):
            v = request.form.get(key, default)
            try:
                return float(v) if v not in (None, '') else float(default)
            except (ValueError, TypeError):
                return float(default)

        name = (request.form.get('name') or '').strip()
        if not name:
            flash('Product name is required.', 'danger')
            return redirect(url_for('products.new_product'))
        product = Product(
            name=name,
            category=request.form['category'],
            hsn_code=request.form.get('hsn_code', ''),
            gst_percent=fnum('gst_percent', 12.0),
            cost_price=fnum('cost_price'),
            coach_price=fnum('coach_price'),
            mrp=fnum('mrp'),
            coach_local=fnum('coach_local'),
            coach_direct=fnum('coach_direct'),
            coach_self=fnum('coach_self'),
            bulk_local=fnum('bulk_local'),
            bulk_direct=fnum('bulk_direct'),
            bulk_self=fnum('bulk_self'),
            dealer_price=fnum('dealer_price'),
        )

        # Handle image upload
        file = request.files.get('image')
        if file and file.filename:
            saved = save_product_image(file) if allowed_file(file.filename) else None
            if saved:
                product.image_path = saved
            else:
                flash('Photo not saved - use JPG, PNG, WebP or GIF.', 'warning')

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
      except Exception as e:
        db.session.rollback()
        flash(f'Error creating product: {str(e)}', 'danger')
        return redirect(url_for('products.new_product'))

    return render_template('products/form.html', product=None, colors=COLORS, sizes=SIZES, categories=CATEGORIES)


@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('view_products')
def edit_product(id):
    product = Product.query.get_or_404(id)
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        if not name:
            flash('Product name is required.', 'danger')
            return redirect(url_for('products.edit_product', id=id))
        product.name = name
        product.category = request.form.get('category', product.category)
        product.hsn_code = request.form.get('hsn_code', '')
        product.gst_percent = form_float(request.form, 'gst_percent', 12.0)
        product.cost_price = form_float(request.form, 'cost_price', 0)
        product.coach_price = form_float(request.form, 'coach_price', 0)
        product.mrp = form_float(request.form, 'mrp', 0)
        product.coach_local = form_float(request.form, 'coach_local', 0)
        product.coach_direct = form_float(request.form, 'coach_direct', 0)
        product.coach_self = form_float(request.form, 'coach_self', 0)
        product.bulk_local = form_float(request.form, 'bulk_local', 0)
        product.bulk_direct = form_float(request.form, 'bulk_direct', 0)
        product.bulk_self = form_float(request.form, 'bulk_self', 0)
        product.dealer_price = form_float(request.form, 'dealer_price', 0)

        # Handle image upload - save the new one first, only then drop the old one
        file = request.files.get('image')
        if file and file.filename:
            saved = save_product_image(file) if allowed_file(file.filename) else None
            if saved:
                if product.image_path:
                    delete_product_image(product.image_path)
                product.image_path = saved
            else:
                flash('Photo not saved - use JPG, PNG, WebP or GIF. Previous photo kept.', 'warning')

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
@permission_required('view_products')
def add_variant(id):
    product = Product.query.get_or_404(id)
    color = request.form.get('color') or None
    size = request.form.get('size') or None

    existing = ProductVariant.query.filter_by(product_id=product.id, color=color, size=size).first()
    if existing:
        if not existing.is_active:
            existing.is_active = True
            db.session.commit()
            flash(f'Variant {existing.sku_code} re-activated.', 'success')
        else:
            flash(f'Variant {existing.sku_code} already exists.', 'warning')
    else:
        sku = generate_sku(product.name, color, size)
        variant = ProductVariant(product_id=product.id, color=color, size=size, sku_code=sku)
        db.session.add(variant)
        db.session.commit()
        flash(f'Variant {sku} added.', 'success')

    return redirect(url_for('products.edit_product', id=id))


@bp.route('/variant/<int:vid>/edit', methods=['POST'])
@login_required
@permission_required('view_products')
def edit_variant(vid):
    variant = ProductVariant.query.get_or_404(vid)
    new_color = request.form.get('color') or None
    new_size = request.form.get('size') or None

    if (new_color, new_size) != (variant.color, variant.size):
        clash = (ProductVariant.query
                 .filter_by(product_id=variant.product_id, color=new_color, size=new_size)
                 .filter(ProductVariant.id != variant.id).first())
        if clash:
            flash(f'Another variant ({clash.sku_code}) already has that colour/size.', 'danger')
            return redirect(url_for('products.edit_product', id=variant.product_id))
        variant.color, variant.size = new_color, new_size
        # Only re-derive the SKU when the variant actually changed. Regenerating it
        # on every save collided with its own SKU and appended -2, -3...
        variant.sku_code = generate_sku(variant.product.name, new_color, new_size,
                                        exclude_id=variant.id)

    # Blank or 0 means "no override - use the product price"
    variant.cost_price_override = form_opt_float(request.form, 'cost_override') or None
    variant.coach_price_override = form_opt_float(request.form, 'coach_override') or None
    variant.mrp_override = form_opt_float(request.form, 'mrp_override') or None
    db.session.commit()
    flash(f'Variant {variant.sku_code} updated.', 'success')
    return redirect(url_for('products.edit_product', id=variant.product_id))


@bp.route('/variant/<int:vid>/delete', methods=['POST'])
@login_required
@permission_required('view_products')
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
@permission_required('view_products')
def delete_product(id):
    product = Product.query.get_or_404(id)
    product.is_active = False
    for v in product.variants:
        v.is_active = False
    db.session.commit()
    flash(f'Product "{product.name}" deactivated.', 'info')
    return redirect(url_for('products.list_products'))
