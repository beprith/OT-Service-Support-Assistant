import os
import json
from datetime import datetime
from typing import Any, Dict

import requests
from fastapi import FastAPI, UploadFile, File, Form, Body
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# ── CORS ───────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # (lock this down in prod)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploaded_files"

# ── Helpers ────────────────────────────────────────────────────────────
def call_langflow(session_id: str, url: str, data: str):
    """Fire a Langflow ‘run’ endpoint and return a *Python* object
    (dict | list | str) that FastAPI can JSON-serialise cleanly.
    """
    payload = {
        "session_id": session_id,
        "input_value": data,
        "output_type": "chat",
        "input_type": "chat",
    }
    headers = {"Content-Type": "application/json"}

    try:
        r = requests.post(url, json=payload, headers=headers)
        r.raise_for_status()

        # Prefer JSON if possible
        try:
            return r.json()      # → dict / list
        except ValueError:
            return r.text        # → str (already plain answer)

    except requests.RequestException as e:
        print(f"[Langflow] Request error: {e}")
        return {"error": str(e)}  # still JSON-serialisable


# ── Routes ─────────────────────────────────────────────────────────────
@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    session_id: str = Form(...),
):
    timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename   = f"{timestamp}_{file.filename}"
    user_dir   = os.path.join(UPLOAD_DIR, session_id)
    os.makedirs(user_dir, exist_ok=True)

    file_path = os.path.join(user_dir, filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())

    path = os.path.abspath(user_dir)
    flow_url = "http://127.0.0.1:7860/api/v1/run/241b68b2-7e77-49f1-b2f7-f752729c2ae0"
    _ = call_langflow(session_id, flow_url, path)

    return {
        "status": "success",
        "filename": filename,
        "file_path": file_path,
        "session_id": session_id,
    }


@app.post("/api/query")
async def query_text(payload: Dict[str, Any] = Body(...)):
    flow_url = (
        "http://127.0.0.1:7860/api/v1/run/"
        "9763e618-c8a0-43aa-b601-96f6f15ca162?stream=false"
    )

    langflow_resp = call_langflow(
        payload["session_id"],
        flow_url,
        payload["query"],
    )

    return {
        "status": "success",
        "session_id": payload["session_id"],
        "response": langflow_resp,   # <— now a dict or safe string
    }
