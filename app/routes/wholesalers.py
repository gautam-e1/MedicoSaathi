from flask import Blueprint
from flask import request
from flask import jsonify

from app.models.models import Wholesaler
from app.extensions.extensions import db

wholesalers_bp = Blueprint(
    "wholesalers",
    __name__
)


@wholesalers_bp.route("/api/wholesalers")
def get_wholesalers():

    wholesalers = Wholesaler.query.order_by(
        Wholesaler.name.asc()
    ).all()

    result = []

    for w in wholesalers:

        result.append({

            "id": w.id,

            "name": w.name,

            "phone": w.phone
        })

    return jsonify(result)


@wholesalers_bp.route(
    "/api/wholesalers",
    methods=["POST"]
)
def add_wholesaler():

    d = request.json

    wholesaler = Wholesaler(

    name=d["name"],

    phone=d["phone"],

    shop_id=1
)

    db.session.add(wholesaler)

    db.session.commit()

    return jsonify({
        "status": "ok"
    })


@wholesalers_bp.route(
    "/api/wholesalers/<int:wid>",
    methods=["DELETE"]
)
def delete_wholesaler(wid):

    wholesaler = Wholesaler.query.get(wid)

    if not wholesaler:

        return jsonify({
            "error": "Wholesaler not found"
        }), 404

    db.session.delete(wholesaler)

    db.session.commit()

    return jsonify({
        "status": "ok"
    })