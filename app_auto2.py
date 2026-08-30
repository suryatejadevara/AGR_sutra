import streamlit as st
from rembg import remove, new_session
from PIL import Image
import speech_recognition as sr
import io
import re
import hashlib
import json
import google.genai as genai
from google.genai import types
import pandas as pd
import os

DATA_PATH = "data/products.csv"
IMAGE_DIR = "assets/products"
# -------------------- Gemini Setup --------------------
# Store your key in .streamlit/secrets.toml as:
#   GEMINI_API_KEY = "your-key-here"
# Never hardcode API keys directly in the script.
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")


@st.cache_resource(show_spinner=False)
def get_gemini_client():
    """Creates and caches the Gemini client once per server process.
    Returns None if no API key is configured, so callers can fall back gracefully."""
    if not GEMINI_API_KEY:
        return None
    return genai.Client(api_key=GEMINI_API_KEY)


def transcribe_audio_gemini(audio_bytes: bytes, mime_type: str):
    """Sends the raw voice recording directly to Gemini so it can automatically
    detect which language the artisan spoke — ANY language, not limited to a
    hardcoded list — and transcribe it in the same call. This is the primary
    transcription path; it has no language ceiling the way the offline
    speech_recognition fallback does. Returns (transcript, detected_language)
    on success, or None if Gemini isn't configured or the call/parse fails —
    callers should fall back to local speech recognition in that case."""
    client = get_gemini_client()
    if client is None:
        return None

    prompt = """Listen to this audio of an Indian artisan describing their handmade product.

Automatically detect which language they are speaking. It could be any language spoken in
India — including but not limited to Hindi, English, Marathi, Tamil, Telugu, Bengali,
Gujarati, Kannada, Malayalam, Punjabi, Urdu, Odia, Assamese, Nepali, Sanskrit, Sindhi,
Bhojpuri, Maithili, Konkani, Manipuri (Meitei), Dogri, Bodo, or Santali — or any other
language. Do not assume the language in advance; identify it from what you hear.

Respond with ONLY valid JSON, no markdown code fences, no extra text, in exactly this shape:
{"detected_language": "<English name of the language, e.g. Hindi, Bhojpuri, Santali>", "transcript": "<what they said, transcribed in its original language and script>"}"""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                prompt,
            ],
        )
        cleaned = response.text.strip()
        cleaned = re.sub(r"^```(json)?|```$", "", cleaned, flags=re.MULTILINE).strip()
        data = json.loads(cleaned)
        transcript = data.get("transcript")
        detected_language = data.get("detected_language")
        if transcript:
            return transcript, (detected_language or "Unknown")
        return None
    except Exception:
        return None


def generate_ai_description(raw_text: str, category: str, material: str, spoken_language: str):
    """Calls Gemini to turn a rough description into a product name plus
    English and Hindi e-commerce copy. `spoken_language` is the human-readable
    name of the language the artisan actually spoke in (e.g. "Marathi"), so
    Gemini knows what it's translating from rather than assuming English.
    Returns (name, english, hindi) on success, or None if the API isn't
    configured or the call/parse fails — callers should fall back to the
    template-based generator in that case."""
    client = get_gemini_client()
    if client is None:
        return None

    prompt = f"""You are helping an Indian artisan write an e-commerce product listing.

The artisan spoke in {spoken_language}. Here is the transcribed text of what they said (it may
contain transcription errors — use your best judgement to understand the intended meaning):
"{raw_text}"

Category: {category}
Material: {material}

Write:
1. A short, catchy product name (max 6 words), in English
2. A professional, SEO-friendly product description in English, based on what the artisan
   described (translate/interpret from {spoken_language} as needed)
3. A natural Hindi translation of that same description

Respond with ONLY valid JSON, no markdown code fences, no extra text, in exactly this shape:
{{"product_name": "...", "english": "...", "hindi": "..."}}"""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
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

# -------------------- Landing screen --------------------
# The upload/describe/price/publish form only appears after the artisan taps
# this button, instead of showing immediately when the page loads.
if 'selling_started' not in st.session_state:
    st.session_state['selling_started'] = False

if not st.session_state['selling_started']:
    st.markdown("#### Ready to list a new product?")
    st.write("Tap below to upload a photo, describe your product, and get an AI-suggested price.")
    if st.button("🛍️ Place Product for Selling", type="primary", use_container_width=True):
        st.session_state['selling_started'] = True
        st.rerun()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊 Dashboard", use_container_width=True):
            st.switch_page("pages/dashboard.py")
    with col2:
        if st.button("🛒 Marketplace", use_container_width=True):
            st.switch_page("pages/marketplace.py")

    st.stop()

# -------------------- Categories --------------------
CATEGORIES = ["Pottery", "Handloom / Textile", "Handicraft", "Jewelry", "Woodwork", "Other"]
FALLBACK_CATEGORY = "Handicraft"

# Common materials to listen for in the spoken description
MATERIAL_KEYWORDS = [
    "clay", "terracotta", "cotton", "silk", "wool", "jute", "wood", "bamboo",
    "brass", "copper", "bronze", "silver", "gold", "leather", "stone", "glass",
    "ceramic", "iron", "cane", "wax", "paper"
]

# -------------------- Supported voice languages --------------------
# Labels are shown in native script first (so low-literacy / regional-language
# users can recognize their own language at a glance), with the English name
# in brackets. Codes are the locale strings Google's speech API expects.
LANGUAGES = {
    "हिंदी (Hindi)": ("hi-IN", "Hindi"),
    "English": ("en-IN", "English"),
    "मराठी (Marathi)": ("mr-IN", "Marathi"),
    "தமிழ் (Tamil)": ("ta-IN", "Tamil"),
    "తెలుగు (Telugu)": ("te-IN", "Telugu"),
    "বাংলা (Bengali)": ("bn-IN", "Bengali"),
    "ગુજરાતી (Gujarati)": ("gu-IN", "Gujarati"),
    "ಕನ್ನಡ (Kannada)": ("kn-IN", "Kannada"),
    "മലയാളം (Malayalam)": ("ml-IN", "Malayalam"),
    "ਪੰਜਾਬੀ (Punjabi)": ("pa-IN", "Punjabi"),
    "اردو (Urdu)": ("ur-IN", "Urdu"),
    "ଓଡ଼ିଆ (Odia)": ("or-IN", "Odia"),
    "অসমীয়া (Assamese)": ("as-IN", "Assamese"),
    "नेपाली (Nepali)": ("ne-NP", "Nepali"),
    "संस्कृत (Sanskrit)": ("sa-IN", "Sanskrit"),
    "سنڌي (Sindhi)": ("sd-IN", "Sindhi"),
    "भोजपुरी (Bhojpuri)": ("bho-IN", "Bhojpuri"),
    "मैथिली (Maithili)": ("mai-IN", "Maithili"),
    "कोंकणी (Konkani)": ("kok-IN", "Konkani"),
    "ꯃꯤꯇꯩꯂꯣꯟ (Manipuri)": ("mni-IN", "Manipuri"),
    "डोगरी (Dogri)": ("doi-IN", "Dogri"),
    "बड़ो (Bodo)": ("brx-IN", "Bodo"),
    "ᱥᱟᱱᱛᱟᱲᱤ (Santali)": ("sat-IN", "Santali"),
}
DEFAULT_LANGUAGE_LABEL = "हिंदी (Hindi)"
# NOTE: this manual list is only used as an OFFLINE FALLBACK when Gemini isn't
# configured (see transcribe_audio_gemini above, which is the primary path and
# has no language ceiling). It relies on speech_recognition's FREE Google Web
# Speech API, which has undocumented and inconsistent language coverage — not
# the same as Google's paid Cloud Speech-to-Text. The first ten languages
# (Hindi through Punjabi) are commonly reported to work well. Urdu through
# Sindhi are less consistently supported. Bhojpuri through Santali are
# included for completeness of India's 22 scheduled languages, but their
# locale codes are unverified against the free API and may not work at all —
# test each before a live demo. This is exactly the gap the Gemini path
# above solves: it doesn't need a matching locale code per language.

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

def save_product(product_name, category, material, price, stock, english_desc, image):
    """Appends one product to data/products.csv and saves its image to disk.
    Creates the data/ and assets/products/ folders on first run."""
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    os.makedirs(IMAGE_DIR, exist_ok=True)

    safe_name = re.sub(r"[^a-zA-Z0-9]+", "_", product_name).strip("_").lower()
    image_path = os.path.join(IMAGE_DIR, f"{safe_name}.png")
    image.save(image_path, format="PNG")

    new_row = pd.DataFrame([{
        "product_name": product_name,
        "category": category,
        "material": material,
        "price": price,
        "stock": stock,
        "english_desc": english_desc,
        "image_path": image_path,
    }])

    if os.path.exists(DATA_PATH):
        df = pd.read_csv(DATA_PATH)
        df = pd.concat([df, new_row], ignore_index=True)
    else:
        df = new_row

    df.to_csv(DATA_PATH, index=False)

# -------------------- Back to home --------------------
if st.button("← Back", use_container_width=True):
    st.session_state['selling_started'] = False
    st.rerun()

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
        mime="image/png",
        use_container_width=True
    )

# -------------------- Mandatory photo gate --------------------
# A product photo is REQUIRED. Nothing below this point (voice description,
# pricing, publishing) is reachable without a successfully processed image —
# rather than silently hiding the final step, we tell the artisan clearly why
# they can't continue yet.
if enhanced_image is None:
    st.error("📸 A product photo is required. Please upload a photo above before continuing.")
    st.stop()

st.divider()

# -------------------- 2. Speak About Your Product --------------------
st.subheader("2️⃣ Speak About Your Product")
st.markdown("🎤 Describe what it is, what it's made of, and how it's made — the AI will do the rest.")

# ---- Language: Gemini auto-detects it from the audio directly — no list, ----
# ---- no ceiling. The manual picker below only appears if Gemini isn't ----
# ---- configured, as an offline fallback with limited language coverage. ----
gemini_available = get_gemini_client() is not None
selected_lang_code, selected_lang_name = LANGUAGES[DEFAULT_LANGUAGE_LABEL]

if gemini_available:
    st.caption("🌐 Speak in any language — the AI will automatically detect it, no need to select.")
else:
    st.warning("⚠️ AI auto-detect isn't configured — please select your language manually.")
    st.markdown("**🌐 अपनी भाषा चुनें / Select your language**")
    selected_label = st.pills(
        "Voice language",
        options=list(LANGUAGES.keys()),
        default=st.session_state.get('language_label', DEFAULT_LANGUAGE_LABEL),
        label_visibility="collapsed",
    )
    if selected_label is None:
        selected_label = st.session_state.get('language_label', DEFAULT_LANGUAGE_LABEL)
    st.session_state['language_label'] = selected_label
    selected_lang_code, selected_lang_name = LANGUAGES[selected_label]

audio_value = st.audio_input("Record your voice description")

if audio_value is not None:
    audio_bytes = audio_value.getvalue()
    cache_key = hashlib.md5(audio_bytes).hexdigest()
    if not gemini_available:
        # Re-transcribe if the artisan changes the manual language too.
        cache_key += f":{selected_lang_code}"

    if st.session_state.get('audio_cache_key') != cache_key:
        transcript = None
        detected_language = None

        if gemini_available:
            with st.spinner("🌐 Detecting language and transcribing..."):
                result = transcribe_audio_gemini(audio_bytes, audio_value.type or "audio/wav")
            if result:
                transcript, detected_language = result
            else:
                st.info("Auto-detect had trouble with that recording — trying standard transcription.")

        if transcript is None:
            # Either Gemini isn't configured, or the Gemini call above failed —
            # fall back to local speech_recognition with the selected language.
            recognizer = sr.Recognizer()
            with st.spinner("Transcribing your voice..."):
                try:
                    audio_value.seek(0)
                    with sr.AudioFile(audio_value) as source:
                        audio_data = recognizer.record(source)
                        transcript = recognizer.recognize_google(audio_data, language=selected_lang_code)
                        detected_language = selected_lang_name
                except Exception:
                    transcript = None

        if transcript:
            st.success(f"Heard ({detected_language}): \"{transcript}\"")
        else:
            st.warning("Couldn't transcribe that clearly — please re-record and try again.")

        st.session_state['audio_cache_key'] = cache_key
        st.session_state['spoken_text'] = transcript or ""
        st.session_state['detected_language'] = detected_language
    else:
        cached_transcript = st.session_state.get('spoken_text', "")
        cached_language = st.session_state.get('detected_language')
        if cached_transcript:
            st.success(f"Heard ({cached_language}): \"{cached_transcript}\"")

spoken_text = st.session_state.get('spoken_text', "")

typed_desc = st.text_input("...or type a quick description instead (if the mic isn't working)")

if st.button("✨ Generate Professional Description", type="primary", use_container_width=True):
    raw_input = spoken_text or typed_desc

    if raw_input:
        with st.spinner("AI is writing professional catalog copy..."):

            category = st.session_state.get('category', FALLBACK_CATEGORY)
            material = extract_material(raw_input)
            # Typed input has no audio to detect a language from — assume
            # English. Spoken input uses whatever was auto-detected by
            # Gemini (or manually picked in the offline fallback).
            language_for_ai = st.session_state.get('detected_language', 'English') if spoken_text else "English"

            ai_result = generate_ai_description(raw_input, category, material, language_for_ai)

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

    stock_qty = st.number_input("Available Quantity", min_value=1, value=5)

    if st.button("🚀 PUBLISH PRODUCT", type="primary", use_container_width=True):
        save_product(
            product_name=st.session_state['product_name'],
            category=current_category,
            material=st.session_state.get('material', 'Traditional materials'),
            price=suggested_price,
            stock=stock_qty,
            english_desc=st.session_state['english_desc'],
            image=enhanced_image,
        )
        st.success("✅ PRODUCT PUBLISHED — your product is now in the AGR Sutra Marketplace.")
        st.balloons()