import json
import os
import sqlite3
import uuid
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.utils import secure_filename


BASE_DIR = Path(__file__).resolve().parent

DB_PATH = BASE_DIR / "instance" / "store.db"

UPLOAD_DIR = BASE_DIR / "static" / "uploads"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


app = Flask(__name__)

app.secret_key = os.getenv(
    "SECRET_KEY",
    "change-this-secret-key"
)

app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024


ADMIN_USER = os.getenv(
    "ADMIN_USER",
    "admin"
)

ADMIN_PASSWORD = os.getenv(
    "ADMIN_PASSWORD",
    "change-me-now"
)


ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "webp",
    "gif",
}


ORDER_STATUSES = [
    "pending",
    "confirmed",
    "processing",
    "shipped",
    "delivered",
    "cancelled",
]


# =========================================================
# DATABASE
# =========================================================

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS categories (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            image TEXT,
            description TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category_id TEXT,
            description TEXT DEFAULT '',
            price REAL NOT NULL DEFAULT 0,
            offer_price REAL,
            stock INTEGER NOT NULL DEFAULT 0,
            featured INTEGER NOT NULL DEFAULT 0,
            images TEXT NOT NULL DEFAULT '[]',
            colors TEXT NOT NULL DEFAULT '[]',
            has_blouse_option INTEGER NOT NULL DEFAULT 0,
            price_with_blouse REAL,
            price_without_blouse REAL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(category_id)
                REFERENCES categories(id)
                ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            tracking_id TEXT NOT NULL UNIQUE,
            customer_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            district TEXT NOT NULL,
            upazila TEXT NOT NULL,
            full_address TEXT NOT NULL,
            items TEXT NOT NULL,
            product_total REAL NOT NULL,
            delivery_charge REAL NOT NULL DEFAULT 0,
            total_price REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )

    # Starter categories
    if conn.execute(
        "SELECT COUNT(*) FROM categories"
    ).fetchone()[0] == 0:

        now = datetime.utcnow().isoformat(
            timespec="seconds"
        )

        starter = [
            (
                "cat-cotton",
                "কটন",
                "",
                "আরামদায়ক কটন শাড়ি",
            ),
            (
                "cat-jamdani",
                "জামদানি",
                "",
                "ঐতিহ্যবাহী জামদানি",
            ),
            (
                "cat-half-silk",
                "হাফসিল্ক",
                "",
                "এলিগ্যান্ট হাফসিল্ক",
            ),
            (
                "cat-party",
                "পার্টি",
                "",
                "উৎসব ও পার্টি কালেকশন",
            ),
        ]

        conn.executemany(
            """
            INSERT INTO categories
            (id, name, image, description, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (a, b, c, d, now)
                for a, b, c, d in starter
            ],
        )

    conn.commit()
    conn.close()


# =========================================================
# HELPERS
# =========================================================

def json_load(value, default=None):
    try:
        data = json.loads(value or "null")

        if data is not None:
            return data

        return default if default is not None else []

    except (TypeError, json.JSONDecodeError):
        return default if default is not None else []


def serialize_product(row):
    p = dict(row)

    p["images"] = json_load(
        p.get("images"),
        []
    )

    p["colors"] = json_load(
        p.get("colors"),
        []
    )

    p["featured"] = bool(
        p.get("featured")
    )

    p["has_blouse_option"] = bool(
        p.get("has_blouse_option")
    )

    return p


def get_catalog():
    conn = db()

    categories = [
        dict(r)
        for r in conn.execute(
            "SELECT * FROM categories ORDER BY name"
        ).fetchall()
    ]

    products = [
        serialize_product(r)
        for r in conn.execute(
            """
            SELECT *
            FROM products
            ORDER BY featured DESC, created_at DESC
            """
        ).fetchall()
    ]

    conn.close()

    return categories, products


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(
            ".",
            1
        )[1].lower()
        in ALLOWED_EXTENSIONS
    )


def save_images(files):
    paths = []

    for f in files:

        if not f or not f.filename:
            continue

        if not allowed_file(f.filename):
            continue

        original_name = secure_filename(
            f.filename
        )

        ext = original_name.rsplit(
            ".",
            1
        )[1].lower()

        filename = (
            f"{uuid.uuid4().hex}.{ext}"
        )

        f.save(
            UPLOAD_DIR / filename
        )

        paths.append(
            f"uploads/{filename}"
        )

    return paths


def delete_image(rel_path):
    if not rel_path:
        return

    target = BASE_DIR / "static" / rel_path

    if (
        target.exists()
        and target.is_file()
        and UPLOAD_DIR in target.parents
    ):
        try:
            target.unlink()
        except OSError:
            pass


# =========================================================
# ADMIN AUTH
# =========================================================

def admin_required(view):

    @wraps(view)
    def wrapped(*args, **kwargs):

        if not session.get("is_admin"):
            return redirect(
                url_for("admin_login")
            )

        return view(*args, **kwargs)

    return wrapped


@app.context_processor
def inject_globals():
    return {
        "order_statuses": ORDER_STATUSES,
        "admin_logged_in": bool(
            session.get("is_admin")
        ),
        "now_year": datetime.now().year,
    }


# =========================================================
# WEBSITE
# =========================================================

@app.get("/")
def home():

    categories, products = get_catalog()

    category_map = {
        c["id"]: c["name"]
        for c in categories
    }

    return render_template(
        "index.html",
        categories=categories,
        products=products,
        category_map=category_map,
    )


@app.get("/category/<category_id>")
def category_page(category_id):

    conn = db()

    category = conn.execute(
        """
        SELECT *
        FROM categories
        WHERE id=?
        """,
        (category_id,),
    ).fetchone()

    products = [
        serialize_product(r)
        for r in conn.execute(
            """
            SELECT *
            FROM products
            WHERE category_id=?
            ORDER BY featured DESC, created_at DESC
            """,
            (category_id,),
        ).fetchall()
    ]

    categories = [
        dict(r)
        for r in conn.execute(
            "SELECT * FROM categories ORDER BY name"
        ).fetchall()
    ]

    conn.close()

    if not category:
        return redirect(
            url_for("home")
        )

    return render_template(
        "category.html",
        category=dict(category),
        categories=categories,
        products=products,
    )


@app.get("/product/<product_id>")
def product_page(product_id):

    conn = db()

    row = conn.execute(
        """
        SELECT *
        FROM products
        WHERE id=?
        """,
        (product_id,),
    ).fetchone()

    categories = [
        dict(r)
        for r in conn.execute(
            "SELECT * FROM categories ORDER BY name"
        ).fetchall()
    ]

    conn.close()

    if not row:
        return redirect(
            url_for("home")
        )

    return render_template(
        "product.html",
        product=serialize_product(row),
        categories=categories,
    )


@app.get("/checkout")
def checkout():

    categories, _ = get_catalog()

    return render_template(
        "checkout.html",
        categories=categories,
    )


@app.get("/track")
def tracking():

    return render_template(
        "track.html"
    )


@app.get("/api/catalog")
def api_catalog():

    categories, products = get_catalog()

    return jsonify(
        {
            "categories": categories,
            "products": products,
        }
    )


# =========================================================
# ORDERS
# =========================================================

@app.post("/api/orders")
def create_order():

    payload = (
        request.get_json(silent=True)
        or request.form
    )

    try:

        items = (
            json.loads(
                payload.get(
                    "items",
                    "[]"
                )
            )
            if isinstance(
                payload.get("items"),
                str,
            )
            else payload.get(
                "items",
                [],
            )
        )

    except json.JSONDecodeError:

        items = []

    if not items:
        return jsonify(
            {
                "ok": False,
                "error": "Cart is empty.",
            }
        ), 400

    name = str(
        payload.get(
            "customer_name",
            ""
        )
    ).strip()

    phone = str(
        payload.get(
            "phone",
            ""
        )
    ).strip()

    district = str(
        payload.get(
            "district",
            ""
        )
    ).strip()

    upazila = str(
        payload.get(
            "upazila",
            ""
        )
    ).strip()

    full_address = str(
        payload.get(
            "full_address",
            ""
        )
    ).strip()

    delivery = float(
        payload.get(
            "delivery_charge",
            0
        ) or 0
    )

    if not all(
        [
            name,
            phone,
            district,
            upazila,
            full_address,
        ]
    ):
        return jsonify(
            {
                "ok": False,
                "error": "সব তথ্য পূরণ করুন।",
            }
        ), 400

    conn = db()

    valid_items = []
    product_total = 0

    try:

        for item in items:

            pid = str(
                item.get(
                    "id",
                    ""
                )
            )

            qty = int(
                item.get(
                    "qty",
                    1
                )
            )

            if not pid or qty < 1:
                continue

            product = conn.execute(
                """
                SELECT *
                FROM products
                WHERE id=?
                """,
                (pid,),
            ).fetchone()

            if not product:
                continue

            stock = int(
                product["stock"] or 0
            )

            if stock < qty:
                return jsonify(
                    {
                        "ok": False,
                        "error": (
                            f"{product['name']} "
                            "এর পর্যাপ্ত স্টক নেই।"
                        ),
                    }
                ), 400

            unit = float(
                product["offer_price"]
                if product["offer_price"]
                is not None
                else product["price"]
            )

            line = unit * qty

            valid_items.append(
                {
                    "id": pid,
                    "name": product["name"],
                    "price": unit,
                    "qty": qty,
                }
            )

            product_total += line

        if not valid_items:
            return jsonify(
                {
                    "ok": False,
                    "error": (
                        "Valid product পাওয়া যায়নি।"
                    ),
                }
            ), 400

        total = product_total + delivery

        now = datetime.utcnow().isoformat(
            timespec="seconds"
        )

        tracking_id = (
            f"SC-"
            f"{datetime.utcnow().strftime('%y%m%d%H%M%S')}-"
            f"{uuid.uuid4().hex[:5].upper()}"
        )

        order_id = uuid.uuid4().hex

        conn.execute(
            """
            INSERT INTO orders
            (
                id,
                tracking_id,
                customer_name,
                phone,
                district,
                upazila,
                full_address,
                items,
                product_total,
                delivery_charge,
                total_price,
                status,
                created_at,
                updated_at
            )
            VALUES
            (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                order_id,
                tracking_id,
                name,
                phone,
                district,
                upazila,
                full_address,
                json.dumps(
                    valid_items,
                    ensure_ascii=False,
                ),
                product_total,
                delivery,
                total,
                "pending",
                now,
                now,
            ),
        )

        for item in valid_items:

            conn.execute(
                """
                UPDATE products
                SET stock = stock - ?
                WHERE id=?
                """,
                (
                    item["qty"],
                    item["id"],
                ),
            )

        conn.commit()

    finally:

        conn.close()

    return jsonify(
        {
            "ok": True,
            "tracking_id": tracking_id,
            "total": total,
        }
    )


@app.get("/api/orders/<tracking_id>")
def order_status(tracking_id):

    conn = db()

    row = conn.execute(
        """
        SELECT *
        FROM orders
        WHERE tracking_id=?
        """,
        (tracking_id.strip(),),
    ).fetchone()

    conn.close()

    if not row:
        return jsonify(
            {
                "ok": False,
                "error": "Order পাওয়া যায়নি।",
            }
        ), 404

    data = dict(row)

    data["items"] = json_load(
        data["items"],
        [],
    )

    return jsonify(
        {
            "ok": True,
            "order": data,
        }
    )


# =========================================================
# ADMIN LOGIN
# =========================================================

@app.get("/admin/login")
def admin_login():

    return render_template(
        "admin_login.html"
    )


@app.post("/admin/login")
def admin_login_post():

    username = request.form.get(
        "username",
        ""
    )

    password = request.form.get(
        "password",
        ""
    )

    if (
        username == ADMIN_USER
        and password == ADMIN_PASSWORD
    ):

        session["is_admin"] = True

        return redirect(
            url_for("admin_dashboard")
        )

    flash(
        "লগইন তথ্য সঠিক নয়।",
        "error",
    )

    return redirect(
        url_for("admin_login")
    )


@app.get("/admin/logout")
def admin_logout():

    session.clear()

    return redirect(
        url_for("admin_login")
    )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.get("/admin")
@admin_required
def admin_dashboard():

    conn = db()

    categories = [
        dict(r)
        for r in conn.execute(
            """
            SELECT *
            FROM categories
            ORDER BY name
            """
        ).fetchall()
    ]

    products = [
        serialize_product(r)
        for r in conn.execute(
            """
            SELECT *
            FROM products
            ORDER BY created_at DESC
            """
        ).fetchall()
    ]

    orders = [
        dict(r)
        for r in conn.execute(
            """
            SELECT *
            FROM orders
            ORDER BY created_at DESC
            """
        ).fetchall()
    ]

    # Product Edit
    edit_product_id = request.args.get(
        "edit_product"
    )

    edit_product = None

    if edit_product_id:

        row = conn.execute(
            """
            SELECT *
            FROM products
            WHERE id=?
            """,
            (edit_product_id,),
        ).fetchone()

        if row:
            edit_product = serialize_product(
                row
            )

    stats = {
        "products": len(products),
        "categories": len(categories),
        "orders": len(orders),
        "revenue": sum(
            float(o["total_price"])
            for o in orders
            if o["status"] != "cancelled"
        ),
        "low_stock": sum(
            1
            for p in products
            if int(p["stock"]) <= 3
        ),
    }

    conn.close()

    category_map = {
        c["id"]: c["name"]
        for c in categories
    }

    return render_template(
        "admin.html",
        categories=categories,
        products=products,
        orders=orders,
        stats=stats,
        category_map=category_map,
        edit_product=edit_product,
    )


# =========================================================
# CATEGORY
# =========================================================

@app.post("/admin/category/save")
@admin_required
def admin_category_save():

    category_id = (
        request.form.get("id")
        or f"cat-{uuid.uuid4().hex[:10]}"
    )

    name = request.form.get(
        "name",
        ""
    ).strip()

    description = request.form.get(
        "description",
        ""
    ).strip()

    image = request.files.get(
        "image"
    )

    if not name:

        flash(
            "Category name required.",
            "error",
        )

        return redirect(
            url_for("admin_dashboard")
        )

    image_path = None

    if (
        image
        and image.filename
        and allowed_file(image.filename)
    ):

        image_path = save_images(
            [image]
        )[0]

    conn = db()

    existing = conn.execute(
        """
        SELECT image
        FROM categories
        WHERE id=?
        """,
        (category_id,),
    ).fetchone()

    if image_path is None and existing:

        image_path = existing["image"]

    conn.execute(
        """
        INSERT INTO categories
        (
            id,
            name,
            image,
            description,
            created_at
        )
        VALUES (?,?,?,?,?)

        ON CONFLICT(id)
        DO UPDATE SET
            name=excluded.name,
            image=excluded.image,
            description=excluded.description
        """,
        (
            category_id,
            name,
            image_path,
            description,
            datetime.utcnow().isoformat(
                timespec="seconds"
            ),
        ),
    )

    conn.commit()
    conn.close()

    flash(
        "Category saved.",
        "success",
    )

    return redirect(
        url_for("admin_dashboard")
    )


@app.post("/admin/category/delete/<category_id>")
@admin_required
def admin_category_delete(category_id):

    conn = db()

    row = conn.execute(
        """
        SELECT image
        FROM categories
        WHERE id=?
        """,
        (category_id,),
    ).fetchone()

    conn.execute(
        """
        DELETE FROM categories
        WHERE id=?
        """,
        (category_id,),
    )

    conn.commit()
    conn.close()

    if row:

        delete_image(
            row["image"]
        )

    flash(
        "Category deleted.",
        "success",
    )

    return redirect(
        url_for("admin_dashboard")
    )


# =========================================================
# PRODUCT SAVE / ADD / UPDATE
# =========================================================

@app.post("/admin/product/save")
@admin_required
def admin_product_save():

    product_id = (
        request.form.get("id")
        or uuid.uuid4().hex
    )

    name = request.form.get(
        "name",
        ""
    ).strip()

    category_id = (
        request.form.get("category_id")
        or None
    )

    description = request.form.get(
        "description",
        ""
    ).strip()

    price = float(
        request.form.get("price")
        or 0
    )

    offer_raw = request.form.get(
        "offer_price",
        ""
    ).strip()

    offer_price = (
        float(offer_raw)
        if offer_raw
        else None
    )

    stock = int(
        request.form.get("stock")
        or 0
    )

    featured = (
        1
        if request.form.get("featured") == "on"
        else 0
    )

    colors = [
        c.strip()
        for c in request.form.get(
            "colors",
            ""
        ).split(",")
        if c.strip()
    ]

    has_blouse = (
        1
        if request.form.get("has_blouse") == "on"
        else 0
    )

    price_with_raw = request.form.get(
        "price_with_blouse",
        ""
    ).strip()

    price_without_raw = request.form.get(
        "price_without_blouse",
        ""
    ).strip()

    price_with = (
        float(price_with_raw)
        if price_with_raw
        else None
    )

    price_without = (
        float(price_without_raw)
        if price_without_raw
        else None
    )

    if not name:

        flash(
            "Product name required.",
            "error",
        )

        return redirect(
            url_for("admin_dashboard")
        )

    conn = db()

    old = conn.execute(
        """
        SELECT *
        FROM products
        WHERE id=?
        """,
        (product_id,),
    ).fetchone()

    # Existing images
    old_images = (
        json_load(
            old["images"],
            [],
        )
        if old
        else []
    )

    # New images
    new_images = save_images(
        request.files.getlist("images")
    )

    # Keep old images and add new images
    images = old_images + new_images

    conn.execute(
        """
        INSERT INTO products
        (
            id,
            name,
            category_id,
            description,
            price,
            offer_price,
            stock,
            featured,
            images,
            colors,
            has_blouse_option,
            price_with_blouse,
            price_without_blouse,
            created_at
        )
        VALUES
        (?,?,?,?,?,?,?,?,?,?,?,?,?,?)

        ON CONFLICT(id)
        DO UPDATE SET

            name=excluded.name,
            category_id=excluded.category_id,
            description=excluded.description,
            price=excluded.price,
            offer_price=excluded.offer_price,
            stock=excluded.stock,
            featured=excluded.featured,
            images=excluded.images,
            colors=excluded.colors,
            has_blouse_option=excluded.has_blouse_option,
            price_with_blouse=excluded.price_with_blouse,
            price_without_blouse=excluded.price_without_blouse
        """,
        (
            product_id,
            name,
            category_id,
            description,
            price,
            offer_price,
            stock,
            featured,
            json.dumps(
                images,
                ensure_ascii=False,
            ),
            json.dumps(
                colors,
                ensure_ascii=False,
            ),
            has_blouse,
            price_with,
            price_without,
            datetime.utcnow().isoformat(
                timespec="seconds"
            ),
        ),
    )

    conn.commit()
    conn.close()

    flash(
        "Product saved.",
        "success",
    )

    return redirect(
        url_for("admin_dashboard")
    )


# =========================================================
# PRODUCT DELETE
# =========================================================

@app.post("/admin/product/delete/<product_id>")
@admin_required
def admin_product_delete(product_id):

    conn = db()

    row = conn.execute(
        """
        SELECT images
        FROM products
        WHERE id=?
        """,
        (product_id,),
    ).fetchone()

    conn.execute(
        """
        DELETE FROM products
        WHERE id=?
        """,
        (product_id,),
    )

    conn.commit()
    conn.close()

    if row:

        for img in json_load(
            row["images"],
            [],
        ):

            delete_image(img)

    flash(
        "Product deleted.",
        "success",
    )

    return redirect(
        url_for("admin_dashboard")
    )


# =========================================================
# DELETE SINGLE PRODUCT IMAGE
# =========================================================

@app.post("/admin/product/image-delete")
@admin_required
def admin_product_image_delete():

    product_id = request.form.get(
        "product_id"
    )

    image = request.form.get(
        "image"
    )

    if not product_id or not image:

        return redirect(
            url_for("admin_dashboard")
        )

    conn = db()

    row = conn.execute(
        """
        SELECT images
        FROM products
        WHERE id=?
        """,
        (product_id,),
    ).fetchone()

    if row:

        images = json_load(
            row["images"],
            [],
        )

        if image in images:

            # Remove selected image
            images.remove(image)

            # First remaining image
            # becomes thumbnail.
            conn.execute(
                """
                UPDATE products
                SET images=?
                WHERE id=?
                """,
                (
                    json.dumps(
                        images,
                        ensure_ascii=False,
                    ),
                    product_id,
                ),
            )

            conn.commit()

    conn.close()

    # Delete physical image file
    delete_image(image)

    flash(
        "Image deleted.",
        "success",
    )

    return redirect(
        url_for(
            "admin_dashboard",
            edit_product=product_id,
        )
    )


# =========================================================
# SET PRODUCT THUMBNAIL
# =========================================================

@app.post("/admin/product/set-thumbnail")
@admin_required
def admin_product_set_thumbnail():

    product_id = request.form.get(
        "product_id"
    )

    image = request.form.get(
        "image"
    )

    if not product_id or not image:

        return redirect(
            url_for("admin_dashboard")
        )

    conn = db()

    row = conn.execute(
        """
        SELECT images
        FROM products
        WHERE id=?
        """,
        (product_id,),
    ).fetchone()

    if row:

        images = json_load(
            row["images"],
            [],
        )

        # Make sure image exists
        if image in images:

            # Move selected image
            # to first position.
            images.remove(image)
            images.insert(0, image)

            conn.execute(
                """
                UPDATE products
                SET images=?
                WHERE id=?
                """,
                (
                    json.dumps(
                        images,
                        ensure_ascii=False,
                    ),
                    product_id,
                ),
            )

            conn.commit()

    conn.close()

    flash(
        "Thumbnail changed.",
        "success",
    )

    return redirect(
        url_for(
            "admin_dashboard",
            edit_product=product_id,
        )
    )


# =========================================================
# ORDER STATUS
# =========================================================

@app.post("/admin/order/status/<tracking_id>")
@admin_required
def admin_order_status(tracking_id):

    status = request.form.get(
        "status",
        "pending",
    )

    if status not in ORDER_STATUSES:
        status = "pending"

    conn = db()

    conn.execute(
        """
        UPDATE orders
        SET status=?,
            updated_at=?
        WHERE tracking_id=?
        """,
        (
            status,
            datetime.utcnow().isoformat(
                timespec="seconds"
            ),
            tracking_id,
        ),
    )

    conn.commit()
    conn.close()

    flash(
        "Order status updated.",
        "success",
    )

    return redirect(
        url_for("admin_dashboard")
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    init_db()

    app.run(
        host="0.0.0.0",
        port=int(
            os.getenv(
                "PORT",
                "5000",
            )
        ),
        debug=True,
    )

else:

    init_db()
