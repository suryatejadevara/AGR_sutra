"""
utils/data_store.py
--------------------
Lightweight CSV-backed persistence for the demo. Swap these functions
for real database calls (Postgres/Supabase/Firebase) when moving past
a prototype — every function signature here is the contract the rest
of the app relies on, so the pages themselves won't need to change.
"""

import os
import uuid
from datetime import datetime

import pandas as pd
from PIL import Image

DATA_DIR = "data"
IMAGES_DIR = os.path.join(DATA_DIR, "images")
USERS_PATH = os.path.join(DATA_DIR, "users.csv")
PRODUCTS_PATH = os.path.join(DATA_DIR, "products.csv")
ORDERS_PATH = os.path.join(DATA_DIR, "orders.csv")
REVIEWS_PATH = os.path.join(DATA_DIR, "reviews.csv")

USER_COLUMNS = [
    "user_id", "full_name", "phone", "email", "pin_code",
    "language", "role", "latitude", "longitude", "created_at",
]
PRODUCT_COLUMNS = [
    "product_id", "seller_id", "product_name", "category", "material",
    "language", "price", "stock", "english_desc", "hindi_desc",
    "image_path", "status", "created_at",
]
ORDER_COLUMNS = [
    "order_id", "buyer_id", "seller_id", "product_id", "product_name",
    "quantity", "total_amount", "shipping_address", "payment_method",
    "status", "created_at",
]

# review_type values:
#   "product"        -> buyer rates a product they ordered (tied to an order)
#   "seller"          -> buyer rates the seller/store (tied to an order)
#   "buyer"           -> seller rates the buyer (tied to an order)
#   "seller_initial"  -> seller's own opening review of their product
#                        (no order involved; one per product)
REVIEW_COLUMNS = [
    "review_id", "review_type", "order_id", "product_id", "seller_id",
    "buyer_id", "rating", "comment", "created_at",
]
VALID_REVIEW_TYPES = {"product", "seller", "buyer", "seller_initial"}

# Columns that must NEVER be inferred as a numeric dtype, even if every
# value currently in the CSV happens to look like a number (phone
# numbers, PIN codes, IDs). Without this, pandas silently infers them
# as int64 on read, and any later write of a differently-formatted
# value (e.g. a phone number with a leading '+91', or a leading zero
# in a PIN code) raises:
#   TypeError: Invalid value '...' for dtype 'int64'
# Forcing these to load as plain strings prevents that entirely.
_STRING_COLUMNS = {
    "user_id", "phone", "email", "pin_code",
    "product_id", "seller_id", "buyer_id", "order_id", "review_id",
}

os.makedirs(IMAGES_DIR, exist_ok=True)


def _ensure_csv(path: str, columns: list):
    if not os.path.exists(path):
        pd.DataFrame(columns=columns).to_csv(path, index=False)


def _load(path: str, columns: list) -> pd.DataFrame:
    _ensure_csv(path, columns)
    try:
        # Force known ID/contact columns to load as strings so pandas
        # never infers int64 (or any numeric type) for them -- this is
        # what prevents write-time "Invalid value for dtype" errors when
        # saving phone numbers, PIN codes, or IDs later.
        dtype_overrides = {col: str for col in columns if col in _STRING_COLUMNS}
        df = pd.read_csv(path, dtype=dtype_overrides, keep_default_na=True)
        for col in columns:
            if col not in df.columns:
                df[col] = pd.NA
        return df
    except Exception:
        return pd.DataFrame(columns=columns)


def _save(df: pd.DataFrame, path: str):
    df.to_csv(path, index=False)


# =====================================================================
# USERS
# =====================================================================
def load_users() -> pd.DataFrame:
    return _load(USERS_PATH, USER_COLUMNS)


def get_user_by_contact(phone: str = "", email: str = ""):
    df = load_users()
    if df.empty:
        return None
    match = pd.DataFrame()
    if phone:
        match = df[df["phone"].astype(str) == str(phone)]
    if match.empty and email:
        match = df[df["email"].astype(str) == str(email)]
    if match.empty:
        return None
    return match.iloc[-1].to_dict()

def get_user(user_id: str) -> dict | None:
    """Look up any user (buyer or seller) by their user_id."""
    df = load_users()
    if df.empty:
        return None
    match = df[df["user_id"] == user_id]
    return None if match.empty else match.iloc[0].to_dict()


def create_or_update_user(full_name, phone, email, pin_code, language, role) -> dict:
    df = load_users()

    existing = get_user_by_contact(phone=phone, email=email)
    if existing:
        idx = df[df["user_id"] == existing["user_id"]].index
        df.loc[idx, ["full_name", "phone", "email", "pin_code", "language", "role"]] = [
            full_name, phone, email, pin_code, language, role,
        ]
        _save(df, USERS_PATH)
        return df.loc[idx[0]].to_dict()

    user_id = str(uuid.uuid4())[:8]
    new_row = {
        "user_id": user_id, "full_name": full_name, "phone": phone,
        "email": email, "pin_code": pin_code, "language": language,
        "role": role, "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    _save(df, USERS_PATH)
    return new_row


def update_user_profile(user_id: str, **fields) -> dict | None:
    df = load_users()
    idx = df[df["user_id"] == user_id].index
    if idx.empty:
        return None
    for key, value in fields.items():
        if key in df.columns:
            df.loc[idx, key] = value
    _save(df, USERS_PATH)
    return df.loc[idx[0]].to_dict()


# =====================================================================
# PRODUCTS
# =====================================================================
def load_products() -> pd.DataFrame:
    return _load(PRODUCTS_PATH, PRODUCT_COLUMNS)


def save_product(seller_id, product_name, category, material, price, stock,
                  english_desc, hindi_desc, image: Image.Image, language=None) -> str:
    df = load_products()
    product_id = str(uuid.uuid4())[:8]

    image_path = os.path.join(IMAGES_DIR, f"{product_id}.png")
    try:
        image.save(image_path, format="PNG")
    except Exception:
        image_path = ""

    new_row = {
        "product_id": product_id, "seller_id": seller_id, "product_name": product_name,
        "category": category, "material": material,
        "language": language or "Not detected", "price": price, "stock": stock,
        "english_desc": english_desc, "hindi_desc": hindi_desc,
        "image_path": image_path, "status": "Active",
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    _save(df, PRODUCTS_PATH)
    return product_id


def get_product(product_id: str):
    df = load_products()
    match = df[df["product_id"] == product_id]
    return None if match.empty else match.iloc[0].to_dict()


def update_product_status(product_id: str, status: str):
    df = load_products()
    df.loc[df["product_id"] == product_id, "status"] = status
    _save(df, PRODUCTS_PATH)


def update_product_stock(product_id: str, new_stock: int):
    df = load_products()
    df.loc[df["product_id"] == product_id, "stock"] = new_stock
    _save(df, PRODUCTS_PATH)


def delete_product(product_id: str):
    df = load_products()
    row = df[df["product_id"] == product_id]
    if not row.empty:
        img_path = row.iloc[0].get("image_path")
        if isinstance(img_path, str) and img_path and os.path.exists(img_path):
            try:
                os.remove(img_path)
            except OSError:
                pass
    df = df[df["product_id"] != product_id]
    _save(df, PRODUCTS_PATH)


# =====================================================================
# ORDERS
# =====================================================================
def load_orders() -> pd.DataFrame:
    return _load(ORDERS_PATH, ORDER_COLUMNS)


def place_order(buyer_id, product_id, quantity, shipping_address, payment_method) -> str | None:
    product = get_product(product_id)
    if product is None:
        return None

    order_id = str(uuid.uuid4())[:8].upper()
    total_amount = int(product["price"]) * int(quantity)

    new_row = {
        "order_id": order_id, "buyer_id": buyer_id, "seller_id": product["seller_id"],
        "product_id": product_id, "product_name": product["product_name"],
        "quantity": quantity, "total_amount": total_amount,
        "shipping_address": shipping_address, "payment_method": payment_method,
        "status": "New", "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    df = load_orders()
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    _save(df, ORDERS_PATH)

    # decrement stock, never below 0
    products_df = load_products()
    idx = products_df[products_df["product_id"] == product_id].index
    if not idx.empty:
        current_stock = int(products_df.loc[idx[0], "stock"])
        products_df.loc[idx[0], "stock"] = max(0, current_stock - int(quantity))
        _save(products_df, PRODUCTS_PATH)

    return order_id


def get_order(order_id: str):
    df = load_orders()
    match = df[df["order_id"] == order_id]
    return None if match.empty else match.iloc[0].to_dict()


def update_order_status(order_id: str, status: str):
    df = load_orders()
    df.loc[df["order_id"] == order_id, "status"] = status
    _save(df, ORDERS_PATH)


# =====================================================================
# REVIEWS & RATINGS
# =====================================================================
def load_reviews() -> pd.DataFrame:
    """Reviews of every type live in one CSV, distinguished by review_type.
    Rows saved before review_type existed are treated as ordinary buyer
    product reviews, so nothing written under the old schema is lost."""
    df = _load(REVIEWS_PATH, REVIEW_COLUMNS)
    if not df.empty:
        df["review_type"] = df["review_type"].fillna("product")
        df.loc[~df["review_type"].isin(VALID_REVIEW_TYPES), "review_type"] = "product"
    return df


def _add_review(review_type: str, rating: int, comment: str = "", order_id: str = "",
                 product_id: str = "", seller_id: str = "", buyer_id: str = "") -> str:
    review_id = str(uuid.uuid4())[:8]
    new_row = {
        "review_id": review_id, "review_type": review_type, "order_id": order_id or "",
        "product_id": product_id or "", "seller_id": seller_id or "", "buyer_id": buyer_id or "",
        "rating": max(1, min(5, int(rating))), "comment": (comment or "").strip(),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    df = load_reviews()
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    _save(df, REVIEWS_PATH)
    return review_id


def has_reviewed_order(order_id: str, review_type: str = "product") -> bool:
    """One review of a given type per order (e.g. one product review AND
    one seller review AND one buyer review can all exist for the same
    order — but not two of the same type)."""
    df = load_reviews()
    if df.empty:
        return False
    return not df[(df["order_id"] == order_id) & (df["review_type"] == review_type)].empty


# ---------- Buyer rates a product ----------
def get_reviewable_product_orders(buyer_id: str, product_id: str):
    """Completed orders for this buyer+product that don't have a product
    review yet. Returns a list of order dicts, most recent first."""
    orders = load_orders()
    if orders.empty:
        return []
    candidates = orders[
        (orders["buyer_id"] == buyer_id)
        & (orders["product_id"] == product_id)
        & (orders["status"] == "Completed")
    ]
    if candidates.empty:
        return []
    reviews = load_reviews()
    reviewed_ids = set(reviews[reviews["review_type"] == "product"]["order_id"]) if not reviews.empty else set()
    pending = candidates[~candidates["order_id"].isin(reviewed_ids)]
    return pending.sort_values("created_at", ascending=False).to_dict("records")


def add_product_review(order_id: str, product_id: str, seller_id: str, buyer_id: str,
                        rating: int, comment: str) -> str | None:
    if has_reviewed_order(order_id, "product"):
        return None
    return _add_review("product", rating, comment, order_id=order_id,
                        product_id=product_id, seller_id=seller_id, buyer_id=buyer_id)


# ---------- Buyer rates the seller ----------
def get_reviewable_seller_orders(buyer_id: str, seller_id: str):
    """Completed orders where this buyer bought from this seller and
    hasn't rated the seller for that order yet."""
    orders = load_orders()
    if orders.empty:
        return []
    candidates = orders[
        (orders["buyer_id"] == buyer_id)
        & (orders["seller_id"] == seller_id)
        & (orders["status"] == "Completed")
    ]
    if candidates.empty:
        return []
    reviews = load_reviews()
    reviewed_ids = set(reviews[reviews["review_type"] == "seller"]["order_id"]) if not reviews.empty else set()
    pending = candidates[~candidates["order_id"].isin(reviewed_ids)]
    return pending.sort_values("created_at", ascending=False).to_dict("records")


def add_seller_review(order_id: str, product_id: str, seller_id: str, buyer_id: str,
                       rating: int, comment: str) -> str | None:
    if has_reviewed_order(order_id, "seller"):
        return None
    return _add_review("seller", rating, comment, order_id=order_id,
                        product_id=product_id, seller_id=seller_id, buyer_id=buyer_id)


# ---------- Seller rates the buyer ----------
def get_reviewable_buyer_order(order_id: str) -> bool:
    """Whether the seller can still rate the buyer for this order."""
    return not has_reviewed_order(order_id, "buyer")


def add_buyer_review(order_id: str, product_id: str, seller_id: str, buyer_id: str,
                      rating: int, comment: str) -> str | None:
    if has_reviewed_order(order_id, "buyer"):
        return None
    return _add_review("buyer", rating, comment, order_id=order_id,
                        product_id=product_id, seller_id=seller_id, buyer_id=buyer_id)


# ---------- Seller's own initial review of a product ----------
def has_seller_reviewed_product(product_id: str) -> bool:
    df = load_reviews()
    if df.empty:
        return False
    return not df[(df["product_id"] == product_id) & (df["review_type"] == "seller_initial")].empty


def add_seller_initial_review(product_id: str, seller_id: str, rating: int, comment: str) -> str | None:
    """One opening review per product, written by the seller themselves
    to kick-start the product's review section."""
    if has_seller_reviewed_product(product_id):
        return None
    return _add_review("seller_initial", rating, comment, product_id=product_id, seller_id=seller_id)


# ---------- Aggregates & display helpers ----------
def get_product_rating(product_id: str) -> tuple[float, int]:
    """(average_rating, review_count) from BUYER product reviews only —
    the seller's own initial review is shown alongside reviews but never
    counted toward the average, so sellers can't inflate their own score."""
    df = load_reviews()
    if df.empty:
        return 0.0, 0
    subset = df[(df["product_id"] == product_id) & (df["review_type"] == "product")]
    if subset.empty:
        return 0.0, 0
    ratings = pd.to_numeric(subset["rating"], errors="coerce").dropna()
    if ratings.empty:
        return 0.0, 0
    return round(float(ratings.mean()), 1), int(len(ratings))


def get_ratings_by_product() -> pd.DataFrame:
    """Bulk version of get_product_rating for list views (Marketplace,
    My Listings). Buyer product reviews only, same as get_product_rating.
    Returns a DataFrame indexed by product_id with 'avg_rating' and
    'review_count' columns."""
    df = load_reviews()
    if df.empty:
        return pd.DataFrame(columns=["avg_rating", "review_count"])
    subset = df[df["review_type"] == "product"].copy()
    if subset.empty:
        return pd.DataFrame(columns=["avg_rating", "review_count"])
    subset["rating"] = pd.to_numeric(subset["rating"], errors="coerce")
    grouped = subset.groupby("product_id")["rating"].agg(["mean", "count"])
    grouped = grouped.rename(columns={"mean": "avg_rating", "count": "review_count"})
    grouped["avg_rating"] = grouped["avg_rating"].round(1)
    return grouped


def get_reviews_for_product(product_id: str) -> pd.DataFrame:
    """All reviews attached to a product for display: buyer reviews AND
    the seller's own initial review (flagged via review_type so the page
    can label it as such), most recent first."""
    df = load_reviews()
    if df.empty:
        return df
    subset = df[(df["product_id"] == product_id) & (df["review_type"].isin(["product", "seller_initial"]))].copy()
    if subset.empty:
        return subset
    subset["created_at"] = pd.to_datetime(subset["created_at"], errors="coerce")
    return subset.sort_values("created_at", ascending=False)


def get_seller_rating(seller_id: str) -> tuple[float, int]:
    """Store-wide rating a seller has received directly from buyers
    (review_type == 'seller') — this is what shows on the seller's
    dashboard and product pages as their overall store rating."""
    df = load_reviews()
    if df.empty:
        return 0.0, 0
    subset = df[(df["seller_id"] == seller_id) & (df["review_type"] == "seller")]
    if subset.empty:
        return 0.0, 0
    ratings = pd.to_numeric(subset["rating"], errors="coerce").dropna()
    if ratings.empty:
        return 0.0, 0
    return round(float(ratings.mean()), 1), int(len(ratings))


def get_buyer_rating(buyer_id: str) -> tuple[float, int]:
    """A buyer's rating as given by sellers they've ordered from
    (review_type == 'buyer')."""
    df = load_reviews()
    if df.empty:
        return 0.0, 0
    subset = df[(df["buyer_id"] == buyer_id) & (df["review_type"] == "buyer")]
    if subset.empty:
        return 0.0, 0
    ratings = pd.to_numeric(subset["rating"], errors="coerce").dropna()
    if ratings.empty:
        return 0.0, 0
    return round(float(ratings.mean()), 1), int(len(ratings))


def format_stars(avg_rating: float) -> str:
    """Renders a 5-star string with a filled star per whole point,
    rounding to the nearest half is skipped for simplicity -- nearest
    whole star keeps this readable in small captions."""
    if avg_rating <= 0:
        return "☆☆☆☆☆"
    full = int(round(avg_rating))
    full = max(0, min(5, full))
    return "⭐" * full + "☆" * (5 - full)