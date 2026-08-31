import os
import pandas as pd
import streamlit as st

from utils.auth import require_login
from utils.data_store import load_orders, load_products, update_order_status, get_product, update_product_stock

st.set_page_config(page_title="AGR Sutra — My Orders", page_icon="📦", layout="centered")

user = require_login(required_role="Buyer")

st.title("📦 My Orders")

if st.button("← Back to Home"):
    st.switch_page("pages/6_Buyer_Home.py")

st.divider()

orders = load_orders()
products = load_products()

my_orders = orders[orders["buyer_id"] == user["user_id"]] if not orders.empty else orders

if my_orders.empty:
    st.info("You haven't placed any orders yet. Browse the Marketplace to find something you love.")
    if st.button("Go to Marketplace", type="primary"):
        st.switch_page("pages/7_Marketplace.py")
    st.stop()

my_orders = my_orders.copy()
my_orders["created_at"] = pd.to_datetime(my_orders["created_at"], errors="coerce")

product_images = products.set_index("product_id")["image_path"] if not products.empty else pd.Series(dtype=str)

tab_new, tab_processing, tab_completed, tab_cancelled = st.tabs(
    ["🆕 New", "⏳ Processing", "✅ Completed", "🚫 Cancelled"]
)


def render_order(row, allow_cancel=False):
    col1, col2 = st.columns([1, 2])
    with col1:
        image_path = product_images.get(row["product_id"]) if not product_images.empty else None
        if isinstance(image_path, str) and image_path and os.path.exists(image_path):
            st.image(image_path, use_container_width=True)
        else:
            st.markdown("🧣")
    with col2:
        st.markdown(f"**Order #{row['order_id']}**")
        st.write(f"{row['product_name']} — Qty {int(row['quantity'])}")
        st.markdown(f"₹{int(row['total_amount']):,}")
        if pd.notna(row["created_at"]):
            st.caption(f"Placed on {row['created_at'].strftime('%d %b %Y, %I:%M %p')}")
        st.caption(f"Ship to: {row.get('shipping_address', 'N/A')}")
        st.caption(f"Payment: {row.get('payment_method', 'N/A')}")

        if allow_cancel:
            if st.button("Cancel Order", key=f"cancel_{row['order_id']}"):
                update_order_status(row["order_id"], "Cancelled")
                product = get_product(row["product_id"])
                if product is not None:
                    try:
                        current_stock = int(product.get("stock", 0))
                    except (TypeError, ValueError):
                        current_stock = 0
                    update_product_stock(row["product_id"], current_stock + int(row["quantity"]))
                st.success("Order cancelled.")
                st.rerun()
    st.divider()


with tab_new:
    subset = my_orders[my_orders["status"] == "New"]
    if subset.empty:
        st.caption("No new orders.")
    else:
        for _, r in subset.iloc[::-1].iterrows():
            render_order(r, allow_cancel=True)

with tab_processing:
    subset = my_orders[my_orders["status"] == "Processing"]
    if subset.empty:
        st.caption("Nothing in progress.")
    else:
        for _, r in subset.iloc[::-1].iterrows():
            render_order(r)

with tab_completed:
    subset = my_orders[my_orders["status"] == "Completed"]
    if subset.empty:
        st.caption("No completed orders yet.")
    else:
        for _, r in subset.iloc[::-1].iterrows():
            render_order(r)

with tab_cancelled:
    subset = my_orders[my_orders["status"] == "Cancelled"]
    if subset.empty:
        st.caption("No cancelled orders.")
    else:
        for _, r in subset.iloc[::-1].iterrows():
            render_order(r)