from flask import Blueprint, request, jsonify

from app.models.models import Order, Medicine
from app.extensions.extensions import db

import uuid
from datetime import datetime

orders_bp = Blueprint(
    "orders",
    __name__
)


# =========================
# GET ORDER HISTORY
# =========================
@orders_bp.route("/api/orders", methods=["GET"])
def get_orders():

    orders = Order.query.order_by(
        Order.id.desc()
    ).all()

    grouped = {}

    for o in orders:

        oid = o.order_id

        if oid not in grouped:

            grouped[oid] = {
                "order_id": oid,
                "wholesaler": o.wholesaler,
                "date": o.date,
                "items": []
            }

        grouped[oid]["items"].append({
            "name": o.medicine_name,
            "qty": o.quantity
        })

    return jsonify(list(grouped.values()))


# =========================
# LOW STOCK + SAVE ORDER
# =========================
@orders_bp.route(
    "/api/order-stock",
    methods=["GET", "POST"]
)
def order_stock():

    # ===== GET LOW STOCK =====
    if request.method == "GET":

        medicines = Medicine.query.filter(
            Medicine.quantity <= 10
        ).order_by(
            Medicine.quantity.asc()
        ).all()

        result = []

        for m in medicines:

            result.append({
                "id": m.id,
                "name": m.name,
                "quantity": m.quantity,
                "price": m.price,
                "category": m.category,
                "expiry_date": m.expiry_date,
                "image": m.image,
                "gst": m.gst
            })

        return jsonify(result)

    # ===== SAVE ORDER =====
    data = request.get_json()

    items = data.get("items", [])

    wholesaler = data.get(
        "wholesaler",
        "Unknown"
    )

    order_id = str(uuid.uuid4())

    for item in items:

        order = Order(

            order_id=order_id,

            medicine_name=item["name"],

            quantity=item["qty"],

            wholesaler=wholesaler,

            date=datetime.now().strftime(
                "%d %b %Y"
            ),

            shop_id=1
        )

        db.session.add(order)

    db.session.commit()

    return jsonify({
        "status": "ok"
    })


# =========================
# DELETE ORDER
# =========================
@orders_bp.route(
    "/api/orders/<order_id>",
    methods=["DELETE"]
)
def delete_order(order_id):

    orders = Order.query.filter_by(
        order_id=order_id
    ).all()

    if not orders:

        return jsonify({
            "error": "Order not found"
        }), 404

    for order in orders:

        db.session.delete(order)

    db.session.commit()

    return jsonify({
        "status": "ok"
    })


# =========================
# DELETE ALL ORDERS
# =========================
@orders_bp.route(
    "/api/orders",
    methods=["DELETE"]
)
def delete_all_orders():

    Order.query.delete()

    db.session.commit()

    return jsonify({
        "status": "all deleted"
    })