import os
from datetime import date
from app import create_app, db
from app.models import (Product, ProductVariant, Supplier, PackagePrice,
                        BusinessProfile, Customer, PurchaseOrder, PurchaseItem,
                        SaleOrder, SaleItem, User, Location, AdminPermission,
                        PERMISSION_KEYS, MANDATORY_PERMISSIONS)

app = create_app()


def seed_and_import():
    """Seed products, users, locations + import all existing purchase/sales data on first run."""
    from seed import PRODUCTS, PACKAGES
    from import_data import PURCHASE_ORDERS, CUSTOMER_SALES
    from app.routes.products import generate_sku
    from app.data.india_locations import INDIA_STATES_DISTRICTS

    # === Create default location (Bangalore) ===
    print("=== Seeding locations ===")
    bangalore = Location(state='Karnataka', district='Bengaluru Urban', state_code='29')
    db.session.add(bangalore)
    db.session.flush()
    print(f"  Default location: {bangalore.display_name} (id={bangalore.id})")

    # === Create superadmin user ===
    print("=== Creating superadmin ===")
    admin = User(
        username='admin',
        full_name='Super Admin',
        role='superadmin',
        location_id=None,
    )
    admin.set_password('admin123')
    db.session.add(admin)
    db.session.flush()
    # Grant all permissions to superadmin
    for key in PERMISSION_KEYS:
        db.session.add(AdminPermission(user_id=admin.id, permission_key=key, is_granted=True))
    print(f"  Superadmin: admin / admin123")

    # === Business profile ===
    profile = BusinessProfile(id=1, name='Sportspedal', city='Bangalore', state='Karnataka', state_code='29')
    db.session.add(profile)
    supplier = Supplier(name='True Spin', address='India')
    db.session.add(supplier)
    db.session.flush()

    # Create supplier user for True Spin
    sup_user = User(username='truespin', full_name='True Spin', role='supplier', supplier_id=supplier.id)
    sup_user.set_password('truespin123')
    db.session.add(sup_user)
    print(f"  Supplier user: truespin / truespin123")

    # === Seed products ===
    print("=== Seeding products ===")
    for name, category, cost, coach, mrp, gst, colors, sizes in PRODUCTS:
        product = Product(name=name, category=category, cost_price=cost, coach_price=coach, mrp=mrp, gst_percent=gst)
        db.session.add(product)
        db.session.flush()
        if colors and sizes:
            for color in colors:
                for size in sizes:
                    db.session.add(ProductVariant(product_id=product.id, color=color, size=size, sku_code=generate_sku(name, color, size)))
        elif colors:
            for color in colors:
                db.session.add(ProductVariant(product_id=product.id, color=color, sku_code=generate_sku(name, color, None)))
        else:
            db.session.add(ProductVariant(product_id=product.id, sku_code=generate_sku(name, None, None)))
    db.session.flush()

    for pkg_name, skate_name, coach_price, public_price in PACKAGES:
        skate = Product.query.filter_by(name=skate_name).first()
        if skate:
            db.session.add(PackagePrice(name=pkg_name, skate_product_id=skate.id, coach_price=coach_price, public_price=public_price))
    db.session.flush()
    print(f"  Products: {Product.query.count()}, Variants: {ProductVariant.query.count()}")

    # === Import purchases (all to Bangalore) ===
    print("=== Importing purchases ===")
    supplier = Supplier.query.first()
    for po_data in PURCHASE_ORDERS:
        po = PurchaseOrder(
            order_number=po_data['number'], supplier_id=supplier.id,
            order_date=po_data['date'], transporter=po_data['transporter'],
            status='delivered', location_id=bangalore.id, notes=po_data['notes'],
        )
        db.session.add(po)
        db.session.flush()
        for prod_name, color, size, qty, price in po_data['items']:
            if qty <= 0:
                continue
            product = Product.query.filter_by(name=prod_name, is_active=True).first()
            if not product:
                continue
            if color and size:
                variant = ProductVariant.query.filter_by(product_id=product.id, color=color, size=size).first()
            else:
                variant = ProductVariant.query.filter_by(product_id=product.id, is_active=True).first()
            if not variant:
                continue
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

    # === Import customer sales (all to Bangalore, 0% GST) ===
    print("=== Importing sales ===")
    sold_tracker = {}
    for idx, sale_data in enumerate(CUSTOMER_SALES):
        customer = Customer(
            name=sale_data['name'], customer_type=sale_data['type'],
            city='Bangalore', state='Karnataka', location_id=bangalore.id,
        )
        db.session.add(customer)
        db.session.flush()

        sale = SaleOrder(
            invoice_number=f"SP/2025-26/{idx+1:03d}",
            challan_number=f"DC/2025-26/{idx+1:03d}",
            customer_id=customer.id,
            sale_date=date(2026, 3, 25 + idx // 4),
            status='delivered', payment_status='paid',
            location_id=bangalore.id,
        )
        db.session.add(sale)
        db.session.flush()

        for product_name, sell_price, qty in sale_data['items']:
            product = Product.query.filter_by(name=product_name, is_active=True).first()
            if not product:
                continue
            if product.category == 'skates':
                variants = ProductVariant.query.filter_by(product_id=product.id, is_active=True).all()
                variant = None
                for v in variants:
                    sold = sold_tracker.get(v.id, 0)
                    inward = sum(pi.quantity_received for pi in PurchaseItem.query.filter_by(variant_id=v.id).all())
                    if inward - sold > 0:
                        variant = v
                        break
                if not variant:
                    variant = variants[0] if variants else None
            else:
                variant = ProductVariant.query.filter_by(product_id=product.id, is_active=True).first()
            if not variant:
                continue
            db.session.add(SaleItem(
                sale_order_id=sale.id, variant_id=variant.id,
                quantity=qty, unit_price=sell_price,
                cost_at_sale=variant.effective_cost,
                gst_percent=0, gst_amount=0,
                total_amount=sell_price * qty,
            ))
            sold_tracker[variant.id] = sold_tracker.get(variant.id, 0) + qty
        print(f"  Sale {idx+1}: {sale_data['name']}")

    db.session.commit()
    print(f"=== Done: {PurchaseOrder.query.count()} purchases, {SaleOrder.query.count()} sales, {Customer.query.count()} customers ===")
    print(f"=== Login: admin / admin123 ===")


def init_database():
    """Initialize DB with tables, migrations, and seeding. Defensive - never raises."""
    print("=== Initializing database ===")

    # Step 1: Create tables for any new models
    try:
        db.create_all()
        print("  db.create_all() OK")
    except Exception as e:
        print(f"  create_all error: {e}")

    # Step 2: Add missing columns to existing tables (preserves data)
    migrations = [
        ('sale_item', 'cost_at_sale', 'FLOAT DEFAULT 0'),
        ('user', 'supplier_id', 'INTEGER'),
        ('sale_order', 'shipping_cost', 'FLOAT DEFAULT 0'),
        ('sale_order', 'shipping_carrier', 'VARCHAR(100)'),
        ('sale_order', 'shipping_tracking', 'VARCHAR(100)'),
        ('sale_order', 'shipping_paid_by', "VARCHAR(20) DEFAULT 'self'"),
        ('sale_order', 'location_id', 'INTEGER'),
        ('sale_order', 'payment_status', "VARCHAR(20) DEFAULT 'paid'"),
        ('sale_order', 'transport_type', "VARCHAR(20) DEFAULT 'self'"),
        ('sale_order', 'is_bulk', 'BOOLEAN DEFAULT 0'),
        ('product', 'image_path', 'VARCHAR(200)'),
        ('product', 'coach_local', 'FLOAT DEFAULT 0'),
        ('product', 'coach_direct', 'FLOAT DEFAULT 0'),
        ('product', 'coach_self', 'FLOAT DEFAULT 0'),
        ('product', 'bulk_local', 'FLOAT DEFAULT 0'),
        ('product', 'bulk_direct', 'FLOAT DEFAULT 0'),
        ('product', 'bulk_self', 'FLOAT DEFAULT 0'),
        ('product', 'dealer_price', 'FLOAT DEFAULT 0'),
        ('purchase_order', 'location_id', 'INTEGER'),
        ('purchase_order', 'bulk_discount', 'FLOAT DEFAULT 0'),
        ('purchase_order', 'discount_reason', 'VARCHAR(200)'),
        ('customer', 'location_id', 'INTEGER'),
        ('supplier_payment', 'shipping_deduction', 'FLOAT DEFAULT 0'),
    ]

    from sqlalchemy import text
    for table, col, col_def in migrations:
        try:
            with db.engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}"))
            print(f"  Added column: {table}.{col}")
        except Exception:
            pass  # Column already exists - this is fine

    # Step 3: Seed if empty
    try:
        if User.query.count() == 0:
            print("=== Seeding database ===")
            seed_and_import()
        else:
            print(f"=== DB ready: {User.query.count()} users, {Product.query.count()} products ===")
    except Exception as e:
        print(f"  Seed check error: {e}")


with app.app_context():
    try:
        init_database()
    except Exception as e:
        print(f"=== DB init failed (continuing anyway): {e} ===")

if __name__ == '__main__':
    debug = os.environ.get('FLASK_ENV') != 'production'
    app.run(debug=debug, port=int(os.environ.get('PORT', 5000)), use_reloader=False)
