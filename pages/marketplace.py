import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="AGR Sutra — Marketplace", page_icon="🛒", layout="centered")

DATA_PATH = "data/products.csv"

st.title("🛒 AGR SUTRA Marketplace")
st.divider()

if os.path.exists(DATA_PATH):
    df = pd.read_csv(DATA_PATH)
else:
    df = pd.DataFrame(columns=["product_name", "category", "material", "price", "stock", "english_desc", "image_path"])

search = st.text_input("Search products...")

categories = ["All"] + sorted(df["category"].dropna().unique().tolist()) if not df.empty else ["All"]
selected_category = st.selectbox("Category", categories)

filtered = df.copy()
if search:
    filtered = filtered[filtered["product_name"].str.contains(search, case=False, na=False)]
if selected_category != "All":
    filtered = filtered[filtered["category"] == selected_category]

st.divider()

if filtered.empty:
    st.info("No products found. Publish a product from the Add Product page first.")
else:
    for _, row in filtered.iloc[::-1].iterrows():
        col1, col2 = st.columns([1, 2])
        with col1:
            if isinstance(row.get("image_path"), str) and row["image_path"] and os.path.exists(row["image_path"]):
                st.image(row["image_path"], use_container_width=True)
            else:
                st.markdown("🧣")
        with col2:
            st.markdown(f"**{row['product_name']}**")
            st.markdown(f"₹{int(row['price']):,}")
            st.caption(f"{row['category']} · {row.get('material', '')}")
            if st.button("VIEW PRODUCT", key=f"view_{row['product_name']}_{row['price']}"):
                st.write(row.get("english_desc", ""))
        st.divider()