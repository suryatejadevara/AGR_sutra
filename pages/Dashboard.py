import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="AGR Sutra — Dashboard", page_icon="🧵", layout="centered")

DATA_PATH = "data/products.csv"

st.title("🧵 AGR SUTRA")
st.markdown("### Your AI Business Manager")
st.divider()

st.markdown("#### Namaste 👋")

# Load products, or start empty if the file/columns don't exist yet
if os.path.exists(DATA_PATH):
    df = pd.read_csv(DATA_PATH)
else:
    df = pd.DataFrame(columns=["product_name", "category", "material", "price", "stock", "english_desc", "image_path"])

col1, col2 = st.columns(2)
with col1:
    st.metric("Products", len(df))
with col2:
    total_revenue = int((df["price"] * (df.get("sold", 0) if "sold" in df.columns else 0)).sum()) if not df.empty else 0
    # No real sales tracking yet — show potential inventory value instead, labeled honestly
    inventory_value = int(df["price"].sum()) if not df.empty else 0
    st.metric("Inventory Value", f"₹{inventory_value:,}")

st.divider()

if st.button("➕ ADD NEW PRODUCT", type="primary", use_container_width=True):
    st.switch_page("app.py")

st.divider()
st.markdown("#### Recent Products")

if df.empty:
    st.info("No products yet. Add your first product to see it here.")
else:
    recent = df.tail(5).iloc[::-1]  # most recently added first
    for _, row in recent.iterrows():
        c1, c2 = st.columns([3, 1])
        with c1:
            st.markdown(f"**{row['product_name']}**  \n*{row['category']}*")
        with c2:
            st.markdown(f"₹{int(row['price']):,}")
        st.divider()