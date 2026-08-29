from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Expense, ExpenseCategory, Supplier
from app.decorators import superadmin_required
from sqlalchemy import func

bp = Blueprint('expenses', __name__)

DEFAULT_CATEGORIES = ['Travel', 'Website / Design', 'Marketing', 'Packaging',
                      'Rent', 'Salary', 'Utilities', 'Misc']


def ensure_default_categories():
    """Seed a starter set of categories once, so the dropdown is never empty."""
    if ExpenseCategory.query.count() == 0:
        for name in DEFAULT_CATEGORIES:
            db.session.add(ExpenseCategory(name=name))
        db.session.commit()


@bp.route('/')
@login_required
@superadmin_required
def list_expenses():
    ensure_default_categories()
    cat_filter = request.args.get('category_id', type=int)
    query = Expense.query
    if cat_filter:
        query = query.filter_by(category_id=cat_filter)
    expenses = query.order_by(Expense.expense_date.desc(), Expense.id.desc()).all()

    total = sum(e.amount for e in expenses)
    total_deducted = sum(e.amount for e in expenses if e.deduct_from_supplier)
    total_own = total - total_deducted

    # Per-category rollup (all expenses, not just the filtered view)
    rollup = (db.session.query(ExpenseCategory.name, func.sum(Expense.amount), func.count(Expense.id))
              .join(Expense, Expense.category_id == ExpenseCategory.id)
              .group_by(ExpenseCategory.name)
              .order_by(func.sum(Expense.amount).desc()).all())

    categories = ExpenseCategory.query.order_by(ExpenseCategory.name).all()
    return render_template('expenses/list.html', expenses=expenses, categories=categories,
                           total=total, total_deducted=total_deducted, total_own=total_own,
                           rollup=rollup, cat_filter=cat_filter)


@bp.route('/new', methods=['GET', 'POST'])
@login_required
@superadmin_required
def new_expense():
    ensure_default_categories()
    if request.method == 'POST':
        # Allow creating a brand-new category inline
        cat_id = request.form.get('category_id')
        new_cat = (request.form.get('new_category') or '').strip()
        if new_cat:
            existing = ExpenseCategory.query.filter(
                func.lower(ExpenseCategory.name) == new_cat.lower()).first()
            if existing:
                cat_id = existing.id
            else:
                c = ExpenseCategory(name=new_cat)
                db.session.add(c)
                db.session.flush()
                cat_id = c.id

        deduct = request.form.get('deduct_from_supplier') == '1'
        e = Expense(
            expense_date=date.fromisoformat(request.form['expense_date']),
            category_id=int(cat_id) if cat_id else None,
            description=request.form.get('description', ''),
            amount=float(request.form['amount']),
            deduct_from_supplier=deduct,
            supplier_id=(int(request.form['supplier_id'])
                         if deduct and request.form.get('supplier_id') else None),
            reference_number=request.form.get('reference_number', ''),
            notes=request.form.get('notes', ''),
            created_by=current_user.id,
        )
        db.session.add(e)
        db.session.commit()
        msg = f'Expense Rs.{e.amount:,.2f} recorded.'
        if deduct:
            msg += ' Deducted from supplier dues.'
        flash(msg, 'success')
        return redirect(url_for('expenses.list_expenses'))

    categories = ExpenseCategory.query.order_by(ExpenseCategory.name).all()
    suppliers = Supplier.query.order_by(Supplier.name).all()
    return render_template('expenses/form.html', categories=categories, suppliers=suppliers,
                           today=date.today().isoformat())


@bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@superadmin_required
def delete_expense(id):
    e = Expense.query.get_or_404(id)
    amt = e.amount
    db.session.delete(e)
    db.session.commit()
    flash(f'Deleted expense Rs.{amt:,.2f}.', 'info')
    return redirect(url_for('expenses.list_expenses'))


@bp.route('/categories/<int:id>/delete', methods=['POST'])
@login_required
@superadmin_required
def delete_category(id):
    c = ExpenseCategory.query.get_or_404(id)
    if Expense.query.filter_by(category_id=c.id).count() > 0:
        flash(f'Cannot delete "{c.name}" - expenses are using it.', 'danger')
        return redirect(url_for('expenses.list_expenses'))
    name = c.name
    db.session.delete(c)
    db.session.commit()
    flash(f'Category "{name}" deleted.', 'info')
    return redirect(url_for('expenses.list_expenses'))
