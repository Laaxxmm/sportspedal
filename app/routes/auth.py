from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from datetime import datetime
from app import db
from app.models import User

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_supplier_user:
            return redirect(url_for('supplier_portal.portal_dashboard'))
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password) and user.is_active:
            user.last_login = datetime.utcnow()
            db.session.commit()
            login_user(user, remember=request.form.get('remember'))
            next_page = request.args.get('next') or ''
            # Only follow same-site relative paths; '//evil.com' or 'https://..'
            # would otherwise bounce a freshly logged-in user to another site.
            if not next_page.startswith('/') or next_page.startswith('//') or '\\' in next_page:
                next_page = None
            flash(f'Welcome, {user.full_name}!', 'success')
            if user.is_supplier_user:
                return redirect(url_for('supplier_portal.portal_dashboard'))
            return redirect(next_page or url_for('dashboard.index'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('auth/login.html')


@bp.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
