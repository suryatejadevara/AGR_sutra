import streamlit as st

from utils.auth import require_login, log_out
from utils.data_store import load_products, load_orders, get_seller_rating, format_stars

st.set_page_config(page_title="AGR Sutra — Seller Dashboard", page_icon="🏠", layout="centered")
user = require_login(required_role="Seller")

st.title(f"Namaste, {user['full_name'].split()[0]}! 👋")
st.caption("Manage your business")

products = load_products()
orders = load_orders()
my_products = products[products["seller_id"] == user["user_id"]] if not products.empty else products
my_orders = orders[orders["seller_id"] == user["user_id"]] if not orders.empty else orders

total_earnings = 0
if not my_orders.empty:
    completed = my_orders[my_orders["status"] == "Completed"]
    total_earnings = int(completed["total_amount"].sum()) if not completed.empty else 0

avg_rating, review_count = get_seller_rating(user["user_id"])

col1, col2, col3 = st.columns(3)
col1.metric("Total Listings", len(my_products))
col2.metric("Total Orders", len(my_orders))
col3.metric("Total Earnings", f"₹{total_earnings:,}")

if review_count > 0:
    st.markdown(f"#### {format_stars(avg_rating)} {avg_rating} store rating · {review_count} review{'s' if review_count != 1 else ''}")
else:
    st.caption("☆☆☆☆☆ No reviews yet — ratings will appear here once buyers review your products.")

st.divider()
st.markdown("#### Quick Actions")
c1, c2 = st.columns(2)
with c1:
    if st.button("➕ Add Product", type="primary", use_container_width=True):
        st.switch_page("pages/2_Add_Product.py")
    if st.button("📦 My Listings", use_container_width=True):
        st.switch_page("pages/3_My_Listings.py")
with c2:
    if st.button("🧾 Orders", use_container_width=True):
        st.switch_page("pages/4_Orders.py")
    if st.button("📊 Earnings & Analytics", use_container_width=True):
        st.switch_page("pages/5_Earnings_Analytics.py")

st.divider()

if not my_orders.empty:
    st.markdown("#### Recent Orders")
    for _, row in my_orders.sort_values("created_at", ascending=False).head(5).iterrows():
        c1, c2, c3 = st.columns([2, 1, 1])
        c1.write(f"**{row['product_name']}**")
        c2.write(f"₹{int(row['total_amount']):,}")
        c3.caption(row["status"])
    st.divider()

if st.button("Log out"):
    log_out()
    st.switch_page("home.py")