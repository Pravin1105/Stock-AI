"""FastAPI application factory and middleware configuration."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router


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

    return app


app = create_app()
