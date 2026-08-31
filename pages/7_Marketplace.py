import os
import streamlit as st
import pandas as pd

from utils.auth import require_login
from utils.data_store import load_products, get_ratings_by_product, format_stars

st.set_page_config(page_title="AGR Sutra — Marketplace", page_icon="🛒", layout="centered")

user = require_login(required_role="Buyer")

st.title("🛒 Marketplace")

col_back, col_cart = st.columns(2)
with col_back:
    if st.button("← Back to Home", use_container_width=True):
        st.switch_page("pages/6_Buyer_Home.py")
with col_cart:
    cart = st.session_state.get("cart", {})
    cart_count = sum(cart.values()) if cart else 0
    if st.button(f"🛍️ Cart ({cart_count})", use_container_width=True):
        st.switch_page("pages/9_Cart_Checkout.py")

st.divider()

products = load_products()
df = products[products["status"] == "Active"] if not products.empty else products
ratings = get_ratings_by_product()

# -------------------- Filters --------------------
search = st.text_input("Search products...")

categories = ["All"] + sorted(df["category"].dropna().unique().tolist()) if not df.empty else ["All"]
preselected_category = st.session_state.pop("marketplace_category_filter", None)
default_index = categories.index(preselected_category) if preselected_category in categories else 0
selected_category = st.selectbox("Category", categories, index=default_index)

sort_option = st.selectbox(
    "Sort by", ["Newest First", "Price: Low to High", "Price: High to Low", "Highest Rated"]
)

filtered = df.copy()
if search:
    filtered = filtered[filtered["product_name"].str.contains(search, case=False, na=False)]
if selected_category != "All":
    filtered = filtered[filtered["category"] == selected_category]

if not filtered.empty:
    filtered["price"] = pd.to_numeric(filtered["price"], errors="coerce").fillna(0)
    if sort_option == "Price: Low to High":
        filtered = filtered.sort_values("price", ascending=True)
    elif sort_option == "Price: High to Low":
        filtered = filtered.sort_values("price", ascending=False)
    elif sort_option == "Highest Rated":
        filtered = filtered.copy()
        filtered["_avg_rating"] = filtered["product_id"].map(
            ratings["avg_rating"] if not ratings.empty else {}
        ).fillna(0)
        filtered = filtered.sort_values("_avg_rating", ascending=False)
    else:
        filtered = filtered.iloc[::-1]  # newest first (most recently added)

st.divider()

if filtered.empty:
    st.info("No products found. Try a different search or category.")
else:
    st.caption(f"{len(filtered)} product(s) found")
    for idx, row in filtered.iterrows():
        col1, col2 = st.columns([1, 2])
        with col1:
            if isinstance(row.get("image_path"), str) and row["image_path"] and os.path.exists(row["image_path"]):
                st.image(row["image_path"], use_container_width=True)
            else:
                st.markdown("🧣")
        with col2:
            st.markdown(f"**{row['product_name']}**")
            st.markdown(f"₹{int(row['price']):,}")

            if not ratings.empty and row["product_id"] in ratings.index:
                avg_rating = ratings.loc[row["product_id"], "avg_rating"]
                review_count = int(ratings.loc[row["product_id"], "review_count"])
                st.caption(f"{format_stars(avg_rating)} {avg_rating} ({review_count} review{'s' if review_count != 1 else ''})")
            else:
                st.caption("☆☆☆☆☆ No reviews yet")

            st.caption(f"{row['category']} · {row.get('material', '')}")

            stock = row.get("stock")
            in_stock = False
            if pd.notna(stock):
                stock = int(stock)
                if stock <= 0:
                    st.caption("🔴 Out of stock")
                elif stock <= 2:
                    st.caption(f"🟠 Only {stock} left")
                    in_stock = True
                else:
                    st.caption(f"🟢 {stock} available")
                    in_stock = True

            language = row.get("language")
            if isinstance(language, str) and language != "Not detected":
                st.caption(f"🌐 Listed in {language}")

            c1, c2 = st.columns(2)
            with c1:
                # Keyed on the DataFrame row index (idx), not name+price, so two
                # products that happen to share a name and price can't collide.
                if st.button("View Details", key=f"view_{idx}", use_container_width=True):
                    st.session_state["selected_product_id"] = row["product_id"]
                    st.switch_page("pages/8_Product_Detail.py")
            with c2:
                if st.button("🛍️ Add to Cart", key=f"addcart_{idx}", use_container_width=True, disabled=not in_stock):
                    cart = st.session_state.get("cart", {})
                    cart[row["product_id"]] = cart.get(row["product_id"], 0) + 1
                    st.session_state["cart"] = cart
                    st.toast(f"Added {row['product_name']} to cart")
        st.divider()