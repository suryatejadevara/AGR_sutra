import io
import hashlib

import streamlit as st
from PIL import Image

from utils.auth import require_login
from utils.data_store import save_product
from utils.ai_engine import (
    CATEGORIES, FALLBACK_CATEGORY, LANGUAGES, DEFAULT_LANGUAGE_LABEL,
    is_gemini_available, transcribe_audio_gemini, transcribe_offline,
    generate_ai_description, remove_background, resize_for_processing,
    extract_product_name, extract_material, predict_price,
)

st.set_page_config(page_title="AGR Sutra — Add Product", page_icon="📸", layout="centered")
user = require_login(required_role="Seller")

st.title("📸 AI Camera Studio")
st.caption("Upload photo → AI cleans image → Describe by voice → AI writes copy → Get a suggested price → Publish")

if st.button("← Back to Dashboard"):
    st.switch_page("pages/1_Seller_Dashboard.py")

st.divider()

# -------------------- 1. Photo --------------------
st.subheader("1️⃣ Upload Product Photo")
uploaded_file = st.file_uploader("Take or upload a clear photo of your product", type=["jpg", "jpeg", "png"])

enhanced_image = None

if uploaded_file is not None:
    file_bytes = uploaded_file.getvalue()
    file_hash = hashlib.md5(file_bytes).hexdigest()

    if st.session_state.get("processed_file_hash") != file_hash:
        input_image = Image.open(io.BytesIO(file_bytes)).convert("RGBA")
        input_image = resize_for_processing(input_image)
        with st.spinner("AI is removing background and enhancing image..."):
            enhanced_image = remove_background(input_image)
        st.session_state["processed_file_hash"] = file_hash
        st.session_state["input_image"] = input_image
        st.session_state["enhanced_image"] = enhanced_image
    else:
        input_image = st.session_state["input_image"]
        enhanced_image = st.session_state["enhanced_image"]

    col1, col2 = st.columns(2)
    with col1:
        st.image(input_image, caption="Original Photo", use_container_width=True)
    with col2:
        st.image(enhanced_image, caption="AI Enhanced (Background Removed)", use_container_width=True)

    default_index = CATEGORIES.index(st.session_state.get("category", FALLBACK_CATEGORY)) \
        if st.session_state.get("category", FALLBACK_CATEGORY) in CATEGORIES else CATEGORIES.index(FALLBACK_CATEGORY)
    category = st.selectbox("Select Product Category", CATEGORIES, index=default_index)
    st.session_state["category"] = category

    buf = io.BytesIO()
    enhanced_image.save(buf, format="PNG")
    st.download_button("⬇️ Download Clean Product Image", data=buf.getvalue(),
                        file_name="enhanced_product.png", mime="image/png", use_container_width=True)

if enhanced_image is None:
    st.error("📸 A product photo is required. Please upload a photo above before continuing.")
    st.stop()

st.divider()

# -------------------- 2. Describe --------------------
st.subheader("2️⃣ Describe Your Product")
st.markdown("🎤 Describe what it is, what it's made of, and how it's made — the AI will do the rest.")

gemini_available = is_gemini_available()
if gemini_available:
    st.caption("🌐 Speak in any language — the AI will automatically detect it. "
               "(The picker below is only used if auto-detect fails on a recording.)")
else:
    st.warning("⚠️ AI auto-detect isn't configured — please select your language manually.")

st.markdown("**🌐 अपनी भाषा चुनें / Select your language**")
selected_label = st.pills(
    "Voice language", options=list(LANGUAGES.keys()),
    default=st.session_state.get("language_label", DEFAULT_LANGUAGE_LABEL),
    label_visibility="collapsed",
)
if selected_label is None:
    selected_label = st.session_state.get("language_label", DEFAULT_LANGUAGE_LABEL)
st.session_state["language_label"] = selected_label
selected_lang_code, selected_lang_name = LANGUAGES[selected_label]

audio_value = st.audio_input("Record your voice description")

if audio_value is not None:
    audio_bytes = audio_value.getvalue()
    cache_key = hashlib.md5(audio_bytes).hexdigest() + f":{selected_lang_code}"

    if st.session_state.get("audio_cache_key") != cache_key:
        transcript, detected_language = None, None

        if gemini_available:
            with st.spinner("🌐 Detecting language and transcribing..."):
                result = transcribe_audio_gemini(audio_bytes, audio_value.type or "audio/wav")
            if result:
                transcript, detected_language = result
            else:
                st.info(f"Auto-detect had trouble with that recording — trying standard transcription in {selected_lang_name}.")

        if transcript is None:
            with st.spinner("Transcribing your voice..."):
                transcript, detected_language, err = transcribe_offline(audio_value, selected_lang_code, selected_lang_name)
            if err:
                st.warning(err) if "re-record" in err else st.error(err)

        if transcript:
            st.success(f"Heard ({detected_language}): \"{transcript}\"")
        else:
            st.warning("Couldn't transcribe that clearly — please re-record and try again.")

        st.session_state["audio_cache_key"] = cache_key
        st.session_state["spoken_text"] = transcript or ""
        st.session_state["detected_language"] = detected_language
    else:
        cached_transcript = st.session_state.get("spoken_text", "")
        cached_language = st.session_state.get("detected_language")
        if cached_transcript:
            st.success(f"Heard ({cached_language}): \"{cached_transcript}\"")

spoken_text = st.session_state.get("spoken_text", "")
typed_desc = st.text_input("...or type a quick description instead (if the mic isn't working)")

if st.button("✨ Generate Professional Description", type="primary", use_container_width=True):
    raw_input = spoken_text or typed_desc
    if raw_input:
        with st.spinner("AI is writing professional catalog copy..."):
            category = st.session_state.get("category", FALLBACK_CATEGORY)
            material = extract_material(raw_input)
            language_for_ai = st.session_state.get("detected_language", "English") if spoken_text else "English"

            ai_result = generate_ai_description(raw_input, category, material, language_for_ai)

            if ai_result:
                ai_name, english_desc, hindi_desc = ai_result
                product_name = ai_name or extract_product_name(raw_input)
            else:
                st.info("AI writing service unavailable right now — using a basic template instead.")
                product_name = extract_product_name(raw_input)
                english_desc = (
                    f"Handcrafted {product_name} made using traditional techniques by skilled Indian artisans.\n\n"
                    f"Material: {material}\nCategory: {category}\n\n{raw_input}\n\n"
                    "This authentic piece reflects the rich cultural heritage and craftsmanship of Indian artisans. "
                    "Perfect for home décor, gifting, or wholesale buyers looking for genuine handmade products."
                )
                hindi_desc = (
                    f"कुशल भारतीय कारीगरों द्वारा पारंपरिक तकनीकों से हाथ से बनाया गया {product_name}।\n\n"
                    f"सामग्री: {material}\nश्रेणी: {category}\n\n{raw_input}\n\n"
                    "यह प्रामाणिक उत्पाद भारतीय कारीगरों की समृद्ध सांस्कृतिक विरासत और शिल्प कौशल को दर्शाता है। "
                    "घर की सजावट, उपहार या थोक खरीदारों के लिए बिल्कुल उपयुक्त।"
                )

            st.success("Description Generated!")
            st.markdown("#### 🇬🇧 English (SEO Friendly)")
            st.info(english_desc)
            st.markdown("#### 🇮🇳 Hindi")
            st.info(hindi_desc)

            st.session_state["english_desc"] = english_desc
            st.session_state["hindi_desc"] = hindi_desc
            st.session_state["product_name"] = product_name
            st.session_state["material"] = material
    else:
        st.warning("Please record a voice description or type one first.")

st.divider()

# -------------------- 3. Pricing --------------------
st.subheader("3️⃣ Dynamic Pricing Assistant")

col1, col2, col3 = st.columns(3)
with col1:
    raw_cost = st.number_input("Raw Material Cost (₹)", min_value=0, value=100)
with col2:
    labor_cost = st.number_input("Labor / Time Cost (₹)", min_value=0, value=80)
with col3:
    size = st.selectbox("Size / Complexity", ["Small", "Medium", "Large / Detailed"])

current_category = st.session_state.get("category", FALLBACK_CATEGORY)
base = raw_cost + labor_cost
suggested_price = predict_price(current_category, size, raw_cost, labor_cost)

st.metric(
    label="Recommended Selling Price", value=f"₹ {suggested_price}",
    delta=f"Markup: {int((suggested_price / base - 1) * 100)}%" if base > 0 else None,
)
st.caption("🤖 Price suggested by a regression model trained on category, material, size, "
           "and cost patterns — improves as real listings are published.")

st.divider()

# -------------------- 4. Publish --------------------
if enhanced_image is not None and "english_desc" in st.session_state:
    st.subheader("4️⃣ Final Product Card (Ready to Share)")

    st.markdown(f"### {st.session_state['product_name']}")
    st.image(enhanced_image, width=300)
    st.markdown(f"**Category:** {current_category}")
    st.markdown(f"**Material:** {st.session_state.get('material', 'Traditional materials')}")
    st.markdown("**English Description:**")
    st.write(st.session_state["english_desc"])
    st.markdown(f"**Suggested Price:** ₹ {suggested_price}")

    stock_qty = st.number_input("Available Quantity", min_value=1, value=5)

    if st.button("🚀 PUBLISH PRODUCT", type="primary", use_container_width=True):
        save_product(
            seller_id=user["user_id"],
            product_name=st.session_state["product_name"],
            category=current_category,
            material=st.session_state.get("material", "Traditional materials"),
            price=suggested_price,
            stock=stock_qty,
            english_desc=st.session_state["english_desc"],
            hindi_desc=st.session_state.get("hindi_desc", ""),
            image=enhanced_image,
            language=st.session_state.get("detected_language"),
        )
        st.success("✅ PRODUCT PUBLISHED — your product is now in the AGR Sutra Marketplace.")

        for key in (
            "processed_file_hash", "input_image", "enhanced_image", "category",
            "audio_cache_key", "spoken_text", "detected_language",
            "english_desc", "hindi_desc", "product_name", "material",
        ):
            st.session_state.pop(key, None)

        st.switch_page("pages/3_My_Listings.py")