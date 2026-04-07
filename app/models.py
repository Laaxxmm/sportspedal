from datetime import datetime, date
from app import db


class BusinessProfile(db.Model):
    __tablename__ = 'business_profile'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), default='Sportspedal')
    address = db.Column(db.Text)
    city = db.Column(db.String(100), default='Bangalore')
    state = db.Column(db.String(100), default='Karnataka')
    state_code = db.Column(db.String(5), default='29')
    gstin = db.Column(db.String(20))
    pan = db.Column(db.String(15))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    bank_name = db.Column(db.String(100))
    bank_account = db.Column(db.String(30))
    bank_ifsc = db.Column(db.String(15))
    logo_path = db.Column(db.String(200))
    invoice_prefix = db.Column(db.String(10), default='SP')
    challan_prefix = db.Column(db.String(10), default='DC')
    current_fy = db.Column(db.String(10), default='2025-26')


class Product(db.Model):
    __tablename__ = 'product'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # skates, helmet, guards, bag, freebie
    hsn_code = db.Column(db.String(20))
    gst_percent = db.Column(db.Float, default=12.0)
    cost_price = db.Column(db.Float, default=0)
    coach_price = db.Column(db.Float, default=0)
    mrp = db.Column(db.Float, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    variants = db.relationship('ProductVariant', backref='product', lazy='dynamic', cascade='all, delete-orphan')


class ProductVariant(db.Model):
    __tablename__ = 'product_variant'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    color = db.Column(db.String(30))
    size = db.Column(db.String(10))
    sku_code = db.Column(db.String(30), unique=True)
    cost_price_override = db.Column(db.Float)
    coach_price_override = db.Column(db.Float)
    mrp_override = db.Column(db.Float)
    is_active = db.Column(db.Boolean, default=True)

    __table_args__ = (db.UniqueConstraint('product_id', 'color', 'size', name='uq_variant'),)

    @property
    def display_name(self):
        parts = [self.product.name]
        if self.color:
            parts.append(self.color)
        if self.size:
            parts.append(self.size)
        return ' - '.join(parts)

    @property
    def effective_cost(self):
        return self.cost_price_override if self.cost_price_override else self.product.cost_price

    @property
    def effective_coach_price(self):
        return self.coach_price_override if self.coach_price_override else self.product.coach_price

    @property
    def effective_mrp(self):
        return self.mrp_override if self.mrp_override else self.product.mrp


class Supplier(db.Model):
    __tablename__ = 'supplier'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    gstin = db.Column(db.String(20))
    address = db.Column(db.Text)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    purchase_orders = db.relationship('PurchaseOrder', backref='supplier', lazy='dynamic')


class Customer(db.Model):
    __tablename__ = 'customer'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    customer_type = db.Column(db.String(10), default='public')  # coach / public
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    state = db.Column(db.String(100), default='Karnataka')
    gstin = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sale_orders = db.relationship('SaleOrder', backref='customer', lazy='dynamic')


class PurchaseOrder(db.Model):
    __tablename__ = 'purchase_order'
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50))
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=False)
    order_date = db.Column(db.Date, default=date.today)
    location = db.Column(db.String(100), default='Bangalore')
    transporter = db.Column(db.String(100))
    status = db.Column(db.String(20), default='ordered')  # ordered / dispatched / delivered
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship('PurchaseItem', backref='purchase_order', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def total_amount(self):
        return sum(i.total_amount or 0 for i in self.items)

    @property
    def total_gst(self):
        return sum(i.gst_amount or 0 for i in self.items)


class PurchaseItem(db.Model):
    __tablename__ = 'purchase_item'
    id = db.Column(db.Integer, primary_key=True)
    purchase_order_id = db.Column(db.Integer, db.ForeignKey('purchase_order.id'), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey('product_variant.id'), nullable=False)
    quantity_dispatched = db.Column(db.Integer, default=0)
    quantity_received = db.Column(db.Integer, default=0)
    unit_price = db.Column(db.Float, default=0)
    gst_percent = db.Column(db.Float, default=12.0)
    gst_amount = db.Column(db.Float, default=0)
    total_amount = db.Column(db.Float, default=0)

    variant = db.relationship('ProductVariant')


class SaleOrder(db.Model):
    __tablename__ = 'sale_order'
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(30), unique=True)
    challan_number = db.Column(db.String(30))
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    sale_date = db.Column(db.Date, default=date.today)
    status = db.Column(db.String(20), default='confirmed')  # confirmed / dispatched / delivered
    transport_mode = db.Column(db.String(50))
    transport_charge = db.Column(db.Float, default=0)
    discount_amount = db.Column(db.Float, default=0)
    is_package = db.Column(db.Boolean, default=False)
    package_type = db.Column(db.String(50))  # e.g. "Velo Package", "Twister Package"
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship('SaleItem', backref='sale_order', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def subtotal(self):
        return sum(i.total_amount or 0 for i in self.items)

    @property
    def total_gst(self):
        return sum(i.gst_amount or 0 for i in self.items)

    @property
    def grand_total(self):
        return self.subtotal + (self.transport_charge or 0) - (self.discount_amount or 0)


class SaleItem(db.Model):
    __tablename__ = 'sale_item'
    id = db.Column(db.Integer, primary_key=True)
    sale_order_id = db.Column(db.Integer, db.ForeignKey('sale_order.id'), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey('product_variant.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Float, default=0)
    gst_percent = db.Column(db.Float, default=12.0)
    gst_amount = db.Column(db.Float, default=0)
    total_amount = db.Column(db.Float, default=0)

    variant = db.relationship('ProductVariant')


class PackagePrice(db.Model):
    __tablename__ = 'package_price'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)  # "Velo Package", "Twister Package", "Glider Package"
    skate_product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    coach_price = db.Column(db.Float, default=0)
    public_price = db.Column(db.Float, default=0)

    skate_product = db.relationship('Product')
