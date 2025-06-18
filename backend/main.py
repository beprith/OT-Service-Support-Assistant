import requests
from fastapi import FastAPI, UploadFile, File, Form,Body
from fastapi.middleware.cors import CORSMiddleware
import os
from typing import Any, Dict

from datetime import datetime

from requests import session

app = FastAPI()

# CORS so Streamlit can talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Optional: restrict to Streamlit origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploaded_files"


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), session_id: str = Form(...)):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    os.makedirs(os.path.join(UPLOAD_DIR,session_id), exist_ok=True)
    file_path = os.path.join(os.path.join(UPLOAD_DIR,session_id), filename)

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    path = os.path.abspath(os.path.join(UPLOAD_DIR,session_id))
    print(path)
    url = f"http://127.0.0.1:7860/api/v1/run/241b68b2-7e77-49f1-b2f7-f752729c2ae0"
    print(url)
    call_langflow(session_id,url,path)
    return {
        "status": "success",
        "filename": filename,
        "file_path": file_path,
        "session_id": session_id
    }

def call_langflow(session_id,url,data):
    # Request payload configuration
    payload = {
        "session_id" : session_id,
        "input_value": data,  # The input value to be processed by the flow
        "output_type": "chat",  # Specifies the expected output format
        "input_type": "chat"  # Specifies the input format
    }

    # Request headers
    headers = {
        "Content-Type": "application/json"
    }

    try:
        # Send API request
        response = requests.request("POST", url, json=payload, headers=headers)
        response.raise_for_status()  # Raise exception for bad status codes

        # Print response
        return response.text

    except requests.exceptions.RequestException as e:
        print(f"Error making API request: {e}")
    except ValueError as e:
        print(f"Error parsing response: {e}")


@app.post("/api/query")
async def query_text(payload: Dict[str, Any] = Body(...)):

    url = f"http://127.0.0.1:7860/api/v1/run/9763e618-c8a0-43aa-b601-96f6f15ca162?stream=false"
    print(url)
    print(payload["session_id"])
    print(payload["query"])
    response = call_langflow(payload["session_id"],url,payload["query"])
    return {
        "status": "success",
        "session_id": payload["session_id"],
        "response" : response

    }
