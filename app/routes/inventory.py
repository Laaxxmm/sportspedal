from flask import Blueprint, render_template
from app.services.stock import get_inventory_data

bp = Blueprint('inventory', __name__)


@bp.route('/')
def view_inventory():
    inventory = get_inventory_data()
    return render_template('inventory.html', inventory=inventory)


@bp.route('/download')
def download_inventory():
    from app.services.excel_export import export_inventory
    inventory = get_inventory_data()
    return export_inventory(inventory)
