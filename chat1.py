import os
import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="Gemini Chatbot", page_icon="🤖", layout="centered")

# --- API Key ---
API_KEY = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))

if not API_KEY:
    st.error("No API key found. Add GEMINI_API_KEY in `.streamlit/secrets.toml` or set env var GEMINI_API_KEY.")
    st.stop()

genai.configure(api_key=API_KEY)

MODEL_NAME = "gemini-2.5-flash"

# --- Page Header ---
st.title("🤖 Gemini Chatbot")
st.caption("Powered by Gemini 2.5 Flash · Session memory enabled")

# --- Session State Init ---
if "chat_session" not in st.session_state:
    model = genai.GenerativeModel(model_name=MODEL_NAME)
    st.session_state.chat_session = model.start_chat(history=[])

if "messages" not in st.session_state:
    st.session_state.messages = []  # list of {"role": "user"|"assistant", "content": str}

# --- Sidebar Controls ---
with st.sidebar:
    st.header("⚙️ Settings")
    temperature = st.slider("Temperature", 0.0, 1.0, 0.7, 0.1)
    max_tokens = st.slider("Max output tokens", 256, 2048, 1024, 128)
    st.divider()
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        model = genai.GenerativeModel(model_name=MODEL_NAME)
        st.session_state.chat_session = model.start_chat(history=[])
        st.rerun()
    st.caption(f"Model: `{MODEL_NAME}`")
    st.caption(f"Messages in session: {len(st.session_state.messages)}")

# --- Render Chat History ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- Chat Input ---
if user_input := st.chat_input("Type a message..."):
    # Show user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Send to Gemini with session memory
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = st.session_state.chat_session.send_message(
                user_input,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )
            reply = response.text

        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
