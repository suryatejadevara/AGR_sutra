import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="AGR Sutra — Dashboard", page_icon="🧵", layout="centered")

DATA_PATH = "data/products.csv"
EXPECTED_COLUMNS = ["product_name", "category", "material", "language", "price", "stock", "english_desc", "image_path"]

st.title("🧵 AGR SUTRA")
st.markdown("### Your AI Business Manager")
st.divider()

st.markdown("#### Namaste 👋")

# Load products, or start empty if the file/columns don't exist yet
if os.path.exists(DATA_PATH):
    try:
        df = pd.read_csv(DATA_PATH)
    except Exception:
        st.error("⚠️ Couldn't read your product data — the file may be damaged. Add a new product to start fresh.")
        df = pd.DataFrame(columns=EXPECTED_COLUMNS)
else:
    df = pd.DataFrame(columns=EXPECTED_COLUMNS)

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Products", len(df))
with col2:
    # No real sales tracking yet — show potential inventory value instead, labeled honestly
    inventory_value = int(df["price"].sum()) if not df.empty else 0
    st.metric("Inventory Value", f"₹{inventory_value:,}")
with col3:
    if not df.empty and "language" in df.columns:
        languages_used = df["language"].replace("Not detected", pd.NA).dropna().nunique()
    else:
        languages_used = 0
    st.metric("Languages Used", languages_used)

st.divider()

if st.button("➕ ADD NEW PRODUCT", type="primary", use_container_width=True):
    st.session_state['selling_started'] = True
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
            language = row.get('language')
            language_tag = f" · 🌐 {language}" if isinstance(language, str) and language != "Not detected" else ""
            st.markdown(f"**{row['product_name']}**  \n*{row['category']}*{language_tag}")
        with c2:
            st.markdown(f"₹{int(row['price']):,}")
        st.divider()