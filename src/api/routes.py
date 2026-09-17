"""FastAPI routes for Stock AI analytical services."""

from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.pipeline import StockAIPipeline
from src.schemas.intent import StructuredIntent
from src.schemas.results import UnifiedResult

router = APIRouter(prefix="/api")

# Singleton pipeline instance for request processing
pipeline = StockAIPipeline()


class QueryRequest(BaseModel):
    """User query payload."""
    query: str = Field(..., min_length=1, description="Natural language user question.")


class QueryResponse(BaseModel):
    """Unified API response mirroring PipelineResponse."""
    query: str
    intent: StructuredIntent
    result: UnifiedResult
    explanation: str


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


@router.post("/query", response_model=QueryResponse)
def execute_query(req: QueryRequest) -> QueryResponse:
    """Execute end-to-end analytical pipeline: routing, retrieval, and explanation."""
    clean_query = req.query.strip()
    if not clean_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    try:
        response = pipeline.run(clean_query)
        return QueryResponse(
            query=response.query,
            intent=response.intent,
            result=response.result,
            explanation=response.explanation,
        )
    except Exception as err:
        raise HTTPException(
            status_code=500, detail=f"Pipeline execution failed: {err}"
        ) from err
