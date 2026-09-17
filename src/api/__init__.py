"""API package exposing the FastAPI app instance."""

from src.api.app import app, create_app

__all__ = ["app", "create_app"]
