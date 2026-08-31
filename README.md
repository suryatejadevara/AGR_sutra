# 🌱 AGR Sutra

**AI-Driven Market Linkage & Smart Cataloging for Marginalized Artisans**

An app that bridges artisans with buyers — artisans upload product photos, generate AI-assisted descriptions, set prices, and publish listings; buyers browse and purchase them through a Marketplace, with a two-way rating system for buyers, sellers, and products.

---

## ✨ Features

- **AI Camera Studio** — background removal, voice-to-text product descriptions (auto language detection), AI-generated bilingual (EN/HI) catalog copy, and dynamic price suggestions
- **Marketplace** — search, filter, and sort by category, price, or rating
- **Orders & Checkout** — cart, buy-now, stock-aware checkout, order tracking
- **Analytics Dashboard** — earnings over time, order status breakdown, top products, revenue by category, low-stock alerts
- **Ratings system**
  - 🛒 Buyers rate **products** they've ordered
  - 🛒 Buyers rate the **seller/store** they ordered from
  - 🏪 Sellers rate **buyers** after a completed order
  - 🧑‍🎨 Sellers can add an **initial review** to their own product listing to give it a starting point

---

## 🗂️ Project Structure

```
AGR_sutra/
├── home.py                        # Login / signup / role selection
├── pages/
│   ├── 1_Seller_Dashboard.py
│   ├── 2_Add_Product.py           # AI Camera Studio
│   ├── 3_My_Listings.py
│   ├── 4_Orders.py
│   ├── 5_Earnings_Analytics.py
│   ├── 6_Buyer_Home.py
│   ├── 7_Marketplace.py
│   ├── 8_Product_Detail.py
│   ├── 9_Cart_Checkout.py
│   ├── 10_My_Orders.py
│   └── 11_Profile_Settings.py
├── utils/
│   ├── auth.py                    # session auth, OTP, phone validation
│   ├── ai_engine.py               # image/voice/copy AI + pricing
│   └── data_store.py              # CSV-backed persistence
├── data/
│   ├── users.csv
│   ├── products.csv
│   ├── orders.csv
│   ├── reviews.csv
│   └── images/
├── requirements.txt
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

---

## 🔑 Configuration

### Gemini API key (optional but recommended)

Used for voice transcription + language auto-detect and AI catalog copy generation.

1. Get a key from [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Create `.streamlit/secrets.toml` in the project root (already gitignored, so it won't be committed):
   ```toml
   GEMINI_API_KEY = "your-key-here"
   ```
3. `home.py` / `utils/ai_engine.py` read it automatically via:
   ```python
   GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
   ```

   Without a key configured, the app falls back gracefully:
   - Voice transcription uses local `speech_recognition` with a manual language picker
   - Product descriptions use a basic template instead of AI-generated copy

### Microphone input

If recording audio directly through the app (not uploading audio files), `speech_recognition` also needs `PyAudio`, which requires the system library `portaudio`:

| OS | Command |
|---|---|
| Mac | `brew install portaudio` then `pip install pyaudio` |
| Windows | `pip install pyaudio` (usually works directly) |
| Linux | `sudo apt-get install portaudio19-dev` then `pip install pyaudio` |

### First run

`rembg` downloads a background-removal model on first use — make sure you have an internet connection the first time you run the app.

### Phone number format

Mobile numbers are validated everywhere they're entered (login, sign-up, profile settings). A number must be either:
- exactly **10 digits**, e.g. `9876543210`, or
- the **+91** country code followed by 10 digits, e.g. `+919876543210` (13 characters total)

Any other format is rejected with an inline warning asking the user to correct it.

---

## 📊 Data Schema

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

---

## 🧑‍💻 Team Notes

- No database yet — all data is stored in `data/*.csv` files as a prototype shortcut. Every function in `utils/data_store.py` is written so its signature stays stable if these are later swapped for real database calls (Postgres/Supabase/Firebase).
- Add any additional required API keys or environment variables to this README as the project grows.