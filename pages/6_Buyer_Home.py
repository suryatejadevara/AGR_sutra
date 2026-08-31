import os
import streamlit as st

from utils.auth import require_login, log_out
from utils.data_store import load_products, load_orders

st.set_page_config(page_title="AGR Sutra — Buyer Home", page_icon="🏠", layout="centered")

user = require_login(required_role="Buyer")

st.title(f"Namaste, {user['full_name'].split()[0]}! 👋")
st.caption("Discover authentic handmade products from artisans across India")

products = load_products()
orders = load_orders()

active_products = products[products["status"] == "Active"] if not products.empty else products
my_orders = orders[orders["buyer_id"] == user["user_id"]] if not orders.empty else orders

col1, col2, col3 = st.columns(3)
col1.metric("Products Available", len(active_products))
col2.metric("My Orders", len(my_orders))
pending_orders = my_orders[my_orders["status"] != "Completed"] if not my_orders.empty else my_orders
col3.metric("In Progress", len(pending_orders))

st.divider()
st.markdown("#### Quick Actions")

c1, c2 = st.columns(2)
with c1:
    if st.button("🛒 Browse Marketplace", type="primary", use_container_width=True):
        st.switch_page("pages/7_Marketplace.py")
    if st.button("📦 My Orders", use_container_width=True):
        st.switch_page("pages/10_My_Orders.py")
with c2:
    if st.button("🛍️ My Cart", use_container_width=True):
        st.switch_page("pages/9_Cart_Checkout.py")
    if st.button("⚙️ Profile Settings", use_container_width=True):
        st.switch_page("pages/11_Profile_Settings.py")

st.divider()

# -------------------- Browse by category --------------------
st.markdown("#### 🗂️ Browse by Category")

if active_products.empty:
    st.info("No products available yet — check back soon!")
else:
    categories = sorted(active_products["category"].dropna().unique().tolist())
    cols = st.columns(2)
    for i, category in enumerate(categories):
        count = len(active_products[active_products["category"] == category])
        with cols[i % 2]:
            if st.button(f"{category} ({count})", key=f"cat_{category}", use_container_width=True):
                st.session_state["marketplace_category_filter"] = category
                st.switch_page("pages/7_Marketplace.py")

st.divider()

# -------------------- Newly added products --------------------
st.markdown("#### ✨ New Arrivals")

if active_products.empty:
    st.caption("No products yet.")
else:
    recent = active_products.tail(4).iloc[::-1]
    for _, row in recent.iterrows():
        col1, col2 = st.columns([1, 2])
        with col1:
            if isinstance(row.get("image_path"), str) and row["image_path"] and os.path.exists(row["image_path"]):
                st.image(row["image_path"], use_container_width=True)
            else:
                st.markdown("🧣")
        with col2:
            st.markdown(f"**{row['product_name']}**")
            st.caption(f"{row['category']} · {row.get('material', '')}")
            st.markdown(f"₹{int(row['price']):,}")
            if st.button("View", key=f"newarrival_{row['product_id']}", use_container_width=True):
                st.session_state["selected_product_id"] = row["product_id"]
                st.switch_page("pages/8_Product_Detail.py")
        st.divider()

if st.button("Log out"):
    log_out()
    st.switch_page("home.py")