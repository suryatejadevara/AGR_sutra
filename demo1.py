import streamlit as st
from rembg import remove, new_session
from PIL import Image
import io
import base64

# -------------------- Page Config --------------------
st.set_page_config(
    page_title="Artisan AI Product Studio",
    page_icon="🧵",
    layout="centered"
)

st.title("🧵 Artisan AI Product Studio")
st.markdown("### AI-powered tool for artisans & micro-entrepreneurs")
st.caption("Upload photo → AI cleans image → Generates description → Suggests price")

st.divider()

# -------------------- 1. Image Upload & Enhancement --------------------
st.subheader("1️⃣ Upload Product Photo")

uploaded_file = st.file_uploader(
    "Take or upload a clear photo of your product",
    type=["jpg", "jpeg", "png"]
)

enhanced_image = None

if uploaded_file is not None:
    input_image = Image.open(uploaded_file).convert("RGBA")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.image(input_image, caption="Original Photo", use_container_width=True)
    
    with st.spinner("AI is removing background and enhancing image..."):
        session = new_session("u2netp")          # lighter & faster model
        output_image = remove(input_image, session=session)
        enhanced_image = output_image
    
    with col2:
        st.image(enhanced_image, caption="AI Enhanced (Background Removed)", use_container_width=True)
    
    # Download button for enhanced image
    buf = io.BytesIO()
    enhanced_image.save(buf, format="PNG")
    byte_im = buf.getvalue()
    
    st.download_button(
        label="⬇️ Download Clean Product Image",
        data=byte_im,
        file_name="enhanced_product.png",
        mime="image/png"
    )

st.divider()

# -------------------- 2. Product Description --------------------
st.subheader("2️⃣ Product Details")

col_a, col_b = st.columns(2)

with col_a:
    product_name = st.text_input("Product Name (e.g. Clay Water Pot, Handwoven Stole)")
    
with col_b:
    category = st.selectbox(
        "Category",
        ["Pottery", "Handloom / Textile", "Handicraft", "Jewelry", "Woodwork", "Other"]
    )

material = st.text_input("Main Material (e.g. Clay, Cotton, Brass, Wood)")
description_input = st.text_area(
    "Describe your product in simple words (or paste voice transcription)",
    placeholder="Example: Traditional blue pottery water pot made by hand in Jaipur..."
)

if st.button("✨ Generate Professional Description", type="primary"):
    if product_name and description_input:
        with st.spinner("AI is writing professional catalog..."):
            
            # Simple but effective template (can be replaced with real LLM later)
            english_desc = f"""Handcrafted {product_name} made using traditional techniques by skilled Indian artisans.

Material: {material if material else 'Traditional materials'}
Category: {category}

{description_input}

This authentic piece reflects the rich cultural heritage and craftsmanship of Indian artisans. Perfect for home décor, gifting, or wholesale buyers looking for genuine handmade products."""

            hindi_desc = f"""कुशल भारतीय कारीगरों द्वारा पारंपरिक तकनीकों से हाथ से बनाया गया {product_name}।

सामग्री: {material if material else 'पारंपरिक सामग्री'}
श्रेणी: {category}

{description_input}

यह प्रामाणिक उत्पाद भारतीय कारीगरों की समृद्ध सांस्कृतिक विरासत और शिल्प कौशल को दर्शाता है। घर की सजावट, उपहार या थोक खरीदारों के लिए बिल्कुल उपयुक्त।"""

            st.success("Description Generated!")
            
            st.markdown("#### 🇬🇧 English (SEO Friendly)")
            st.info(english_desc)
            
            st.markdown("#### 🇮🇳 Hindi")
            st.info(hindi_desc)
            
            # Save for later use
            st.session_state['english_desc'] = english_desc
            st.session_state['hindi_desc'] = hindi_desc
            st.session_state['product_name'] = product_name
    else:
        st.warning("Please enter Product Name and Description")

st.divider()

# -------------------- 3. Dynamic Pricing --------------------
st.subheader("3️⃣ Dynamic Pricing Assistant")

col1, col2, col3 = st.columns(3)

with col1:
    raw_cost = st.number_input("Raw Material Cost (₹)", min_value=0, value=100)

with col2:
    labor_cost = st.number_input("Labor / Time Cost (₹)", min_value=0, value=80)

with col3:
    size = st.selectbox("Size / Complexity", ["Small", "Medium", "Large / Detailed"])

# Simple pricing logic
multiplier = {
    "Small": 1.6,
    "Medium": 1.9,
    "Large / Detailed": 2.3
}

base = raw_cost + labor_cost
suggested_price = int(base * multiplier[size])

# Add category bonus
if category in ["Handloom / Textile", "Jewelry"]:
    suggested_price = int(suggested_price * 1.15)

st.metric(
    label="Recommended Selling Price",
    value=f"₹ {suggested_price}",
    delta=f"Markup: {int((suggested_price/base - 1)*100)}%" if base > 0 else None
)

st.caption("Price is calculated based on material + labor + size + category market trends.")

st.divider()

# -------------------- 4. Final Product Card --------------------
if enhanced_image is not None and 'english_desc' in st.session_state:
    st.subheader("4️⃣ Final Product Card (Ready to Share)")
    
    st.markdown(f"### {st.session_state['product_name']}")
    st.image(enhanced_image, width=300)
    
    st.markdown("**English Description:**")
    st.write(st.session_state['english_desc'])
    
    st.markdown(f"**Suggested Price:** ₹ {suggested_price}")
    
    st.success("✅ Your product is ready for digital marketplace / WhatsApp / Exhibition!")

# -------------------- Footer --------------------
st.divider()
st.caption("Prototype for Socio-Economic Upliftment of Artisans | Built with ❤️ using Streamlit + AI")