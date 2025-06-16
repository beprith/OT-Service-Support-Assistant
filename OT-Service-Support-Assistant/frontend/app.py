import os
import streamlit as st
import requests
from PIL import Image
from io import BytesIO
import uuid
from datetime import datetime

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="OT Service Support Assistant",
    page_icon="🤖",
    layout="wide",
)

# --- LOAD EXTERNAL CSS & HEADER ---
css_path = os.path.join(os.path.dirname(__file__), "static/style.css")
with open(css_path) as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown(
    """
<div class="app-header">
  <h1>🔧 OT Service Support Assistant | Powered by Langflow</h1>
  <h2>🤖 Chat with the SOP Bot</h2>
  <p>Type below and hit ⏎ or click Send to start the conversation.</p>
</div>
""",
    unsafe_allow_html=True,
)

# --- API ENDPOINTS ---
QUERY_URL    = "http://localhost:8000/api/query"
UPLOAD_URL   = "http://localhost:8000/api/upload"
FEEDBACK_URL = "http://localhost:8000/api/feedback"

# --- SESSION SETUP ---
if "session_id" not in st.session_state:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state.session_id = f"{ts}_{uuid.uuid4().hex[:6]}"
SESSION_ID = st.session_state.session_id

# --- SIDEBAR: UPLOAD & SESSION CONTROLS ---
with st.sidebar:
    st.markdown("## 🏭 Upload Center")
    st.markdown("Enhance your session by uploading SOPs or machine logs.")
    up = st.file_uploader("Upload SOPs, logs, or instructions", type=["pdf","docx","txt"])
    if up:
        with st.spinner("Uploading…"):
            r = requests.post(
                UPLOAD_URL,
                files={"file": (up.name, up, up.type)},
                params={"session_id": SESSION_ID}
            )
        st.success("✅ File uploaded!" if r.ok else "❌ Upload failed.")
    st.markdown("---")
    st.markdown(f"**🆔 Session ID:** `{SESSION_ID}`")
    if st.button("🔄 Start New Session"):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        st.session_state.session_id = f"{ts}_{uuid.uuid4().hex[:6]}"
        st.experimental_rerun()
    st.caption("All actions and data are session-aware.")
    st.caption("Made with 💡 by Langflow + Streamlit")

# --- INITIALIZE CHAT HISTORY ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- RENDER EXISTING CHAT MESSAGES ---
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- CHAT INPUT + SEND ---
prompt = st.chat_input("🧠 Type your question and press Enter…")
if prompt:
    # display user's message
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    # get and display assistant's reply
    with st.chat_message("assistant"):
        with st.spinner("🤖 Thinking…"):
            res = requests.post(
                QUERY_URL,
                json={"query": prompt, "session_id": SESSION_ID},
            )
            res.raise_for_status()
            data = res.json()
            reply = data.get("response", "_No guidance found._")
            st.markdown(reply)

            # optional image
            if img_ref := data.get("image_ref"):
                raw = requests.get(f"http://localhost:8000/{img_ref}").content
                st.image(Image.open(BytesIO(raw)), use_column_width=True)

    st.session_state.chat_history.append({"role": "assistant", "content": reply})

    # feedback form after assistant reply
    with st.chat_message("assistant"):
        st.markdown("**Was this helpful?**")
        fb = st.text_input("Share feedback…", key=f"fb_{len(st.session_state.chat_history)}")
        if st.button("📩 Submit Feedback", key=f"submit_fb_{len(st.session_state.chat_history)}"):
            fr = requests.post(
                FEEDBACK_URL,
                json={
                    "query": prompt,
                    "response": reply,
                    "feedback": fb,
                    "session_id": SESSION_ID,
                },
            )
            if fr.ok:
                st.success("📬 Feedback submitted!")
            else:
                st.error("🚫 Failed to send feedback.")
