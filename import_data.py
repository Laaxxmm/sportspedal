"""Import existing data from Excel files into the database."""
from datetime import date
from app import create_app, db
from app.models import (Product, ProductVariant, Supplier, Customer,
                        PurchaseOrder, PurchaseItem, SaleOrder, SaleItem,
                        BusinessProfile, PackagePrice)

app = create_app()

# ===== PURCHASE DATA =====
# From "Order Received" sheet + "Inward" sheet + "Inventory" sheet
# PO1: March 23 - Velo Kids (28), Pebble (30), Bag (30)
# PO2: March 26 - Twister (30), Pebble (20)
# PO3: Guards purchase (Petron ~9, Brutal ~3) - no date in Excel, assume March 23

PURCHASE_ORDERS = [
    {
        'number': 'PO-001', 'date': date(2026, 3, 23),
        'transporter': 'Xpress', 'notes': 'First order',
        'items': [
            # Velo Kids 28 total: 7 per variant
            ('Velo Kids', 'Blue', 'XS', 7, 2250),
            ('Velo Kids', 'Pink', 'XS', 7, 2250),
            ('Velo Kids', 'Blue', 'S', 7, 2250),
            ('Velo Kids', 'Pink', 'S', 7, 2250),
            # Pebble 30: split across 4 variants (8,8,7,7)
            ('Pebble', 'Blue', 'XS', 8, 699),
            ('Pebble', 'Blue', 'S', 8, 699),
            ('Pebble', 'Pink', 'XS', 7, 699),
            ('Pebble', 'Pink', 'S', 7, 699),
            # Bag 30
            ('Kids Bag', None, None, 30, 599),
        ],
    },
    {
        'number': 'PO-002', 'date': date(2026, 3, 26),
        'transporter': 'RCPL', 'notes': 'Second order',
        'items': [
            # Twister 30 total per inventory sheet
            ('Twister', 'Blue', 'XS', 6, 3999),
            ('Twister', 'Pink', 'XS', 4, 3999),
            ('Twister', 'Blue', 'S', 5, 3999),
            ('Twister', 'Pink', 'S', 5, 3999),
            ('Twister', 'Blue', 'M', 10, 3999),
            # Twister Pink M/L: 0 in inventory
            # Pebble 20 more: split (5,5,5,5)
            ('Pebble', 'Blue', 'XS', 5, 699),
            ('Pebble', 'Blue', 'S', 5, 699),
            ('Pebble', 'Pink', 'XS', 5, 699),
            ('Pebble', 'Pink', 'S', 5, 699),
        ],
    },
    {
        'number': 'PO-003', 'date': date(2026, 3, 23),
        'transporter': 'Xpress', 'notes': 'Guards purchase',
        'items': [
            # Guards for packages - enough to cover sales
            ('Petron', None, None, 15, 699),
            ('Brutal', None, None, 10, 749),
        ],
    },
]

# ===== CUSTOMER SALES DATA =====
# From "customer Details" sheet
# NOTE: "Helmet Decathlon" (999) = NOT our product, bought from Decathlon and bundled.
#        We DON'T deduct these from our inventory.
#        "Helmet TS" = our Pebble helmet
# Guards sold at 1199 = Petron, at 1799 = Brutal
CUSTOMER_SALES = [
    {'name': 'Ramya Raj', 'type': 'public', 'items': [
        ('Velo Kids', 3000, 1), ('Petron', 1199, 1), ('Kids Bag', 600, 1)]},
    {'name': 'Agnes Solamina', 'type': 'public', 'items': [
        ('Velo Kids', 3002, 1), ('Petron', 1199, 1), ('Kids Bag', 600, 1)]},
    # Helmet Decathlon 999 excluded - not our product
    {'name': 'Gowtham Vellore', 'type': 'public', 'items': [
        ('Velo Kids', 2299, 1), ('Kids Bag', 499, 1)]},
    {'name': 'Manjunath', 'type': 'coach', 'items': [
        ('Twister', 4500, 1), ('Pebble', 1500, 1)]},
    {'name': 'Swetha', 'type': 'public', 'items': [
        ('Velo Kids', 3002, 1), ('Petron', 1199, 1), ('Kids Bag', 600, 1)]},
    {'name': 'Jitendar', 'type': 'public', 'items': [
        ('Velo Kids', 2902, 1), ('Petron', 1199, 1), ('Kids Bag', 600, 1)]},
    {'name': 'Jitendar (2)', 'type': 'public', 'items': [
        ('Velo Kids', 2902, 1), ('Petron', 1199, 1), ('Kids Bag', 600, 1)]},
    {'name': 'Dsouzuo', 'type': 'public', 'items': [
        ('Twister', 5402, 1), ('Brutal', 1799, 1), ('Pebble', 999, 1), ('Kids Bag', 600, 1)]},
    {'name': 'Yasmeen', 'type': 'public', 'items': [
        ('Velo Kids', 3002, 1), ('Petron', 1199, 1), ('Kids Bag', 600, 1)]},
    {'name': 'Yasmeen (2)', 'type': 'public', 'items': [
        ('Twister', 5402, 1), ('Brutal', 1799, 1), ('Pebble', 999, 1), ('Kids Bag', 600, 1)]},
    {'name': 'Kavitha', 'type': 'public', 'items': [
        ('Velo Kids', 3002, 1), ('Petron', 1199, 1), ('Kids Bag', 600, 1)]},
    {'name': 'Kavitha (2)', 'type': 'public', 'items': [
        ('Twister', 5402, 1), ('Brutal', 1799, 1), ('Pebble', 999, 1), ('Kids Bag', 600, 1)]},
    {'name': 'Gowtham', 'type': 'public', 'items': [
        ('Velo Kids', 2299, 1), ('Kids Bag', 499, 1)]},
    {'name': 'Gubuchu Play', 'type': 'public', 'items': [
        ('Velo Kids', 3002, 1), ('Petron', 1199, 1), ('Kids Bag', 600, 1)]},
    {'name': 'New Girl Pink', 'type': 'public', 'items': [
        ('Velo Kids', 3002, 1), ('Petron', 1199, 1), ('Kids Bag', 600, 1)]},
    {'name': '2 Bags Customer', 'type': 'public', 'items': [
        ('Kids Bag', 500, 2)]},  # 2 bags at 1000 total = 500 each
]

# ===== EXPECTED STOCK (from Inventory sheet) for verification =====
EXPECTED_STOCK = {
    'Velo Kids': {'inward': 28, 'outward': 13, 'stock': 15},
    'Twister':   {'inward': 30, 'outward': 6,  'stock': 24},
    'Pebble':    {'inward': 50, 'outward': 5,  'stock': 45},
    'Kids Bag':  {'inward': 30, 'outward': 14, 'stock': 16},
}


def find_variant(product_name, color=None, size=None):
    product = Product.query.filter_by(name=product_name, is_active=True).first()
    if not product:
        return None
    if color and size:
        return ProductVariant.query.filter_by(
            product_id=product.id, color=color, size=size, is_active=True).first()
    return ProductVariant.query.filter_by(product_id=product.id, is_active=True).first()


def find_variant_with_stock(product_name, sold_tracker):
    """Pick a variant that still has remaining stock based on inward - sold so far."""
    product = Product.query.filter_by(name=product_name, is_active=True).first()
    if not product:
        return None
    variants = ProductVariant.query.filter_by(product_id=product.id, is_active=True).all()
    for v in variants:
        sold = sold_tracker.get(v.id, 0)
        # Use inward from purchase items
        inward = sum(pi.quantity_received for pi in PurchaseItem.query.filter_by(variant_id=v.id).all())
        if inward - sold > 0:
            return v
    return variants[0] if variants else None


with app.app_context():
    db.create_all()

    if PurchaseOrder.query.count() > 0:
        print("Data already imported! Delete data/sportspedal.db and run seed.py + import_data.py")
        exit()

    supplier = Supplier.query.filter_by(name='True Spin').first()

    # ===== CREATE PURCHASE ORDERS =====
    print("Importing purchases...")
    for po_data in PURCHASE_ORDERS:
        po = PurchaseOrder(
            order_number=po_data['number'],
            supplier_id=supplier.id,
            order_date=po_data['date'],
            transporter=po_data['transporter'],
            status='delivered',
            location='Bangalore',
            notes=po_data['notes'],
        )
        db.session.add(po)
        db.session.flush()

        for prod_name, color, size, qty, price in po_data['items']:
            if qty <= 0:
                continue
            variant = find_variant(prod_name, color, size)
            if not variant:
                print(f"  WARNING: Variant not found: {prod_name} {color} {size}")
                continue
            product = variant.product
            gst_pct = product.gst_percent
            taxable = price * qty
            gst = taxable * gst_pct / 100
            db.session.add(PurchaseItem(
                purchase_order_id=po.id, variant_id=variant.id,
                quantity_dispatched=qty, quantity_received=qty,
                unit_price=price, gst_percent=gst_pct,
                gst_amount=gst, total_amount=taxable + gst,
            ))
        print(f"  {po_data['number']}: {po_data['notes']}")

    db.session.flush()

    # ===== CREATE CUSTOMERS & SALES =====
    print("\nImporting sales...")
    sold_tracker = {}  # {variant_id: qty sold so far}

    for idx, sale_data in enumerate(CUSTOMER_SALES):
        cust_name = sale_data['name']
        customer = Customer.query.filter_by(name=cust_name).first()
        if not customer:
            customer = Customer(
                name=cust_name,
                customer_type=sale_data['type'],
                city='Bangalore', state='Karnataka',
            )
            db.session.add(customer)
            db.session.flush()

        sale = SaleOrder(
            invoice_number=f"SP/2025-26/{idx+1:03d}",
            challan_number=f"DC/2025-26/{idx+1:03d}",
            customer_id=customer.id,
            sale_date=date(2026, 3, 25 + idx // 4),
            status='delivered',
        )
        db.session.add(sale)
        db.session.flush()

        sale_total = 0
        for product_name, sell_price, qty in sale_data['items']:
            product = Product.query.filter_by(name=product_name, is_active=True).first()
            if not product:
                print(f"  WARNING: Product '{product_name}' not found")
                continue

            if product.category == 'skates':
                variant = find_variant_with_stock(product_name, sold_tracker)
            else:
                variant = find_variant(product_name)

            if not variant:
                print(f"  WARNING: No variant for '{product_name}'")
                continue

            gst_pct = product.gst_percent
            # sell_price is the total price charged (GST inclusive)
            unit_price_incl = sell_price
            unit_price_excl = round(sell_price / (1 + gst_pct / 100), 2)
            gst_amt = round(unit_price_incl - unit_price_excl, 2)

            db.session.add(SaleItem(
                sale_order_id=sale.id,
                variant_id=variant.id,
                quantity=qty,
                unit_price=unit_price_excl,
                gst_percent=gst_pct,
                gst_amount=gst_amt * qty,
                total_amount=unit_price_incl * qty,
            ))

            sold_tracker[variant.id] = sold_tracker.get(variant.id, 0) + qty
            sale_total += unit_price_incl * qty

        print(f"  Sale {idx+1}: {cust_name} - Rs.{sale_total:.0f}")

    db.session.commit()

    # ===== VERIFICATION =====
    from app.services.stock import get_stock_map, get_inventory_data
    stock_map = get_stock_map()
    inventory = get_inventory_data()

    print(f"\n{'='*60}")
    print(f"IMPORT SUMMARY")
    print(f"{'='*60}")
    print(f"  Purchase Orders: {PurchaseOrder.query.count()}")
    print(f"  Customers:       {Customer.query.count()}")
    print(f"  Sales:           {SaleOrder.query.count()}")

    print(f"\n{'='*60}")
    print(f"STOCK BY PRODUCT")
    print(f"{'='*60}")
    # Aggregate by product
    from collections import defaultdict
    product_stock = defaultdict(lambda: {'inward': 0, 'outward': 0, 'stock': 0})
    for item in inventory:
        key = item['product_name']
        product_stock[key]['inward'] += item['inward']
        product_stock[key]['outward'] += item['outward']
        product_stock[key]['stock'] += item['stock']

    for name in sorted(product_stock.keys()):
        d = product_stock[name]
        expected = EXPECTED_STOCK.get(name, {})
        exp_stock = expected.get('stock', '?')
        match = ' OK' if d['stock'] == exp_stock else f' (expected {exp_stock})'
        print(f"  {name:15s}  In:{d['inward']:3d}  Out:{d['outward']:3d}  Stock:{d['stock']:3d}{match}")

    # Financial summary
    total_purchase = sum(po.total_amount for po in PurchaseOrder.query.all())
    total_revenue = sum(s.grand_total for s in SaleOrder.query.all())
    total_cogs = 0
    for si in SaleItem.query.all():
        cost = si.variant.effective_cost or 0
        total_cogs += cost * si.quantity

    print(f"\n{'='*60}")
    print(f"FINANCIAL SUMMARY")
    print(f"{'='*60}")
    print(f"  Total Purchase Cost (incl GST): Rs.{total_purchase:,.2f}")
    print(f"  Total Revenue (from sales):     Rs.{total_revenue:,.2f}")
    print(f"  Cost of Goods Sold:             Rs.{total_cogs:,.2f}")
    print(f"  Gross Profit:                   Rs.{total_revenue - total_cogs:,.2f}")
