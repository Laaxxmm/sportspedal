from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import SupplierPayment, Supplier, PurchaseItem
from app.decorators import superadmin_required
from sqlalchemy import func

bp = Blueprint('payments', __name__)


def get_supplier_balance(supplier_id=None):
    """Calculate supplier running account balance."""
    # Total owed = sum of all purchase items total_amount
    owed_query = db.session.query(func.sum(PurchaseItem.total_amount))
    if supplier_id:
        from app.models import PurchaseOrder
        owed_query = owed_query.join(PurchaseOrder).filter(PurchaseOrder.supplier_id == supplier_id)
    total_owed = owed_query.scalar() or 0

    # Total paid
    paid_query = db.session.query(func.sum(SupplierPayment.amount))
    if supplier_id:
        paid_query = paid_query.filter(SupplierPayment.supplier_id == supplier_id)
    total_paid = paid_query.scalar() or 0

    return {'owed': total_owed, 'paid': total_paid, 'balance': total_owed - total_paid}


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
        payment = SupplierPayment(
            supplier_id=int(request.form['supplier_id']),
            payment_date=request.form['payment_date'],
            amount=float(request.form['amount']),
            payment_mode=request.form.get('payment_mode', ''),
            reference_number=request.form.get('reference_number', ''),
            notes=request.form.get('notes', ''),
            created_by=current_user.id,
        )
        db.session.add(payment)
        db.session.commit()
        flash(f'Payment of Rs.{payment.amount:,.2f} recorded.', 'success')
        return redirect(url_for('payments.list_payments'))

    suppliers = Supplier.query.all()
    balances = {s.id: get_supplier_balance(s.id) for s in suppliers}
    return render_template('payments/form.html', suppliers=suppliers, balances=balances)
