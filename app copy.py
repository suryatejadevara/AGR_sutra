import streamlit as st
from rembg import remove, new_session
from PIL import Image
import speech_recognition as sr
import io
import re
import hashlib
import json
import google.generativeai as genai

# -------------------- Gemini Setup --------------------
# Store your key in .streamlit/secrets.toml as:
#   GEMINI_API_KEY = "your-key-here"
# Never hardcode API keys directly in the script.
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")


@st.cache_resource(show_spinner=False)
def get_gemini_model():
    """Configures and caches the Gemini model once per server process.
    Returns None if no API key is configured, so callers can fall back gracefully."""
    if not GEMINI_API_KEY:
        return None
    genai.configure(api_key=GEMINI_API_KEY)
    return genai.GenerativeModel("gemini-2.0-flash")


def generate_ai_description(raw_text: str, category: str, material: str):
    """Calls Gemini to turn a rough description into a product name plus
    English and Hindi e-commerce copy. Returns (name, english, hindi) on
    success, or None if the API isn't configured or the call/parse fails —
    callers should fall back to the template-based generator in that case."""
    model = get_gemini_model()
    if model is None:
        return None

    prompt = f"""You are helping an Indian artisan write an e-commerce product listing.

Rough description from the artisan: "{raw_text}"
Category: {category}
Material: {material}

Write:
1. A short, catchy product name (max 6 words)
2. A professional, SEO-friendly product description in English
3. A natural Hindi translation of that same description

Respond with ONLY valid JSON, no markdown code fences, no extra text, in exactly this shape:
{{"product_name": "...", "english": "...", "hindi": "..."}}"""

    try:
        response = model.generate_content(prompt)
        cleaned = response.text.strip()
        cleaned = re.sub(r"^```(json)?|```$", "", cleaned, flags=re.MULTILINE).strip()
        data = json.loads(cleaned)
        name = data.get("product_name")
        english = data.get("english")
        hindi = data.get("hindi")
        if english and hindi:
            return name, english, hindi
        return None
    except Exception:
        return None

# -------------------- Page Config --------------------
st.set_page_config(
    page_title="Artisan AI Product Studio",
    page_icon="🧵",
    layout="centered"
)

st.title("🧵 Artisan AI Product Studio")
st.markdown("### AI-powered tool for artisans & micro-entrepreneurs")
st.caption("Upload photo → AI cleans image → Choose category → Speak about your product → "
           "AI writes a professional description → Suggests price")

st.divider()

# -------------------- Categories --------------------
CATEGORIES = ["Pottery", "Handloom / Textile", "Handicraft", "Jewelry", "Woodwork", "Other"]
FALLBACK_CATEGORY = "Handicraft"

# Common materials to listen for in the spoken description
MATERIAL_KEYWORDS = [
    "clay", "terracotta", "cotton", "silk", "wool", "jute", "wood", "bamboo",
    "brass", "copper", "bronze", "silver", "gold", "leather", "stone", "glass",
    "ceramic", "iron", "cane", "wax", "paper"
]

# Cap the working image size — full-resolution phone photos (12MP+) make
# background removal much slower for no visible catalog benefit.
MAX_DIM = 1000


def resize_for_processing(image: Image.Image, max_dim: int = MAX_DIM) -> Image.Image:
    """Downscales an image so its longest side is at most max_dim, preserving aspect ratio.
    Leaves small images untouched."""
    width, height = image.size
    if max(width, height) <= max_dim:
        return image
    scale = max_dim / max(width, height)
    new_size = (int(width * scale), int(height * scale))
    return image.resize(new_size, Image.LANCZOS)


@st.cache_resource(show_spinner=False)
def get_rembg_session():
    """Loads the background-removal model once per server process and reuses it.
    Without this, Streamlit's rerun-on-every-interaction behavior reloads the
    model from disk on every button click / slider move — the single biggest
    slowdown in this app."""
    return new_session("u2netp")


def extract_product_name(text: str) -> str:
    """Pulls a short title out of the spoken description (first clause, up to ~6 words)."""
    if not text:
        return "Handcrafted Product"
    first_clause = re.split(r"[.,;]", text.strip())[0]
    words = first_clause.split()[:6]
    name = " ".join(words).strip()
    return name.title() if name else "Handcrafted Product"


def extract_material(text: str) -> str:
    """Looks for a known material keyword in the spoken description."""
    if not text:
        return "Traditional materials"
    lowered = text.lower()
    for keyword in MATERIAL_KEYWORDS:
        if keyword in lowered:
            return keyword.title()
    return "Traditional materials"


# -------------------- 1. Image Upload & Background Removal --------------------
st.subheader("1️⃣ Upload Product Photo")

uploaded_file = st.file_uploader(
    "Take or upload a clear photo of your product",
    type=["jpg", "jpeg", "png"]
)

enhanced_image = None

if uploaded_file is not None:
    # Hash the upload so we can tell whether this is a NEW photo or just a
    # Streamlit rerun triggered by some other widget (price slider, etc).
    file_bytes = uploaded_file.getvalue()
    file_hash = hashlib.md5(file_bytes).hexdigest()

    if st.session_state.get('processed_file_hash') != file_hash:
        # New photo — run the (slow) background removal once and cache the result.
        input_image = Image.open(io.BytesIO(file_bytes)).convert("RGBA")
        input_image = resize_for_processing(input_image)

        with st.spinner("AI is removing background and enhancing image..."):
            enhanced_image = remove(input_image, session=get_rembg_session())

        st.session_state['processed_file_hash'] = file_hash
        st.session_state['input_image'] = input_image
        st.session_state['enhanced_image'] = enhanced_image
    else:
        # Same photo as last rerun — reuse cached results, skip AI calls entirely.
        input_image = st.session_state['input_image']
        enhanced_image = st.session_state['enhanced_image']

    col1, col2 = st.columns(2)

    with col1:
        st.image(input_image, caption="Original Photo", use_container_width=True)

    with col2:
        st.image(enhanced_image, caption="AI Enhanced (Background Removed)", use_container_width=True)

    # Manual category selection (replaces automatic detection)
    default_index = CATEGORIES.index(st.session_state.get('category', FALLBACK_CATEGORY)) \
        if st.session_state.get('category', FALLBACK_CATEGORY) in CATEGORIES else CATEGORIES.index(FALLBACK_CATEGORY)
    category = st.selectbox("Select Product Category", CATEGORIES, index=default_index)
    st.session_state['category'] = category

    # Download button for enhanced image
    buf = io.BytesIO()
    enhanced_image.save(buf, format="PNG")
    st.download_button(
        label="⬇️ Download Clean Product Image",
        data=buf.getvalue(),
        file_name="enhanced_product.png",
        mime="image/png"
    )

st.divider()

# -------------------- 2. Speak About Your Product --------------------
st.subheader("2️⃣ Speak About Your Product")
st.markdown("🎤 Describe what it is, what it's made of, and how it's made — the AI will do the rest.")

audio_value = st.audio_input("Record your voice description")

spoken_text = ""
if audio_value is not None:
    recognizer = sr.Recognizer()
    with st.spinner("Transcribing your voice..."):
        try:
            with sr.AudioFile(audio_value) as source:
                audio_data = recognizer.record(source)
                spoken_text = recognizer.recognize_google(audio_data)
            st.success(f"Heard: \"{spoken_text}\"")
            st.session_state['spoken_text'] = spoken_text
        except Exception:
            st.warning("Couldn't transcribe that clearly — please re-record and try again.")

spoken_text = st.session_state.get('spoken_text', spoken_text)

typed_desc = st.text_input("...or type a quick description instead (if the mic isn't working)")

if st.button("✨ Generate Professional Description", type="primary"):
    raw_input = spoken_text or typed_desc

    if raw_input:
        with st.spinner("AI is writing professional catalog copy..."):

            category = st.session_state.get('category', FALLBACK_CATEGORY)
            material = extract_material(raw_input)

            ai_result = generate_ai_description(raw_input, category, material)

            if ai_result:
                ai_name, english_desc, hindi_desc = ai_result
                product_name = ai_name or extract_product_name(raw_input)
            else:
                st.info("AI writing service unavailable right now — using a basic template instead.")
                product_name = extract_product_name(raw_input)

                english_desc = f"""Handcrafted {product_name} made using traditional techniques by skilled Indian artisans.

Material: {material}
Category: {category}

{raw_input}

This authentic piece reflects the rich cultural heritage and craftsmanship of Indian artisans. Perfect for home décor, gifting, or wholesale buyers looking for genuine handmade products."""

                hindi_desc = f"""कुशल भारतीय कारीगरों द्वारा पारंपरिक तकनीकों से हाथ से बनाया गया {product_name}।

सामग्री: {material}
श्रेणी: {category}

{raw_input}

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
            st.session_state['material'] = material
    else:
        st.warning("Please record a voice description or type one first.")

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

# Pricing logic
multiplier = {
    "Small": 1.6,
    "Medium": 1.9,
    "Large / Detailed": 2.3
}

base = raw_cost + labor_cost
suggested_price = int(base * multiplier[size])

# Category bonus for higher-value categories
current_category = st.session_state.get('category', FALLBACK_CATEGORY)
if current_category in ["Handloom / Textile", "Jewelry"]:
    suggested_price = int(suggested_price * 1.15)

st.metric(
    label="Recommended Selling Price",
    value=f"₹ {suggested_price}",
    delta=f"Markup: {int((suggested_price / base - 1) * 100)}%" if base > 0 else None
)

st.caption("Price is calculated based on material + labor + size + category market trends.")

st.divider()

# -------------------- 4. Final Product Card --------------------
if enhanced_image is not None and 'english_desc' in st.session_state:
    st.subheader("4️⃣ Final Product Card (Ready to Share)")

    st.markdown(f"### {st.session_state['product_name']}")
    st.image(enhanced_image, width=300)

    st.markdown(f"**Category:** {current_category}")
    st.markdown(f"**Material:** {st.session_state.get('material', 'Traditional materials')}")
    st.markdown("**English Description:**")
    st.write(st.session_state['english_desc'])

    st.markdown(f"**Suggested Price:** ₹ {suggested_price}")

    st.success("✅ Your product is ready for digital marketplace / WhatsApp / Exhibition!")