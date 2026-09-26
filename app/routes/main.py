import csv
from datetime import datetime
from io import StringIO

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app import db
from app.models import Adjustment, Delivery, Product, Receipt, StockLedger, Transfer


def _decode_csv_bytes(raw_bytes):
    encodings = ["utf-8-sig", "utf-8", "utf-16", "utf-16-le", "utf-16-be", "cp1252", "latin-1"]
    for encoding in encodings:
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw_bytes.decode("utf-8", errors="replace")


main_bp = Blueprint("main", __name__)


def login_required(route):
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("auth.login"))
        return route(*args, **kwargs)

    wrapped.__name__ = route.__name__
    return wrapped


@main_bp.route("/dashboard")
@login_required
def dashboard():
    products = Product.query.order_by(Product.name).all()
    receipts = Receipt.query.order_by(Receipt.created_at.desc()).all()
    deliveries = Delivery.query.order_by(Delivery.created_at.desc()).all()
    transfers = Transfer.query.order_by(Transfer.created_at.desc()).all()
    adjustments = Adjustment.query.order_by(Adjustment.created_at.desc()).all()

    total_stock = sum(item.stock_quantity for item in products)
    low_stock = sum(1 for item in products if item.stock_quantity <= item.reorder_level)
    out_of_stock = sum(1 for item in products if item.stock_quantity <= 0)
    pending_receipts = sum(1 for item in receipts if item.status in {"Draft", "Waiting", "Ready"})
    pending_deliveries = sum(1 for item in deliveries if item.status in {"Draft", "Waiting", "Ready"})
    internal_transfers = sum(1 for item in transfers if item.status in {"Scheduled", "In Transit"})

    categories = {}
    for product in products:
        categories[product.category] = categories.get(product.category, 0) + 1

    movement_data = []
    for item in StockLedger.query.order_by(StockLedger.created_at.asc()).all()[:10]:
        movement_data.append({
            "label": item.product.name,
            "value": item.quantity_change,
            "type": item.document_type,
        })

    ledger_entries = StockLedger.query.order_by(StockLedger.created_at.desc()).limit(8).all()

    document_type = request.args.get("document_type", "all")
    status = request.args.get("status", "all")
    warehouse = request.args.get("warehouse", "all")
    category = request.args.get("category", "all")

    filtered_entries = []
    for entry in ledger_entries:
        product = entry.product
        if category != "all" and product.category != category:
            continue
        if warehouse != "all" and product.location != warehouse:
            continue
        if document_type != "all" and entry.document_type.lower() != document_type.lower():
            continue
        if status != "all":
            match_status = None
            if entry.document_type == "Receipt":
                match_status = Receipt.query.filter_by(id=entry.description.split("#")[-1] if entry.description.startswith("Receipt") else None).first()
            if match_status is not None:
                if match_status.status.lower() != status.lower():
                    continue
        filtered_entries.append(entry)

    warehouses = sorted({product.location for product in products})
    categories_list = sorted({product.category for product in products})
    chart_labels = [item.name for item in products]
    chart_values = [item.stock_quantity for item in products]

    return render_template(
        "dashboard.html",
        products=products,
        receipts=receipts,
        deliveries=deliveries,
        transfers=transfers,
        adjustments=adjustments,
        total_stock=total_stock,
        low_stock=low_stock,
        out_of_stock=out_of_stock,
        pending_receipts=pending_receipts,
        pending_deliveries=pending_deliveries,
        internal_transfers=internal_transfers,
        categories=categories,
        movement_data=movement_data,
        ledger_entries=filtered_entries or ledger_entries,
        warehouses=warehouses,
        categories_list=categories_list,
        current_filters={
            "document_type": document_type,
            "status": status,
            "warehouse": warehouse,
            "category": category,
        },
        chart_labels=chart_labels,
        chart_values=chart_values,
    )


@main_bp.route("/products", methods=["GET", "POST"])
@login_required
def products():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        sku = request.form.get("sku", "").strip()
        category = request.form.get("category", "").strip()
        unit = request.form.get("unit_of_measure", "").strip()
        initial_stock = int(request.form.get("initial_stock", 0) or 0)
        location = request.form.get("location", "Main Warehouse").strip()

        if not name or not sku or not category or not unit:
            flash("All product fields are required.", "error")
            return redirect(url_for("main.products"))

        existing = Product.query.filter_by(sku=sku).first()
        if existing:
            flash("A product with that SKU already exists.", "error")
            return redirect(url_for("main.products"))

        new_product = Product(
            name=name,
            sku=sku,
            category=category,
            unit_of_measure=unit,
            stock_quantity=initial_stock,
            location=location,
            reorder_level=10,
        )
        db.session.add(new_product)
        db.session.commit()

        if initial_stock > 0:
            ledger_entry = StockLedger(
                product_id=new_product.id,
                document_type="Initial Stock",
                quantity_change=initial_stock,
                description=f"Initial stock entry for {new_product.name}.",
                created_at=datetime.utcnow(),
            )
            db.session.add(ledger_entry)
            db.session.commit()

        flash("Product created successfully.", "success")
        return redirect(url_for("main.products"))

    all_products = Product.query.order_by(Product.name).all()
    return render_template("products.html", products=all_products)


@main_bp.route("/products/upload-csv", methods=["POST"])
@login_required
def upload_products_csv():
    file = request.files.get("file")
    if not file or file.filename == "":
        flash("Please choose a CSV file to upload.", "error")
        return redirect(url_for("main.products"))

    if not file.filename.lower().endswith(".csv"):
        flash("Only CSV files are supported.", "error")
        return redirect(url_for("main.products"))

    try:
        csv_text = _decode_csv_bytes(file.read())
    except Exception:
        flash("The CSV file could not be read. Please save it as UTF-8/UTF-16 or plain CSV and try again.", "error")
        return redirect(url_for("main.products"))

    reader = csv.DictReader(StringIO(csv_text))
    if not reader.fieldnames:
        flash("The CSV file is empty.", "error")
        return redirect(url_for("main.products"))

    normalized_columns = {field.strip().lower(): field for field in reader.fieldnames if field}
    required_columns = ["name", "sku", "category", "unit_of_measure", "location", "initial_stock", "reorder_level"]
    missing = [col for col in required_columns if col not in normalized_columns]
    if missing:
        flash(f"CSV is missing required columns: {', '.join(missing)}.", "error")
        return redirect(url_for("main.products"))

    added = 0
    updated = 0

    for row in reader:
        name = (row.get(normalized_columns["name"]) or "").strip()
        sku = (row.get(normalized_columns["sku"]) or "").strip()
        category = (row.get(normalized_columns["category"]) or "").strip()
        unit = (row.get(normalized_columns["unit_of_measure"]) or "").strip()
        location = (row.get(normalized_columns["location"]) or "Main Warehouse").strip()

        if not name or not sku:
            continue

        try:
            initial_stock = int(str(row.get(normalized_columns["initial_stock"]) or 0).replace(",", "").strip())
        except ValueError:
            initial_stock = 0

        try:
            reorder_level = int(str(row.get(normalized_columns["reorder_level"]) or 10).replace(",", "").strip())
        except ValueError:
            reorder_level = 10

        product = Product.query.filter_by(sku=sku).first()
        if product is None:
            product = Product(
                name=name,
                sku=sku,
                category=category or "General",
                unit_of_measure=unit or "pcs",
                location=location,
                stock_quantity=initial_stock,
                reorder_level=reorder_level,
            )
            db.session.add(product)
            db.session.flush()
            added += 1
        else:
            product.name = name
            product.category = category or product.category
            product.unit_of_measure = unit or product.unit_of_measure
            product.location = location or product.location
            product.stock_quantity = max(0, initial_stock)
            product.reorder_level = reorder_level
            updated += 1

        db.session.add(
            StockLedger(
                product_id=product.id,
                document_type="Initial Stock",
                quantity_change=initial_stock,
                description=f"CSV import for {product.name}.",
                created_at=datetime.utcnow(),
            )
        )

    db.session.commit()
    flash(f"CSV imported successfully: {added} new products and {updated} updates.", "success")
    return redirect(url_for("main.products"))


@main_bp.route("/operations", methods=["GET", "POST"])
@login_required
def operations():
    products = Product.query.order_by(Product.name).all()

    if request.method == "POST":
        operation = request.form.get("operation")
        product_id = int(request.form.get("product_id"))
        product = Product.query.get_or_404(product_id)

        if operation == "receipt":
            quantity = int(request.form.get("quantity", 0) or 0)
            supplier = request.form.get("supplier", "Vendor").strip()
            if quantity <= 0:
                flash("Receipt quantity must be greater than zero.", "error")
            else:
                product.stock_quantity += quantity
                receipt = Receipt(product_id=product.id, supplier=supplier, quantity=quantity, status="Waiting")
                db.session.add(receipt)
                db.session.add(StockLedger(product_id=product.id, document_type="Receipt", quantity_change=quantity, description=f"Receipt #{receipt.id} from {supplier}."))
                db.session.commit()
                flash(f"Receipt created for {quantity} {product.unit_of_measure} of {product.name}.", "success")

        elif operation == "delivery":
            quantity = int(request.form.get("quantity", 0) or 0)
            customer = request.form.get("customer", "Customer").strip()
            if quantity <= 0:
                flash("Delivery quantity must be greater than zero.", "error")
            elif quantity > product.stock_quantity:
                flash("Not enough stock available for this delivery.", "error")
            else:
                product.stock_quantity -= quantity
                delivery = Delivery(product_id=product.id, customer=customer, quantity=quantity, status="Ready")
                db.session.add(delivery)
                db.session.add(StockLedger(product_id=product.id, document_type="Delivery", quantity_change=-quantity, description=f"Delivery #{delivery.id} to {customer}."))
                db.session.commit()
                flash(f"Delivery recorded for {quantity} {product.unit_of_measure} of {product.name}.", "success")

        elif operation == "transfer":
            quantity = int(request.form.get("quantity", 0) or 0)
            from_location = request.form.get("from_location", product.location).strip()
            to_location = request.form.get("to_location", "Production Rack").strip()
            if quantity <= 0:
                flash("Transfer quantity must be greater than zero.", "error")
            else:
                transfer = Transfer(product_id=product.id, from_location=from_location, to_location=to_location, quantity=quantity, status="Scheduled")
                db.session.add(transfer)
                db.session.add(StockLedger(product_id=product.id, document_type="Transfer", quantity_change=0, description=f"Transfer from {from_location} to {to_location}."))
                product.location = to_location
                db.session.commit()
                flash(f"Internal transfer scheduled from {from_location} to {to_location}.", "success")

        elif operation == "adjustment":
            quantity_delta = int(request.form.get("quantity_delta", 0) or 0)
            reason = request.form.get("reason", "Physical count adjustment").strip()
            location = request.form.get("location", product.location).strip()
            if quantity_delta == 0:
                flash("Adjustment quantity cannot be zero.", "error")
            else:
                product.stock_quantity += quantity_delta
                adjustment = Adjustment(product_id=product.id, location=location, quantity_delta=quantity_delta, reason=reason, status="Done")
                db.session.add(adjustment)
                db.session.add(StockLedger(product_id=product.id, document_type="Adjustment", quantity_change=quantity_delta, description=f"Adjustment: {reason}."))
                db.session.commit()
                flash(f"Inventory adjusted by {quantity_delta} {product.unit_of_measure}.", "success")

        return redirect(url_for("main.operations"))

    receipts = Receipt.query.order_by(Receipt.created_at.desc()).all()
    deliveries = Delivery.query.order_by(Delivery.created_at.desc()).all()
    transfers = Transfer.query.order_by(Transfer.created_at.desc()).all()
    adjustments = Adjustment.query.order_by(Adjustment.created_at.desc()).all()

    return render_template(
        "operations.html",
        products=products,
        receipts=receipts,
        deliveries=deliveries,
        transfers=transfers,
        adjustments=adjustments,
    )


@main_bp.route("/settings")
@login_required
def settings():
    products = Product.query.order_by(Product.location).all()
    warehouses = sorted({product.location for product in products})
    return render_template("settings.html", warehouses=warehouses)


@main_bp.route("/profile")
@login_required
def profile():
    user = None
    from app.models import User
    user = User.query.get(session.get("user_id"))
    return render_template("profile.html", user=user)
