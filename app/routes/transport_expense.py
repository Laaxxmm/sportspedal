from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import TransportExpense, Supplier
from app.decorators import superadmin_required

bp = Blueprint('transport_expense', __name__)


@bp.route('/')
@login_required
@superadmin_required
def list_expenses():
    expenses = (TransportExpense.query
                .order_by(TransportExpense.expense_date.desc(), TransportExpense.id.desc()).all())
    total_supplier = sum(e.amount for e in expenses if e.borne_by == 'supplier')
    total_self = sum(e.amount for e in expenses if e.borne_by == 'self')
    return render_template('transport_expenses/list.html', expenses=expenses,
                           total_supplier=total_supplier, total_self=total_self)


@bp.route('/new', methods=['GET', 'POST'])
@login_required
@superadmin_required
def new_expense():
    if request.method == 'POST':
        borne = request.form.get('borne_by', 'supplier')
        e = TransportExpense(
            expense_date=date.fromisoformat(request.form['expense_date']),
            amount=float(request.form['amount']),
            borne_by=borne,
            supplier_id=(int(request.form['supplier_id'])
                         if borne == 'supplier' and request.form.get('supplier_id') else None),
            carrier=request.form.get('carrier', ''),
            reference_number=request.form.get('reference_number', ''),
            notes=request.form.get('notes', ''),
            created_by=current_user.id,
        )
        db.session.add(e)
        db.session.commit()
        msg = f'Transport expense Rs.{e.amount:,.2f} recorded.'
        if borne == 'supplier':
            msg += ' Deducted from supplier dues.'
        flash(msg, 'success')
        return redirect(url_for('transport_expense.list_expenses'))

    suppliers = Supplier.query.order_by(Supplier.name).all()
    return render_template('transport_expenses/form.html', suppliers=suppliers,
                           today=date.today().isoformat())


@bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@superadmin_required
def delete_expense(id):
    e = TransportExpense.query.get_or_404(id)
    amt = e.amount
    db.session.delete(e)
    db.session.commit()
    flash(f'Deleted transport expense Rs.{amt:,.2f}.', 'info')
    return redirect(url_for('transport_expense.list_expenses'))
