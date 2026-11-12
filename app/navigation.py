"""Navigation model shared by the sidebar, the in-page section tabs and the
dashboard quick actions.

The app used to list 16 pages flat in the sidebar. Related pages are now grouped
into a handful of sections; each section shows its pages as tabs at the top of
the page, so a page is reachable from exactly one sidebar entry. Every existing
URL keeps working - only how you get to it changes.
"""
from flask import request, url_for


def _can(user, perm):
    if perm is None:
        return True
    if perm == 'superadmin':
        return user.is_superadmin
    return user.has_permission(perm)


# Customer pages that belong to the "Advances" tab rather than "Customers"
_ADVANCE_ENDPOINTS = {
    'customers.accounts', 'customers.account_detail',
    'customers.record_payment', 'customers.new_advance',
}

# section key -> (sidebar label, sidebar icon, [tabs])
# A tab matches the current page by blueprint (all its pages) or exact endpoint.
SECTIONS = [
    ('sales', 'Sales', 'bi-receipt-cutoff', [
        dict(label='Sales', icon='bi-receipt-cutoff', endpoint='sales.list_sales',
             blueprints={'sales'}, exclude={'sales.discount_report'}, perm='view_sales'),
        dict(label='Discounts given', icon='bi-tags', endpoint='sales.discount_report',
             endpoints={'sales.discount_report'}, perm='view_sales'),
    ]),
    ('customers', 'Customers', 'bi-people-fill', [
        dict(label='Customers', icon='bi-people', endpoint='customers.list_customers',
             blueprints={'customers'}, exclude=_ADVANCE_ENDPOINTS, perm='view_customers'),
        dict(label='Advances', icon='bi-wallet2', endpoint='customers.accounts',
             endpoints=_ADVANCE_ENDPOINTS, perm='superadmin'),
    ]),
    ('stock', 'Stock', 'bi-box-seam-fill', [
        dict(label='Stock levels', icon='bi-clipboard-data', endpoint='inventory.view_inventory',
             blueprints={'inventory'}, perm='view_inventory'),
        dict(label='Products & prices', icon='bi-box-seam', endpoint='products.list_products',
             blueprints={'products'}, perm='view_products'),
        dict(label='Give-aways & damage', icon='bi-gift', endpoint='adjustments.list_adjustments',
             blueprints={'adjustments'}, perm='view_sales'),
        dict(label='Transfers', icon='bi-arrow-left-right', endpoint='transfers.list_transfers',
             blueprints={'transfers'}, perm='superadmin'),
    ]),
    ('purchases', 'Purchases', 'bi-cart-plus-fill', [
        dict(label='Purchase orders', icon='bi-cart-plus', endpoint='purchases.list_purchases',
             blueprints={'purchases'}, perm='view_purchases'),
        dict(label='Supplier payments', icon='bi-cash-coin', endpoint='payments.list_payments',
             blueprints={'payments'}, perm='superadmin'),
        dict(label='Suppliers', icon='bi-building', endpoint='suppliers.list_suppliers',
             blueprints={'suppliers'}, perm='superadmin'),
    ]),
    ('expenses', 'Expenses', 'bi-receipt', [
        dict(label='Expenses', icon='bi-receipt', endpoint='expenses.list_expenses',
             blueprints={'expenses'}, perm='superadmin'),
        dict(label='Transport', icon='bi-truck', endpoint='transport_expense.list_expenses',
             blueprints={'transport_expense'}, perm='superadmin'),
    ]),
]

ADMIN_LINKS = [
    dict(label='Users', icon='bi-person-gear', endpoint='users.list_users',
         blueprints={'users'}, perm='superadmin'),
    dict(label='Settings', icon='bi-gear-fill', endpoint='settings.business_settings',
         blueprints={'settings'}, perm='superadmin'),
]

# Things people actually come to the app to do, in rough order of frequency.
QUICK_ACTIONS = [
    dict(label='New sale', hint='Bill a customer', icon='bi-receipt-cutoff',
         endpoint='sales.new_sale', perm='edit_sales', tone='green'),
    dict(label='Stock arrived', hint='Goods received from supplier', icon='bi-box-arrow-in-down',
         endpoint='purchases.new_purchase', perm='edit_purchases', tone='blue'),
    dict(label='Pay supplier', hint='Money you paid out', icon='bi-cash-coin',
         endpoint='payments.new_payment', perm='superadmin', tone='amber'),
    dict(label='Customer advance', hint='Money a buyer paid in', icon='bi-wallet2',
         endpoint='customers.new_advance', perm='superadmin', tone='green'),
    dict(label='Add expense', hint='Travel, website, rent...', icon='bi-receipt',
         endpoint='expenses.new_expense', perm='superadmin', tone='rose'),
    dict(label='Log transport', hint='Courier / freight cost', icon='bi-truck',
         endpoint='transport_expense.new_expense', perm='superadmin', tone='indigo'),
    dict(label='Give-away / damage', hint='Promo, damaged or lost stock', icon='bi-gift',
         endpoint='adjustments.new_adjustment', perm='view_sales', tone='purple'),
    dict(label='Add product', hint='New item, colours, sizes', icon='bi-box-seam',
         endpoint='products.new_product', perm='view_products', tone='blue'),
    dict(label='Add customer', hint='Coach, bulk or public', icon='bi-person-plus',
         endpoint='customers.new_customer', perm='view_customers', tone='indigo'),
    dict(label='Move stock', hint='Between locations', icon='bi-arrow-left-right',
         endpoint='transfers.new_transfer', perm='superadmin', tone='amber'),
]


def _matches(tab, endpoint, blueprint):
    if endpoint in tab.get('exclude', ()):
        return False
    return endpoint in tab.get('endpoints', ()) or blueprint in tab.get('blueprints', ())


def build_navigation(user):
    """Return the sidebar items, the current page's section tabs and quick actions."""
    endpoint = request.endpoint or ''
    blueprint = request.blueprint or ''

    sidebar, tabs = [], []
    for key, label, icon, section_tabs in SECTIONS:
        visible = [t for t in section_tabs if _can(user, t['perm'])]
        if not visible:
            continue
        rendered = [dict(label=t['label'], icon=t['icon'], url=url_for(t['endpoint']),
                         active=_matches(t, endpoint, blueprint)) for t in visible]
        active = any(t['active'] for t in rendered)
        sidebar.append(dict(key=key, label=label, icon=icon,
                            url=rendered[0]['url'], active=active))
        if active and len(rendered) > 1:
            tabs = rendered

    admin = [dict(label=a['label'], icon=a['icon'], url=url_for(a['endpoint']),
                  active=_matches(a, endpoint, blueprint))
             for a in ADMIN_LINKS if _can(user, a['perm'])]

    actions = [dict(label=a['label'], hint=a['hint'], icon=a['icon'], tone=a['tone'],
                    url=url_for(a['endpoint']))
               for a in QUICK_ACTIONS if _can(user, a['perm'])]

    return dict(sidebar=sidebar, admin=admin, tabs=tabs, actions=actions,
                home_active=(endpoint == 'dashboard.index'))
