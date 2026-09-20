"""Vercel serverless function entrypoint for Stock AI FastAPI backend."""

import os
import sys
import traceback
from pathlib import Path

# Ensure api directory, project root, and any vendored packages are in sys.path BEFORE importing dependencies
api_dir = Path(__file__).resolve().parent
root_dir = api_dir.parent

for candidate in [
    str(api_dir),
    str(root_dir),
    str(api_dir / "_vendor"),
    str(root_dir / "_vendor"),
    str(api_dir / "src"),
]:
    if candidate not in sys.path and Path(candidate).exists():
        sys.path.insert(0, candidate)

# Inject lightweight in-memory scipy stub to satisfy xgboost's top-level
# `import scipy.sparse` without requiring the heavy (150MB+) scipy binary.
# Our forecast engine only uses xgb.Booster and xgb.DMatrix with pandas DataFrames.
try:
    import scipy  # noqa: F401
except ImportError:
    import types

    scipy_mod = types.ModuleType("scipy")
    scipy_mod.__path__ = ["<stub>"]
    scipy_mod.__package__ = "scipy"

    sparse_mod = types.ModuleType("scipy.sparse")
    sparse_mod.__package__ = "scipy.sparse"
    sparse_mod.__path__ = ["<stub>"]

    class _StubSparseMatrix:
        pass

    sparse_mod.csr_matrix = _StubSparseMatrix
    sparse_mod.csc_matrix = _StubSparseMatrix
    sparse_mod.coo_matrix = _StubSparseMatrix
    sparse_mod.csr_array = _StubSparseMatrix
    sparse_mod.csc_array = _StubSparseMatrix
    sparse_mod.coo_array = _StubSparseMatrix
    sparse_mod.issparse = lambda x: False
    sparse_mod.isspmatrix = lambda x: False
    sparse_mod.isspmatrix_csr = lambda x: False
    sparse_mod.isspmatrix_csc = lambda x: False
    sparse_mod.vstack = lambda *a, **k: None

    scipy_mod.sparse = sparse_mod

    special_mod = types.ModuleType("scipy.special")
    special_mod.__package__ = "scipy.special"
    special_mod.softmax = lambda x, **k: None
    special_mod.expit = lambda x: None
    scipy_mod.special = special_mod

    sys.modules["scipy"] = scipy_mod
    sys.modules["scipy.sparse"] = sparse_mod
    sys.modules["scipy.special"] = special_mod

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

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

# Safely initialize settings and point to bundled or root data directories
init_error = None
try:
    from src.core.config import settings

    for candidate in [api_dir, root_dir]:
        if (candidate / "dataset" / "train.csv").exists():
            object.__setattr__(settings, "dataset_dir", candidate / "dataset")
            break

    for candidate in [api_dir, root_dir]:
        if (candidate / "model" / "tuned_xgboost_model.json").exists():
            object.__setattr__(settings, "model_dir", candidate / "model")
            break
except Exception as e:
    init_error = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"


@app.get("/api/health")
@app.get("/health")
@app.get("/api/index.py")
def health_check():
    """Diagnostic health check that reliably reports runtime status without crashing."""
    health_data = {
        "status": "healthy" if init_error is None else "degraded",
        "version": "0.1.0",
        "init_error": init_error,
        "python_version": sys.version,
        "api_dir": str(api_dir),
        "api_contents": [p.name for p in api_dir.iterdir()] if api_dir.exists() else [],
    }

    if init_error is None:
        health_data["train_csv_found"] = (settings.dataset_dir / "train.csv").exists()
        health_data["train_csv_path"] = str(settings.dataset_dir / "train.csv")
        health_data["model_file_found"] = (settings.model_dir / "tuned_xgboost_model.json").exists()
        health_data["model_file_path"] = str(settings.model_dir / "tuned_xgboost_model.json")
        health_data["gemini_api_key_configured"] = bool(settings.gemini_api_key)
        try:
            import xgboost
            health_data["xgboost_version"] = getattr(xgboost, "__version__", "loaded")
        except Exception as e:
            health_data["xgboost_error"] = str(e)

    return health_data


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)


# Lazy-loaded pipeline singleton to prevent cold-start import crashes
_pipeline = None


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        if init_error is not None:
            raise RuntimeError(f"Config init failed:\n{init_error}")
        from src.pipeline import StockAIPipeline
        _pipeline = StockAIPipeline()
    return _pipeline


@app.post("/api/query")
@app.post("/query")
@app.post("/api/index.py")
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
