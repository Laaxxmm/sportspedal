from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Customer, CustomerPayment, SaleOrder
from app.decorators import superadmin_required
from app.services.customer_account import get_customer_balance

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


# ===== Buyer Accounts (advances / ledger) =====

@bp.route('/accounts')
@login_required
@superadmin_required
def accounts():
    """List of buyers with advances or billed orders."""
    customers = Customer.query.order_by(Customer.name).all()
    rows = []
    totals = {'received': 0, 'billed': 0, 'advance_held': 0, 'due': 0}
    for c in customers:
        bal = get_customer_balance(c.id)
        # Only show buyers who have any money movement
        if bal['received'] == 0 and bal['billed'] == 0:
            continue
        rows.append({'customer': c, 'bal': bal})
        totals['received'] += bal['received']
        totals['billed'] += bal['billed']
        if bal['remaining'] > 0:
            totals['advance_held'] += bal['remaining']
        else:
            totals['due'] += -bal['remaining']
    # Sort: advances first (largest remaining), then dues
    rows.sort(key=lambda r: r['bal']['remaining'], reverse=True)
    return render_template('customers/accounts.html', rows=rows, totals=totals)


@bp.route('/<int:id>/account')
@login_required
@superadmin_required
def account_detail(id):
    customer = Customer.query.get_or_404(id)
    bal = get_customer_balance(id)
    payments = (CustomerPayment.query.filter_by(customer_id=id)
                .order_by(CustomerPayment.payment_date.desc(), CustomerPayment.id.desc()).all())
    sales = (SaleOrder.query.filter_by(customer_id=id)
             .order_by(SaleOrder.sale_date.asc(), SaleOrder.id.asc()).all())

    # Build a running-balance ledger: advances add, orders subtract (chronological)
    events = []
    for p in payments:
        events.append({'date': p.payment_date, 'kind': 'payment', 'obj': p,
                       'credit': p.amount, 'debit': 0})
    for s in sales:
        events.append({'date': s.sale_date, 'kind': 'sale', 'obj': s,
                       'credit': 0, 'debit': s.grand_total})
    events.sort(key=lambda e: (e['date'], 0 if e['kind'] == 'payment' else 1))
    running = 0
    for e in events:
        running += e['credit'] - e['debit']
        e['running'] = running

    return render_template('customers/account_detail.html', customer=customer,
                           bal=bal, payments=payments, events=events)


@bp.route('/<int:id>/payment', methods=['GET', 'POST'])
@login_required
@superadmin_required
def record_payment(id):
    customer = Customer.query.get_or_404(id)
    if request.method == 'POST':
        payment = CustomerPayment(
            customer_id=customer.id,
            payment_date=date.fromisoformat(request.form['payment_date']),
            amount=float(request.form['amount']),
            payment_type=request.form.get('payment_type', 'advance'),
            payment_mode=request.form.get('payment_mode', ''),
            reference_number=request.form.get('reference_number', ''),
            notes=request.form.get('notes', ''),
            created_by=current_user.id,
        )
        db.session.add(payment)
        db.session.commit()
        flash(f'Recorded Rs.{payment.amount:,.2f} from {customer.name}.', 'success')
        return redirect(url_for('customers.account_detail', id=customer.id))

    bal = get_customer_balance(id)
    return render_template('customers/payment_form.html', customer=customer, bal=bal,
                           today=date.today().isoformat())


@bp.route('/payment/<int:pid>/delete', methods=['POST'])
@login_required
@superadmin_required
def delete_payment(pid):
    payment = CustomerPayment.query.get_or_404(pid)
    cid = payment.customer_id
    amt = payment.amount
    db.session.delete(payment)
    db.session.commit()
    flash(f'Deleted payment of Rs.{amt:,.2f}.', 'info')
    return redirect(url_for('customers.account_detail', id=cid))


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
