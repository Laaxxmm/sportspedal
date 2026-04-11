from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import PurchaseOrder, PurchaseItem, Supplier, ProductVariant, Product

bp = Blueprint('purchases', __name__)


@bp.route('/')
@login_required
def list_purchases():
    purchases = PurchaseOrder.query.order_by(PurchaseOrder.order_date.desc()).all()
    return render_template('purchases/list.html', purchases=purchases)


@bp.route('/download')
@login_required
def download_purchases():
    from app.services.excel_export import export_purchases
    purchases = PurchaseOrder.query.order_by(PurchaseOrder.order_date.desc()).all()
    return export_purchases(purchases)


@bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_purchase():
    if request.method == 'POST':
        po = PurchaseOrder(
            order_number=request.form.get('order_number', ''),
            supplier_id=int(request.form['supplier_id']),
            order_date=request.form['order_date'],
            location=request.form.get('location', 'Bangalore'),
            transporter=request.form.get('transporter', ''),
            status=request.form.get('status', 'ordered'),
            notes=request.form.get('notes', ''),
        )
        db.session.add(po)
        db.session.flush()

        variant_ids = request.form.getlist('variant_id[]')
        qtys_dispatched = request.form.getlist('qty_dispatched[]')
        qtys_received = request.form.getlist('qty_received[]')
        unit_prices = request.form.getlist('unit_price[]')
        gst_percents = request.form.getlist('gst_percent[]')

        for i in range(len(variant_ids)):
            if not variant_ids[i]:
                continue
            qty_d = int(qtys_dispatched[i] or 0)
            qty_r = int(qtys_received[i] or 0)
            price = float(unit_prices[i] or 0)
            gst_pct = float(gst_percents[i] or 12.0)
            taxable = price * qty_r
            gst_amt = taxable * gst_pct / 100
            item = PurchaseItem(
                purchase_order_id=po.id,
                variant_id=int(variant_ids[i]),
                quantity_dispatched=qty_d,
                quantity_received=qty_r,
                unit_price=price,
                gst_percent=gst_pct,
                gst_amount=gst_amt,
                total_amount=taxable + gst_amt,
            )
            db.session.add(item)

        db.session.commit()
        flash(f'Purchase Order #{po.order_number or po.id} created.', 'success')
        return redirect(url_for('purchases.list_purchases'))

    suppliers = Supplier.query.all()
    variants = (db.session.query(ProductVariant, Product)
                .join(Product)
                .filter(ProductVariant.is_active == True, Product.is_active == True)
                .order_by(Product.name, ProductVariant.color, ProductVariant.size)
                .all())
    return render_template('purchases/form.html', purchase=None, suppliers=suppliers, variants=variants)


@bp.route('/<int:id>')
@login_required
def view_purchase(id):
    po = PurchaseOrder.query.get_or_404(id)
    return render_template('purchases/detail.html', purchase=po)


@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_purchase(id):
    po = PurchaseOrder.query.get_or_404(id)
    if request.method == 'POST':
        po.order_number = request.form.get('order_number', '')
        po.supplier_id = int(request.form['supplier_id'])
        po.order_date = request.form['order_date']
        po.location = request.form.get('location', 'Bangalore')
        po.transporter = request.form.get('transporter', '')
        po.status = request.form.get('status', 'ordered')
        po.notes = request.form.get('notes', '')

        PurchaseItem.query.filter_by(purchase_order_id=po.id).delete()

        variant_ids = request.form.getlist('variant_id[]')
        qtys_dispatched = request.form.getlist('qty_dispatched[]')
        qtys_received = request.form.getlist('qty_received[]')
        unit_prices = request.form.getlist('unit_price[]')
        gst_percents = request.form.getlist('gst_percent[]')

        for i in range(len(variant_ids)):
            if not variant_ids[i]:
                continue
            qty_d = int(qtys_dispatched[i] or 0)
            qty_r = int(qtys_received[i] or 0)
            price = float(unit_prices[i] or 0)
            gst_pct = float(gst_percents[i] or 12.0)
            taxable = price * qty_r
            gst_amt = taxable * gst_pct / 100
            item = PurchaseItem(
                purchase_order_id=po.id,
                variant_id=int(variant_ids[i]),
                quantity_dispatched=qty_d,
                quantity_received=qty_r,
                unit_price=price,
                gst_percent=gst_pct,
                gst_amount=gst_amt,
                total_amount=taxable + gst_amt,
            )
            db.session.add(item)

        db.session.commit()
        flash(f'Purchase Order updated.', 'success')
        return redirect(url_for('purchases.view_purchase', id=po.id))

    suppliers = Supplier.query.all()
    variants = (db.session.query(ProductVariant, Product)
                .join(Product)
                .filter(ProductVariant.is_active == True, Product.is_active == True)
                .order_by(Product.name, ProductVariant.color, ProductVariant.size)
                .all())
    return render_template('purchases/form.html', purchase=po, suppliers=suppliers, variants=variants)
