from flask import Flask, render_template, request, jsonify, send_from_directory
import sqlite3
import os
import uuid
import json
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename

app = Flask(__name__)
DB = "shop.db"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024


# ✅ image serve (kept)
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.executescript("""
    CREATE TABLE IF NOT EXISTS medicines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        quantity INTEGER DEFAULT 0,
        price REAL DEFAULT 0,
        category TEXT DEFAULT '',
        expiry_date TEXT DEFAULT '',
        image TEXT DEFAULT '',
        gst REAL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS wholesalers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS bills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice TEXT,
        customer_name TEXT,
        phone TEXT,
        total REAL,
        date TEXT,
        items TEXT
    );
    CREATE TABLE IF NOT EXISTS sales_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    total_sales REAL DEFAULT 0,
    total_bills INTEGER DEFAULT 0
);

    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT,
        medicine_name TEXT,
        quantity INTEGER,
        date TEXT,
        wholesaler TEXT
    );
    """)

   # ✅ GST column safe add
    try:
        conn.execute("ALTER TABLE bills ADD COLUMN items TEXT")
        conn.commit()
    except:
        pass

    # ✅ sales summary default row
    check = conn.execute(
        "SELECT COUNT(*) FROM sales_summary"
    ).fetchone()[0]

    if check == 0:
        conn.execute("""
            INSERT INTO sales_summary
            (total_sales, total_bills)
            VALUES (0,0)
        """)
        conn.commit()

    conn.close()

@app.route("/")
def index():
    return render_template("index.html")


def get_status(qty, expiry_date=""):

    today = datetime.now().date()

    # Default
    expiry_status = "safe"

    if expiry_date:
        try:
            exp = datetime.strptime(expiry_date, "%Y-%m-%d").date()

            days_left = (exp - today).days

            if days_left < 0:
                expiry_status = "expired"

            elif days_left <= 30:
                expiry_status = "warning"

        except:
            pass

    # Stock status
    stock_status = "ok"

    if qty == 0:
        stock_status = "out"

    elif qty <= 10:
        stock_status = "low"

    return {
        "stock": stock_status,
        "expiry": expiry_status
    }


@app.route("/api/medicines")
def get_medicines():
    search = request.args.get("search", "")
    f = request.args.get("filter", "all")

    conn = get_db()
    q, params, conds = "SELECT * FROM medicines", [], []

    if search:
        conds.append("name LIKE ?")
        params.append(f"%{search}%")

    if f == "low":
        conds.append("quantity > 0 AND quantity <= 10")
    elif f == "out":
        conds.append("quantity = 0")
    elif f == "expiry":
        today = datetime.now().strftime("%Y-%m-%d")
        soon = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        conds.append("expiry_date != '' AND expiry_date BETWEEN ? AND ?")
        params.extend([today, soon])

    if conds:
        q += " WHERE " + " AND ".join(conds)

    q += " ORDER BY quantity ASC"

    rows = conn.execute(q, params).fetchall()
    conn.close()

    result = []
    for r in rows:
        item = dict(r)
        item["status"] = get_status(
    item["quantity"],
    item["expiry_date"]
)
        result.append(item)

    return jsonify(result)


@app.route("/api/medicines", methods=["POST"])
def add_medicine():
    d = request.json
    conn = get_db()
    conn.execute(
        "INSERT INTO medicines (name, quantity, price, category, expiry_date, image, gst) VALUES (?,?,?,?,?,?,?)",
        (d["name"], d["quantity"], d["price"], d["category"], d["expiry_date"], d.get("image", ""), d.get("gst", 5)),
    )
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


@app.route("/api/medicines/<int:mid>", methods=["PUT"])
def update_medicine(mid):
    d = request.json
    conn = get_db()
    conn.execute(
        "UPDATE medicines SET name=?, quantity=?, price=?, category=?, expiry_date=?, image=?, gst=? WHERE id=?",
        (d["name"], d["quantity"], d["price"], d["category"], d["expiry_date"], d.get("image", ""), d.get("gst", 5), mid),
    )
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


@app.route("/api/medicines/<int:mid>", methods=["DELETE"])
def delete_medicine(mid):
    conn = get_db()
    conn.execute("DELETE FROM medicines WHERE id=?", (mid,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


# ✅ image upload (kept)
@app.route("/api/upload", methods=["POST"])
def upload_image():
    file = request.files.get("image")
    if not file:
        return jsonify({"error": "No file"}), 400

    filename = secure_filename(file.filename)
    unique_name = str(uuid.uuid4()) + "_" + filename
    path = os.path.join(UPLOAD_DIR, unique_name)
    file.save(path)

    return jsonify({"path": f"/uploads/{unique_name}"})


# ✅ DASHBOARD (expiry included again)
@app.route("/api/dashboard")
def dashboard():

    conn = get_db()

    total = conn.execute(
        "SELECT COUNT(*) FROM medicines"
    ).fetchone()[0]

    low = conn.execute(
        "SELECT COUNT(*) FROM medicines WHERE quantity > 0 AND quantity <= 10"
    ).fetchone()[0]

    out = conn.execute(
        "SELECT COUNT(*) FROM medicines WHERE quantity = 0"
    ).fetchone()[0]

    summary = conn.execute("""
    SELECT total_sales, total_bills
    FROM sales_summary
    LIMIT 1
""").fetchone()

    today_sales = summary["total_sales"]
    today_bills = summary["total_bills"]
    monthly_revenue = summary["total_sales"]

    today = datetime.now().date().isoformat()

    soon = (
        datetime.now() + timedelta(days=30)
    ).strftime("%Y-%m-%d")

    expiring = conn.execute(
        """
        SELECT COUNT(*)
        FROM medicines
        WHERE expiry_date != ''
        AND expiry_date BETWEEN ? AND ?
        """,
        (today, soon)
    ).fetchone()[0]

    conn.close()

    return jsonify({
        "total": total,
        "low_stock": low,
        "out_of_stock": out,
        "expiring_soon": expiring,

        "today_sales": round(today_sales, 2),
        "today_bills": today_bills,
        "monthly_revenue": round(monthly_revenue, 2)
    })

@app.route("/api/wholesalers")
def get_wholesalers():
    conn = get_db()
    rows = conn.execute("SELECT * FROM wholesalers ORDER BY name").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/wholesalers", methods=["POST"])
def add_wholesaler():
    d = request.json
    conn = get_db()
    conn.execute("INSERT INTO wholesalers (name, phone) VALUES (?,?)", (d["name"], d["phone"]))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


@app.route("/api/wholesalers/<int:wid>", methods=["DELETE"])
def delete_wholesaler(wid):
    conn = get_db()
    conn.execute("DELETE FROM wholesalers WHERE id=?", (wid,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


@app.route("/api/low-stock")
def low_stock_list():
    conn = get_db()
    rows = conn.execute(
        "SELECT name, quantity FROM medicines WHERE quantity <= 10 ORDER BY quantity ASC"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


# ✅ stock reduce (kept)
@app.route("/api/sell", methods=["POST"])
def sell_medicines():
    data = request.json
    conn = get_db()

    for item in data:
        conn.execute(
            "UPDATE medicines SET quantity = quantity - ? WHERE id = ?",
            (item["qty"], item["id"])
        )

    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

# ✅ SAVE BILL
@app.route("/api/save-bill", methods=["POST"])
def save_bill():
    try:
        data = request.get_json()

        conn = get_db()

        conn.execute(
            """
            INSERT INTO bills
            (invoice, customer_name, phone, total, date, items)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                data.get("invoice"),
                data.get("name"),
                data.get("phone"),
                data.get("total"),
                data.get("date"),
                json.dumps(data.get("items", []))
            )
        )
        conn.execute("""
    UPDATE sales_summary
    SET
    total_sales = total_sales + ?,
    total_bills = total_bills + 1
""", (data.get("total"),))
        conn.commit()
        conn.close()

        return jsonify({"success": True})

    except Exception as e:
        print("SAVE BILL ERROR:", e)
        return jsonify({"error": str(e)}), 500
@app.route("/api/bills")
def get_bills():
    conn = get_db()
    rows = conn.execute("SELECT * FROM bills ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])
@app.route("/api/bills", methods=["DELETE"])
def delete_all_bills():
    conn = get_db()
    conn.execute("DELETE FROM bills")
    conn.commit()
    conn.close()
    return jsonify({"status": "all bills deleted"})   
    
@app.route("/api/bills/<int:id>", methods=["DELETE"])
def delete_bill(id):
    conn = get_db()
    conn.execute("DELETE FROM bills WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})
@app.route("/api/orders/<order_id>", methods=["DELETE"])
def delete_order(order_id):
    conn = get_db()
    conn.execute("DELETE FROM orders WHERE order_id=?", (order_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})
@app.route("/api/restore-orders", methods=["POST"])
def restore_orders():
    data = request.json
    conn = get_db()

    for order in data:
        for item in order["items"]:
            conn.execute(
                "INSERT INTO orders (order_id, medicine_name, quantity, wholesaler, date) VALUES (?,?,?,?,?)",
                (order["order_id"], item["name"], item["qty"], order["wholesaler"], order["date"])
            )

    conn.commit()
    conn.close()
    return jsonify({"status": "restored"})    
@app.route("/api/orders", methods=["DELETE"])
def delete_all_orders():
    conn = get_db()
    conn.execute("DELETE FROM orders")
    conn.commit()
    conn.close()
    return jsonify({"status": "all orders deleted"})    
    
# ✅ ORDER STOCK
@app.route("/api/order-stock", methods=["POST"])
def order_stock():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data received"}), 400

        items = data.get("items", [])
        wholesaler = data.get("wholesaler", "Unknown")

        import uuid
        order_id = str(uuid.uuid4())

        conn = get_db()

        for item in items:
            name = item.get("name", "Unknown")

            qty = item.get("quantity")
            if qty is None:
                qty = item.get("qty", 0)

            conn.execute(
                "INSERT INTO orders (order_id, medicine_name, quantity, wholesaler, date) VALUES (?,?,?,?,?)",
                (order_id, name, qty, wholesaler, datetime.now().isoformat())
            )

        conn.commit()
        conn.close()

        return jsonify({"status": "ok"})
    except Exception as e:
        print("ERROR:", e)
        return jsonify({"error": str(e)}), 500

@app.route("/api/orders")
def get_orders():

    conn = get_db()
    rows = conn.execute("SELECT * FROM orders ORDER BY date DESC").fetchall()

    orders = {}

    for r in rows:
        oid = r["order_id"]

        if oid not in orders:
            orders[oid] = {
                "order_id": oid,
                "date": r["date"],
                "wholesaler": r["wholesaler"],
                "items": []
            }

        orders[oid]["items"].append({
            "name": r["medicine_name"],
            "qty": r["quantity"]
        })

    conn.close()

    return jsonify(list(orders.values()))
@app.route("/api/orders/bulk-delete", methods=["POST"])
def bulk_delete():
    ids = request.json
    conn = get_db()

    for oid in ids:
        conn.execute("DELETE FROM orders WHERE order_id=?", (oid,))
    conn.commit()
    conn.close()
    return jsonify({"status": "deleted"})
if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)