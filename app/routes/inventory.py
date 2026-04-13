from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from app.services.stock import get_inventory_data
from app.models import Location

bp = Blueprint('inventory', __name__)


@bp.route('/')
@login_required
def view_inventory():
    # Determine which location to show
    view = request.args.get('view', 'my')  # 'my' or 'global'
    location_id = None

    if current_user.is_superadmin:
        # Superadmin: can filter by state/location or see global
        loc_param = request.args.get('location_id', type=int)
        if loc_param:
            location_id = loc_param
            view = 'location'
    else:
        # Admin: default to their location, can toggle to global
        if view == 'my' and current_user.location_id:
            location_id = current_user.location_id
        else:
            location_id = None  # global view

    inventory = get_inventory_data(location_id)

    # Get locations for the filter (superadmin only)
    locations = []
    if current_user.is_superadmin:
        locations = Location.query.filter_by(is_active=True).order_by(Location.state, Location.district).all()

    selected_location = Location.query.get(location_id) if location_id else None

    return render_template('inventory.html', inventory=inventory, view=view,
                           locations=locations, selected_location=selected_location)


@bp.route('/download')
@login_required
def download_inventory():
    from app.services.excel_export import export_inventory
    location_id = None
    if not current_user.is_superadmin and current_user.location_id:
        view = request.args.get('view', 'my')
        if view == 'my':
            location_id = current_user.location_id
    else:
        location_id = request.args.get('location_id', type=int)
    inventory = get_inventory_data(location_id)
    return export_inventory(inventory)
