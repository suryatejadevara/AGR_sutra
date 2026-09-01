import os
import pandas as pd
import streamlit as st

from utils.auth import require_login
from utils.data_store import (
    get_product, get_product_rating, get_reviews_for_product,
    get_reviewable_product_orders, add_product_review,
    get_reviewable_seller_orders, add_seller_review,
    get_seller_rating, format_stars, get_user,
)
from utils.ai_engine import translate_text, language_display_name
from utils.geo import valid_coord

st.set_page_config(page_title="AGR Sutra — Product Detail", page_icon="🧵", layout="centered")

user = require_login(required_role="Buyer")

if st.button("← Back to Marketplace"):
    st.switch_page("pages/7_Marketplace.py")

st.divider()

product_id = st.session_state.get("selected_product_id")
product = get_product(product_id) if product_id else None

if product is None:
    st.warning("No product selected. Please choose a product from the Marketplace.")
    if st.button("Go to Marketplace", type="primary"):
        st.switch_page("pages/7_Marketplace.py")
    st.stop()

if product.get("status") != "Active":
    st.warning("This product is no longer available.")
    if st.button("Browse other products", type="primary"):
        st.switch_page("pages/7_Marketplace.py")
    st.stop()

# -------------------- Image --------------------
image_path = product.get("image_path")
if isinstance(image_path, str) and image_path and os.path.exists(image_path):
    st.image(image_path, use_container_width=True)
else:
    st.markdown("### 🧣")

# -------------------- Title & price --------------------
st.markdown(f"## {product['product_name']}")
st.markdown(f"### ₹{int(product['price']):,}")

avg_rating, review_count = get_product_rating(product_id)
if review_count > 0:
    st.markdown(f"{format_stars(avg_rating)} **{avg_rating}** out of 5 · {review_count} review{'s' if review_count != 1 else ''}")
else:
    st.caption("☆☆☆☆☆ No reviews yet")

seller_avg, seller_review_count = get_seller_rating(product["seller_id"])
if seller_review_count > 0:
    st.caption(f"🏪 Seller rating: {format_stars(seller_avg)} {seller_avg} ({seller_review_count} review{'s' if seller_review_count != 1 else ''})")
else:
    st.caption("🏪 Seller rating: ☆☆☆☆☆ No reviews yet")

# -------------------- Seller Details --------------------
# expanded=True so location (and the rest of the seller's details) is
# always visible on the page instead of hidden behind a click -- buyers
# should see who and where they're buying from without having to know
# to open a collapsed section.
seller = get_user(product["seller_id"])
if seller:
    with st.expander("🧑‍🎨 Seller Details", expanded=True):
        st.markdown(f"**Name:** {seller.get('full_name', 'N/A')}")
        if seller.get("phone"):
            st.markdown(f"**Phone:** {seller['phone']}")

        st.markdown("**📍 Location**")
        lat = valid_coord(seller.get("latitude"))
        lon = valid_coord(seller.get("longitude"))
        if lat is not None and lon is not None:
            st.caption(f"{lat:.5f}, {lon:.5f}")
            st.map(pd.DataFrame({"lat": [lat], "lon": [lon]}))
        elif seller.get("pin_code"):
            st.caption(f"Pin code: {seller['pin_code']}")
        else:
            st.caption("This seller hasn't shared a location yet.")

st.divider()

stock = product.get("stock")
try:
    stock = int(stock)
except (TypeError, ValueError):
    stock = 0

if stock <= 0:
    st.error("🔴 Out of stock")
elif stock <= 2:
    st.warning(f"🟠 Only {stock} left — order soon!")
else:
    st.success(f"🟢 {stock} available")

st.caption(f"{product['category']} · {product.get('material', 'Traditional materials')}")

language = product.get("language")
if isinstance(language, str) and language != "Not detected":
    st.caption(f"🌐 Listed in {language}")

st.divider()

# -------------------- Descriptions --------------------
preferred_label = user.get("language", "English")
preferred_name = language_display_name(preferred_label)
show_preferred_tab = preferred_label not in ("English",) and preferred_name.lower() != "hindi"

if show_preferred_tab:
    tab_en, tab_hi, tab_pref = st.tabs(["🇬🇧 English", "🇮🇳 हिंदी", f"🌐 {preferred_name}"])
else:
    tab_en, tab_hi = st.tabs(["🇬🇧 English", "🇮🇳 हिंदी"])
    tab_pref = None

with tab_en:
    st.write(product.get("english_desc", "No description available."))
with tab_hi:
    hindi_desc = product.get("hindi_desc", "")
    st.write(hindi_desc if hindi_desc else "हिंदी विवरण उपलब्ध नहीं है।")

if tab_pref is not None:
    with tab_pref:
        cache_key = f"translated_desc_{product_id}_{preferred_label}"
        if cache_key not in st.session_state:
            with st.spinner(f"Translating into {preferred_name}..."):
                st.session_state[cache_key] = translate_text(
                    product.get("english_desc", ""), preferred_name
                )
        translated = st.session_state[cache_key]

        if translated:
            st.write(translated)
        else:
            st.info(f"Automatic translation into {preferred_name} isn't available right now — showing English instead.")
            st.write(product.get("english_desc", "No description available."))

st.divider()

# -------------------- Purchase actions --------------------
if stock > 0:
    quantity = st.number_input("Quantity", min_value=1, max_value=stock, value=1)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🛍️ Add to Cart", use_container_width=True):
            cart = st.session_state.get("cart", {})
            cart[product["product_id"]] = cart.get(product["product_id"], 0) + quantity
            st.session_state["cart"] = cart
            st.toast(f"Added {quantity} × {product['product_name']} to cart")
    with c2:
        if st.button("⚡ Buy Now", type="primary", use_container_width=True):
            st.session_state["buy_now_product_id"] = product["product_id"]
            st.session_state["buy_now_quantity"] = quantity
            st.switch_page("pages/9_Cart_Checkout.py")
else:
    st.button("🛍️ Add to Cart", use_container_width=True, disabled=True)
    st.caption("This product is currently out of stock. Check back later.")

st.divider()

# -------------------- Rate the product --------------------
st.markdown("#### 💬 Ratings & Reviews")

reviewable_orders = get_reviewable_product_orders(user["user_id"], product_id)

if reviewable_orders:
    with st.expander("⭐ Rate this product", expanded=True):
        order_to_review = reviewable_orders[0]
        if len(reviewable_orders) > 1:
            st.caption(f"You have {len(reviewable_orders)} completed orders for this product waiting for a review.")

        rating_value = st.slider("Your rating", min_value=1, max_value=5, value=5, key="product_review_rating")
        st.caption(format_stars(rating_value))
        comment_text = st.text_area("Share your experience (optional)", key="product_review_comment")

        if st.button("Submit Product Review", type="primary", use_container_width=True):
            review_id = add_product_review(
                order_id=order_to_review["order_id"],
                product_id=product_id,
                seller_id=product["seller_id"],
                buyer_id=user["user_id"],
                rating=rating_value,
                comment=comment_text,
            )
            if review_id:
                st.success("Thanks for your review! 🙏")
                st.rerun()
            else:
                st.warning("That order has already been reviewed.")

reviews_df = get_reviews_for_product(product_id)

if reviews_df.empty:
    st.caption("No reviews yet — be the first to share your experience once your order is delivered.")
else:
    for _, review in reviews_df.iterrows():
        stars = format_stars(review["rating"])
        badge = "🧑‍🎨 Seller's Review" if review["review_type"] == "seller_initial" else "🛒 Buyer Review"
        st.markdown(f"{stars} **{int(review['rating'])}/5** · {badge}")
        if isinstance(review.get("comment"), str) and review["comment"].strip():
            st.write(review["comment"])
        if pd.notna(review["created_at"]):
            st.caption(review["created_at"].strftime("%d %b %Y"))
        st.divider()

# -------------------- Rate the seller --------------------
st.markdown("#### 🏪 Rate This Seller")

reviewable_seller_orders = get_reviewable_seller_orders(user["user_id"], product["seller_id"])

if reviewable_seller_orders:
    with st.expander("⭐ Rate the seller"):
        seller_order_to_review = reviewable_seller_orders[0]
        if len(reviewable_seller_orders) > 1:
            st.caption(f"You have {len(reviewable_seller_orders)} completed orders with this seller waiting for a rating.")

        seller_rating_value = st.slider("Seller rating", min_value=1, max_value=5, value=5, key="seller_review_rating")
        st.caption(format_stars(seller_rating_value))
        seller_comment_text = st.text_area("How was your experience with this seller? (optional)", key="seller_review_comment")

        if st.button("Submit Seller Review", type="primary", use_container_width=True):
            review_id = add_seller_review(
                order_id=seller_order_to_review["order_id"],
                product_id=seller_order_to_review["product_id"],
                seller_id=product["seller_id"],
                buyer_id=user["user_id"],
                rating=seller_rating_value,
                comment=seller_comment_text,
            )
            if review_id:
                st.success("Thanks for rating the seller! 🙏")
                st.rerun()
            else:
                st.warning("You've already rated this seller for that order.")
elif seller_review_count == 0:
    st.caption("Complete an order with this seller to leave them a rating.")