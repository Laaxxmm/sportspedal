from datetime import datetime, date
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


# ===== Authentication & Permissions =====

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    role = db.Column(db.String(20), nullable=False, default='admin')  # superadmin | admin | supplier
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=True)
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    location = db.relationship('Location', backref='users')
    supplier_link = db.relationship('Supplier', backref='users')
    permissions = db.relationship('AdminPermission', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_superadmin(self):
        return self.role == 'superadmin'

    @property
    def is_supplier_user(self):
        return self.role == 'supplier'

    def has_permission(self, key):
        if self.is_superadmin:
            return True
        perm = AdminPermission.query.filter_by(user_id=self.id, permission_key=key).first()
        return perm.is_granted if perm else False


class AdminPermission(db.Model):
    __tablename__ = 'admin_permission'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    permission_key = db.Column(db.String(100), nullable=False)
    is_granted = db.Column(db.Boolean, default=True)

    __table_args__ = (db.UniqueConstraint('user_id', 'permission_key', name='uq_user_perm'),)


# All permission keys used in the system
PERMISSION_KEYS = {
    # Page access
    'view_dashboard': 'View Dashboard',
    'view_products': 'View Products',
    'view_inventory': 'View Inventory',
    'view_purchases': 'View Purchases',
    'view_sales': 'View Sales',
    'view_customers': 'View Customers',
    'edit_sales': 'Create/Edit Sales',
    'edit_purchases': 'Create/Edit Purchases',
    # KPI cards
    'kpi_revenue': 'KPI: Revenue',
    'kpi_profit': 'KPI: Profit',
    'kpi_stock_value': 'KPI: Stock Value',
    'kpi_supplier_payable': 'KPI: Supplier Payable',
    'kpi_coach_public': 'KPI: Coach/Public Split',
}

# Mandatory permissions for all admins (always granted)
MANDATORY_PERMISSIONS = ['view_dashboard', 'view_inventory', 'view_sales', 'kpi_revenue']


# ===== Location =====

class Location(db.Model):
    __tablename__ = 'location'
    id = db.Column(db.Integer, primary_key=True)
    state = db.Column(db.String(100), nullable=False)
    district = db.Column(db.String(100), nullable=False)
    state_code = db.Column(db.String(5))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('state', 'district', name='uq_state_district'),)

    @property
    def display_name(self):
        return f"{self.district}, {self.state}"


# ===== Business Profile =====

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


# ===== Products =====

class Product(db.Model):
    __tablename__ = 'product'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    hsn_code = db.Column(db.String(20))
    gst_percent = db.Column(db.Float, default=12.0)
    cost_price = db.Column(db.Float, default=0)
    coach_price = db.Column(db.Float, default=0)
    mrp = db.Column(db.Float, default=0)
    image_path = db.Column(db.String(200))  # WebP thumbnail path
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    variants = db.relationship('ProductVariant', backref='product', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def image_url(self):
        if self.image_path:
            return f'/api/image/{self.image_path}'
        return None


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


# ===== Supplier =====

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
    payments = db.relationship('SupplierPayment', backref='supplier', lazy='dynamic')


# ===== Customer =====

class Customer(db.Model):
    __tablename__ = 'customer'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    customer_type = db.Column(db.String(10), default='public')
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    state = db.Column(db.String(100), default='Karnataka')
    gstin = db.Column(db.String(20))
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    location = db.relationship('Location')
    sale_orders = db.relationship('SaleOrder', backref='customer', lazy='dynamic')


# ===== Purchase Orders =====

class PurchaseOrder(db.Model):
    __tablename__ = 'purchase_order'
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50))
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=False)
    order_date = db.Column(db.Date, default=date.today)
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=True)
    transporter = db.Column(db.String(100))
    status = db.Column(db.String(20), default='ordered')
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    location = db.relationship('Location')
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


# ===== Sale Orders =====

class SaleOrder(db.Model):
    __tablename__ = 'sale_order'
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(30), unique=True)
    challan_number = db.Column(db.String(30))
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    sale_date = db.Column(db.Date, default=date.today)
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=True)
    status = db.Column(db.String(20), default='confirmed')
    payment_status = db.Column(db.String(20), default='paid')  # paid | pending | partial
    transport_mode = db.Column(db.String(50))
    transport_charge = db.Column(db.Float, default=0)
    discount_amount = db.Column(db.Float, default=0)
    is_package = db.Column(db.Boolean, default=False)
    package_type = db.Column(db.String(50))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    location = db.relationship('Location')
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


# ===== Package Pricing =====

class PackagePrice(db.Model):
    __tablename__ = 'package_price'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    skate_product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    coach_price = db.Column(db.Float, default=0)
    public_price = db.Column(db.Float, default=0)

    skate_product = db.relationship('Product')


# ===== Stock Transfers =====

class StockTransfer(db.Model):
    __tablename__ = 'stock_transfer'
    id = db.Column(db.Integer, primary_key=True)
    transfer_number = db.Column(db.String(50))
    from_location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=False)
    to_location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=False)
    transfer_date = db.Column(db.Date, default=date.today)
    status = db.Column(db.String(20), default='pending')  # pending | in_transit | completed
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    from_location = db.relationship('Location', foreign_keys=[from_location_id])
    to_location = db.relationship('Location', foreign_keys=[to_location_id])
    creator = db.relationship('User')
    items = db.relationship('StockTransferItem', backref='transfer', lazy='dynamic', cascade='all, delete-orphan')


class StockTransferItem(db.Model):
    __tablename__ = 'stock_transfer_item'
    id = db.Column(db.Integer, primary_key=True)
    transfer_id = db.Column(db.Integer, db.ForeignKey('stock_transfer.id'), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey('product_variant.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    variant = db.relationship('ProductVariant')


# ===== Supplier Payments =====

class SupplierPayment(db.Model):
    __tablename__ = 'supplier_payment'
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=False)
    payment_date = db.Column(db.Date, nullable=False, default=date.today)
    amount = db.Column(db.Float, nullable=False)
    payment_mode = db.Column(db.String(50))  # cash | bank_transfer | upi | cheque
    reference_number = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creator = db.relationship('User')
