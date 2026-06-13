"""
FastAPI application entry point.
Imports the real application from backend.app.main so that the Dockerfile
CMD ("python -m uvicorn backend.app.main:app") serves the full platform,
not a skeleton health-check endpoint.
"""
import sys
import os

# Ensure backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

from backend.app.main import app  # noqa: F401  -- re-export for uvicorn
