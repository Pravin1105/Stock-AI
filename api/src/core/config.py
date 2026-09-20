"""Core configuration and settings for Stock AI."""

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Automatically load environment variables from .env file if present
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    """Application settings and API configurations."""

    # Gemini API Settings
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    # Project Paths
    base_dir: Path = BASE_DIR
    dataset_dir: Path = BASE_DIR / "dataset"
    model_dir: Path = BASE_DIR / "model"


# Global settings singleton
settings = Settings()
