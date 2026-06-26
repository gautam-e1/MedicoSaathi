from flask import Blueprint
from flask import request
from flask import jsonify
from datetime import datetime

from app.models.models import Medicine
from app.extensions.extensions import db

medicines_bp = Blueprint(
    "medicines",
    __name__
)


@medicines_bp.route("/api/medicines")
def get_medicines():

    # SHOP ID

    shop_id = request.args.get(
        "shop_id"
    )

    if not shop_id:

        return jsonify({
            "error": "Unauthorized"
        }), 401

    # SEARCH

    search = request.args.get(
        "search",
        ""
    )

    f = request.args.get(
        "filter",
        "all"
    )

    # QUERY

    query = Medicine.query.filter_by(
        shop_id=shop_id
    )

    # SEARCH FILTER

    if search:

        query = query.filter(
            Medicine.name.ilike(
                f"%{search}%"
            )
        )

    # STOCK FILTER

    if f == "low":

        query = query.filter(
            Medicine.quantity > 0,
            Medicine.quantity <= 10
        )

    elif f == "out":

        query = query.filter(
            Medicine.quantity == 0
        )

    medicines = query.order_by(
        Medicine.quantity.asc()
    ).all()

    result = []

    for m in medicines:

        # EXPIRY STATUS

        expiry_status = "safe"

        days_left = None

        if m.expiry_date:

            try:

                expiry = datetime.strptime(
                    m.expiry_date,
                    "%Y-%m-%d"
                )

                days_left = (
                    expiry - datetime.now()
                ).days

                if days_left < 0:

                    expiry_status = "expired"

                elif days_left <= 14:

                    expiry_status = "warning"

            except:
                pass

        item = {

            "id": m.id,

            "name": m.name,

            "quantity": m.quantity,

            "price": m.price,

            "category": m.category,

            "expiry_date": m.expiry_date,

            "image": m.image,

            "gst": m.gst,

            "expiry_status": expiry_status,

            "days_left": days_left
        }

        # STOCK STATUS

        if m.quantity == 0:

            item["status"] = {
                "stock": "out"
            }

        elif m.quantity <= 10:

            item["status"] = {
                "stock": "low"
            }

        else:

            item["status"] = {
                "stock": "ok"
            }

        result.append(item)

    return jsonify(result)


@medicines_bp.route(
    "/api/medicines",
    methods=["POST"]
)
def add_medicine():

    d = request.json

    medicine = Medicine(

        name=d["name"],

        quantity=d["quantity"],

        price=d["price"],

        category=d["category"],

        expiry_date=d["expiry_date"],

        image=d.get("image", ""),

        gst=d.get("gst", 5),

        shop_id=d["shop_id"]
    )

    db.session.add(medicine)

    db.session.commit()

    return jsonify({
        "status": "ok"
    })


@medicines_bp.route(
    "/api/medicines/<int:mid>",
    methods=["PUT"]
)
def update_medicine(mid):

    d = request.json

    medicine = Medicine.query.get(mid)

    if not medicine:

        return jsonify({
            "error": "Medicine not found"
        }), 404

    medicine.name = d["name"]

    medicine.quantity = d["quantity"]

    medicine.price = d["price"]

    medicine.category = d["category"]

    medicine.expiry_date = d["expiry_date"]

    medicine.image = d.get("image", "")

    medicine.gst = d.get("gst", 5)

    db.session.commit()

    return jsonify({
        "status": "ok"
    })

@medicines_bp.route(
    "/api/medicines/<int:mid>",
    methods=["DELETE"]
)
def delete_medicine(mid):

    medicine = Medicine.query.get(mid)

    if not medicine:

        return jsonify({
            "error": "Medicine not found"
        }), 404

    db.session.delete(medicine)

    db.session.commit()

    return jsonify({
        "status": "ok"
    })