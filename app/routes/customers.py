from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Customer

bp = Blueprint('customers', __name__)


@bp.route('/')
@login_required
def list_customers():
    customers = Customer.query.order_by(Customer.name).all()
    return render_template('customers/list.html', customers=customers)


@bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_customer():
    if request.method == 'POST':
        customer = Customer(
            name=request.form['name'],
            customer_type=request.form.get('customer_type', 'public'),
            phone=request.form.get('phone', ''),
            email=request.form.get('email', ''),
            address=request.form.get('address', ''),
            city=request.form.get('city', ''),
            state=request.form.get('state', 'Karnataka'),
            gstin=request.form.get('gstin', ''),
        )
        db.session.add(customer)
        db.session.commit()
        flash(f'Customer "{customer.name}" added.', 'success')
        return redirect(url_for('customers.list_customers'))

    return render_template('customers/form.html', customer=None)


@bp.route('/quick-add', methods=['POST'])
@login_required
def quick_add():
    """AJAX endpoint to add a customer from the sales form."""
    name = request.form.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    customer = Customer(
        name=name,
        customer_type=request.form.get('customer_type', 'public'),
        phone=request.form.get('phone', ''),
        city=request.form.get('city', ''),
        state=request.form.get('state', 'Karnataka'),
    )
    db.session.add(customer)
    db.session.commit()
    return jsonify({'id': customer.id, 'name': customer.name, 'type': customer.customer_type})


@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_customer(id):
    customer = Customer.query.get_or_404(id)
    if request.method == 'POST':
        customer.name = request.form['name']
        customer.customer_type = request.form.get('customer_type', 'public')
        customer.phone = request.form.get('phone', '')
        customer.email = request.form.get('email', '')
        customer.address = request.form.get('address', '')
        customer.city = request.form.get('city', '')
        customer.state = request.form.get('state', 'Karnataka')
        customer.gstin = request.form.get('gstin', '')
        db.session.commit()
        flash(f'Customer "{customer.name}" updated.', 'success')
        return redirect(url_for('customers.list_customers'))

    return render_template('customers/form.html', customer=customer)
