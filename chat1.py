import os
import time
import streamlit as st

# --- Gemini (new SDK) ---
from google import genai
from google.genai import types  # for GenerateContentConfig

# --- Supabase ---
from supabase import create_client, Client  # supabase>=2.x

# ---------- Config ----------
st.set_page_config(page_title="Persistent Gemini Chat", page_icon="💬", layout="centered")

GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))
SUPABASE_URL = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL", ""))
SUPABASE_KEY = st.secrets.get("SUPABASE_ANON_KEY", os.getenv("SUPABASE_ANON_KEY", ""))

if not (GEMINI_API_KEY and SUPABASE_URL and SUPABASE_KEY):
    st.error("Missing one or more secrets: GEMINI_API_KEY, SUPABASE_URL, SUPABASE_ANON_KEY")
    st.stop()

# Gemini client
genai_client = genai.Client(api_key=GEMINI_API_KEY)  # Quickstart pattern per docs
# Model choice: 2.5 family is current/stable
MODEL_NAME = "gemini-2.5-flash"  # switch to 'gemini-2.5-pro' if you want higher quality

# Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------- Auth UI ----------
with st.sidebar:
    st.header("Account")
    if "sb_session" not in st.session_state:
        st.session_state.sb_session = None
        st.session_state.user = None

    if st.session_state.user is None:
        login_tab, signup_tab = st.tabs(["Log in", "Sign up"])
        with login_tab:
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_pw")
            if st.button("Log in", type="primary", use_container_width=True):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.sb_session = res.session
                    st.session_state.user = res.user
                    st.success("Logged in.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Login failed: {e}")
        with signup_tab:
            email_su = st.text_input("Email ", key="signup_email")
            pw_su = st.text_input("Password ", type="password", key="signup_pw")
            if st.button("Create account", use_container_width=True):
                try:
                    supabase.auth.sign_up({"email": email_su, "password": pw_su})
                    st.success("Account created. Please login.")
                except Exception as e:
                    st.error(f"Sign up failed: {e}")
    else:
        st.caption(f"Signed in as **{st.session_state.user.email}**")
        if st.button("Sign out", use_container_width=True):
            try:
                supabase.auth.sign_out()
            except Exception:
                pass
            st.session_state.clear()
            st.rerun()

# Guard the rest of the app
if st.session_state.get("user") is None:
    st.stop()

user = st.session_state.user
user_id = user.id  # used by RLS policies

# ---------- Conversation selector ----------
st.title("💬 Persistent Gemini Chat")

# Load user's conversations
@st.cache_data(ttl=30)
def load_conversations(uid: str):
    resp = supabase.table("conversations") \
        .select("*") \
        .eq("user_id", uid) \
        .order("created_at", desc=True) \
        .execute()
    return resp.data or []

convos = load_conversations(user_id)
convo_titles = [c["title"] or f"Chat {i+1}" for i, c in enumerate(convos)]
convo_ids = [c["id"] for c in convos]

col1, col2 = st.columns([3,1])
with col1:
    selected_idx = st.selectbox("Choose a conversation", range(len(convos)), format_func=lambda i: convo_titles[i]) if convos else None
with col2:
    if st.button("➕ New"):
        # Create a fresh conversation
        title = time.strftime("Chat %Y-%m-%d %H:%M")
        ins = supabase.table("conversations").insert({"user_id": user_id, "title": title}).execute()
        new_id = ins.data[0]["id"]
        st.cache_data.clear()  # bust cache
        st.session_state.current_convo = new_id
        st.rerun()

# Determine current conversation id
if "current_convo" not in st.session_state:
    st.session_state.current_convo = convo_ids[selected_idx] if selected_idx is not None else None
else:
    # update from new selection
    if selected_idx is not None:
        st.session_state.current_convo = convo_ids[selected_idx]

convo_id = st.session_state.current_convo

# ---------- Messages ----------
def load_messages(conversation_id: str):
    resp = supabase.table("messages") \
        .select("*") \
        .eq("conversation_id", conversation_id) \
        .order("created_at", desc=False) \
        .execute()
    return resp.data or []

def add_message(conversation_id: str, role: str, content: str):
    supabase.table("messages").insert({
        "conversation_id": conversation_id,
        "role": role,
        "content": content
    }).execute()

if convo_id is None and not convos:
    st.info("Create your first conversation with the ➕ New button.")
    st.stop()

if convo_id is None:
    st.stop()

history = load_messages(convo_id)

# Render history
for m in history:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# ---------- Chat input ----------
user_msg = st.chat_input("Type your message")
if user_msg:
    # 1) Persist the user message
    add_message(convo_id, "user", user_msg)
    with st.chat_message("user"):
        st.markdown(user_msg)

    # 2) Build the prompt from full history for better continuity
    # Google Gen AI SDK accepts plain strings or structured contents. We'll send an interleaved list.
    genai_contents = []
    for m in load_messages(convo_id):
        role = "user" if m["role"] == "user" else "model"
        genai_contents.append({"role": role, "parts": [{"text": m["content"]}]})

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                resp = genai_client.models.generate_content(
                    model=MODEL_NAME,
                    contents=genai_contents,   # passes the full chat
                    config=types.GenerateContentConfig(
                        temperature=0.7,
                        max_output_tokens=512
                    ),
                )
                assistant_text = resp.text
            except Exception as e:
                assistant_text = f"⚠️ Generation error: {e}"

        st.markdown(assistant_text)

    # 3) Persist the assistant message
    add_message(convo_id, "model", assistant_text)

    # 4) Clear any caches and rerun so the history list updates
    st.cache_data.clear()
    st.rerun()
