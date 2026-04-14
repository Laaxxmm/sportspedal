from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import SupplierPayment, Supplier, PurchaseItem
from app.decorators import superadmin_required
from sqlalchemy import func

bp = Blueprint('payments', __name__)


def get_supplier_balance(supplier_id=None):
    """Calculate supplier running account balance including shipping credits."""
    from app.models import PurchaseOrder, SaleOrder

    # Total owed = sum of all purchase items total_amount
    owed_query = db.session.query(func.sum(PurchaseItem.total_amount))
    if supplier_id:
        owed_query = owed_query.join(PurchaseOrder).filter(PurchaseOrder.supplier_id == supplier_id)
    total_owed = owed_query.scalar() or 0

    # Total paid
    paid_query = db.session.query(func.sum(SupplierPayment.amount))
    if supplier_id:
        paid_query = paid_query.filter(SupplierPayment.supplier_id == supplier_id)
    total_paid = paid_query.scalar() or 0

    # Shipping credits (supplier owes us for shipping they agreed to pay)
    shipping_credit = db.session.query(func.sum(SaleOrder.shipping_cost)).filter(
        SaleOrder.shipping_paid_by == 'supplier',
        SaleOrder.shipping_cost > 0
    ).scalar() or 0

    # Shipping deductions already applied in payments
    shipping_settled = db.session.query(func.sum(SupplierPayment.shipping_deduction))
    if supplier_id:
        shipping_settled = shipping_settled.filter(SupplierPayment.supplier_id == supplier_id)
    shipping_settled = shipping_settled.scalar() or 0

    shipping_pending = shipping_credit - shipping_settled

    net_balance = total_owed - total_paid - shipping_pending

    return {
        'owed': total_owed,
        'paid': total_paid,
        'shipping_credit': shipping_credit,
        'shipping_settled': shipping_settled,
        'shipping_pending': shipping_pending,
        'balance': net_balance,
    }


@bp.route('/')
@login_required
@superadmin_required
def list_payments():
    payments = SupplierPayment.query.order_by(SupplierPayment.payment_date.desc()).all()
    suppliers = Supplier.query.all()

    # Calculate running balance per supplier
    balances = {}
    for s in suppliers:
        balances[s.id] = get_supplier_balance(s.id)

    overall = get_supplier_balance()
    return render_template('payments/list.html', payments=payments, suppliers=suppliers,
                           balances=balances, overall=overall)


@bp.route('/new', methods=['GET', 'POST'])
@login_required
@superadmin_required
def new_payment():
    if request.method == 'POST':
        shipping_ded = float(request.form.get('shipping_deduction', 0))
        payment = SupplierPayment(
            supplier_id=int(request.form['supplier_id']),
            payment_date=date.fromisoformat(request.form['payment_date']),
            amount=float(request.form['amount']),
            shipping_deduction=shipping_ded,
            payment_mode=request.form.get('payment_mode', ''),
            reference_number=request.form.get('reference_number', ''),
            notes=request.form.get('notes', ''),
            created_by=current_user.id,
        )
        db.session.add(payment)
        db.session.commit()
        msg = f'Payment of Rs.{payment.amount:,.2f} recorded.'
        if shipping_ded > 0:
            msg += f' (includes Rs.{shipping_ded:,.2f} shipping deduction)'
        flash(msg, 'success')
        return redirect(url_for('payments.list_payments'))

    suppliers = Supplier.query.all()
    balances = {s.id: get_supplier_balance(s.id) for s in suppliers}
    return render_template('payments/form.html', payment=None, suppliers=suppliers, balances=balances)


@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@superadmin_required
def edit_payment(id):
    payment = SupplierPayment.query.get_or_404(id)
    if request.method == 'POST':
        payment.supplier_id = int(request.form['supplier_id'])
        payment.payment_date = date.fromisoformat(request.form['payment_date'])
        payment.amount = float(request.form['amount'])
        payment.payment_mode = request.form.get('payment_mode', '')
        payment.reference_number = request.form.get('reference_number', '')
        payment.notes = request.form.get('notes', '')
        db.session.commit()
        flash(f'Payment updated.', 'success')
        return redirect(url_for('payments.list_payments'))

    suppliers = Supplier.query.all()
    balances = {s.id: get_supplier_balance(s.id) for s in suppliers}
    return render_template('payments/form.html', payment=payment, suppliers=suppliers, balances=balances)


@bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@superadmin_required
def delete_payment(id):
    payment = SupplierPayment.query.get_or_404(id)
    amt = payment.amount
    db.session.delete(payment)
    db.session.commit()
    flash(f'Payment of Rs.{amt:,.2f} deleted.', 'info')
    return redirect(url_for('payments.list_payments'))
