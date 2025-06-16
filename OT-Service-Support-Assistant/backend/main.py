from fastapi import FastAPI
from backend.upload_handler import router as upload_router
from backend.query_handler import router as query_router
from backend.feedback_handler import router as feedback_router

app = FastAPI()

# Mount all routers
app.include_router(upload_router)
app.include_router(query_router)
app.include_router(feedback_router)

# Serve images (if needed)
from fastapi.staticfiles import StaticFiles
app.mount("/images", StaticFiles(directory="images"), name="images")

