"""
utils/ai_engine.py
-------------------
Every "AI" capability the app needs, each with a graceful offline
fallback so the demo works even without API keys / optional packages:

  - Background removal / image cleanup   -> rembg if installed, else PIL fallback
  - Voice transcription + language ID    -> Gemini if GEMINI_API_KEY set, else
                                             speech_recognition (Google Web Speech)
  - Catalog copy generation (EN + HI)    -> Gemini if available, else a
                                             template-based generator
  - Translation (preferred-language tab) -> Gemini if available, else
                                             deep-translator (free, no key)
  - Dynamic pricing                      -> simple, explainable regression-style
                                             heuristic (swap in a trained sklearn
                                             model later without changing the
                                             calling code in 2_Add_Product.py)

Configure real keys via st.secrets["GEMINI_API_KEY"] or the
GEMINI_API_KEY environment variable.
"""

import io
import os
import re
import unicodedata

import streamlit as st
from PIL import Image, ImageOps, ImageEnhance, ImageFilter

# ---------------------------------------------------------------------
# Constants shared with the pages
# ---------------------------------------------------------------------
CATEGORIES = [
    "Textiles & Sarees", "Pottery & Terracotta", "Wooden Crafts",
    "Bamboo & Cane", "Jewelry", "Home Décor", "Bags & Accessories",
    "Paintings & Wall Art", "Toys & Dolls", "Other Handicraft",
]
FALLBACK_CATEGORY = "Other Handicraft"

# label -> (BCP-47 code, display name)
# Expanded to cover the major Indian languages speech_recognition /
# Google Web Speech supports. Add/remove entries here only -- every
# page reads from this single dict.
LANGUAGES = {
    "English": ("en-IN", "English"),
    "हिंदी (Hindi)": ("hi-IN", "Hindi"),
    "मराठी (Marathi)": ("mr-IN", "Marathi"),
    "தமிழ் (Tamil)": ("ta-IN", "Tamil"),
    "తెలుగు (Telugu)": ("te-IN", "Telugu"),
    "বাংলা (Bengali)": ("bn-IN", "Bengali"),
    "ગુજરાતી (Gujarati)": ("gu-IN", "Gujarati"),
    "ಕನ್ನಡ (Kannada)": ("kn-IN", "Kannada"),
    "മലയാളം (Malayalam)": ("ml-IN", "Malayalam"),
    "ਪੰਜਾਬੀ (Punjabi)": ("pa-IN", "Punjabi"),
    "ଓଡ଼ିଆ (Odia)": ("or-IN", "Odia"),
    "اردو (Urdu)": ("ur-IN", "Urdu"),
    "অসমীয়া (Assamese)": ("as-IN", "Assamese"),
    "कोंकणी (Konkani)": ("kok-IN", "Konkani"),
}
DEFAULT_LANGUAGE_LABEL = "English"


# =======================================================================
# Availability check
# =======================================================================
def _gemini_key() -> str | None:
    try:
        key = st.secrets.get("GEMINI_API_KEY")
    except Exception:
        key = None
    return key or os.environ.get("GEMINI_API_KEY")


def is_gemini_available() -> bool:
    if not _gemini_key():
        return False
    try:
        import google.generativeai  # noqa: F401
        return True
    except ImportError:
        return False


def _get_gemini_model():
    import google.generativeai as genai
    genai.configure(api_key=_gemini_key())
    return genai.GenerativeModel("gemini-1.5-flash")


# =======================================================================
# 1. IMAGE ENHANCEMENT / BACKGROUND REMOVAL
# =======================================================================
def resize_for_processing(image: Image.Image, max_dim: int = 2000) -> Image.Image:
    """Downscale very large phone-camera photos before processing.
    Raised from 1200 -> 2000: 1200 was throwing away too much detail
    from modern phone-camera photos before enhancement even ran."""
    w, h = image.size
    if max(w, h) <= max_dim:
        return image
    scale = max_dim / max(w, h)
    return image.resize((int(w * scale), int(h * scale)), Image.LANCZOS)


@st.cache_resource(show_spinner=False)
def _get_rembg_session():
    """Loads the rembg ONNX model exactly once per app process and
    reuses it for every image. Without this, remove_background() was
    re-initializing the model from scratch on every single upload,
    which is the main reason background removal felt slow.

    Set REMBG_MODEL=u2netp as an env var / st.secrets value for a
    much faster (smaller, slightly lower quality) model -- good for
    live demos where speed matters more than perfect edges."""
    from rembg import new_session
    model_name = os.environ.get("REMBG_MODEL")
    try:
        model_name = model_name or st.secrets.get("REMBG_MODEL")
    except Exception:
        pass
    return new_session(model_name or "u2net")


def remove_background(image: Image.Image, matte_size: int = 800) -> Image.Image:
    """Remove background and lightly enhance lighting/contrast.
    Uses rembg (U^2-Net) when available for real background removal;
    otherwise falls back to an auto-lighting/contrast pass only (no
    background masking), so the pipeline never breaks.

    Speed: the actual segmentation ("matting") runs on a small
    downscaled copy (matte_size, default 800px) instead of the full
    resolution image -- inference cost scales with pixel count, so
    this alone is a large speedup. Only the resulting alpha mask is
    upscaled back onto the original full-resolution image, so final
    output quality is unaffected."""
    original_rgb = image.convert("RGB")

    try:
        session = _get_rembg_session()
        from rembg import remove as rembg_remove

        small = resize_for_processing(original_rgb, max_dim=matte_size)
        buf = io.BytesIO()
        small.save(buf, format="PNG")
        result_bytes = rembg_remove(buf.getvalue(), session=session)
        small_cutout = Image.open(io.BytesIO(result_bytes)).convert("RGBA")

        # Upscale just the alpha mask back to the original's full size.
        alpha_small = small_cutout.split()[-1]
        alpha_full = alpha_small.resize(original_rgb.size, Image.LANCZOS)

        original_rgba = original_rgb.convert("RGBA")
        original_rgba.putalpha(alpha_full)

        white_bg = Image.new("RGBA", original_rgb.size, (255, 255, 255, 255))
        white_bg.paste(original_rgba, (0, 0), original_rgba)
        enhanced = white_bg.convert("RGB")
    except Exception:
        enhanced = original_rgb

    # lighting / contrast correction (always applied)
    enhanced = ImageOps.autocontrast(enhanced, cutoff=1)
    enhanced = ImageEnhance.Brightness(enhanced).enhance(1.05)
    enhanced = ImageEnhance.Color(enhanced).enhance(1.1)
    enhanced = ImageEnhance.Sharpness(enhanced).enhance(1.15)
    # NOTE: removed ImageFilter.SMOOTH_MORE here -- it ran right after
    # the sharpness boost and blurred the image back out, cancelling
    # the sharpening and softening fine detail (weave/grain/texture).
    # If a denoise pass is ever needed again, use the much gentler
    # ImageFilter.SMOOTH and apply it BEFORE the sharpness step, not after.

    return enhanced.convert("RGBA")


# =======================================================================
# 2. VOICE TRANSCRIPTION
# =======================================================================
def transcribe_audio_gemini(audio_bytes: bytes, mime_type: str):
    """Auto-detect language + transcribe using Gemini multimodal input.
    Returns (transcript, detected_language) or None on failure."""
    if not is_gemini_available():
        return None
    try:
        model = _get_gemini_model()
        prompt = (
            "Transcribe this voice recording exactly as spoken. The speaker is "
            "describing a handmade product for an e-commerce listing, likely in "
            "an Indian regional language. Respond in this exact format:\n"
            "LANGUAGE: <detected language name in English>\n"
            "TRANSCRIPT: <transcription in its original language>"
        )
        response = model.generate_content([
            prompt,
            {"mime_type": mime_type or "audio/wav", "data": audio_bytes},
        ])
        text = response.text or ""
        lang_match = re.search(r"LANGUAGE:\s*(.+)", text)
        transcript_match = re.search(r"TRANSCRIPT:\s*(.+)", text, re.DOTALL)
        if transcript_match:
            transcript = transcript_match.group(1).strip()
            language = lang_match.group(1).strip() if lang_match else "Unknown"
            return transcript, language
    except Exception:
        pass
    return None


def _prepare_wav_for_recognition(audio_bytes: bytes) -> bytes:
    """
    st.audio_input records in WebM/Opus, but speech_recognition's
    AudioFile can only read WAV/AIFF/FLAC directly. Without this
    conversion step, every offline transcription attempt fails at the
    file-reading stage -- BEFORE it ever listens to the actual speech --
    which is why bad recordings and perfectly clear ones produced the
    same generic "couldn't understand" error.

    This converts the raw bytes to 16kHz mono WAV (the format Google's
    speech API expects) and applies noise reduction if the optional
    `noisereduce` package is installed, to help with background noise
    from phone/market recording environments.

    Raises on failure so the caller can report a clear, specific error
    instead of a misleading "couldn't understand" message.
    """
    from pydub import AudioSegment

    audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)

    # Optional noise reduction pass -- skipped silently if the
    # `noisereduce` + `soundfile` + `numpy` stack isn't installed.
    try:
        import numpy as np
        import noisereduce as nr

        samples = np.array(audio.get_array_of_samples()).astype(np.float32)
        reduced = nr.reduce_noise(y=samples, sr=16000)
        audio = AudioSegment(
            reduced.astype(np.int16).tobytes(),
            frame_rate=16000, sample_width=2, channels=1,
        )
    except ImportError:
        pass  # noise reduction is a nice-to-have, not required

    out = io.BytesIO()
    audio.export(out, format="wav")
    return out.getvalue()


def transcribe_offline(audio_value, lang_code: str, lang_name: str):
    """Fallback transcription using speech_recognition (Google Web Speech API,
    free tier, requires internet). Returns (transcript, language, error)."""
    try:
        import speech_recognition as sr
    except ImportError:
        return None, None, (
            "⚠️ Offline transcription isn't installed "
            "(`pip install SpeechRecognition`). Please type your description instead."
        )

    audio_bytes = audio_value.getvalue()

    try:
        wav_bytes = _prepare_wav_for_recognition(audio_bytes)
    except ImportError:
        return None, None, (
            "⚠️ Audio conversion isn't installed (`pip install pydub`, and make "
            "sure `ffmpeg` is installed on your system). Please type your "
            "description instead."
        )
    except Exception:
        return None, None, (
            "Couldn't process that recording — please try recording again."
        )

    try:
        recognizer = sr.Recognizer()
        with sr.AudioFile(io.BytesIO(wav_bytes)) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.3)
            audio_data = recognizer.record(source)
        transcript = recognizer.recognize_google(audio_data, language=lang_code)
        return transcript, lang_name, None
    except sr.UnknownValueError:
        return None, None, (
            "Couldn't make out any speech in that recording — please re-record "
            "in a quieter place, speak a bit closer to the mic, or type your "
            "description instead."
        )
    except sr.RequestError:
        return None, None, (
            "⚠️ Couldn't reach the transcription service — check your internet "
            "connection, or type your description instead."
        )
    except Exception:
        return None, None, (
            "Something went wrong transcribing that recording — please "
            "re-record or type your description instead."
        )


# =======================================================================
# 3. CATALOG COPY GENERATION
# =======================================================================
def generate_ai_description(raw_text: str, category: str, material: str, source_language: str):
    """Returns (product_name, english_desc, hindi_desc) or None on failure."""
    if not is_gemini_available():
        return None
    try:
        model = _get_gemini_model()
        prompt = f"""You are a professional e-commerce copywriter for an Indian artisan marketplace.
An artisan described their handmade product in {source_language}:

"{raw_text}"

Category: {category}
Material mentioned: {material}

Write:
1. A short, appealing product name (5-8 words)
2. An SEO-friendly English product description (60-100 words) that highlights
   craftsmanship, material, and cultural authenticity, suitable for online buyers.
3. The same description translated naturally into Hindi (not a literal translation).

Respond in exactly this format with no extra commentary:
NAME: <product name>
ENGLISH: <english description>
HINDI: <hindi description>"""
        response = model.generate_content(prompt)
        text = response.text or ""

        name_match = re.search(r"NAME:\s*(.+)", text)
        eng_match = re.search(r"ENGLISH:\s*(.+?)(?=HINDI:|$)", text, re.DOTALL)
        hin_match = re.search(r"HINDI:\s*(.+)", text, re.DOTALL)

        if eng_match and hin_match:
            name = name_match.group(1).strip() if name_match else extract_product_name(raw_text)
            return name, eng_match.group(1).strip(), hin_match.group(1).strip()
    except Exception:
        pass
    return None


# =======================================================================
# 3b. TRANSLATION (preferred-language display, on top of EN/HI)
# =======================================================================
def _resolve_language(label: str):
    """Best-effort match of a language label (as stored on the user's
    profile) to an entry in LANGUAGES.

    This is deliberately tolerant of small text differences, because
    the same-looking native-script text (e.g. "मराठी") can be stored as
    different underlying Unicode byte sequences depending on where it
    was typed/copied from (composed vs decomposed accents) -- an exact
    string match can silently fail even though the text looks identical
    on screen. To sidestep that entirely, this also matches on just the
    plain-ASCII English name inside the parentheses, e.g. "Marathi" out
    of "मराठी (Marathi)", which has no such encoding ambiguity.

    Returns (iso_code, english_name), or (None, None) if unresolved."""
    if not label:
        return None, None

    normalized = unicodedata.normalize("NFC", label.strip())

    # 1. Exact match against a LANGUAGES key (normalized).
    for key, (code, name) in LANGUAGES.items():
        if unicodedata.normalize("NFC", key) == normalized:
            return code, name

    # 2. Match on the English name in parentheses instead, e.g.
    #    "मराठी (Marathi)" -> "Marathi" -> looked up by name.
    match = re.search(r"\(([^)]+)\)", normalized)
    candidate = (match.group(1).strip() if match else normalized).lower()
    for code, name in LANGUAGES.values():
        if name.lower() == candidate:
            return code, name

    return None, None


def language_display_name(label: str) -> str:
    """Converts a LANGUAGES-style label (e.g. 'मराठी (Marathi)') into its
    plain English display name (e.g. 'Marathi') for use in prompts and
    UI captions. Falls back to the original label if unresolved."""
    _, name = _resolve_language(label)
    return name or label


def _translate_offline(text: str, iso_code: str) -> str | None:
    """Free, keyless fallback translation via Google Translate
    (deep-translator package, no API key required). This is what makes
    translation work even when Gemini isn't configured -- same pattern
    as transcribe_offline() for voice."""
    try:
        from deep_translator import GoogleTranslator
    except ImportError:
        return None
    try:
        translated = GoogleTranslator(source="en", target=iso_code).translate(text)
        return translated.strip() if translated else None
    except Exception:
        return None


def translate_text(text: str, target_label: str) -> str | None:
    """Translates text (typically an English product description) into
    the language identified by target_label (as stored on the user's
    profile, e.g. 'मराठी (Marathi)').

    Tries Gemini first for better-quality, natural-sounding translation.
    If Gemini isn't configured or the call fails, falls back to free
    Google Translate via deep-translator -- so this works even with zero
    API keys set up. Returns None only if the target resolves to
    English, the label can't be resolved at all, or BOTH translation
    routes fail; callers should fall back to showing the English text
    in that case."""
    if not text or not text.strip():
        return None

    target_code, target_name = _resolve_language(target_label)
    if not target_code:
        return None
    if target_name.lower() == "english":
        return None
    iso_code = target_code.split("-")[0]  # "hi-IN" -> "hi"

    if is_gemini_available():
        try:
            model = _get_gemini_model()
            prompt = (
                f"Translate the following e-commerce product description "
                f"naturally into {target_name}. Keep the tone suitable for "
                f"online buyers -- do not translate word-for-word, translate "
                f"the meaning. Respond with ONLY the translated text and "
                f"nothing else (no preamble, no notes, no quotes).\n\n"
                f"{text}"
            )
            response = model.generate_content(prompt)
            translated = (response.text or "").strip()
            if translated:
                return translated
        except Exception:
            pass  # fall through to offline translation below

    return _translate_offline(text, iso_code)


def extract_product_name(raw_text: str) -> str:
    """Very lightweight heuristic title extractor for the offline fallback."""
    words = re.findall(r"[A-Za-z]+", raw_text)
    if not words:
        return "Handmade Product"
    title_words = [w.capitalize() for w in words[:4]]
    return " ".join(title_words) if title_words else "Handmade Product"


def extract_material(raw_text: str) -> str:
    known_materials = [
        "cotton", "silk", "wool", "jute", "bamboo", "cane", "wood", "terracotta",
        "clay", "brass", "copper", "silver", "leather", "wax", "stone", "bead",
        "handloom", "khadi",
    ]
    lowered = raw_text.lower()
    found = [m.capitalize() for m in known_materials if m in lowered]
    return ", ".join(found) if found else "Traditional handmade materials"


# =======================================================================
# 4. DYNAMIC PRICING
# =======================================================================
_CATEGORY_MULTIPLIER = {
    "Textiles & Sarees": 1.6,
    "Pottery & Terracotta": 1.3,
    "Wooden Crafts": 1.5,
    "Bamboo & Cane": 1.3,
    "Jewelry": 1.8,
    "Home Décor": 1.4,
    "Bags & Accessories": 1.5,
    "Paintings & Wall Art": 1.7,
    "Toys & Dolls": 1.3,
    "Other Handicraft": 1.35,
}
_SIZE_MULTIPLIER = {"Small": 1.0, "Medium": 1.25, "Large / Detailed": 1.6}


def predict_price(category: str, size: str, raw_cost: float, labor_cost: float) -> int:
    """Explainable heuristic pricing model:
    price = (raw_cost + labor_cost) x category_market_multiplier x size_multiplier
    Rounded to the nearest ₹10 so it reads as a natural retail price.
    (Swap this function's body for a trained sklearn/regression model —
    every caller already expects a single int return.)"""
    base_cost = max(raw_cost, 0) + max(labor_cost, 0)
    if base_cost <= 0:
        return 0
    cat_mult = _CATEGORY_MULTIPLIER.get(category, 1.35)
    size_mult = _SIZE_MULTIPLIER.get(size, 1.0)
    price = base_cost * cat_mult * size_mult
    return int(round(price / 10.0) * 10)