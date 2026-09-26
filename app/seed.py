from datetime import datetime

from app import db
from app.models import Adjustment, Delivery, Product, Receipt, StockLedger, Transfer, User
from werkzeug.security import generate_password_hash


def seed_demo_data():
    if User.query.filter_by(email="admin@stocvue.com").first() is None:
        user = User(
            username="admin",
            email="admin@stocvue.com",
            password_hash=generate_password_hash("admin123"),
        )
        db.session.add(user)

    existing_skus = {product.sku for product in Product.query.all()}
    products = [
        Product(name="Steel Rods", sku="STL-001", category="Raw Material", unit_of_measure="kg", stock_quantity=150, location="Main Warehouse", reorder_level=25),
        Product(name="Industrial Chair", sku="CHA-204", category="Furniture", unit_of_measure="pcs", stock_quantity=85, location="Rack A", reorder_level=20),
        Product(name="Packing Tape", sku="PKG-118", category="Packaging", unit_of_measure="rolls", stock_quantity=42, location="Production Floor", reorder_level=15),
        Product(name="Glass Panels", sku="GLS-310", category="Construction", unit_of_measure="sheets", stock_quantity=12, location="Main Warehouse", reorder_level=10),
        Product(name="Cables", sku="CAB-011", category="Electrical", unit_of_measure="m", stock_quantity=230, location="Warehouse 2", reorder_level=35),
    ]
    new_products = [product for product in products if product.sku not in existing_skus]
    if new_products:
        db.session.add_all(new_products)
        db.session.flush()

        receipts = [
            Receipt(product_id=new_products[0].id, supplier="Atlas Metals", quantity=100, status="Done"),
            Receipt(product_id=new_products[1].id, supplier="Casewell Furnitures", quantity=40, status="Waiting"),
            Receipt(product_id=new_products[2].id, supplier="PackPro", quantity=60, status="Done"),
        ]
        db.session.add_all(receipts)

        deliveries = [
            Delivery(product_id=new_products[1].id, customer="Northline Office", quantity=15, status="Ready"),
            Delivery(product_id=new_products[3].id, customer="Hudson Build", quantity=9, status="Done"),
            Delivery(product_id=new_products[2].id, customer="Walden Retail", quantity=8, status="Waiting"),
        ]
        db.session.add_all(deliveries)

        transfers = [
            Transfer(product_id=new_products[0].id, from_location="Main Warehouse", to_location="Production Floor", quantity=20, status="Done"),
            Transfer(product_id=new_products[1].id, from_location="Rack A", to_location="Rack B", quantity=10, status="Scheduled"),
            Transfer(product_id=new_products[4].id, from_location="Warehouse 2", to_location="Main Warehouse", quantity=30, status="In Transit"),
        ]
        db.session.add_all(transfers)

        adjustments = [
            Adjustment(product_id=new_products[3].id, location="Main Warehouse", quantity_delta=-2, reason="Broken panel during handling", status="Done"),
            Adjustment(product_id=new_products[2].id, location="Production Floor", quantity_delta=3, reason="New stock count verified", status="Done"),
        ]
        db.session.add_all(adjustments)

        ledger = [
            StockLedger(product_id=new_products[0].id, document_type="Receipt", quantity_change=100, description="Receipt #1 from Atlas Metals.", created_at=datetime(2026, 9, 16)),
            StockLedger(product_id=new_products[1].id, document_type="Receipt", quantity_change=40, description="Receipt #2 from Casewell Furnitures.", created_at=datetime(2026, 9, 18)),
            StockLedger(product_id=new_products[1].id, document_type="Delivery", quantity_change=-15, description="Delivery #1 to Northline Office.", created_at=datetime(2026, 9, 20)),
            StockLedger(product_id=new_products[3].id, document_type="Adjustment", quantity_change=-2, description="Adjustment: Broken panel during handling.", created_at=datetime(2026, 9, 21)),
            StockLedger(product_id=new_products[0].id, document_type="Transfer", quantity_change=0, description="Transfer from Main Warehouse to Production Floor.", created_at=datetime(2026, 9, 22)),
            StockLedger(product_id=new_products[4].id, document_type="Receipt", quantity_change=200, description="Receipt #5 from Volt Supply.", created_at=datetime(2026, 9, 23)),
        ]
        db.session.add_all(ledger)

    db.session.commit()
