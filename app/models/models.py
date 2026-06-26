from app.extensions.extensions import db
from datetime import datetime


# =========================
# MEDICINES
# =========================
class Medicine(db.Model):

    __tablename__ = "medicines"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(200),
        nullable=False
    )

    quantity = db.Column(
        db.Integer,
        default=0
    )

    price = db.Column(
        db.Float,
        default=0
    )

    category = db.Column(
        db.String(100),
        default=""
    )

    expiry_date = db.Column(
        db.String(50),
        default=""
    )

    image = db.Column(
        db.String(300),
        default=""
    )

    gst = db.Column(
        db.Float,
        default=0
    )

    shop_id = db.Column(
    db.Integer,
    db.ForeignKey("shops.id")
)


# =========================
# BILLS
# =========================
class Bill(db.Model):

    __tablename__ = "bills"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    invoice = db.Column(
        db.String(100),
        default=""
    )

    customer_name = db.Column(
        db.String(200),
        default=""
    )

    phone = db.Column(
        db.String(50),
        default=""
    )

    total = db.Column(
        db.Float,
        default=0
    )

    paid_amount = db.Column(
        db.Float,
        default=0
    )

    due_amount = db.Column(
        db.Float,
        default=0
    )

    payment_method = db.Column(
        db.String(50),
        default="Cash"
    )

    payment_status = db.Column(
        db.String(50),
        default="Paid"
    )

    date = db.Column(
        db.String(100),
        default=""
    )

    items = db.Column(
        db.Text
    )

    shop_id = db.Column(
        db.Integer,
        db.ForeignKey("shops.id")
    )


# =========================
# WHOLESALERS
# =========================
class Wholesaler(db.Model):

    __tablename__ = "wholesalers"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(200),
        nullable=False
    )

    phone = db.Column(
        db.String(50),
        default=""
    )

    shop_id = db.Column(
    db.Integer,
    db.ForeignKey("shops.id")
)


# =========================
# ORDERS
# =========================
class Order(db.Model):

    __tablename__ = "orders"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    order_id = db.Column(
        db.String(100),
        default=""
    )

    medicine_name = db.Column(
        db.String(200),
        default=""
    )

    quantity = db.Column(
        db.Integer,
        default=0
    )

    wholesaler = db.Column(
        db.String(200),
        default=""
    )

    # IMPORTANT:
    # Existing SQLite table uses "date"
    # NOT "created_at"
    date = db.Column(
        db.String(100),
        default=""
    )

    shop_id = db.Column(
    db.Integer,
    db.ForeignKey("shops.id")
)

class Customer(db.Model):

    __tablename__ = "customers"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    shop_id = db.Column(
        db.Integer,
        nullable=False
    )

    name = db.Column(
        db.String(120),
        nullable=False
    )

    phone = db.Column(
    db.String(20),
    nullable=False,
    index=True
)

    total_due = db.Column(
        db.Float,
        default=0
    )

    last_purchase = db.Column(
        db.String(50)
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    __table_args__ = (

    db.UniqueConstraint(
        "shop_id",
        "phone",
        name="unique_customer_phone_per_shop"
    ),

)

class Shop(db.Model):

    __tablename__ = "shops"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    shop_name = db.Column(
        db.String(200),
        nullable=False
    )

    owner_name = db.Column(
        db.String(200),
        default=""
    )

    phone = db.Column(
        db.String(50),
        unique=True,
        nullable=False
    )

    address = db.Column(
        db.String(500),
        default=""
    )

    gst_number = db.Column(
        db.String(100),
        default=""
    )

    business_type = db.Column(
        db.String(50),
        default="Non-GST Shop"
    )

    created_at = db.Column(
        db.String(100),
        default=""
    )


class User(db.Model):

    __tablename__ = "users"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    username = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(300),
        nullable=False
    )

    role = db.Column(
        db.String(50),
        default="owner"
    )

    shop_id = db.Column(
        db.Integer,
        db.ForeignKey("shops.id")
    )