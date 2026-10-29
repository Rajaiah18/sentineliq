"""
Vercel Serverless Python ASGI Entrypoint for SentinelIQ Platform
Serves full application: UI routes, API endpoints, OpenAPI documentation, and health telemetry.
"""
import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.main import app

# Export app for Vercel serverless runtime
__all__ = ["app"]
