import pandas as pd
import streamlit as st

from utils.auth import require_login
from utils.data_store import load_products, load_orders

st.set_page_config(page_title="AGR Sutra — Earnings & Analytics", page_icon="📊", layout="centered")

user = require_login(required_role="Seller")

st.title("📊 Earnings & Analytics")

if st.button("← Back to Dashboard"):
    st.switch_page("pages/1_Seller_Dashboard.py")

st.divider()

products = load_products()
orders = load_orders()

my_products = products[products["seller_id"] == user["user_id"]] if not products.empty else products
my_orders = orders[orders["seller_id"] == user["user_id"]] if not orders.empty else orders

if my_orders.empty:
    st.info("No orders yet. Your earnings and trends will appear here once buyers start ordering.")
    st.stop()

my_orders = my_orders.copy()
my_orders["created_at"] = pd.to_datetime(my_orders["created_at"], errors="coerce")
my_orders["total_amount"] = pd.to_numeric(my_orders["total_amount"], errors="coerce").fillna(0)

# -------------------- Date range filter --------------------
range_label = st.selectbox("Time range", ["Last 7 days", "Last 30 days", "Last 90 days", "All time"], index=1)
days_map = {"Last 7 days": 7, "Last 30 days": 30, "Last 90 days": 90, "All time": None}
days = days_map[range_label]

if days is not None:
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=days)
    filtered_orders = my_orders[my_orders["created_at"] >= cutoff]
else:
    filtered_orders = my_orders

st.divider()

# -------------------- Top metrics --------------------
completed = filtered_orders[filtered_orders["status"] == "Completed"]
pending = filtered_orders[filtered_orders["status"] != "Completed"]

total_earnings = int(completed["total_amount"].sum()) if not completed.empty else 0
pending_earnings = int(pending["total_amount"].sum()) if not pending.empty else 0
avg_order_value = int(filtered_orders["total_amount"].mean()) if not filtered_orders.empty else 0

col1, col2, col3 = st.columns(3)
col1.metric("Earnings (Completed)", f"₹{total_earnings:,}")
col2.metric("Pending Earnings", f"₹{pending_earnings:,}")
col3.metric("Avg Order Value", f"₹{avg_order_value:,}")

st.divider()

# -------------------- Earnings over time --------------------
st.markdown("#### 📈 Earnings Over Time")
if completed.empty:
    st.caption("No completed orders in this range yet.")
else:
    daily = (
        completed.assign(date=completed["created_at"].dt.date)
        .groupby("date")["total_amount"]
        .sum()
        .sort_index()
    )
    st.line_chart(daily)

st.divider()

# -------------------- Order status breakdown --------------------
st.markdown("#### 🧾 Order Status Breakdown")
status_counts = filtered_orders["status"].value_counts()
if status_counts.empty:
    st.caption("No orders in this range.")
else:
    st.bar_chart(status_counts)

st.divider()

# -------------------- Top products by revenue --------------------
st.markdown("#### 🏆 Top Products by Revenue")
if filtered_orders.empty:
    st.caption("No orders in this range.")
else:
    top_products = (
        filtered_orders.groupby("product_name")["total_amount"]
        .sum()
        .sort_values(ascending=False)
        .head(5)
    )
    if top_products.empty:
        st.caption("No product sales in this range.")
    else:
        st.bar_chart(top_products)

st.divider()

# -------------------- Category performance --------------------
st.markdown("#### 🗂️ Revenue by Category")
if not my_products.empty and not filtered_orders.empty:
    product_category = my_products.set_index("product_id")["category"]
    orders_with_category = filtered_orders.copy()
    orders_with_category["category"] = orders_with_category["product_id"].map(product_category)
    orders_with_category = orders_with_category.dropna(subset=["category"])

    if orders_with_category.empty:
        st.caption("Not enough data yet to break down revenue by category.")
    else:
        category_revenue = (
            orders_with_category.groupby("category")["total_amount"]
            .sum()
            .sort_values(ascending=False)
        )
        st.bar_chart(category_revenue)
else:
    st.caption("Not enough data yet to break down revenue by category.")

st.divider()

# -------------------- Low stock alert --------------------
st.markdown("#### ⚠️ Inventory Alerts")
if my_products.empty:
    st.caption("No listings yet.")
else:
    low_stock = my_products[pd.to_numeric(my_products["stock"], errors="coerce").fillna(0) <= 2]
    low_stock = low_stock[low_stock["status"] == "Active"]
    if low_stock.empty:
        st.caption("✅ All active listings are well stocked.")
    else:
        for _, row in low_stock.iterrows():
            stock_val = int(row["stock"]) if pd.notna(row["stock"]) else 0
            if stock_val <= 0:
                st.error(f"🔴 **{row['product_name']}** is out of stock.")
            else:
                st.warning(f"🟠 **{row['product_name']}** has only {stock_val} left.")