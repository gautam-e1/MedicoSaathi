import json
from flask import Blueprint
from flask import render_template
from flask import jsonify
from flask import request

from datetime import datetime

from app.models.models import (
    Medicine,
    Bill,
    Shop,
    Customer
)

dashboard_bp = Blueprint(
    "dashboard",
    __name__
)


# =========================
# HOME PAGE
# =========================

@dashboard_bp.route("/")
def index():

    return render_template(
        "index.html"
    )


# =========================
# DASHBOARD API
# =========================

@dashboard_bp.route("/api/dashboard")
def dashboard():

    shop_id = int(
        request.args.get(
            "shop_id",
            0
        )
    )
    shop = Shop.query.get(shop_id)
    print("SHOP:", shop)
    
    if not shop:
        return jsonify({
            "total": 0,
            "low_stock": 0,
            "out_of_stock": 0,
            "today_sales": 0,
            "today_bills": 0,
            "monthly_revenue": 0,
            "total_bills": 0,
            "total_sales_items": 0,
            "shop_name": "Medical Shop"
        })

    medicines = Medicine.query.filter_by(
        shop_id=shop_id
    ).all()

    bills = Bill.query.filter_by(
        shop_id=shop_id
    ).all()

    # =========================
    # MEDICINE COUNTS
    # =========================

    total = len(medicines)

    low = len([

        m for m in medicines

        if m.quantity > 0
        and m.quantity <= 10
    ])

    out = len([

        m for m in medicines

        if m.quantity == 0
    ])

    # =========================
    # TODAY DATE
    # =========================

    today = str(
        datetime.utcnow().date()
    )

    today_bills = []

    # =========================
    # FILTER TODAY BILLS
    # =========================

    for b in bills:

        try:

            bill_date = str(

                datetime.fromisoformat(

                    str(b.date).replace(
                        "Z",
                        "+00:00"
                    )

                ).date()

            )

            print(
                "BILL DATE:",
                bill_date,
                "TODAY:",
                today
            )

            if bill_date == today:

                today_bills.append(b)

        except Exception as e:

            print(
                "DATE ERROR:",
                e
            )

    # =========================
    # SALES CALCULATIONS
    # =========================

    today_sales = sum([

        float(b.total or 0)

        for b in today_bills

        if b.total
    ])
    # CURRENT MONTH
    current_month = datetime.now().month
    current_year = datetime.now().year

    month_bills = []

    for b in bills:

        try:

            bill_date = datetime.fromisoformat(
                str(b.date).replace(
                    "Z",
                    "+00:00"
                )
            )

            if (
                bill_date.month == current_month
                and
                bill_date.year == current_year
            ):

                month_bills.append(b)

        except:
            pass

    monthly_revenue = sum(
        float(b.total or 0)
        for b in month_bills
    )

    # =========================
    # REVENUE GROWTH %
    # =========================

    last_month = current_month - 1
    last_month_year = current_year

    if last_month == 0:
        last_month = 12
        last_month_year -= 1

    last_month_revenue = 0

    for b in bills:
        try:

            bill_date = datetime.fromisoformat(
                str(b.date).replace(
                    "Z",
                    "+00:00"
                )
            )

            if (
                bill_date.month == last_month
                and
                bill_date.year == last_month_year
            ):

                last_month_revenue += float(
                    b.total or 0
                )

        except:
            pass

    # compute revenue growth after summing last month's revenue
    revenue_growth = None

    if last_month_revenue > 0:
        revenue_growth = round(
            (
                (monthly_revenue - last_month_revenue)
                / last_month_revenue
            ) * 100,
            1
        )

    # =========================
# BEST SALES DAY
# =========================

    daily_sales = {}

    for bill in month_bills:

        try:

            bill_date = datetime.fromisoformat(
                str(bill.date).replace(
                    "Z",
                    "+00:00"
                )
            )

            day_name = bill_date.strftime("%A")

            daily_sales[day_name] = (
                daily_sales.get(day_name, 0)
                + float(bill.total or 0)
            )

        except:
            pass

    best_sales_day = "-"

    best_sales_amount = 0

    if daily_sales:

        best_sales_day = max(
            daily_sales,
            key=daily_sales.get
        )

        best_sales_amount = round(
            daily_sales[best_sales_day],
            2
        )

    # =========================
    # TOTAL BILLS
    # =========================

    total_bills = len(bills)

    # =========================
    # TOTAL MEDICINES SOLD
    # =========================

    total_sales_items = 0

    for b in bills:
        try:
            items = json.loads(
                b.items or "[]"
            )

            for item in items:
                total_sales_items += item.get("qty", 0)

        except:
            pass

    average_bill = 0

    if today_bills:
        average_bill = (
            today_sales /
            len(today_bills)
        )

    highest_bill = 0

    if today_bills:
        highest_bill = max(
            float(b.total or 0)
            for b in today_bills
        )

    total_due = sum(
        float(b.due_amount or 0)
        for b in bills
    )

    total_paid = sum(
    float(b.paid_amount or 0)
    for b in month_bills
)

    total_sales = sum(
    float(b.total or 0)
    for b in month_bills
)

    collection_rate = 0

    if total_sales > 0:
        collection_rate = (
            total_paid /
            total_sales
        ) * 100

    return jsonify({
        "total": total,
        "low_stock": low,
        "out_of_stock": out,
        "today_sales": round(today_sales, 2),
        "today_bills": len(today_bills),
        "monthly_revenue": round(monthly_revenue, 2),
        "total_bills": total_bills,
        "total_sales_items": total_sales_items,
        "average_bill": round(average_bill, 2),
        "highest_bill": round(highest_bill, 2),
        "total_due": round(total_due, 2),
        "collection_rate": round(collection_rate, 1),
        "best_sales_day":
    best_sales_day,

"best_sales_amount":
    best_sales_amount,
    "revenue_growth":
    revenue_growth,

"last_month_revenue":
    round(
        last_month_revenue,
        2
    ),
        "shop_name": shop.shop_name if shop else "Medical Shop",
    })

# =========================
# LOW STOCK API
# =========================

@dashboard_bp.route("/api/low-stock")
def low_stock_list():

    shop_id = int(
        request.args.get(
            "shop_id",
            0
        )
    )

    medicines = Medicine.query.filter_by(
        shop_id=shop_id
    ).all()

    low_stock = [

        {
            "name": m.name,
            "quantity": m.quantity
        }

        for m in medicines

        if m.quantity <= 10
    ]

    low_stock.sort(
        key=lambda x: x["quantity"]
    )

    return jsonify(
        low_stock
    )

@dashboard_bp.route(
    "/api/analytics"
)
def analytics():

    from collections import OrderedDict
    from datetime import datetime, timedelta

    import json

    shop_id = request.args.get(
        "shop_id"
    )

    if not shop_id:

        return jsonify({
            "error": "Unauthorized"
        }), 401

    dead_stock = Medicine.query.filter(
        Medicine.shop_id == shop_id,
        Medicine.quantity > 30
    ).count()

    bills = Bill.query.filter_by(
        shop_id=shop_id
    ).all()

    # WEEK ORDER

    from datetime import timedelta

    revenue = OrderedDict()

    for i in range(6, -1, -1):

        day = (
            datetime.now() -
            timedelta(days=i)
        )

        revenue[
            day.strftime("%d %b")
        ] = 0

    medicine_sales = {}

    # PROCESS BILLS

    for b in bills:

        try:

            bill_date = datetime.strptime(
            b.date[:10],
            "%Y-%m-%d"
)

            day_key = bill_date.strftime(
            "%d %b"
)

            if day_key in revenue:

                revenue[day_key] += (
                    float(b.total or 0)
                )

        except:

            pass

        # TOP MEDICINES

        try:

            items = json.loads(
                b.items or "[]"
            )

            for item in items:

                name = item.get(
                    "name",
                    "Unknown"
                )

                qty = item.get(
                    "qty",
                    0
                )

                medicine_sales[name] = (

                    medicine_sales.get(
                        name,
                        0
                    ) + qty
                )

        except:

            pass

    # TOP 5 MEDICINES

    top = sorted(

        medicine_sales.items(),

        key=lambda x: x[1],

        reverse=True

    )[:5]

    # BEST SELLER

    best_medicine = None

    if top:

        best_medicine = {

            "name": top[0][0],

            "qty": top[0][1]
        }

    # RESPONSE

    return jsonify({

        "revenue": revenue,

        "top_medicines": top,

        "best_medicine": best_medicine,

        "dead_stock": dead_stock
    })