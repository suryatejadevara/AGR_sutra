# AGR Sutra

An app that bridges marginal artisans with buyers — artisans upload product photos, generate descriptions, and publish listings; buyers browse them via a Dashboard and Marketplace.

## Setup

1. Clone the repo:
   ```
   git clone https://github.com/suryatejadevara/AGR_sutra.git
   cd AGR_sutra
   ```
2. Create a virtual environment:
   ```
   python -m venv venv
   ```
3. Activate it:
   - Mac/Linux: `source venv/bin/activate`
   - Windows: `venv\Scripts\activate`
4. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Run

```
streamlit run app.py
```

## Project structure

```
AGR_sutra/
├── app.py
├── pages/
│   ├── Dashboard.py
│   └── Marketplace.py
├── data/
│   └── products.csv
├── requirements.txt
└── README.md
```

## How it works

1. Upload a product photo and record/type a description.
2. Generate the product description.
3. Set a stock quantity and hit Publish.
4. The product appears instantly in the Dashboard and Marketplace pages.

## Data schema — `data/products.csv`

| Column          | Description                              |
|-----------------|-------------------------------------------|
| `product_name`  | Name of the product                       |
| `category`      | Product category                          |
| `material`      | Material the product is made from         |
| `price`         | Listed price                              |
| `stock`         | Quantity available                        |
| `english_desc`  | Generated English product description     |
| `image_path`    | Path to the processed (background-removed) product image, saved under `assets/products/` |
| `language`      | Language the artisan spoke in when describing the product (auto-detected via Gemini, or "Not detected" if typed) |

## API keys / environment variables

This app uses the **Google Gen AI (Gemini)** SDK (`google-genai`) for both voice transcription/language detection and product-description generation. Each teammate needs their own API key:

1. Get a key from [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Create a `.streamlit/secrets.toml` file in the project root (this is already gitignored, so it won't be committed):
   ```toml
   GEMINI_API_KEY = "your-key-here"
   ```
3. `app.py` reads it automatically via:
   ```python
   GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
   client = genai.Client(api_key=GEMINI_API_KEY)
   ```
   If no key is configured, the app falls back gracefully: voice transcription uses local `speech_recognition` with a manual language picker, and product descriptions use a basic template instead of AI-generated copy.

**Microphone input note:** if the app records audio from your mic (not just uploaded audio files), `speech_recognition` also needs `PyAudio`, which requires the system library `portaudio`:
- Mac: `brew install portaudio` then `pip install pyaudio`
- Windows: `pip install pyaudio` usually works directly
- Linux: `sudo apt-get install portaudio19-dev` then `pip install pyaudio`

**First run note:** `rembg` downloads a background-removal model on first use — make sure you have an internet connection the first time you run the app.

## Team notes

- No database yet — product data is stored in `data/products.csv` as a prototype shortcut.
- Add any required API keys or environment variables here as the project grows.