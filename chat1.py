import os
import streamlit as st
from google import genai
from google.genai import types

st.set_page_config(page_title="Gemini + Streamlit (Gen AI SDK)", page_icon="✨")

API_KEY = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))
if not API_KEY:
    st.error("Add GEMINI_API_KEY to Streamlit secrets or your environment.")
    st.stop()

client = genai.Client(api_key=API_KEY)

st.title("✨ Gemini Text Generator (Streamlit)")
st.caption("Provide a prompt, get a completion using a current Gemini model.")

prompt = st.text_area("Your prompt", "Explain transformers like I’m five.")
temperature = st.slider("Temperature", 0.0, 1.0, 0.7, 0.1)

if st.button("Generate"):
    with st.spinner("Thinking..."):
        resp = client.models.generate_content(
            model="gemini-2.5-flash",        # current model family
            contents=prompt,                 # <-- simplified fix
            config=types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=512,
            ),
        )
    st.subheader("Response")
    st.write(resp.text)
