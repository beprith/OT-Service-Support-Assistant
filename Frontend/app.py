# app.py  – OT Service Support Assistant
# Streamlit UI to chat with SOP bot, track tasks, images, & logging

import os, uuid, json, csv, io, re, base64, binascii
from datetime import datetime

import streamlit as st
import requests

# ───────────────────────── helpers ──────────────────────────
def _decode_b64(data: str) -> bytes | None:
    """Return bytes from base-64 string or None if invalid."""
    data = data.strip()
    pad  = (-len(data)) % 4
    try:
        return base64.b64decode(data + "=" * pad)
    except binascii.Error:
        return None


def extract_img_src(text: str) -> list[str]:
    """
    Pull base64 payloads from <img src="data:image/png;base64, …"> tags.
    Handles single block or chunked format like [4,'...'].
    """
    out = []
    for val in re.findall(r'<img[^>]+src="data:image/png;base64,([^"]+)"', text):
        m = re.match(r"\[\s*\d+\s*,\s*'([A-Za-z0-9+/=]+)'\s*\]", val)
        out.append(m.group(1) if m else val)
    return out

def _back_to_chat():
    st.session_state["mode_select"] = "Chat"



# thumbnail + expander
FIXED_IMG_WIDTH = 300
def display_answer_with_images(html: str):
    imgs = extract_img_src(html)
    cleaned = re.sub(r'<img[^>]*>', '', html, flags=re.IGNORECASE)
    st.markdown(cleaned, unsafe_allow_html=True)

    for i, b64 in enumerate(imgs, start=1):
        img = _decode_b64(b64)
        if not img:
            st.warning(f"Image {i} could not be decoded.")
            continue
        st.image(img, caption=f"Related image {i}", width=FIXED_IMG_WIDTH)
        with st.expander("🔍 Click to view full size", expanded=False):
            st.image(img, use_container_width=True)

# ─────────────────────── page config ────────────────────────
st.set_page_config("OT Service Support Assistant", "🤖", layout="wide")
css_path = os.path.join(os.path.dirname(__file__), "static", "style.css")
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown(
    """
<div class="app-header">
  <h1>🔧 OT Service Support Assistant | Powered by Langflow</h1>
  <h2>🤖 Chat with the SOP Bot</h2>
  <p>Type below and hit ⏎ or click <i>Send</i> to start the conversation.</p>
</div>
""",
    unsafe_allow_html=True,
)

# ───────────────────── env & session state ──────────────────
UPLOAD_URL = os.getenv("UPLOAD_URL", "http://localhost:8000/api/upload")
QUERY_URL  = os.getenv("QUERY_URL",  "http://localhost:8000/api/query")

if "all_sessions"        not in st.session_state: st.session_state.all_sessions        = []
if "histories"           not in st.session_state: st.session_state.histories           = {}
if "processed_files_map" not in st.session_state: st.session_state.processed_files_map = {}
if "prepopulate_prompt" not in st.session_state:
    st.session_state["prepopulate_prompt"] = ""
if "last_suggestions" not in st.session_state:
    st.session_state["last_suggestions"] = []
if "pending_suggestion" not in st.session_state:
    st.session_state["pending_suggestion"] = ""



if not st.session_state.all_sessions:
    sid = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    st.session_state.all_sessions.append(sid)
    st.session_state.histories[sid]           = []
    st.session_state.processed_files_map[sid] = {}
    st.session_state.session_id = sid

SESSION_ID    = st.session_state.session_id
chat_history  = st.session_state.histories.setdefault(SESSION_ID, [])
session_files = st.session_state.processed_files_map.setdefault(SESSION_ID, {})

# ───────────────────────── sidebar ──────────────────────────
with st.sidebar:
    st.markdown("## Settings")

    with st.expander("Session Management", True):
        idx = st.session_state.all_sessions.index(SESSION_ID)
        selected = st.selectbox(
            "Select session",
            st.session_state.all_sessions,
            index=idx,
        )
        if selected != SESSION_ID:
            st.session_state.session_id = selected
            # Clear suggestions here
            st.session_state["last_suggestions"] = []
            st.session_state["pending_suggestion"] = ""
            st.rerun()

        if st.button("🔄 New session"):
            new_sid = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
            st.session_state.all_sessions.append(new_sid)
            st.session_state.histories[new_sid] = []
            st.session_state.processed_files_map[new_sid] = {}
            st.session_state.session_id = new_sid
            # Clear suggestions for the new session
            st.session_state["last_suggestions"] = []
            st.session_state["pending_suggestion"] = ""
            st.rerun()

    with st.expander("Upload Center", True):
        st.markdown("Upload your SOPs or logs for analysis.")
        if session_files:
            st.markdown("**Uploaded files:**")
            for fname in session_files:
                st.markdown(f"- {fname}")
                st.download_button("Download",
                                   data=session_files[fname],
                                   file_name=fname,
                                   key=f"dl_{SESSION_ID}_{fname}")

        uploads = st.file_uploader("Select files",
                                   type=["pdf", "docx", "txt"],
                                   accept_multiple_files=True,
                                   key=f"uploader_{SESSION_ID}")
        for up in uploads or []:
            if up.name not in session_files:
                bio = io.BytesIO(up.getvalue()); bio.name = up.name
                with st.spinner(f"Uploading {up.name}…"):
                    res = requests.post(UPLOAD_URL,
                                        files={"file": (up.name, bio, up.type)},
                                        data={"session_id": SESSION_ID})
                if res.ok:
                    st.success(f"Uploaded {up.name}")
                    session_files[up.name] = up.getvalue()
                else:
                    st.error(f"Failed to upload {up.name}")

    st.markdown("---")
    # key lets us switch programmatically
    mode = st.radio("Mode", ("Chat", "Task"), key="mode_select")
    st.markdown(f"**🆔 Session ID:** `{SESSION_ID}`")

    with st.expander("Session History", False):
        for m in chat_history:
            st.markdown(f"**{m['role'].capitalize()}:** {m['content']}")

# ───────────────────── helper for html check ─────────────────
def is_html(text: str) -> bool:
    t = text.strip().lower()
    return t.startswith("<!doctype html") or t.startswith("<html")

def strip_json_block(answer: str) -> str:
    # Remove any ```json ... ``` block from the answer
    return re.sub(r"```json.*?```", "", answer, flags=re.DOTALL).strip()

def get_suggestions_from_resp(resp):
    print("DEBUG: Checking resp:", type(resp), "keys:", list(resp.keys()))
    suggestions = []
    try:
        outputs = resp.get("outputs", [])
        print("DEBUG: Outputs length:", len(outputs))
        # 1. Normal second output block (as before)
        if len(outputs) > 1:
            sugg_output = outputs[1]
            msg = sugg_output["outputs"][0]["results"]["message"]
            if "data" in msg and "text" in msg["data"]:
                sugg_text = msg["data"]["text"]
            else:
                sugg_text = msg.get("text", "")
            clean = re.sub(r'^```json\s*|\s*```$', '', sugg_text, flags=re.DOTALL).strip()
            print("DEBUG: Suggestions text block:\n", clean)
            try:
                parsed = json.loads(clean)
                suggestions = parsed.get("suggestions", [])
                print("DEBUG: Suggestions list:", suggestions)
            except Exception as e:
                print("DEBUG: JSON decode failed:", e)
        # 2. Fallback: look for ```json ... ``` inside outputs[0]
        elif len(outputs) == 1:
            main_output = outputs[0]
            msg = main_output["outputs"][0]["results"]["message"]
            text = msg.get("data", {}).get("text", "") or msg.get("text", "")
            # Find code block: ```json ... ```
            json_match = re.search(r'```json(.*?)```', text, re.DOTALL)
            if json_match:
                clean = json_match.group(1).strip()
                print("DEBUG: Fallback suggestions block:\n", clean)
                try:
                    parsed = json.loads(clean)
                    suggestions = parsed.get("suggestions", [])
                    print("DEBUG: Suggestions (fallback):", suggestions)
                except Exception as e:
                    print("DEBUG: Fallback JSON parse failed:", e)
            else:
                print("DEBUG: No suggestion JSON block found in main output!")
        else:
            print("DEBUG: No outputs in response!")
    except Exception as e:
        print("DEBUG: Exception in suggestion parse:", e)
    print("DEBUG: Final suggestions list:", suggestions)
    return suggestions

# --- Chat Mode ---
if mode == "Chat":
    # 1. Display chat history
    for m in chat_history:
        with st.chat_message(m["role"]):
            if m["role"] == "assistant":
                display_answer_with_images(strip_json_block(m["content"]))
            else:
                st.markdown(m["content"], unsafe_allow_html=True)

    # 2. Suggestion buttons and banner
    suggestions = st.session_state.get("last_suggestions", [])
    pending = st.session_state.get("pending_suggestion", "")
    # Show info banner if a suggestion was clicked
    if pending:
        st.info(
            f"💡 **Suggestion:**\n\n`{pending}`\n\n"
            "Click in the chat box and paste, or type your question."
        )

    # The chat input
    prompt = st.chat_input("Ask me about your SOP…")
    if prompt:
        # Clear banner after any send
        st.session_state["pending_suggestion"] = ""
        # Process user input as usual
        st.chat_message("user").write(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                res = requests.post(
                    QUERY_URL,
                    json={"query": prompt, "session_id": SESSION_ID},
                    timeout=90
                )
                res.raise_for_status()
                outer = res.json()
                resp = outer.get("response")
                if isinstance(resp, str) and resp.strip().startswith("{"):
                    resp = json.loads(resp)
                answer = ""
                try:
                    answer = (
                        resp["outputs"][0]["outputs"][0]["results"]["message"]["text"]
                        if isinstance(resp, dict) else str(resp)
                    )
                except Exception:
                    answer = str(resp)
                answer_main = strip_json_block(answer)
                display_answer_with_images(answer_main)

                # Suggestions extraction
                new_suggestions = get_suggestions_from_resp(resp)
                st.session_state["last_suggestions"] = new_suggestions
                if new_suggestions:
                    st.markdown("#### 💡 You might also ask:")
                    cols = st.columns(min(len(new_suggestions), 3))
                    for i, q in enumerate(new_suggestions):
                        if cols[i % 3].button(q, key=f"sugg_{i}"):
                            st.session_state["pending_suggestion"] = q
                            st.rerun()
                else:
                    st.session_state["last_suggestions"] = []
                    st.info("No suggestions found.")

        # Update chat history after successful run
        chat_history.append({"role": "user", "content": prompt})
        chat_history.append({"role": "assistant", "content": answer_main})

    else:
        # Only show suggestions if there is no active prompt being sent
        if suggestions:
            st.markdown("#### 💡 You might also ask:")
            cols = st.columns(min(len(suggestions), 3))
            for i, q in enumerate(suggestions):
                if cols[i % 3].button(q, key=f"sugg_{i}"):
                    st.session_state["pending_suggestion"] = q
                    st.rerun()



# ─────────────────────── TASK MODE ──────────────────────────
else:
    if not chat_history or chat_history[-1]["role"] != "assistant":
        st.info("Run a chat first so we have something to convert into tasks.")
        st.stop()

    raw_html  = chat_history[-1]["content"]
    img_srcs  = extract_img_src(raw_html)
    chat_text = re.sub(r'<img[^>]*>', '', raw_html, flags=re.IGNORECASE)

    num_pat = re.compile(r"^\s*(\d+)[\.\)\-]\s+(.+)$")
    bul_pat = re.compile(r"^\s*([\-\*\u2022]|•)\s+(.+)$")

    tasks, misc, current = [], [], None
    for raw in chat_text.splitlines():
        line = raw.rstrip()
        if m := num_pat.match(line):
            current = {"id": int(m.group(1)),
                       "description": m.group(2).strip(),
                       "sublines": []}
            tasks.append(current)
        elif (m := bul_pat.match(line)) and current:
            current["sublines"].append(m.group(2).strip())
        elif line.strip():
            misc.append(line)

    if not tasks:
        st.info("I couldn’t find any numbered items in the last reply.")
    else:
        st.markdown("### Task checklist")
        TASK_TYPES = ("General", "Mechanical", "Electrical",
                      "IPC-network", "Docs", "Other")

        for t in tasks:
            # checkbox
            ck_key = f"{SESSION_ID}_task_{t['id']}"
            checked = st.checkbox(t["description"],
                                  value=st.session_state.get(ck_key, False),
                                  key=ck_key)

            # sub-bullets
            for sub in t["sublines"]:
                st.markdown(f"&nbsp;&nbsp;&nbsp;• {sub}")

            # task type selector (same row)
            type_key = f"{SESSION_ID}_type_{t['id']}"
            default_type = st.session_state.get(type_key, "General")
            task_type = st.selectbox(
                "Type",
                TASK_TYPES,
                index=TASK_TYPES.index(default_type),
                key=type_key,
                label_visibility="collapsed",
            )

            # record change
            prev = st.session_state.get(ck_key, False)
            if checked != prev:
                st.session_state[ck_key] = checked
                st.session_state[type_key] = task_type

                log_exists = os.path.exists("interactions.csv")
                with open("interactions.csv", "a", newline="", encoding="utf-8") as f:
                    w = csv.writer(f)
                    if not log_exists:
                        w.writerow(["timestamp", "session_id", "task_id",
                                    "description", "task_type", "status"])
                    w.writerow([
                        datetime.now().isoformat(timespec="seconds"),
                        SESSION_ID,
                        t["id"],
                        t["description"],
                        task_type,
                        "completed" if checked else "incomplete",
                    ])

        # simple progress by type
        by_type = {}
        for t in tasks:
            typ = st.session_state.get(f"{SESSION_ID}_type_{t['id']}", "General")
            done = st.session_state.get(f"{SESSION_ID}_task_{t['id']}", False)
            by_type.setdefault(typ, {"total": 0, "done": 0})
            by_type[typ]["total"] += 1
            by_type[typ]["done"]  += 1 if done else 0

        st.markdown("#### Progress by task type")
        for typ, stat in by_type.items():
            st.text(f"{typ}: {stat['done']}/{stat['total']} completed")

    # related images
    if img_srcs:
        st.markdown("---")
        st.markdown("#### Related images")
        for i, b64 in enumerate(img_srcs, start=1):
            img = _decode_b64(b64)
            if img:
                st.image(img, caption=f"Image {i}", width=FIXED_IMG_WIDTH)

    if misc:
        st.markdown("---")
        st.markdown("#### Additional notes")
        for line in misc:
            st.markdown(line)

    # ── Done button → switch back to Chat mode
    st.markdown("---")
    st.button(
        "✅ Done with tasks – back to chat",
        on_click=_back_to_chat,  # ← call the helper you defined above
    )