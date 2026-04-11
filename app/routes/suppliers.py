from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Supplier

bp = Blueprint('suppliers', __name__)


@bp.route('/')
@login_required
def list_suppliers():
    suppliers = Supplier.query.order_by(Supplier.name).all()
    return render_template('suppliers/list.html', suppliers=suppliers)


@bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_supplier():
    if request.method == 'POST':
        supplier = Supplier(
            name=request.form['name'],
            gstin=request.form.get('gstin', ''),
            address=request.form.get('address', ''),
            phone=request.form.get('phone', ''),
            email=request.form.get('email', ''),
        )
        db.session.add(supplier)
        db.session.commit()
        flash(f'Supplier "{supplier.name}" added.', 'success')
        return redirect(url_for('suppliers.list_suppliers'))

    return render_template('suppliers/form.html', supplier=None)


@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_supplier(id):
    supplier = Supplier.query.get_or_404(id)
    if request.method == 'POST':
        supplier.name = request.form['name']
        supplier.gstin = request.form.get('gstin', '')
        supplier.address = request.form.get('address', '')
        supplier.phone = request.form.get('phone', '')
        supplier.email = request.form.get('email', '')
        db.session.commit()
        flash(f'Supplier "{supplier.name}" updated.', 'success')
        return redirect(url_for('suppliers.list_suppliers'))

    return render_template('suppliers/form.html', supplier=supplier)
