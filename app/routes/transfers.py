from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import StockTransfer, StockTransferItem, Location, ProductVariant, Product
from app.decorators import superadmin_required
from app.services.stock import get_stock_map

bp = Blueprint('transfers', __name__)


@bp.route('/')
@login_required
def list_transfers():
    query = StockTransfer.query.order_by(StockTransfer.created_at.desc())
    if not current_user.is_superadmin:
        query = query.filter(
            (StockTransfer.from_location_id == current_user.location_id) |
            (StockTransfer.to_location_id == current_user.location_id)
        )
    transfers = query.all()
    return render_template('transfers/list.html', transfers=transfers)


@bp.route('/new', methods=['GET', 'POST'])
@login_required
@superadmin_required
def new_transfer():
    if request.method == 'POST':
        from_loc = int(request.form['from_location_id'])
        to_loc = int(request.form['to_location_id'])
        if from_loc == to_loc:
            flash('Source and destination must be different.', 'danger')
            return redirect(url_for('transfers.new_transfer'))

        # Generate transfer number
        count = StockTransfer.query.count() + 1
        transfer = StockTransfer(
            transfer_number=f"TRF-{count:04d}",
            from_location_id=from_loc,
            to_location_id=to_loc,
            transfer_date=request.form.get('transfer_date'),
            status='pending',
            notes=request.form.get('notes', ''),
            created_by=current_user.id,
        )
        db.session.add(transfer)
        db.session.flush()

        stock_map = get_stock_map(location_id=from_loc)
        variant_ids = request.form.getlist('variant_id[]')
        qtys = request.form.getlist('qty[]')

        for i in range(len(variant_ids)):
            if not variant_ids[i]:
                continue
            vid = int(variant_ids[i])
            qty = int(qtys[i] or 0)
            if qty <= 0:
                continue
            available = stock_map.get(vid, 0)
            if qty > available:
                flash(f'Insufficient stock for variant {vid}. Available: {available}', 'warning')
                continue
            db.session.add(StockTransferItem(transfer_id=transfer.id, variant_id=vid, quantity=qty))

        db.session.commit()
        flash(f'Transfer {transfer.transfer_number} created.', 'success')
        return redirect(url_for('transfers.list_transfers'))

    locations = Location.query.filter_by(is_active=True).order_by(Location.state, Location.district).all()
    variants = (db.session.query(ProductVariant, Product)
                .join(Product).filter(ProductVariant.is_active == True, Product.is_active == True)
                .order_by(Product.name, ProductVariant.color, ProductVariant.size).all())
    return render_template('transfers/form.html', transfer=None, locations=locations, variants=variants)


@bp.route('/<int:id>')
@login_required
def view_transfer(id):
    transfer = StockTransfer.query.get_or_404(id)
    return render_template('transfers/detail.html', transfer=transfer)


@bp.route('/<int:id>/complete', methods=['POST'])
@login_required
@superadmin_required
def complete_transfer(id):
    transfer = StockTransfer.query.get_or_404(id)
    if transfer.status == 'completed':
        flash('Transfer already completed.', 'warning')
    else:
        transfer.status = 'completed'
        db.session.commit()
        flash(f'Transfer {transfer.transfer_number} completed. Stock moved.', 'success')
    return redirect(url_for('transfers.view_transfer', id=id))


@bp.route('/<int:id>/cancel', methods=['POST'])
@login_required
@superadmin_required
def cancel_transfer(id):
    transfer = StockTransfer.query.get_or_404(id)
    if transfer.status == 'completed':
        flash('Cannot cancel a completed transfer.', 'danger')
    else:
        transfer.status = 'cancelled'
        db.session.commit()
        flash(f'Transfer {transfer.transfer_number} cancelled.', 'info')
    return redirect(url_for('transfers.list_transfers'))
