"""Intent and scope schemas for query parsing and routing."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class IntentTask(str, Enum):
    """Primary intent categories as defined in the system architecture."""

    RANKING = "ranking"
    TREND = "trend"
    FORECAST = "forecast"


class SortOrder(str, Enum):
    """Sorting order for ranking tasks."""

    ASC = "asc"
    DESC = "desc"


class QueryScope(BaseModel):
    """Extracted scope, dimensions, and filter constraints from the query."""

    store_id: Optional[int] = Field(
        default=None,
        description="Target Store ID (integer 1-10), or None if not restricted to a single store.",
    )
    item_id: Optional[int] = Field(
        default=None,
        description="Target Item ID (integer 1-50), or None if not restricted to a single item.",
    )
    start_date: Optional[str] = Field(
        default=None,
        description="Historical or reference start date in YYYY-MM-DD format.",
    )
    end_date: Optional[str] = Field(
        default=None,
        description="Historical or reference end date in YYYY-MM-DD format.",
    )
    forecast_horizon_days: Optional[int] = Field(
        default=None,
        description="Number of forward-looking days to predict for forecast tasks.",
    )
    limit: Optional[int] = Field(
        default=None,
        description="Number of records to return (e.g., Top 5, Top 10).",
    )
    order: Optional[SortOrder] = Field(
        default=None,
        description="Sorting direction for ranking tasks (asc for bottom/lowest, desc for top/highest).",
    )
    group_by: Optional[str] = Field(
        default=None,
        description="Dimension to aggregate or rank by: 'store', 'item', or 'date'.",
    )

    @field_validator("store_id")
    @classmethod
    def validate_store_id(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (1 <= v <= 10):
            raise ValueError(f"Store ID must be between 1 and 10, got {v}")
        return v

    @field_validator("item_id")
    @classmethod
    def validate_item_id(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (1 <= v <= 50):
            raise ValueError(f"Item ID must be between 1 and 50, got {v}")
        return v


class StructuredIntent(BaseModel):
    """Validated structured intent produced by the Query Parser LLM."""

    raw_query: str = Field(description="The original user query text.")
    task: IntentTask = Field(
        description="Primary analytical category: 'ranking', 'trend', or 'forecast'."
    )
    scope: QueryScope = Field(
        default_factory=QueryScope,
        description="Dimension filters and parameters governing the analytical engine.",
    )
    explanation: Optional[str] = Field(
        default=None,
        description="Brief reasoning describing how the intent and scope were derived.",
    )
