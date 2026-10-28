"""
SentinelIQ Standalone Frontend Application
Can be deployed independently (e.g. Vercel Python Serverless ASGI) or mounted within backend.
Directs API queries to API_BASE_URL when deployed separately.
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os

from backend.app.config import settings
from frontend.routes import frontend_router

frontend_app = FastAPI(
    title="SentinelIQ Frontend",
    description="SentinelIQ Server-Rendered UI",
    version="1.0.0"
)

if os.path.isdir("frontend/static"):
    frontend_app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

frontend_app.include_router(frontend_router)

# Vercel entrypoint alias
app = frontend_app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("frontend.app:app", host="0.0.0.0", port=3000, reload=True)
