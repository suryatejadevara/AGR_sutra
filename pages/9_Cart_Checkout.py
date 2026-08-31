import os
import streamlit as st

from utils.auth import require_login, current_user
from utils.data_store import get_product, place_order

st.set_page_config(page_title="AGR Sutra — Cart & Checkout", page_icon="🛍️", layout="centered")

user = require_login(required_role="Buyer")

st.title("🛍️ Cart & Checkout")

if st.button("← Back to Marketplace"):
    st.switch_page("pages/7_Marketplace.py")

st.divider()

# -------------------- Determine items to checkout --------------------
buy_now_id = st.session_state.get("buy_now_product_id")
buy_now_qty = st.session_state.get("buy_now_quantity", 1)

is_buy_now = buy_now_id is not None

if is_buy_now:
    items = {buy_now_id: buy_now_qty}
    st.caption("⚡ Quick checkout")
else:
    items = st.session_state.get("cart", {})

if not items:
    st.info("Your cart is empty. Browse the Marketplace to find something you love.")
    if st.button("Go to Marketplace", type="primary"):
        st.switch_page("pages/7_Marketplace.py")
    st.stop()

# -------------------- Build line items, dropping unavailable products --------------------
line_items = []
removed_products = []

for product_id, qty in list(items.items()):
    product = get_product(product_id)
    if product is None or product.get("status") != "Active":
        removed_products.append(product_id)
        continue

    stock = product.get("stock")
    try:
        stock = int(stock)
    except (TypeError, ValueError):
        stock = 0

    if stock <= 0:
        removed_products.append(product_id)
        continue

    qty = min(qty, stock)
    line_items.append({"product": product, "quantity": qty, "stock": stock})

if removed_products and not is_buy_now:
    cart = st.session_state.get("cart", {})
    for pid in removed_products:
        cart.pop(pid, None)
    st.session_state["cart"] = cart
    st.warning("Some items in your cart are no longer available and were removed.")

if not line_items:
    st.info("None of your cart items are currently available.")
    if st.button("Go to Marketplace", type="primary"):
        st.switch_page("pages/7_Marketplace.py")
    st.stop()

# -------------------- Cart review --------------------
st.markdown("#### Order Summary")

total_amount = 0
for entry in line_items:
    product = entry["product"]
    pid = product["product_id"]

    col1, col2 = st.columns([1, 2])
    with col1:
        image_path = product.get("image_path")
        if isinstance(image_path, str) and image_path and os.path.exists(image_path):
            st.image(image_path, use_container_width=True)
        else:
            st.markdown("🧣")
    with col2:
        st.markdown(f"**{product['product_name']}**")
        st.caption(f"₹{int(product['price']):,} each")

        if is_buy_now:
            quantity = entry["quantity"]
            st.caption(f"Quantity: {quantity}")
        else:
            quantity = st.number_input(
                "Quantity", min_value=1, max_value=entry["stock"],
                value=entry["quantity"], key=f"qty_{pid}",
            )
            cart = st.session_state.get("cart", {})
            cart[pid] = quantity
            st.session_state["cart"] = cart

            if st.button("Remove", key=f"remove_{pid}"):
                cart = st.session_state.get("cart", {})
                cart.pop(pid, None)
                st.session_state["cart"] = cart
                st.rerun()

        subtotal = int(product["price"]) * quantity
        total_amount += subtotal
        st.markdown(f"Subtotal: ₹{subtotal:,}")
    st.divider()

st.markdown(f"### Total: ₹{total_amount:,}")

st.divider()

# -------------------- Shipping & payment --------------------
st.markdown("#### Shipping Details")

buyer = current_user()
default_address = f"{buyer.get('pin_code', '')}".strip()
shipping_address = st.text_area(
    "Delivery Address",
    placeholder="House/Flat No., Street, City, State, PIN Code",
)

payment_method = st.radio("Payment Method", ["Cash on Delivery", "UPI", "Card"], horizontal=True)

st.divider()

if st.button("✅ Place Order", type="primary", use_container_width=True):
    if not shipping_address.strip():
        st.warning("Please enter a delivery address.")
    else:
        order_ids = []
        for entry in line_items:
            product = entry["product"]
            pid = product["product_id"]
            qty = st.session_state.get("cart", {}).get(pid, entry["quantity"]) if not is_buy_now else entry["quantity"]

            order_id = place_order(
                buyer_id=user["user_id"],
                product_id=pid,
                quantity=qty,
                shipping_address=shipping_address.strip(),
                payment_method=payment_method,
            )
            if order_id:
                order_ids.append(order_id)

        if order_ids:
            # clear whatever was used for this checkout
            if is_buy_now:
                st.session_state.pop("buy_now_product_id", None)
                st.session_state.pop("buy_now_quantity", None)
            else:
                st.session_state["cart"] = {}

            st.success(f"🎉 Order placed successfully! ({len(order_ids)} item(s))")
            st.balloons()
            if st.button("View My Orders", type="primary", use_container_width=True):
                st.switch_page("pages/10_My_Orders.py")
        else:
            st.error("Something went wrong placing your order. Please try again.")