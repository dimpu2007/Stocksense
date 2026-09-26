from datetime import datetime

from app import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    otp_code = db.Column(db.String(10), nullable=True)
    otp_created_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    sku = db.Column(db.String(80), unique=True, nullable=False)
    category = db.Column(db.String(80), nullable=False)
    unit_of_measure = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(80), nullable=False, default="Main Warehouse")
    stock_quantity = db.Column(db.Integer, nullable=False, default=0)
    reorder_level = db.Column(db.Integer, nullable=False, default=10)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    receipts = db.relationship("Receipt", backref="product", lazy=True)
    deliveries = db.relationship("Delivery", backref="product", lazy=True)
    transfers = db.relationship("Transfer", backref="product", lazy=True)
    adjustments = db.relationship("Adjustment", backref="product", lazy=True)
    ledger_entries = db.relationship("StockLedger", backref="product", lazy=True)


class Receipt(db.Model):
    __tablename__ = "receipts"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    supplier = db.Column(db.String(120), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(30), nullable=False, default="Waiting")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Delivery(db.Model):
    __tablename__ = "deliveries"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    customer = db.Column(db.String(120), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(30), nullable=False, default="Ready")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Transfer(db.Model):
    __tablename__ = "transfers"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    from_location = db.Column(db.String(80), nullable=False)
    to_location = db.Column(db.String(80), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(30), nullable=False, default="Scheduled")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Adjustment(db.Model):
    __tablename__ = "adjustments"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    location = db.Column(db.String(80), nullable=False)
    quantity_delta = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="Done")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class StockLedger(db.Model):
    __tablename__ = "stock_ledger"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    document_type = db.Column(db.String(50), nullable=False)
    quantity_change = db.Column(db.Integer, nullable=False, default=0)
    description = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
