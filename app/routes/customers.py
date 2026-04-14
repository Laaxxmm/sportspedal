from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Customer

bp = Blueprint('customers', __name__)


@bp.route('/')
@login_required
def list_customers():
    query = Customer.query
    if not current_user.is_superadmin and current_user.location_id:
        query = query.filter_by(location_id=current_user.location_id)
    customers = query.order_by(Customer.name).all()
    return render_template('customers/list.html', customers=customers)


@bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_customer():
    if request.method == 'POST':
        # Auto-assign location from current user for admins
        loc_id = None
        if not current_user.is_superadmin and current_user.location_id:
            loc_id = current_user.location_id

        customer = Customer(
            name=request.form['name'],
            customer_type=request.form.get('customer_type', 'public'),
            phone=request.form.get('phone', ''),
            email=request.form.get('email', ''),
            address=request.form.get('address', ''),
            city=request.form.get('city', ''),
            state=request.form.get('state', 'Karnataka'),
            gstin=request.form.get('gstin', ''),
            location_id=loc_id,
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

    loc_id = None
    if not current_user.is_superadmin and current_user.location_id:
        loc_id = current_user.location_id

    customer = Customer(
        name=name,
        customer_type=request.form.get('customer_type', 'public'),
        phone=request.form.get('phone', ''),
        city=request.form.get('city', ''),
        state=request.form.get('state', 'Karnataka'),
        location_id=loc_id,
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


@bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_customer(id):
    customer = Customer.query.get_or_404(id)
    # Check if customer has orders
    if customer.sale_orders.count() > 0:
        flash(f'Cannot delete "{customer.name}" - they have {customer.sale_orders.count()} order(s). Delete orders first.', 'danger')
        return redirect(url_for('customers.list_customers'))
    name = customer.name
    db.session.delete(customer)
    db.session.commit()
    flash(f'Customer "{name}" deleted.', 'info')
    return redirect(url_for('customers.list_customers'))
