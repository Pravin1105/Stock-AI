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

from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
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

# Mount frontend static assets directory if available
static_dir = api_dir / "static"
if not static_dir.exists():
    static_dir = root_dir / "public"
if not static_dir.exists():
    static_dir = root_dir / "frontend" / "dist"

if (static_dir / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")

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

    import tempfile
    object.__setattr__(settings, "database_path", Path(tempfile.gettempdir()) / "stock_ai.db")
except Exception as e:
    init_error = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"


@app.get("/")
@app.get("/index.html")
def serve_root():
    """Serves compiled frontend index.html if request is routed to FastAPI."""
    for candidate in [
        static_dir / "index.html",
        api_dir / "static" / "index.html",
        root_dir / "public" / "index.html",
        api_dir / "public" / "index.html",
        root_dir / "frontend" / "dist" / "index.html",
    ]:
        if candidate.exists():
            return FileResponse(str(candidate))
    return {"message": "Stock AI API is running. Visit /docs for API documentation.", "status": "ok"}
 
 
@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    candidate = static_dir / "favicon.ico"
    if candidate.exists():
        return FileResponse(str(candidate))
    return Response(status_code=204)


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


@app.get("/api/models")
@app.get("/models")
def get_available_models():
    """Returns available LLM providers, model catalogs, and key availability."""
    try:
        from src.core.config import PROVIDER_METADATA, settings

        providers_info = {}
        for prov_key, info in PROVIDER_METADATA.items():
            server_key = False
            if prov_key == "gemini":
                server_key = bool(settings.gemini_api_key)
            elif prov_key == "openai":
                server_key = bool(settings.openai_api_key)
            elif prov_key == "anthropic":
                server_key = bool(settings.anthropic_api_key)
            elif prov_key == "groq":
                server_key = bool(settings.groq_api_key)

            providers_info[prov_key] = {
                "name": info["name"],
                "default_model": info["default_model"],
                "models": info["models"],
                "has_server_key": server_key,
            }

        return {
            "default_provider": settings.default_provider,
            "providers": providers_info,
        }
    except Exception as e:
        return {
            "default_provider": "gemini",
            "providers": {},
            "error": str(e),
        }


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None


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
        response = pipeline.run(
            query=clean_query,
            provider=req.provider,
            model=req.model,
            api_key=req.api_key,
        )
        return {
            "query": response.query,
            "intent": response.intent.model_dump(mode="json"),
            "result": response.result.model_dump(mode="json"),
            "explanation": response.explanation,
            "provider": response.provider,
            "model": response.model,
        }
    except Exception as err:
        err_msg = str(err)
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(
            status_code=500,
            detail=f"Backend execution error: {err_msg}",
        ) from err


# --- v2.0 Ingestion Endpoints ---

class SalesRecordItem(BaseModel):
    date: str
    store: int
    item: int
    sales: float


class SalesBatchRequest(BaseModel):
    records: List[SalesRecordItem]
    mode: str = "upsert"


class CsvPayloadRequest(BaseModel):
    csv_data: str
    mode: str = "upsert"


@app.post("/api/ingest/csv")
def ingest_csv_data(req: CsvPayloadRequest):
    try:
        from src.data.ingestion import DataIngestionPipeline
        pipeline = DataIngestionPipeline()
        summary = pipeline.ingest(req.csv_data, mode=req.mode)
        if summary.status == "failed":
            raise HTTPException(status_code=400, detail={"message": "CSV ingestion failed", "summary": summary.to_dict()})
        return summary.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/ingest/sales")
def ingest_sales_batch(req: SalesBatchRequest):
    try:
        from src.data.ingestion import DataIngestionPipeline
        import pandas as pd
        if not req.records:
            raise HTTPException(status_code=400, detail="Records list cannot be empty.")
        records_data = [r.model_dump() for r in req.records]
        df = pd.DataFrame(records_data)
        pipeline = DataIngestionPipeline()
        summary = pipeline.ingest(df, mode=req.mode)
        if summary.status == "failed":
            raise HTTPException(status_code=400, detail={"message": "Sales ingestion failed", "summary": summary.to_dict()})
        return summary.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# --- v2.0 Training Endpoints ---

class RetrainRequest(BaseModel):
    holdout_days: int = 90
    n_estimators: int = 60
    max_depth: int = 6
    learning_rate: float = 0.08
    tolerance_pct: float = 0.0
    background: bool = True


@app.post("/api/train/retrain")
def trigger_retraining(req: RetrainRequest = RetrainRequest()):
    try:
        from src.training.scheduler import TrainingScheduler
        scheduler = TrainingScheduler.get_instance()
        return scheduler.trigger_job(
            background=req.background,
            holdout_days=req.holdout_days,
            n_estimators=req.n_estimators,
            max_depth=req.max_depth,
            learning_rate=req.learning_rate,
            tolerance_pct=req.tolerance_pct,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/train/status")
def get_training_status():
    from src.training.scheduler import TrainingScheduler
    return TrainingScheduler.get_instance().get_status()


@app.get("/api/train/models")
def list_registered_models():
    from src.training.registry import ModelRegistry
    registry = ModelRegistry.get_instance()
    return {
        "active_version": registry.get_active_version(),
        "models": registry.list_models(),
    }


