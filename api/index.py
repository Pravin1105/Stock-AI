"""Vercel serverless function entrypoint for Stock AI FastAPI backend."""

import sys
from pathlib import Path

# Add project root to sys.path so 'src' can be resolved by Python runtime
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.api.app import app

# Export FastAPI app instance for Vercel ASGI runner
__all__ = ["app"]
