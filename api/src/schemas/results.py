"""Unified result schema returned by all analytics engines."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from src.schemas.intent import IntentTask, StructuredIntent


class SummaryMetrics(BaseModel):
    """Standardized statistical summary metrics across analytical tasks."""

    total_sales: Optional[float] = Field(default=None, description="Sum of sales for the selection.")
    mean_sales: Optional[float] = Field(default=None, description="Average sales per period/unit.")
    median_sales: Optional[float] = Field(default=None, description="Median sales value.")
    min_sales: Optional[float] = Field(default=None, description="Minimum recorded sales.")
    max_sales: Optional[float] = Field(default=None, description="Maximum recorded sales.")
    record_count: int = Field(default=0, description="Total number of data points or records returned.")


class UnifiedResult(BaseModel):
    """Contract representing the deterministic output of any analytics engine."""

    intent: StructuredIntent = Field(description="The parsed structured intent that generated this result.")
    task: IntentTask = Field(description="The analytical task type executed: ranking, trend, or forecast.")
    status: str = Field(default="success", description="Execution status: 'success' or 'error'.")
    error_message: Optional[str] = Field(default=None, description="Error explanation if status is 'error'.")
    columns: List[str] = Field(default_factory=list, description="Column headers for tabular rendering.")
    records: List[Dict[str, Any]] = Field(default_factory=list, description="Row-level records for tables and charts.")
    summary: SummaryMetrics = Field(default_factory=SummaryMetrics, description="Aggregated summary figures.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Engine-specific metadata (e.g., model version, horizon).")
