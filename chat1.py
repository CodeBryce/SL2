import os
import streamlit as st

# 1) Install/import Google's Generative AI SDK
# pip install google-generativeai

import google.generativeai as genai

st.set_page_config(page_title="Gemini + Streamlit Quickstart", page_icon="✨")

# --- API key handling ---
# Prefer Streamlit Secrets, fall back to env var
API_KEY = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))

st.title("✨ Gemini Text Generator (Streamlit)")
st.caption("Provide a prompt, get a completion using Gemini.")

if not API_KEY:
    st.error(
        "No API key found. Add GEMINI_API_KEY in `.streamlit/secrets.toml` or set env var GEMINI_API_KEY."
    )
    st.stop()

# Configure SDK
genai.configure(api_key=API_KEY)

# Choose a model (e.g., gemini-1.5-flash for speed, or gemini-1.5-pro for higher quality)
MODEL_NAME = "gemini-1.5-flash"

prompt = st.text_area("Your prompt", "Explain transformers like I’m five.")
temperature = st.slider("Temperature", 0.0, 1.0, 0.7, 0.1)

if st.button("Generate"):
    with st.spinner("Thinking..."):
        model = genai.GenerativeModel(model_name=MODEL_NAME)
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=512,
            ),
        )
    st.subheader("Response")
    st.write(response.text)
