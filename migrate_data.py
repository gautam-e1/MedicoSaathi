import sqlite3

from app import create_app
from app.extensions.extensions import db

from app.models.models import (
    Medicine,
    Bill,
    Wholesaler,
    Order
)

app = create_app()

sqlite_conn = sqlite3.connect("shop.db")
sqlite_conn.row_factory = sqlite3.Row

with app.app_context():

    # Medicines
    medicines = sqlite_conn.execute(
        "SELECT * FROM medicines"
    ).fetchall()

    for m in medicines:

        exists = Medicine.query.filter_by(
            id=m["id"]
        ).first()

        if not exists:

            medicine = Medicine(

                id=m["id"],

                name=m["name"],

                quantity=m["quantity"],

                price=m["price"],

                category=m["category"],

                expiry_date=m["expiry_date"],

                image=m["image"],

                gst=m["gst"]
            )

            db.session.add(medicine)

    # Bills
    bills = sqlite_conn.execute(
        "SELECT * FROM bills"
    ).fetchall()

    for b in bills:

        exists = Bill.query.filter_by(
            id=b["id"]
        ).first()

        if not exists:

            bill = Bill(

                id=b["id"],

                invoice=b["invoice"],

                customer_name=b["customer_name"],

                phone=b["phone"],

                total=b["total"],

                date=b["date"],

                items=b["items"]
            )

            db.session.add(bill)

    # Wholesalers
    wholesalers = sqlite_conn.execute(
        "SELECT * FROM wholesalers"
    ).fetchall()

    for w in wholesalers:

        exists = Wholesaler.query.filter_by(
            id=w["id"]
        ).first()

        if not exists:

            wholesaler = Wholesaler(

                id=w["id"],

                name=w["name"],

                phone=w["phone"]
            )

            db.session.add(wholesaler)

    # Orders
    orders = sqlite_conn.execute(
        "SELECT * FROM orders"
    ).fetchall()

    for o in orders:

        exists = Order.query.filter_by(
            id=o["id"]
        ).first()

        if not exists:

            order = Order(

                id=o["id"],

                order_id=o["order_id"],

                medicine_name=o["medicine_name"],

                quantity=o["quantity"],

                wholesaler=o["wholesaler"],

                status=o["status"],

                created_at=o["created_at"]
            )

            db.session.add(order)

    db.session.commit()

    print("✅ DATA MIGRATION COMPLETED")