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
            # Copying the live file byte-for-byte can capture a half-written page if
            # a save happens mid-copy. The backup API takes a consistent snapshot.
            import sqlite3
            import tempfile
            fd, snap = tempfile.mkstemp(suffix='.db', dir=DATA_DIR)
            os.close(fd)
            try:
                src = sqlite3.connect(db_path)
                dst = sqlite3.connect(snap)
                with dst:
                    src.backup(dst)
                dst.close()
                src.close()
                zf.write(snap, arcname='sportspedal.db')
            finally:
                if os.path.exists(snap):
                    os.remove(snap)
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
        if not f or not f.filename.lower().endswith('.zip'):
            flash('Please upload a .zip backup file.', 'danger')
            return redirect(url_for('settings.restore_backup'))

        import shutil
        import sqlite3
        from datetime import datetime

        tmp_zip = os.path.join(DATA_DIR, '_restore_tmp.zip')
        tmp_db = os.path.join(DATA_DIR, '_restore_tmp.db')
        db_path = os.path.join(DATA_DIR, 'sportspedal.db')
        img_dir = os.path.join(DATA_DIR, 'images', 'products')
        try:
            f.save(tmp_zip)
            if not zipfile.is_zipfile(tmp_zip):
                raise ValueError('That file is not a valid ZIP archive.')

            with zipfile.ZipFile(tmp_zip, 'r') as zf:
                names = zf.namelist()
                if 'sportspedal.db' not in names:
                    raise ValueError('ZIP does not contain sportspedal.db - is this a Sportspedal backup?')

                # Extract the database to a temp file and prove it is a usable
                # Sportspedal database BEFORE touching the live one. Previously a
                # bad ZIP overwrote the live database with no way back.
                with zf.open('sportspedal.db') as src, open(tmp_db, 'wb') as out:
                    shutil.copyfileobj(src, out)
                conn = sqlite3.connect(tmp_db)
                try:
                    if conn.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                        raise ValueError('Backup database failed its integrity check.')
                    tables = {r[0] for r in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'")}
                    if not {'user', 'product', 'sale_order'} <= tables:
                        raise ValueError('Backup database is missing core tables.')
                finally:
                    conn.close()

                # Safety copy of the current database, kept on the volume
                safety = None
                if os.path.exists(db_path):
                    safety = os.path.join(
                        DATA_DIR, f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
                    shutil.copy2(db_path, safety)

                db.session.remove()
                db.engine.dispose()
                os.replace(tmp_db, db_path)

                # Images: plain file names only, written into the images folder
                os.makedirs(img_dir, exist_ok=True)
                restored_imgs = 0
                for member in names:
                    if not member.startswith('images/products/') or member.endswith('/'):
                        continue
                    fname = os.path.basename(member)
                    if not fname or fname.startswith('.'):
                        continue
                    with zf.open(member) as src, open(os.path.join(img_dir, fname), 'wb') as out:
                        shutil.copyfileobj(src, out)
                    restored_imgs += 1

            msg = f'Backup restored ({restored_imgs} images). Redeploy/restart the app to apply any schema updates.'
            if safety:
                msg += f' Previous data saved as {os.path.basename(safety)}.'
            flash(msg, 'success')
            return redirect(url_for('settings.business_settings'))
        except Exception as e:
            flash(f'Restore failed - current data left untouched: {e}', 'danger')
            return redirect(url_for('settings.restore_backup'))
        finally:
            for p in (tmp_zip, tmp_db):
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except OSError:
                        pass

    return render_template('restore.html')
