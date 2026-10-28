"""
SentinelIQ — Intelligent Transaction Risk & Investigation Platform
Main Application Entry Point
Tagline: Explainable Risk. Traceable Decisions.
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, status, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.config import settings
from backend.app.database.mongodb import check_database_health, close_mongo_connection, get_database
from backend.app.database.indexes import create_all_indexes
from backend.app.database.repository import repo
from backend.app.api.v1 import api_v1_router
from frontend.routes import frontend_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup sequence
    print(f"[{settings.APP_NAME}] Initializing {settings.APP_FULL_NAME} (Env: {settings.APP_ENV})")
    healthy, msg, details = check_database_health()
    if healthy:
        print(f"[{settings.APP_NAME}] Connected to MongoDB Atlas/Local successfully.")
        try:
            db = get_database()
            create_all_indexes(db)
            print(f"[{settings.APP_NAME}] Ensured all collection indexes.")
        except Exception as e:
            print(f"[{settings.APP_NAME}] Index creation note: {e}")
    else:
        print(f"[{settings.APP_NAME}] Database Notice: {msg}")
        if repo.storage_mode == "mongodb":
            print(f"[{settings.APP_NAME}] Tip: {details.get('actionable_advice')}")

    # Ensure memory store is loaded with any existing exports
    repo._try_load_exports_into_memory()
    yield

    # Shutdown sequence
    close_mongo_connection()
    print(f"[{settings.APP_NAME}] Shutdown complete.")


app = FastAPI(
    title="SentinelIQ API",
    description="Intelligent Transaction Risk & Investigation Platform — Explainable Risk. Traceable Decisions.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# CORS Allowlisting
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static Files Mount
if os.path.isdir("frontend/static"):
    app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# Health Check Endpoints
@app.get("/health", tags=["Health"])
def health_liveness():
    """Basic service liveness check."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "full_name": settings.APP_FULL_NAME,
        "tagline": settings.APP_TAGLINE,
        "version": "1.0.0",
        "environment": settings.APP_ENV
    }


@app.get("/health/ready", tags=["Health"])
def health_readiness(response: Response):
    """
    Service readiness check including database ping.
    Never fabricates a successful database connection if unreachable.
    """
    healthy, msg, details = check_database_health()
    if not healthy and settings.APP_STORAGE == "mongodb":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "degraded",
            "database_connected": False,
            "storage_mode": settings.APP_STORAGE,
            "message": msg,
            "details": details
        }

    return {
        "status": "ready",
        "database_connected": healthy,
        "storage_mode": settings.APP_STORAGE,
        "message": msg,
        "details": details
    }


# Include Routers
app.include_router(api_v1_router)
app.include_router(frontend_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
