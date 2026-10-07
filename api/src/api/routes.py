"""FastAPI routes for Stock AI analytical services."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.core.config import PROVIDER_METADATA, settings
from src.pipeline import StockAIPipeline
from src.schemas.intent import StructuredIntent
from src.schemas.results import UnifiedResult

router = APIRouter(prefix="/api")

# Singleton pipeline instance for request processing
pipeline = StockAIPipeline()


class QueryRequest(BaseModel):
    """User query payload with optional LLM provider override and BYOK API key."""
    query: str = Field(..., min_length=1, description="Natural language user question.")
    provider: Optional[str] = Field(default=None, description="LLM provider: gemini, openai, anthropic, groq.")
    model: Optional[str] = Field(default=None, description="Specific model name.")
    api_key: Optional[str] = Field(default=None, description="User-provided API key (BYOK).")


class QueryResponse(BaseModel):
    """Unified API response mirroring PipelineResponse."""
    query: str
    intent: StructuredIntent
    result: UnifiedResult
    explanation: str
    provider: Optional[str] = None
    model: Optional[str] = None


class ProviderDetail(BaseModel):
    name: str
    default_model: str
    models: List[str]
    has_server_key: bool


class ModelsResponse(BaseModel):
    default_provider: str
    providers: Dict[str, ProviderDetail]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    engines: List[str]


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Returns application health status and active engines."""
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        engines=["SQL/Data (Ranking)", "Statistics (Trend)", "XGBoost (Forecast)"],
    )


@router.get("/models", response_model=ModelsResponse)
def get_available_models() -> ModelsResponse:
    """Returns available LLM providers, model options, and server-key status."""
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

        providers_info[prov_key] = ProviderDetail(
            name=info["name"],
            default_model=info["default_model"],
            models=info["models"],
            has_server_key=server_key,
        )

    return ModelsResponse(
        default_provider=settings.default_provider,
        providers=providers_info,
    )


@router.post("/query", response_model=QueryResponse)
def execute_query(req: QueryRequest) -> QueryResponse:
    """Execute end-to-end analytical pipeline: routing, retrieval, and explanation."""
    clean_query = req.query.strip()
    if not clean_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    try:
        response = pipeline.run(
            query=clean_query,
            provider=req.provider,
            model=req.model,
            api_key=req.api_key,
        )
        return QueryResponse(
            query=response.query,
            intent=response.intent,
            result=response.result,
            explanation=response.explanation,
            provider=response.provider,
            model=response.model,
        )
    except Exception as err:
        raise HTTPException(
            status_code=500, detail=f"Pipeline execution failed: {err}"
        ) from err

