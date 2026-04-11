from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.services.stock import get_inventory_data

bp = Blueprint('inventory', __name__)


@bp.route('/')
@login_required
def view_inventory():
    inventory = get_inventory_data()
    return render_template('inventory.html', inventory=inventory)


@bp.route('/download')
@login_required
def download_inventory():
    from app.services.excel_export import export_inventory
    inventory = get_inventory_data()
    return export_inventory(inventory)
