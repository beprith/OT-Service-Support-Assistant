import json
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
UPLOAD_URL = "http://localhost:8000/api/upload"
QUERY_URL = "http://localhost:8000/api/query"
LANGFLOW_API = "http://127.0.0.1:7860/api/v1/run/9763e618-c8a0-43aa-b601-96f6f15ca162"

# --- SESSION SETUP ---
if "session_id" not in st.session_state:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state.session_id = f"{ts}_{uuid.uuid4().hex[:6]}"
SESSION_ID = st.session_state.session_id

# --- SIDEBAR: UPLOAD & SESSION CONTROLS ---
with st.sidebar:
    st.markdown("## 🏭 Upload Center")
    st.markdown("Enhance your session by uploading SOPs or machine logs.")

    up_files = st.file_uploader(
        "Upload SOPs, logs, or instructions",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True
    )

    if up_files:
        for up in up_files:
            with st.spinner(f"Uploading `{up.name}` to backend…"):
                upload_response = requests.post(
                    UPLOAD_URL,
                    files={"file": (up.name, up, up.type)},
                    data={"session_id": SESSION_ID}
                )

            if upload_response.ok:
                res_data = upload_response.json()
                size_kb = round(len(up.getvalue()) / 1024, 2)
                st.success(f"✅ Uploaded: `{up.name}` | {size_kb} KB | {up.type}")

                # 🔁 Send file silently to Langflow
                up.seek(0)
            else:
                st.error(f"❌ Upload failed for `{up.name}`. Please check the backend.")

    st.markdown("---")
    st.markdown(f"**🆔 Session ID:** `{SESSION_ID}`")
    st.markdown("### ⚙️ Assistant Options")
    st.session_state.task_mode_toggle = st.sidebar.checkbox("✅ Enable Task Mode")

    if st.button("🔄 Start New Session"):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        st.session_state.session_id = f"{ts}_{uuid.uuid4().hex[:6]}"
        st.rerun()
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
            res = json.loads(reply)
            message = (
                res["outputs"][0]["outputs"][0]["results"]["message"]["text"]
            )

            # now render it as markdown
            st.markdown(message)

    st.session_state.chat_history.append({"role": "assistant", "content": reply})
