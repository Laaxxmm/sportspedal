from app import create_app, db
from app.models import Product, ProductVariant, Supplier, PackagePrice, BusinessProfile

app = create_app()

# Auto-create tables on first run
with app.app_context():
    db.create_all()
    if Product.query.count() == 0:
        print("First run detected - seeding database with product catalog...")
        from seed import PRODUCTS, PACKAGES
        from app.routes.products import generate_sku

        profile = BusinessProfile(id=1, name='Sportspedal', city='Bangalore', state='Karnataka', state_code='29')
        db.session.add(profile)
        supplier = Supplier(name='True Spin', address='India')
        db.session.add(supplier)

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

        db.session.commit()
        print(f"  Seeded {Product.query.count()} products, {ProductVariant.query.count()} variants")

if __name__ == '__main__':
    app.run(debug=True, port=5000, use_reloader=False)
