from flask import Blueprint, jsonify, request
from app.extensions.extensions import db

from app.models.models import (
    Customer,
    Bill
)

customers_bp = Blueprint(
    "customers",
    __name__
)

# =========================
# GET CUSTOMERS
# =========================

@customers_bp.route(
    "/customers",
    methods=["GET"]
)
def get_customers():

    shop_id = int(
        request.args.get(
            "shop_id",
            0
        )
    )

    customers = Customer.query.filter_by(
        shop_id=shop_id
    ).all()

    total_due = 0
    paid_customers = 0
    due_customers = 0

    customer_data = []

    for c in customers:

        bills = Bill.query.filter_by(
            shop_id=shop_id,
            phone=c.phone
        ).all()

        customer_due = sum(
            float(b.due_amount or 0)
            for b in bills
        )

        total_due += customer_due

        if customer_due > 0:
            due_customers += 1
        else:
            paid_customers += 1

        customer_data.append({
            "id": c.id,
            "name": c.name,
            "phone": c.phone,
            "total_due": customer_due,
            "last_purchase": c.last_purchase
        })

    return jsonify({
        "total_customers": len(customers),
        "total_due": round(total_due, 2),
        "paid_customers": paid_customers,
        "due_customers": due_customers,
        "customers": customer_data
    })


# =========================
# DELETE CUSTOMER
# =========================

@customers_bp.route(
    "/customers/<int:id>",
    methods=["DELETE"]
)
def delete_customer(id):

    shop_id = int(
        request.args.get(
            "shop_id",
            0
        )
    )

    customer = Customer.query.filter_by(
        id=id,
        shop_id=shop_id
    ).first()

    if not customer:

        return jsonify({
            "success": False
        }), 404

    bills = Bill.query.filter_by(
        shop_id=shop_id,
        phone=customer.phone
    ).all()

    for bill in bills:

        bill.customer_name = "Deleted Customer"

        bill.phone = ""

    db.session.delete(customer)

    db.session.commit()

    return jsonify({
        "success": True
    })
    
    # =========================
# CUSTOMER ANALYTICS
# =========================

@customers_bp.route(
    "/customers/analytics",
    methods=["GET"]
)
def customer_analytics():

    shop_id = int(
        request.args.get(
            "shop_id",
            0
        )
    )

    customers = Customer.query.filter_by(
        shop_id=shop_id
    ).all()

    bills = Bill.query.filter_by(
        shop_id=shop_id
    ).all()

    purchase_map = {}
    due_map = {}
    visit_map = {}

    # =========================
    # CALCULATE ANALYTICS
    # =========================

    for bill in bills:

        phone = bill.phone or ""

        purchase_map[phone] = (
            purchase_map.get(phone, 0)
            + float(bill.total or 0)
        )

        due_map[phone] = (
            due_map.get(phone, 0)
            + float(bill.due_amount or 0)
        )

        visit_map[phone] = (
            visit_map.get(phone, 0)
            + 1
        )

    # =========================
    # TOP CUSTOMERS
    # =========================

    top_customers = []

    for customer in customers:

        visits = visit_map.get(
            customer.phone,
            0
        )

        # Minimum 3 visits required
        if visits < 3:
            continue

        total_purchase = purchase_map.get(
            customer.phone,
            0
        )

        if total_purchase <= 0:
            continue

        top_customers.append({

            "name": customer.name,

            "phone": customer.phone,

            "visits": visits,

            "total_purchase":
                round(
                    total_purchase,
                    2
                )
        })

    top_customers.sort(
        key=lambda x:
        x["total_purchase"],
        reverse=True
    )

    # =========================
    # HIGHEST DUE
    # =========================

    highest_due = []

    for customer in customers:

        due = due_map.get(
            customer.phone,
            0
        )

        # Show only due > 100
        if due <= 100:
            continue

        highest_due.append({

            "name": customer.name,

            "phone": customer.phone,

            "due":
                round(
                    due,
                    2
                )
        })

    highest_due.sort(
        key=lambda x:
        x["due"],
        reverse=True
    )

    return jsonify({

        "top_customers":
            top_customers[:5],

        "highest_due":
            highest_due[:5]
    })