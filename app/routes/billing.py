from flask import Blueprint
from flask import request
from flask import jsonify

import json

billing_bp = Blueprint(
    "billing",
    __name__
)

from app.models.models import (
    Bill,
    Medicine,
    Customer
)

from app.extensions.extensions import db
# =========================
# SELL MEDICINES
# =========================

@billing_bp.route(
    "/api/sell",
    methods=["POST"]
)
def sell_medicines():

    data = request.json

    for item in data:

        medicine = db.session.get(
            Medicine,
            item["id"]
        )

        if medicine:

            if medicine.quantity < item["qty"]:

                return jsonify({
                    "error":
                    f"{medicine.name} out of stock"
                }), 400

            medicine.quantity = max(
                medicine.quantity - item["qty"],
                0
            )

    db.session.commit()

    return jsonify({
        "status": "ok"
    })


# =========================
# SAVE BILL
# =========================

@billing_bp.route(
    "/api/save-bill",
    methods=["POST"]
)
def save_bill():

    try:

        data = request.get_json()

        print("PAID:", data.get("paid_amount"))
        print("DUE:", data.get("due_amount"))
        print("STATUS:", data.get("payment_status"))

        existing_bill = Bill.query.filter_by(
            invoice=data.get("invoice"),
            shop_id=int(data.get("shop_id", 0))
        ).first()
        if existing_bill:
            return jsonify({
                "error": "Invoice already exists"
            }), 400

        bill = Bill(
            invoice=data.get("invoice"),
            customer_name=data.get("name"),
            phone=data.get("phone"),
            total=float(data.get("total", 0)),
            date=data.get("date"),
            items=json.dumps(data.get("items", [])),
            shop_id=int(data.get("shop_id", 0)),
            paid_amount=float(data.get("paid_amount", 0)),
            due_amount=float(data.get("due_amount", 0)),
            payment_method=data.get("payment_method", "Cash"),
            payment_status=data.get("payment_status", "Paid"),
        )

        db.session.add(bill)

        db.session.flush()

        # =========================
        # SAVE CUSTOMER
        # =========================

        customer_phone = (
            data.get("phone") or ""
        ).strip()

        customer_name = (
            data.get("name") or
            "Walk-in Customer"
        ).strip()

        # Phone blank ho tab bhi customer create karo
        customer_key = (
    customer_phone
    if customer_phone
    else f"walkin_{bill.id}"
)
        bill.phone = customer_key
        existing_customer = Customer.query.filter_by(
            shop_id=int(data.get("shop_id", 0)),
            phone=customer_key
        ).first()

        if existing_customer:
            existing_customer.name = customer_name
            existing_customer.last_purchase = data.get("date")
        else:
            new_customer = Customer(
    shop_id=int(
        data.get("shop_id", 0)
    ),
    name=customer_name,
    phone=customer_key,
    last_purchase=data.get("date"),

    # Due Bills table se calculate hoga
    total_due=0
)
            db.session.add(new_customer)

        db.session.commit()

        print("CUSTOMER SAVED")
        print("NAME:", data.get("name"))
        print("PHONE:", customer_phone)

        all_customers = Customer.query.all()

        print("TOTAL CUSTOMERS:", len(all_customers))

        for c in all_customers:
            print(
                c.id,
                c.name,
                c.phone,
                c.shop_id
            )

        return jsonify({
            "success": True
        })

    except Exception as e:
        db.session.rollback()

        print(
            "SAVE BILL ERROR:",
            e
        )

        return jsonify({
            "error": str(e)
        }), 500


# =========================
# GET BILLS
# =========================

@billing_bp.route("/api/bills")
def get_bills():

    shop_id = int(
    request.args.get("shop_id", 0)
)

    bills = Bill.query.filter_by(
        shop_id=shop_id
    ).order_by(
        Bill.id.desc()
    ).all()

    result = []

    for b in bills:
        result.append({
            "id": b.id,
            "invoice": b.invoice,
            "customer_name": b.customer_name,
            "phone": b.phone,
            "total": float(b.total or 0),
            "paid_amount": float(
                b.paid_amount or 0
            ),
            "due_amount": float(
                b.due_amount or 0
            ),
            "payment_method": b.payment_method,
            "payment_status": b.payment_status,
            "date": b.date,
            "items": b.items
        })
    return jsonify(result)

# =========================
# DELETE ALL BILLS
# =========================
@billing_bp.route(
    "/api/bills",
    methods=["DELETE"]
)
def delete_all_bills():

    shop_id = int(
        request.args.get(
            "shop_id",
            0
        )
    )

    Bill.query.filter_by(
        shop_id=shop_id
    ).delete()

    Customer.query.filter_by(
        shop_id=shop_id
    ).delete()

    db.session.commit()

    return jsonify({
        "status": "all bills deleted"
    })
# DELETE SINGLE BILL

@billing_bp.route(
    "/api/bills/<int:id>",
    methods=["DELETE"]
)
def delete_bill(id):

    shop_id = int(
        request.args.get(
            "shop_id",
            0
        )
    )

    bill = Bill.query.filter_by(
        id=id,
        shop_id=shop_id
    ).first()

    if not bill:

        return jsonify({
            "error": "Bill not found"
        }), 404

    db.session.delete(bill)

    db.session.commit()

    return jsonify({
        "status": "ok"
    })