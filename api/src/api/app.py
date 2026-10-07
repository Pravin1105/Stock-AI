from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.api.routes import router
from src.core.config import settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Stock AI API",
        description="Two-Stage LLM Analytics Architecture for Retail Sales & Demand Forecasting",
        version="0.1.0",
    )

    # Enable CORS for frontend connectivity
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routes
    app.include_router(router)

    # Locate and mount compiled frontend assets
    candidate_dirs = [
        settings.base_dir / "public",
        settings.base_dir / "frontend" / "dist",
        settings.base_dir / "api" / "static",
    ]

    for c_dir in candidate_dirs:
        if (c_dir / "assets").exists():
            app.mount("/assets", StaticFiles(directory=str(c_dir / "assets")), name="assets")
            break

    @app.get("/")
    @app.get("/index.html")
    def serve_root():
        for c_dir in candidate_dirs:
            idx = c_dir / "index.html"
            if idx.exists():
                return FileResponse(str(idx))
        return {"status": "ok", "message": "Stock AI API is active. Visit /docs for documentation."}

    return app


app = create_app()

