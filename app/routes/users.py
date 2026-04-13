from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app import db
from app.models import User, Location, Supplier, AdminPermission, PERMISSION_KEYS, MANDATORY_PERMISSIONS
from app.decorators import superadmin_required
from app.data.india_locations import INDIA_STATES_DISTRICTS, STATES

bp = Blueprint('users', __name__)


@bp.route('/')
@login_required
@superadmin_required
def list_users():
    users = User.query.order_by(User.role.desc(), User.full_name).all()
    return render_template('users/list.html', users=users)


@bp.route('/new', methods=['GET', 'POST'])
@login_required
@superadmin_required
def new_user():
    if request.method == 'POST':
        username = request.form['username'].strip().lower()
        if User.query.filter_by(username=username).first():
            flash(f'Username "{username}" already exists.', 'danger')
            return redirect(url_for('users.new_user'))

        # Find or create location
        state = request.form.get('state', '')
        district = request.form.get('district', '')
        location = None
        if state and district:
            location = Location.query.filter_by(state=state, district=district).first()
            if not location:
                state_data = INDIA_STATES_DISTRICTS.get(state, {})
                location = Location(state=state, district=district, state_code=state_data.get('code', ''))
                db.session.add(location)
                db.session.flush()

        role = request.form.get('role', 'admin')
        supplier_id_val = None
        if role == 'supplier':
            supplier_id_val = request.form.get('supplier_id', type=int)

        user = User(
            username=username,
            full_name=request.form['full_name'].strip(),
            email=request.form.get('email', ''),
            phone=request.form.get('phone', ''),
            role=role,
            location_id=location.id if location else None,
            supplier_id=supplier_id_val,
        )
        password = request.form['password']
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return redirect(url_for('users.new_user'))
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        # Set permissions
        for key in PERMISSION_KEYS:
            is_mandatory = key in MANDATORY_PERMISSIONS
            is_granted = is_mandatory or (request.form.get(f'perm_{key}') == '1')
            db.session.add(AdminPermission(user_id=user.id, permission_key=key, is_granted=is_granted))

        db.session.commit()
        flash(f'User "{user.full_name}" created.', 'success')
        return redirect(url_for('users.list_users'))

    suppliers = Supplier.query.all()
    return render_template('users/form.html', user=None, states=STATES, suppliers=suppliers,
                           permission_keys=PERMISSION_KEYS, mandatory=MANDATORY_PERMISSIONS)


@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@superadmin_required
def edit_user(id):
    user = User.query.get_or_404(id)
    if request.method == 'POST':
        user.full_name = request.form['full_name'].strip()
        user.email = request.form.get('email', '')
        user.phone = request.form.get('phone', '')

        if request.form.get('password'):
            user.set_password(request.form['password'])

        # Update location
        state = request.form.get('state', '')
        district = request.form.get('district', '')
        if state and district and user.role == 'admin':
            location = Location.query.filter_by(state=state, district=district).first()
            if not location:
                state_data = INDIA_STATES_DISTRICTS.get(state, {})
                location = Location(state=state, district=district, state_code=state_data.get('code', ''))
                db.session.add(location)
                db.session.flush()
            user.location_id = location.id

        # Update permissions (only for admin users)
        if user.role == 'admin':
            AdminPermission.query.filter_by(user_id=user.id).delete()
            for key in PERMISSION_KEYS:
                is_mandatory = key in MANDATORY_PERMISSIONS
                is_granted = is_mandatory or (request.form.get(f'perm_{key}') == '1')
                db.session.add(AdminPermission(user_id=user.id, permission_key=key, is_granted=is_granted))

        db.session.commit()
        flash(f'User "{user.full_name}" updated.', 'success')
        return redirect(url_for('users.list_users'))

    # Get current permissions
    user_perms = {p.permission_key: p.is_granted for p in user.permissions}
    suppliers = Supplier.query.all()
    return render_template('users/form.html', user=user, states=STATES, suppliers=suppliers,
                           permission_keys=PERMISSION_KEYS, mandatory=MANDATORY_PERMISSIONS,
                           user_perms=user_perms)


@bp.route('/<int:id>/toggle-active', methods=['POST'])
@login_required
@superadmin_required
def toggle_active(id):
    user = User.query.get_or_404(id)
    if user.role == 'superadmin':
        flash('Cannot deactivate superadmin.', 'warning')
    else:
        user.is_active = not user.is_active
        db.session.commit()
        status = 'activated' if user.is_active else 'deactivated'
        flash(f'User "{user.full_name}" {status}.', 'info')
    return redirect(url_for('users.list_users'))
