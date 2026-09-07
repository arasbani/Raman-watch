import os
import sqlite3
from pathlib import Path
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, send_from_directory
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "watches.db"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
@app.route("/privacy")
def privacy():
    return """
    <html>
    <head>
        <meta charset="utf-8">
        <title>Privacy Policy - Arbil Watches</title>
    </head>
    <body style="font-family:Arial;max-width:800px;margin:40px auto;padding:20px;line-height:1.7">
        <h1>Privacy Policy - Arbil Watches</h1>

        <p>Arbil Watches respects your privacy.</p>

        <h2>Information We Collect</h2>
        <p>When you contact us through WhatsApp, we may receive your phone number,
        name, messages, and order information that you voluntarily provide.</p>

        <h2>How We Use Information</h2>
        <p>We use this information only to communicate with customers,
        process orders, provide product information, and improve our service.</p>

        <h2>Data Sharing</h2>
        <p>We do not sell your personal information to third parties.</p>

        <h2>Data Retention</h2>
        <p>We retain information only as reasonably necessary for customer service,
        orders, and business records.</p>

        <h2>Contact</h2>
        <p>For privacy questions, please contact Arbil Watches through our official
        WhatsApp contact.</p>

        <p>Last updated: September 2026</p>
    </body>
    </html>
    """
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24))

WA_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "")
GRAPH_API_VERSION = os.getenv("GRAPH_API_VERSION", "v23.0")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-this-password")

sessions = {}

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = db()
    con.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            currency TEXT NOT NULL DEFAULT 'IQD',
            unit TEXT NOT NULL DEFAULT 'قطعة',
            category TEXT DEFAULT 'رجالي',
            features TEXT DEFAULT '',
            image TEXT DEFAULT '',
            status TEXT DEFAULT 'available'
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wa_id TEXT,
            product_code TEXT,
            product_name TEXT,
            quantity INTEGER,
            governorate TEXT,
            customer_name TEXT,
            phone TEXT,
            status TEXT DEFAULT 'new',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    con.commit()
    con.close()

def wa_url(path):
    return f"https://graph.facebook.com/{GRAPH_API_VERSION}/{path}"

def wa_headers():
    return {"Authorization": f"Bearer {WA_TOKEN}"}

def send_text(to, body):
    print("WA TO:", to)
    if not WA_TOKEN or not PHONE_NUMBER_ID:
        print("WhatsApp credentials are not configured.")
        return
    r = requests.post(
        wa_url(f"{PHONE_NUMBER_ID}/messages"),
        headers={**wa_headers(), "Content-Type": "application/json"},
        json={
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"preview_url": False, "body": body}
        },
        timeout=30
    )
    print("send_text:", r.status_code, r.text)

def send_image(to, image_path, caption=""):
    """Uploads the local image to WhatsApp and sends it as an image message."""
    if not WA_TOKEN or not PHONE_NUMBER_ID:
        print("WhatsApp credentials are not configured.")
        return
    p = Path(image_path)
    if not p.exists():
        send_text(to, caption or "الصورة غير متوفرة حالياً.")
        return

    with p.open("rb") as f:
        r = requests.post(
            wa_url(f"{PHONE_NUMBER_ID}/media"),
            headers=wa_headers(),
            files={"file": (p.name, f, "application/octet-stream")},
            data={"messaging_product": "whatsapp"},
            timeout=60
        )
    if r.status_code >= 300:
        print("media upload:", r.status_code, r.text)
        send_text(to, caption)
        return

    media_id = r.json().get("id")
    requests.post(
        wa_url(f"{PHONE_NUMBER_ID}/messages"),
        headers={**wa_headers(), "Content-Type": "application/json"},
        json={
            "messaging_product": "whatsapp",
            "to": to,
            "type": "image",
            "image": {"id": media_id, "caption": caption[:1024]}
        },
        timeout=30
    )

def send_list(to, header, body, button_text, rows):
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": header[:60]},
            "body": {"text": body[:1024]},
            "footer": {"text": "ساعات أربيل"},
            "action": {
                "button": button_text[:20],
                "sections": [{"title": "الأسعار", "rows": rows[:10]}]
            }
        }
    }
    r = requests.post(
        wa_url(f"{PHONE_NUMBER_ID}/messages"),
        headers={**wa_headers(), "Content-Type": "application/json"},
        json=payload, timeout=30
    )
    print("send_list:", r.status_code, r.text)

def get_prices():
    con = db()
    rows = con.execute("""
        SELECT DISTINCT price, currency FROM products
        WHERE status='available' ORDER BY price
    """).fetchall()
    con.close()
    return rows

def products_by_price(price):
    con = db()
    rows = con.execute("""
        SELECT * FROM products
        WHERE status='available' AND price=?
        ORDER BY id DESC
        LIMIT 10
    """, (price,)).fetchall()
    con.close()
    return rows

def product_by_code(code):
    con = db()
    row = con.execute("SELECT * FROM products WHERE code=?", (code,)).fetchone()
    con.close()
    return row

def main_menu(to):
    send_text(to,
        "هلا وغلا حبيبي 🌹 نورتنا بـ «ساعات أربيل» ⌚\n\n"
        "شنو تحب تسوي؟\n"
        "1️⃣ تصفح الساعات\n"
        "2️⃣ اختار حسب السعر\n"
        "3️⃣ 🔥 العروض\n"
        "4️⃣ 🆕 أحدث الموديلات\n"
        "5️⃣ 👨 رجالي\n"
        "6️⃣ 👩 نسائي\n"
        "7️⃣ 📞 موظف المبيعات\n\n"
        "اكتب رقم الخيار أو مثل: «أريد ساعات بسبعة»."
    )

def price_menu(to):
    prices = get_prices()
    if not prices:
        send_text(to, "حالياً ما مضاف موديلات للكتالوج بعد 🌹")
        return
    rows = []
    for p in prices[:10]:
        val = float(p["price"])
        label = f"{int(val) if val.is_integer() else val:g} {p['currency']}"
        rows.append({
            "id": f"price:{val}",
            "title": label[:24],
            "description": "عرض الموديلات بهذا السعر"
        })
    # WhatsApp list sections have a 10-row limit in this starter.
    send_list(to, "اختار السعر", "اختار السعر اللي يناسبك 👇", "عرض الأسعار", rows)

def show_products(to, price):
    rows = products_by_price(price)
    if not rows:
        send_text(to, "ما لكيت موديلات متاحة بهذا السعر حالياً 🌹")
        return
    for row in rows:
        caption = (
            f"⌚ {row['name']}\n"
            f"💰 {row['price']:g} {row['currency']}\n"
            f"📦 البيع: {row['unit']}\n"
            f"👤 التصنيف: {row['category']}\n"
            f"🔖 الكود: {row['code']}\n"
        )
        if row["features"]:
            caption += f"✨ {row['features']}\n"
        caption += "\nللطلب اكتب: أريد " + row["code"]
        image = BASE_DIR / row["image"] if row["image"] else None
        if image and image.exists():
            send_image(to, image, caption)
        else:
            send_text(to, caption)

def start_order(to, code):
    row = product_by_code(code)
    if not row:
        send_text(to, "ما لكيت هذا الموديل. اكتب «القائمة» حتى نرجع للبداية.")
        return
    sessions[to] = {"step": "quantity", "code": code}
    send_text(to,
        f"تمام حبيبي ✅\n{row['name']} — {row['price']:g} {row['currency']} / {row['unit']}\n\n"
        "شكد تريد؟ اكتب العدد فقط."
    )

def handle_text(to, text):
    t = text.strip().lower()

    # Active order flow
    state = sessions.get(to)
    if state:
        if state["step"] == "quantity":
            try:
                qty = int(t)
                if qty <= 0 or qty > 10000:
                    raise ValueError
            except ValueError:
                send_text(to, "اكتب عدد صحيح، مثلاً: 5")
                return
            state["quantity"] = qty
            state["step"] = "governorate"
            send_text(to, "تمام 🌹 اكتب اسم المحافظة، مثلاً: أربيل")
            return
        if state["step"] == "governorate":
            state["governorate"] = text.strip()
            state["step"] = "name"
            send_text(to, "اكتب اسمك الثلاثي حتى نثبت الطلب.")
            return
        if state["step"] == "name":
            state["name"] = text.strip()
            row = product_by_code(state["code"])
            con = db()
            con.execute("""
                INSERT INTO orders
                (wa_id, product_code, product_name, quantity, governorate, customer_name, phone)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (to, row["code"], row["name"], state["quantity"],
                  state["governorate"], state["name"], to))
            con.commit()
            con.close()
            sessions.pop(to, None)
            send_text(to,
                "تم تسجيل طلبك بنجاح ✅🌹\n\n"
                f"⌚ {row['name']}\n"
                f"🔢 الكمية: {state['quantity']}\n"
                f"📍 المحافظة: {state['governorate']}\n"
                f"👤 الاسم: {state['name']}\n\n"
                "راح يتواصل وياك موظف المبيعات لتأكيد الطلب."
            )
            return

    if t in {"1", "تصفح", "تصفح الساعات", "الاسعار", "الأسعار"} or "سعر" in t:
        # Natural language price detection
        nums = {
            "اربعة":4, "أربعة":4, "خمسة":5, "خمسه":5,
            "خمسة ونص":5.5, "خمسه ونص":5.5, "ستة":6, "سته":6,
            "ستة ونص":6.5, "سته ونص":6.5, "سبعة":7, "سبعه":7,
            "سبعة ونص":7.5, "سبعه ونص":7.5, "ثمانية":8, "ثمانيه":8,
            "تسعة":9, "تسعه":9, "تسعة ونص":9.5, "عشرة":10, "عشره":10,
            "ثلاثة عشر":13
        }
        for k, v in nums.items():
            if k in t:
                show_products(to, v)
                return
        price_menu(to)
        return

    if t in {"2", "اختار حسب السعر", "السعر"}:
        price_menu(to)
        return
    if t in {"3", "العروض", "عرض"}:
        send_text(to, "قسم العروض نفعّله أول ما تضيف منتجات وتحددها كعروض من لوحة الإدارة 🔥")
        return
    if t in {"4", "احدث", "أحدث", "أحدث الموديلات"}:
        con = db()
        rows = con.execute("SELECT * FROM products WHERE status='available' ORDER BY id DESC LIMIT 6").fetchall()
        con.close()
        for r in rows:
            caption = f"⌚ {r['name']}\n💰 {r['price']:g} {r['currency']}\n📦 {r['unit']}\n🔖 {r['code']}\n\nللطلب اكتب: أريد {r['code']}"
            image = BASE_DIR / r["image"] if r["image"] else None
            if image and image.exists():
                send_image(to, image, caption)
            else:
                send_text(to, caption)
        if not rows:
            send_text(to, "بعدنا ما ضفنا موديلات 🌹")
        return
    if t in {"5", "رجالي"}:
        send_category(to, "رجالي")
        return
    if t in {"6", "نسائي"}:
        send_category(to, "نسائي")
        return
    if t in {"7", "موظف", "موظف المبيعات"}:
        send_text(to, "أكيد حبيبي 🌹 اكتب طلبك بالتفصيل، وموظف المبيعات يتواصل وياك.")
        return
    if "ارخص" in t:
        con = db()
        row = con.execute("SELECT MIN(price) AS p FROM products WHERE status='available'").fetchone()
        con.close()
        if row and row["p"] is not None:
            show_products(to, row["p"])
        else:
            send_text(to, "ماكو منتجات مضافة حالياً.")
        return

    if t.startswith("أريد ") or t.startswith("اريد "):
        code = text.split()[-1].upper()
        if product_by_code(code):
            start_order(to, code)
            return

    if t in {"0", "القائمة", "منيو", "رجوع", "ابدأ", "start", "hi", "hello", "هلا", "السلام عليكم"}:
        main_menu(to)
        return

    send_text(to, "ما فهمت عليك تماماً 🌹\nاكتب «القائمة» حتى تشوف الخيارات، أو مثلاً: «أريد ساعات بسبعة».")

def send_category(to, category):
    con = db()
    rows = con.execute("""
        SELECT * FROM products WHERE status='available' AND category=?
        ORDER BY id DESC LIMIT 8
    """, (category,)).fetchall()
    con.close()
    if not rows:
        send_text(to, f"حالياً ماكو موديلات {category} مضافة.")
        return
    for r in rows:
        caption = f"⌚ {r['name']}\n💰 {r['price']:g} {r['currency']}\n📦 {r['unit']}\n🔖 {r['code']}\n\nللطلب اكتب: أريد {r['code']}"
        image = BASE_DIR / r["image"] if r["image"] else None
        if image and image.exists():
            send_image(to, image, caption)
        else:
            send_text(to, caption)

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == "arbilwatches2026":
        return challenge, 200
    return "Forbidden", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True) or {}
    try:
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for msg in value.get("messages", []) or []:
                    to = msg.get("from")
                    if msg.get("type") == "text":
                        handle_text(to, msg.get("text", {}).get("body", ""))
                    elif msg.get("type") == "interactive":
                        inter = msg.get("interactive", {})
                        if inter.get("type") == "list_reply":
                            rid = inter.get("list_reply", {}).get("id", "")
                            if rid.startswith("price:"):
                                show_products(to, float(rid.split(":")[1]))
                            elif rid.startswith("product:"):
                                start_order(to, rid.split(":",1)[1])
                    else:
                        send_text(to, "حالياً أتعامل ويا الرسائل النصية 🌹 اكتب «القائمة».")
    except Exception as e:
        print("Webhook error:", repr(e))
    return jsonify({"ok": True}), 200

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin"))
        return render_template("login.html", error="كلمة المرور غير صحيحة")
    return render_template("login.html", error=None)

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))

def require_admin():
    return session.get("admin") is True

@app.route("/admin")
def admin():
    if not require_admin():
        return redirect(url_for("admin_login"))
    con = db()
    products = con.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    orders = con.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 50").fetchall()
    con.close()
    return render_template("admin.html", products=products, orders=orders)

@app.route("/admin/product/add", methods=["POST"])
def add_product():
    if not require_admin():
        return "Forbidden", 403
    code = request.form.get("code", "").strip().upper()
    name = request.form.get("name", "").strip()
    price = float(request.form.get("price", "0"))
    currency = request.form.get("currency", "IQD")
    unit = request.form.get("unit", "قطعة")
    category = request.form.get("category", "رجالي")
    features = request.form.get("features", "")
    image = request.files.get("image")
    image_rel = ""
    if image and image.filename:
        safe = "".join(c for c in image.filename if c.isalnum() or c in "._-").strip(".")
        filename = f"{code}_{safe or 'image.jpg'}"
        dest = UPLOAD_DIR / filename
        image.save(dest)
        image_rel = str(Path("static") / "uploads" / filename)
    con = db()
    con.execute("""
        INSERT OR REPLACE INTO products
        (code,name,price,currency,unit,category,features,image,status)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (code,name,price,currency,unit,category,features,image_rel,"available"))
    con.commit()
    con.close()
    return redirect(url_for("admin"))

@app.route("/admin/product/<code>/delete", methods=["POST"])
def delete_product(code):
    if not require_admin():
        return "Forbidden", 403
    con = db()
    con.execute("DELETE FROM products WHERE code=?", (code,))
    con.commit()
    con.close()
    return redirect(url_for("admin"))

@app.route("/health")
def health():
    return jsonify({"ok": True, "products": len(get_prices())})

@app.route("/static/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)

if __name__ == "__main__":
    init_db()
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
