"""Stock Adjustments: promotional giveaways, damaged goods, returns, lost stock."""
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from app import db
from app.models import (StockAdjustment, StockAdjustmentItem, ProductVariant,
                        Product, Location, ADJUSTMENT_TYPES)
from app.services.stock import get_stock_map

bp = Blueprint('adjustments', __name__)


def scope_adjustment(adj):
    """Check if user can access this adjustment (location-scoped for admins)."""
    if not current_user.is_superadmin and current_user.location_id:
        if adj.location_id and adj.location_id != current_user.location_id:
            abort(403)


def generate_adjustment_number():
    last = StockAdjustment.query.order_by(StockAdjustment.id.desc()).first()
    seq = (last.id + 1) if last else 1
    return f"ADJ-{seq:04d}"


@bp.route('/')
@login_required
def list_adjustments():
    query = StockAdjustment.query
    if not current_user.is_superadmin and current_user.location_id:
        query = query.filter_by(location_id=current_user.location_id)

    type_filter = request.args.get('type', '')
    if type_filter:
        query = query.filter_by(adjustment_type=type_filter)

    adjustments = query.order_by(StockAdjustment.adjustment_date.desc()).all()

    # Summary stats
    summary = {}
    for t_key in ADJUSTMENT_TYPES:
        items = [a for a in adjustments if a.adjustment_type == t_key]
        summary[t_key] = {
            'count': len(items),
            'qty': sum(a.total_qty for a in items),
            'value': sum(a.total_value for a in items),
        }

    return render_template('adjustments/list.html', adjustments=adjustments,
                           types=ADJUSTMENT_TYPES, type_filter=type_filter, summary=summary)


@bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_adjustment():
    if request.method == 'POST':
        try:
            loc_id = request.form.get('location_id', type=int)
            if not current_user.is_superadmin:
                loc_id = current_user.location_id or loc_id

            adj = StockAdjustment(
                adjustment_number=generate_adjustment_number(),
                adjustment_date=date.fromisoformat(request.form.get('adjustment_date', date.today().isoformat())),
                location_id=loc_id,
                adjustment_type=request.form.get('adjustment_type', 'promotional'),
                recipient=request.form.get('recipient', ''),
                supplier_credit=request.form.get('supplier_credit') == '1',
                notes=request.form.get('notes', ''),
                created_by=current_user.id,
            )
            db.session.add(adj)
            db.session.flush()

            variant_ids = request.form.getlist('variant_id[]')
            qtys = request.form.getlist('qty[]')

            stock_map = get_stock_map(location_id=loc_id)
            for i in range(len(variant_ids)):
                if not variant_ids[i]:
                    continue
                vid = int(variant_ids[i])
                qty = int(qtys[i] or 0)
                if qty <= 0:
                    continue
                # Validate stock
                available = stock_map.get(vid, 0)
                if qty > available:
                    flash(f'Variant {vid}: requested {qty}, only {available} available. Skipped.', 'warning')
                    continue
                # Get cost - use latest purchase price (incl GST) as landed cost
                from app.models import PurchaseItem, PurchaseOrder
                from sqlalchemy import func
                cost_data = db.session.query(
                    func.sum(PurchaseItem.total_amount),
                    func.sum(PurchaseItem.quantity_received)
                ).join(PurchaseOrder).filter(
                    PurchaseItem.variant_id == vid,
                    PurchaseOrder.status == 'delivered'
                ).first()
                avg_cost = (cost_data[0] / cost_data[1]) if cost_data and cost_data[1] else 0

                db.session.add(StockAdjustmentItem(
                    adjustment_id=adj.id, variant_id=vid,
                    quantity=qty, unit_cost=avg_cost,
                ))

            db.session.commit()
            flash(f'Adjustment {adj.adjustment_number} created. {adj.total_qty} units adjusted.', 'success')
            return redirect(url_for('adjustments.list_adjustments'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('adjustments.new_adjustment'))

    locations = Location.query.filter_by(is_active=True).order_by(Location.state, Location.district).all()
    variants = (db.session.query(ProductVariant, Product)
                .join(Product).filter(ProductVariant.is_active == True, Product.is_active == True)
                .order_by(Product.name, ProductVariant.color, ProductVariant.size).all())

    loc_id = current_user.location_id if not current_user.is_superadmin else None
    stock_map = get_stock_map(location_id=loc_id)

    return render_template('adjustments/form.html', adjustment=None, locations=locations,
                           variants=variants, stock_map=stock_map, types=ADJUSTMENT_TYPES)


@bp.route('/<int:id>')
@login_required
def view_adjustment(id):
    adj = StockAdjustment.query.get_or_404(id)
    scope_adjustment(adj)
    return render_template('adjustments/detail.html', adjustment=adj)


@bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_adjustment(id):
    adj = StockAdjustment.query.get_or_404(id)
    scope_adjustment(adj)
    num = adj.adjustment_number
    StockAdjustmentItem.query.filter_by(adjustment_id=adj.id).delete()
    db.session.delete(adj)
    db.session.commit()
    flash(f'Adjustment {num} deleted. Stock restored.', 'info')
    return redirect(url_for('adjustments.list_adjustments'))
