"""Vercel serverless function entrypoint for Stock AI FastAPI backend."""

import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add project root to sys.path so 'src' can be resolved by Python runtime
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.api.routes import router

# Top-level FastAPI instance explicitly defined for Vercel runtime detection
app = FastAPI(
    title="Stock AI API",
    description="Two-Stage LLM Analytics Architecture for Retail Sales & Demand Forecasting",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
