import os
import io
import zipfile
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, abort
from flask_login import login_required, current_user
from app import db
from app.models import BusinessProfile, PackagePrice
from app.decorators import superadmin_required

bp = Blueprint('settings', __name__)


@bp.route('/', methods=['GET', 'POST'])
@login_required
@superadmin_required
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


@bp.route('/backup')
@login_required
@superadmin_required
def download_backup():
    """Download a ZIP containing the database + all product images."""
    from app.config import DATA_DIR
    db_path = os.path.join(DATA_DIR, 'sportspedal.db')
    images_dir = os.path.join(DATA_DIR, 'images', 'products')

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        if os.path.exists(db_path):
            zf.write(db_path, arcname='sportspedal.db')
        if os.path.exists(images_dir):
            for fname in os.listdir(images_dir):
                fpath = os.path.join(images_dir, fname)
                if os.path.isfile(fpath):
                    zf.write(fpath, arcname=f'images/products/{fname}')

    buf.seek(0)
    from datetime import datetime
    filename = f"sportspedal_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    return send_file(buf, mimetype='application/zip',
                     download_name=filename, as_attachment=True)


@bp.route('/restore', methods=['GET', 'POST'])
@login_required
@superadmin_required
def restore_backup():
    """Upload a backup ZIP to restore the database + images."""
    from app.config import DATA_DIR

    if request.method == 'POST':
        f = request.files.get('backup_file')
        if not f or not f.filename.endswith('.zip'):
            flash('Please upload a .zip backup file.', 'danger')
            return redirect(url_for('settings.restore_backup'))

        try:
            # Save uploaded file temporarily
            tmp_path = os.path.join(DATA_DIR, '_restore_tmp.zip')
            f.save(tmp_path)

            os.makedirs(os.path.join(DATA_DIR, 'images', 'products'), exist_ok=True)

            # Close DB connections before overwriting
            db.session.remove()
            db.engine.dispose()

            with zipfile.ZipFile(tmp_path, 'r') as zf:
                for member in zf.namelist():
                    if member == 'sportspedal.db':
                        zf.extract(member, DATA_DIR)
                    elif member.startswith('images/products/'):
                        zf.extract(member, DATA_DIR)

            os.remove(tmp_path)
            flash('Backup restored! Restart the server to load new data.', 'success')
            return redirect(url_for('settings.business_settings'))
        except Exception as e:
            flash(f'Restore failed: {str(e)}', 'danger')
            return redirect(url_for('settings.restore_backup'))

    return render_template('restore.html')
