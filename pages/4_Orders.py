import streamlit as st
from utils.auth import require_login
from utils.data_store import load_orders, update_order_status, has_reviewed_order, add_buyer_review, format_stars

st.set_page_config(page_title="AGR Sutra — Orders", page_icon="🧾", layout="centered")

user = require_login(required_role="Seller")

st.title("🧾 Orders")

if st.button("← Back to Dashboard"):
    st.switch_page("pages/1_Seller_Dashboard.py")

st.divider()

orders = load_orders()
my_orders = orders[orders["seller_id"] == user["user_id"]] if not orders.empty else orders

if my_orders.empty:
    st.info("No orders yet. Once buyers purchase your products, they'll show up here.")
    st.stop()

tab_new, tab_processing, tab_completed = st.tabs(["🆕 New", "⏳ Processing", "✅ Completed"])


def render_order(row, allow_rate_buyer=False):
    st.markdown(f"**Order #{row['order_id']}**")
    st.write(f"{row['product_name']} — Qty {int(row['quantity'])}")
    st.markdown(f"₹{int(row['total_amount']):,}")
    st.caption(f"Ship to: {row.get('shipping_address', 'N/A')}")
    if row["status"] == "New":
        if st.button("Mark as Processing", key=f"proc_{row['order_id']}"):
            update_order_status(row["order_id"], "Processing")
            st.rerun()
    elif row["status"] == "Processing":
        if st.button("Mark as Completed", key=f"comp_{row['order_id']}"):
            update_order_status(row["order_id"], "Completed")
            st.rerun()

    if allow_rate_buyer:
        if has_reviewed_order(row["order_id"], "buyer"):
            st.caption("✅ You've rated this buyer.")
        else:
            with st.expander("⭐ Rate this buyer"):
                rating_value = st.slider(
                    "Buyer rating", min_value=1, max_value=5, value=5,
                    key=f"buyer_rating_{row['order_id']}",
                )
                st.caption(format_stars(rating_value))
                comment_text = st.text_area(
                    "Notes about this buyer (optional)", key=f"buyer_comment_{row['order_id']}"
                )
                if st.button("Submit Buyer Rating", key=f"submit_buyer_{row['order_id']}"):
                    review_id = add_buyer_review(
                        order_id=row["order_id"],
                        product_id=row["product_id"],
                        seller_id=user["user_id"],
                        buyer_id=row["buyer_id"],
                        rating=rating_value,
                        comment=comment_text,
                    )
                    if review_id:
                        st.success("Thanks for rating the buyer! 🙏")
                        st.rerun()
                    else:
                        st.warning("You've already rated this buyer for this order.")
    st.divider()


with tab_new:
    subset = my_orders[my_orders["status"] == "New"]
    st.caption("No new orders.") if subset.empty else [render_order(r) for _, r in subset.iloc[::-1].iterrows()]

with tab_processing:
    subset = my_orders[my_orders["status"] == "Processing"]
    st.caption("Nothing in progress.") if subset.empty else [render_order(r) for _, r in subset.iloc[::-1].iterrows()]

with tab_completed:
    subset = my_orders[my_orders["status"] == "Completed"]
    st.caption("No completed orders yet.") if subset.empty else [
        render_order(r, allow_rate_buyer=True) for _, r in subset.iloc[::-1].iterrows()
    ]