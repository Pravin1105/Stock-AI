"""Vercel serverless function entrypoint for Stock AI FastAPI backend."""

import sys
import traceback
from pathlib import Path

# Add project root to sys.path so 'src' can be resolved by Python runtime
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

try:
    from src.api.app import app
except Exception as e:
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    err_trace = traceback.format_exc()
    print(f"Error initializing Stock AI app: {err_trace}", file=sys.stderr)

    app = FastAPI(title="Stock AI API (Error Fallback)")

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
    async def fallback_handler(path: str):
        return JSONResponse(
            status_code=500,
            content={
                "error": "Backend initialization error",
                "detail": str(e),
                "trace": err_trace,
            },
        )

# Export FastAPI app instance for Vercel ASGI runner
__all__ = ["app"]
