from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import BusinessProfile, PackagePrice

bp = Blueprint('settings', __name__)


@bp.route('/', methods=['GET', 'POST'])
@login_required
def business_settings():
    profile = BusinessProfile.query.first()
    if not profile:
        profile = BusinessProfile(id=1)
        db.session.add(profile)
        db.session.commit()

    if request.method == 'POST':
        profile.name = request.form.get('name', 'Sportspedal')
        profile.address = request.form.get('address', '')
        profile.city = request.form.get('city', 'Bangalore')
        profile.state = request.form.get('state', 'Karnataka')
        profile.state_code = request.form.get('state_code', '29')
        profile.gstin = request.form.get('gstin', '')
        profile.pan = request.form.get('pan', '')
        profile.phone = request.form.get('phone', '')
        profile.email = request.form.get('email', '')
        profile.bank_name = request.form.get('bank_name', '')
        profile.bank_account = request.form.get('bank_account', '')
        profile.bank_ifsc = request.form.get('bank_ifsc', '')
        profile.invoice_prefix = request.form.get('invoice_prefix', 'SP')
        profile.challan_prefix = request.form.get('challan_prefix', 'DC')
        profile.current_fy = request.form.get('current_fy', '2025-26')
        db.session.commit()
        flash('Business settings updated.', 'success')
        return redirect(url_for('settings.business_settings'))

    packages = PackagePrice.query.all()
    return render_template('settings.html', profile=profile, packages=packages)
