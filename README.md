# 🌱 AGR Sutra

**AI-Driven Market Linkage & Smart Cataloging for Marginalized Artisans**

AGR Sutra is a Streamlit marketplace that bridges artisans (sellers) with buyers. Sellers upload product photos, describe items by voice, get AI-generated bilingual catalog copy and a suggested price, then publish listings. Buyers browse, search, and purchase through a Marketplace, with a two-way rating system covering buyers, sellers, and products.

> Prototype / demo build — data is stored in local CSV files, not a database (see [Team Notes](#-team-notes)).

---

## ✨ Features

- **🔐 Auth (demo OTP)** — mobile or email login, 6-digit OTP (shown on-screen in demo mode, no real SMS/email sent), returning-user auto-login, guided profile + role (Seller/Buyer) setup
- **📸 AI Camera Studio** (Add Product) — background removal, voice-to-text product description with auto language detection, AI-generated bilingual (EN/HI) catalog copy, dynamic price suggestion, seller geolocation capture
- **🛒 Marketplace** — search, filter by category, sort by newest/price/rating
- **🧵 Product Detail** — translated description in the buyer's preferred language, seller info & location, buy now / add to cart, product & seller reviews
- **🛍️ Cart & Checkout** — multi-item cart or quick "buy now", stock-aware checkout, Cash on Delivery / UPI / Card
- **📦 Orders** — buyers track orders (New → Processing → Completed / Cancelled) and rate products/sellers after completion; sellers manage incoming orders and rate buyers
- **📊 Earnings & Analytics** (Seller) — earnings over time, order status breakdown, top products, revenue by category, low-stock alerts, date-range filtering
- **⭐ Two-way ratings system**
  - Buyers rate **products** they've ordered
  - Buyers rate the **seller/store** they ordered from
  - Sellers rate **buyers** after a completed order
  - Sellers can add an **initial review** to their own product listing to give it a starting point (excluded from the public average so sellers can't inflate their own score)
- **⚙️ Profile Settings** — edit contact info, language, PIN code, refresh browser geolocation, view buyer rating

---

## 🗂️ Project Structure

```
AGR_sutra/
├── home.py                        # Login / signup / role selection (entry point)
├── pages/
│   ├── 1_Seller_Dashboard.py      # Seller home: stats, store rating, quick actions
│   ├── 2_Add_Product.py           # AI Camera Studio — the full listing pipeline
│   ├── 3_My_Listings.py           # Seller's products: active/inactive, stock, initial review
│   ├── 4_Orders.py                # Seller: manage orders, rate buyers
│   ├── 5_Earnings_Analytics.py    # Seller: earnings & sales analytics
│   ├── 6_Buyer_Home.py            # Buyer home: stats, quick actions
│   ├── 7_Marketplace.py           # Buyer: search / filter / sort products
│   ├── 8_Product_Detail.py        # Buyer: product page, translation, reviews, buy
│   ├── 9_Cart_Checkout.py         # Buyer: cart & checkout flow
│   ├── 10_My_Orders.py            # Buyer: order tracking, rate products/sellers
│   └── 11_Profile_Settings.py     # Edit profile, geolocation, buyer rating
├── utils/
│   ├── auth.py                    # Session auth, OTP, phone validation, page guards
│   ├── ai_engine.py                # Image/voice/copy AI, translation, dynamic pricing
│   ├── data_store.py               # CSV-backed persistence (users/products/orders/reviews)
│   └── geo.py                      # Shared browser-geolocation capture helper
├── data/
│   ├── users.csv
│   ├── products.csv
│   ├── orders.csv
│   ├── reviews.csv
│   └── images/                    # Processed (background-removed) product images
├── assets/
│   └── products/
├── requirements.txt
├── LICENSE                        # MIT
└── README.md
```

---

## 🚀 Setup

1. Clone the repo:
   ```bash
   git clone https://github.com/suryatejadevara/AGR_sutra.git
   cd AGR_sutra
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate      # Mac/Linux
   venv\Scripts\activate         # Windows
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the app:
   ```bash
   streamlit run home.py
   ```

### Dependencies (`requirements.txt`)

| Package | Used for |
|---|---|
| `streamlit` | App framework / UI |
| `pandas` | CSV-backed data store |
| `Pillow` | Image processing |
| `rembg` | AI background removal (U²-Net) |
| `google-generativeai` | Gemini: transcription, catalog copy, translation |
| `SpeechRecognition` | Offline voice transcription fallback (Google Web Speech) |
| `pydub` | Audio format conversion (WebM/Opus → WAV) |
| `noisereduce`, `soundfile`, `numpy` | Optional noise reduction for voice recordings |
| `deep-translator` | Free, keyless translation fallback when Gemini isn't configured |

---

## 🔑 Configuration

### Gemini API key (optional but recommended)

Used for voice transcription + language auto-detect, AI catalog copy generation, and higher-quality translation.

1. Get a key from [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Create `.streamlit/secrets.toml` in the project root (already gitignored, so it won't be committed):
   ```toml
   GEMINI_API_KEY = "your-key-here"
   ```
3. Read automatically via `st.secrets.get("GEMINI_API_KEY", "")` (env var `GEMINI_API_KEY` also works).

Every AI feature degrades gracefully without a key:

| Feature | With Gemini | Without Gemini |
|---|---|---|
| Voice transcription | Gemini multimodal, auto language detect | `speech_recognition` (Google Web Speech), manual language picker |
| Product description | AI-generated bilingual (EN/HI) copy | Basic template-based generator |
| Translation (preferred language) | Gemini, natural phrasing | `deep-translator` (free Google Translate, no key) |

### Optional: faster background removal

`rembg` downloads the `u2net` model on first use (needs internet the first time). Set `REMBG_MODEL=u2netp` as an env var or `st.secrets` value for a smaller/faster model — good for live demos where speed matters more than edge quality. The model session is cached once per app process (`@st.cache_resource`), and matting runs on a downscaled copy (default 800px) with only the alpha mask upscaled back onto the full-resolution image.

### Microphone input

If recording audio directly through the app (not uploading audio files), `speech_recognition` also needs `PyAudio`, which requires the system library `portaudio`:

| OS | Command |
|---|---|
| Mac | `brew install portaudio` then `pip install pyaudio` |
| Windows | `pip install pyaudio` (usually works directly) |
| Linux | `sudo apt-get install portaudio19-dev` then `pip install pyaudio` |

### Phone number format

Mobile numbers are validated everywhere they're entered (login, sign-up, profile settings). A number must be either:
- exactly **10 digits**, e.g. `9876543210`, or
- the **+91** country code followed by 10 digits, e.g. `+919876543210` (13 characters total)

Any other format is rejected with an inline warning asking the user to correct it.

### Browser geolocation

Sellers can share their current location (shown to buyers on the product page) via `utils/geo.py`. It requests high-accuracy GPS from the browser (`enableHighAccuracy: true`, `maximumAge: 0`) and hands coordinates back to Streamlit via `?lat=&lon=` query params. Requires HTTPS or `localhost`, and the user must grant location permission.

---

## 📊 Data Schema

All data lives in `data/*.csv`, loaded/saved through `utils/data_store.py`.

### `data/users.csv`

| Column | Description |
|---|---|
| `user_id` | Unique user ID |
| `full_name` | User's name |
| `phone` | Mobile number (validated — see above) |
| `email` | Email address (optional if phone is provided) |
| `pin_code` | PIN / postal code |
| `language` | Preferred language |
| `role` | `Seller` or `Buyer` |
| `latitude`, `longitude` | Captured browser geolocation (optional) |
| `created_at` | Account creation timestamp |

### `data/products.csv`

| Column | Description |
|---|---|
| `product_id` | Unique product ID |
| `seller_id` | Owning seller's `user_id` |
| `product_name` | Name of the product |
| `category` | Product category |
| `material` | Material the product is made from |
| `language` | Language the artisan spoke in when describing the product (auto-detected via Gemini, or "Not detected" if typed) |
| `price` | Listed price (₹) |
| `stock` | Quantity available |
| `english_desc` | Generated English product description |
| `hindi_desc` | Generated Hindi product description |
| `image_path` | Path to the processed (background-removed) product image, saved under `data/images/` |
| `status` | `Active` or `Inactive` |
| `created_at` | Listing creation timestamp |

### `data/orders.csv`

| Column | Description |
|---|---|
| `order_id` | Unique order ID |
| `buyer_id` | Buyer's `user_id` |
| `seller_id` | Seller's `user_id` |
| `product_id` | Ordered product's ID |
| `product_name` | Product name (snapshot at order time) |
| `quantity` | Quantity ordered |
| `total_amount` | Total order value (₹) |
| `shipping_address` | Delivery address |
| `payment_method` | `Cash on Delivery`, `UPI`, or `Card` |
| `status` | `New`, `Processing`, `Completed`, or `Cancelled` |
| `created_at` | Order timestamp |

### `data/reviews.csv`

All review types share one file, distinguished by `review_type`:

| Column | Description |
|---|---|
| `review_id` | Unique review ID |
| `review_type` | One of `product`, `seller`, `buyer`, `seller_initial` |
| `order_id` | Order the review is tied to (blank for `seller_initial`) |
| `product_id` | Related product (blank for pure `buyer` reviews of a seller-only nature) |
| `seller_id` | Related seller |
| `buyer_id` | Related buyer (blank for `seller_initial`) |
| `rating` | 1–5 |
| `comment` | Optional free-text comment |
| `created_at` | Review timestamp |

**Review types explained:**
- `product` — a buyer rating the **product** they received (counts toward the product's public average rating)
- `seller` — a buyer rating the **seller/store** after a completed order (counts toward the seller's store rating)
- `buyer` — a seller rating the **buyer** after fulfilling their order (counts toward the buyer's rating, visible on their profile)
- `seller_initial` — a seller's own opening review of **their own product**; shown on the product page for context but **excluded** from the buyer-facing average rating, so sellers can't inflate their own score

Rules enforced in `data_store.py`: at most one review of a given type per order (`has_reviewed_order`), and at most one `seller_initial` review per product (`has_seller_reviewed_product`).

---

## 🧠 How the "AI" pipeline works (`utils/ai_engine.py`)

1. **Background removal** — `rembg` (U²-Net) cuts the product out and composites it onto a white background; falls back to an autocontrast/brightness/color/sharpness enhancement pass only if `rembg` is unavailable or fails.
2. **Voice transcription** — Gemini multimodal transcribes + auto-detects the spoken language in one call; otherwise `speech_recognition` (Google Web Speech, free tier) is used with a manually selected language, after converting the recording to 16kHz mono WAV via `pydub` (with optional `noisereduce` denoising).
3. **Catalog copy generation** — Gemini turns the raw spoken/typed description into a product name, an English description, and a natural (not literal) Hindi translation; the offline fallback extracts a title and known materials heuristically from the raw text.
4. **Translation** — for buyers whose preferred language isn't English or Hindi, the English description is translated on the Product Detail page: Gemini first, `deep-translator` (free Google Translate) as a fallback.
5. **Dynamic pricing** — an explainable heuristic, not a trained model:
   ```
   price = (raw_cost + labor_cost) × category_multiplier × size_multiplier
   ```
   rounded to the nearest ₹10. Multipliers are defined per category (e.g. Jewelry ×1.8, Pottery & Terracotta ×1.3) and per size (Small ×1.0, Medium ×1.25, Large/Detailed ×1.6) in `_CATEGORY_MULTIPLIER` / `_SIZE_MULTIPLIER`. Swappable later for a trained regression model without changing any caller.

Supported languages for voice input span 14 major Indian languages (English, Hindi, Marathi, Tamil, Telugu, Bengali, Gujarati, Kannada, Malayalam, Punjabi, Odia, Urdu, Assamese, Konkani).

---

## 🧑‍💻 Team Notes

- No database yet — all data is stored in `data/*.csv` files as a prototype shortcut. Every function in `utils/data_store.py` is written so its signature stays stable if these are later swapped for real database calls (Postgres/Supabase/Firebase).
- ID/contact columns (`user_id`, `phone`, `email`, `pin_code`, `product_id`, `seller_id`, `buyer_id`, `order_id`, `review_id`) are always force-loaded as strings to avoid pandas silently inferring `int64` and breaking on the next write.
- `home.py` drives a small state machine (`st.session_state["auth_step"]`: `welcome → login → otp_mobile/otp_email → profile → role`) for onboarding; `utils/auth.py` handles the session side, `utils/data_store.py` handles the persisted side.
- Add any additional required API keys or environment variables to this README as the project grows.

---

## 📄 License

MIT — see [LICENSE](LICENSE).