"""
Vercel Serverless Python ASGI Entrypoint for SentinelIQ Frontend
"""
import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from frontend.app import app

# Export app for Vercel serverless runtime
__all__ = ["app"]
