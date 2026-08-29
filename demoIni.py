import streamlit as st
from rembg import remove, new_session
from PIL import Image
import speech_recognition as sr

st.title("Artisan AI Product Studio - Prototype")

uploaded_file = st.file_uploader("Upload a product photo", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    input_image = Image.open(uploaded_file)
    st.image(input_image, caption="Original", use_container_width=True)

    with st.spinner("AI is cleaning the background..."):
        session = new_session("u2netp")
        output_image = remove(input_image, session=session)

    st.image(output_image, caption="AI Enhanced (Background Removed)", use_container_width=True)

    st.subheader("Product Description")
    st.write("🎤 Speak your description, or type it below")

    audio_value = st.audio_input("Record a voice description")

    spoken_text = ""
    if audio_value is not None:
        recognizer = sr.Recognizer()
        with st.spinner("Transcribing your voice..."):
            try:
                with sr.AudioFile(audio_value) as source:
                    audio_data = recognizer.record(source)
                    spoken_text = recognizer.recognize_google(audio_data)
                st.success(f"Heard: \"{spoken_text}\"")
            except Exception as e:
                st.warning("Couldn't transcribe that clearly — try typing instead.")

    typed_text = st.text_input("Or type your product description here", value=spoken_text)

    product_type = typed_text if typed_text else spoken_text

    if product_type:
        st.write("**English:**", f"Handcrafted {product_type}, made using traditional techniques by skilled artisans.")
        st.write("**Hindi:**", f"पारंपरिक तकनीकों से कुशल कारीगरों द्वारा हाथ से बनाया गया {product_type}.")

    st.subheader("Suggested Price")
    base_cost = st.number_input("Enter your raw material + labor cost (₹)", min_value=0, value=150)
    suggested_price = int(base_cost * 1.4)
    st.write(f"**Suggested selling price: ₹{suggested_price}**")