import os
import streamlit as st

from utils.auth import require_login
from utils.data_store import (
    load_products, update_product_status, update_product_stock, delete_product,
    get_ratings_by_product, format_stars,
    has_seller_reviewed_product, add_seller_initial_review,
)

st.set_page_config(page_title="AGR Sutra — My Listings", page_icon="📦", layout="centered")
user = require_login(required_role="Seller")

st.title("📦 My Listings")

if st.button("← Back to Dashboard"):
    st.switch_page("pages/1_Seller_Dashboard.py")
if st.button("➕ Add New Product", type="primary", use_container_width=True):
    st.switch_page("pages/2_Add_Product.py")

st.divider()

products = load_products()
my_products = products[products["seller_id"] == user["user_id"]] if not products.empty else products
ratings = get_ratings_by_product()

if my_products.empty:
    st.info("You haven't listed any products yet.")
    st.stop()

tab_active, tab_inactive = st.tabs(["🟢 Active", "⚪ Inactive"])


def render_listing(row):
    col1, col2 = st.columns([1, 2])
    with col1:
        if isinstance(row.get("image_path"), str) and os.path.exists(row["image_path"]):
            st.image(row["image_path"], use_container_width=True)
    with col2:
        st.markdown(f"**{row['product_name']}**")
        st.caption(f"{row['category']} · {row.get('material', '')}")

        if not ratings.empty and row["product_id"] in ratings.index:
            avg_rating = ratings.loc[row["product_id"], "avg_rating"]
            review_count = int(ratings.loc[row["product_id"], "review_count"])
            st.caption(f"{format_stars(avg_rating)} {avg_rating} ({review_count} review{'s' if review_count != 1 else ''})")
        else:
            st.caption("☆☆☆☆☆ No reviews yet")

        st.markdown(f"₹{int(row['price']):,} · Stock: {int(row['stock'])}")
        new_stock = st.number_input(
            "Update stock", min_value=0, value=int(row["stock"]),
            key=f"stock_{row['product_id']}",
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("Save Stock", key=f"save_{row['product_id']}"):
                update_product_stock(row["product_id"], new_stock)
                st.rerun()
        with c2:
            toggle_label = "Deactivate" if row["status"] == "Active" else "Activate"
            if st.button(toggle_label, key=f"toggle_{row['product_id']}"):
                update_product_status(row["product_id"], "Inactive" if row["status"] == "Active" else "Active")
                st.rerun()
        with c3:
            if st.button("🗑️ Delete", key=f"del_{row['product_id']}"):
                delete_product(row["product_id"])
                st.rerun()

        if has_seller_reviewed_product(row["product_id"]):
            st.caption("✅ You've added your initial review for this product.")
        else:
            with st.expander("🧑‍🎨 Add your initial review for this product"):
                st.caption("Give buyers a starting point — this shows on the product page but isn't counted in the buyer rating average.")
                seller_rating = st.slider(
                    "Your rating", min_value=1, max_value=5, value=5,
                    key=f"seller_initial_rating_{row['product_id']}",
                )
                st.caption(format_stars(seller_rating))
                seller_comment = st.text_area(
                    "Say something about this product (optional)",
                    key=f"seller_initial_comment_{row['product_id']}",
                )
                if st.button("Submit Initial Review", key=f"seller_initial_submit_{row['product_id']}"):
                    review_id = add_seller_initial_review(
                        product_id=row["product_id"], seller_id=user["user_id"],
                        rating=seller_rating, comment=seller_comment,
                    )
                    if review_id:
                        st.success("Initial review added! 🙏")
                        st.rerun()
                    else:
                        st.warning("You've already added an initial review for this product.")
    st.divider()


with tab_active:
    active = my_products[my_products["status"] == "Active"]
    if active.empty:
        st.caption("No active listings.")
    for _, row in active.iloc[::-1].iterrows():
        render_listing(row)

with tab_inactive:
    inactive = my_products[my_products["status"] != "Active"]
    if inactive.empty:
        st.caption("No inactive listings.")
    for _, row in inactive.iloc[::-1].iterrows():
        render_listing(row)