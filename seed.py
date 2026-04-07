"""Seed the database with initial products, variants, supplier, and package prices from Excel data."""
from app import create_app, db
from app.models import Product, ProductVariant, Supplier, PackagePrice, BusinessProfile
from app.routes.products import generate_sku

app = create_app()

PRODUCTS = [
    # (name, category, cost_price, coach_price, mrp, gst%, colors, sizes)
    ('Velo Kids', 'skates', 2250, 2299, 3899, 12, ['Blue', 'Pink'], ['XS', 'S']),
    ('Twister', 'skates', 3999, 4199, 6499, 12, ['Blue', 'Pink'], ['XS', 'S', 'M', 'L']),
    ('Glider', 'skates', 5399, 5399, 8499, 12, ['Blue', 'Grey'], ['M', 'L']),
    ('Pebble', 'helmet', 699, 649, 899, 12, ['Blue', 'Pink'], ['XS', 'S']),
    ('Vortex', 'helmet', 749, 749, 999, 12, [], []),
    ('Petron', 'guards', 699, 699, 999, 12, [], []),
    ('Brutal', 'guards', 749, 749, 1199, 12, [], []),
    ('Kids Bag', 'bag', 399, 399, 599, 12, [], []),
    ('Boys Bag', 'bag', 499, 499, 699, 12, [], []),
]

PACKAGES = [
    # (name, skate_name, coach_price, public_price)
    ('Velo Package', 'Velo Kids', 3899, 5499),
    ('Twister Package', 'Twister', 5799, 8799),
    ('Glider Package', 'Glider', 6990, 10900),
]

with app.app_context():
    db.create_all()

    # Business profile
    if not BusinessProfile.query.first():
        profile = BusinessProfile(id=1, name='Sportspedal', city='Bangalore', state='Karnataka', state_code='29')
        db.session.add(profile)

    # Supplier
    if not Supplier.query.first():
        supplier = Supplier(name='True Spin', address='India')
        db.session.add(supplier)

    # Products
    if Product.query.count() == 0:
        for name, category, cost, coach, mrp, gst, colors, sizes in PRODUCTS:
            product = Product(
                name=name, category=category,
                cost_price=cost, coach_price=coach, mrp=mrp,
                gst_percent=gst,
            )
            db.session.add(product)
            db.session.flush()

            if colors and sizes:
                for color in colors:
                    for size in sizes:
                        v = ProductVariant(
                            product_id=product.id, color=color, size=size,
                            sku_code=generate_sku(name, color, size),
                        )
                        db.session.add(v)
            elif colors:
                for color in colors:
                    v = ProductVariant(
                        product_id=product.id, color=color,
                        sku_code=generate_sku(name, color, None),
                    )
                    db.session.add(v)
            else:
                v = ProductVariant(
                    product_id=product.id,
                    sku_code=generate_sku(name, None, None),
                )
                db.session.add(v)

        db.session.flush()

        # Package prices
        for pkg_name, skate_name, coach_price, public_price in PACKAGES:
            skate = Product.query.filter_by(name=skate_name).first()
            if skate:
                pkg = PackagePrice(
                    name=pkg_name,
                    skate_product_id=skate.id,
                    coach_price=coach_price,
                    public_price=public_price,
                )
                db.session.add(pkg)

    db.session.commit()
    print("Database seeded successfully!")
    print(f"  Products: {Product.query.count()}")
    print(f"  Variants: {ProductVariant.query.count()}")
    print(f"  Packages: {PackagePrice.query.count()}")
    print(f"  Suppliers: {Supplier.query.count()}")
