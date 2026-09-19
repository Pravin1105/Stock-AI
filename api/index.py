"""Vercel serverless function entrypoint for Stock AI FastAPI backend."""

import sys
import traceback
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Add project root to sys.path so 'src' can be resolved by Python runtime
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

api_dir = Path(__file__).resolve().parent

# Ensure dataset_dir and model_dir point to available paths (root or api bundle)
from src.core.config import settings

for candidate in [api_dir, root_dir]:
    if (candidate / "dataset" / "train.csv").exists():
        object.__setattr__(settings, "dataset_dir", candidate / "dataset")
        break

for candidate in [api_dir, root_dir]:
    if (candidate / "model" / "tuned_xgboost_model.json").exists():
        object.__setattr__(settings, "model_dir", candidate / "model")
        break

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


@app.get("/api/health")
def health_check():
    """Diagnostic health check that reliably reports runtime status without crashing."""
    diagnostics = {
        "train_csv": str(settings.dataset_dir / "train.csv"),
        "train_csv_found": (settings.dataset_dir / "train.csv").exists(),
        "model_file": str(settings.model_dir / "tuned_xgboost_model.json"),
        "model_file_found": (settings.model_dir / "tuned_xgboost_model.json").exists(),
        "gemini_api_key_configured": bool(settings.gemini_api_key),
    }

    try:
        import xgboost
        diagnostics["xgboost_version"] = getattr(xgboost, "__version__", "loaded")
    except Exception as e:
        diagnostics["xgboost_error"] = str(e)

    return {
        "status": "healthy" if diagnostics.get("train_csv_found") else "degraded",
        "version": "0.1.0",
        "engines": ["SQL/Data (Ranking)", "Statistics (Trend)", "XGBoost (Forecast)"],
        "diagnostics": diagnostics,
    }


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)


# Lazy-loaded pipeline singleton to prevent cold-start import crashes
_pipeline = None


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        from src.pipeline import StockAIPipeline
        _pipeline = StockAIPipeline()
    return _pipeline


@app.post("/api/query")
def execute_query(req: QueryRequest):
    """Execute query with full exception capturing and error reporting."""
    clean_query = req.query.strip()
    if not clean_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    try:
        pipeline = get_pipeline()
        response = pipeline.run(clean_query)
        return {
            "query": response.query,
            "intent": response.intent.model_dump(mode="json"),
            "result": response.result.model_dump(mode="json"),
            "explanation": response.explanation,
        }
    except Exception as err:
        err_msg = str(err)
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(
            status_code=500,
            detail=f"Backend execution error: {err_msg}",
        ) from err
