from flask import Blueprint
from flask import request
from flask import jsonify

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from app.extensions.extensions import db

from app.models.models import (
    Shop,
    User
)

from datetime import datetime


auth_bp = Blueprint(
    "auth",
    __name__
)


@auth_bp.route(
    "/api/register",
    methods=["POST"]
)
def register():

    data = request.json

    existing_shop = Shop.query.filter_by(
        phone=data["phone"]
    ).first()

    if existing_shop:

        return jsonify({
            "error": "Shop already exists"
        }), 400

    shop = Shop(

        shop_name=data["shop_name"],

        owner_name=data["owner_name"],

        phone=data["phone"],

        address=data.get("address", ""),

        created_at=str(datetime.now())
    )

    db.session.add(shop)

    db.session.flush()

    user = User(

        username=data["username"],

        password_hash=generate_password_hash(
            data["password"]
        ),

        role="owner",

        shop_id=shop.id
    )

    db.session.add(user)

    db.session.commit()

    return jsonify({
        "message": "Registration successful"
    })


@auth_bp.route(
    "/api/login",
    methods=["POST"]
)
def login():

    data = request.json

    user = User.query.filter_by(
        username=data["username"]
    ).first()

    if not user:

        return jsonify({
            "error": "Invalid username"
        }), 401

    valid = check_password_hash(
        user.password_hash,
        data["password"]
    )

    if not valid:

        return jsonify({
            "error": "Invalid password"
        }), 401

    shop = Shop.query.get(user.shop_id)

    return jsonify({

        "message": "Login successful",

        "user": {

            "id": user.id,

            "username": user.username,

            "role": user.role,

            "shop_id": user.shop_id
        },

        "shop": {

            "id": shop.id,

            "shop_name": shop.shop_name,

            "owner_name": shop.owner_name
        }
    })

    # =========================
# SHOP PROFILE
# =========================

@auth_bp.route(
    "/api/shop-profile/<int:shop_id>",
    methods=["GET"]
)
def get_shop_profile(shop_id):

    shop = Shop.query.get(shop_id)

    if not shop:

        return jsonify({
            "error": "Shop not found"
        }), 404

    return jsonify({

        "id": shop.id,

        "shop_name": shop.shop_name,

        "owner_name": shop.owner_name,

        "phone": shop.phone,

        "address": shop.address,

        "gst_number": shop.gst_number,

        "business_type": shop.business_type
    })


@auth_bp.route(
    "/api/shop-profile/<int:shop_id>",
    methods=["POST"]
)
def update_shop_profile(shop_id):

    shop = Shop.query.get(shop_id)

    if not shop:

        return jsonify({
            "error": "Shop not found"
        }), 404

    data = request.json

    shop.shop_name = data.get(
        "shop_name",
        shop.shop_name
    )

    shop.owner_name = data.get(
        "owner_name",
        shop.owner_name
    )

    shop.phone = data.get(
        "phone",
        shop.phone
    )

    shop.address = data.get(
        "address",
        shop.address
    )

    shop.gst_number = data.get(
        "gst_number",
        shop.gst_number
    )

    shop.business_type = data.get(
        "business_type",
        shop.business_type
    )

    db.session.commit()

    return jsonify({

        "message":
            "Shop profile updated successfully"
    })