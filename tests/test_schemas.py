"""Unit tests for Intent and Scope schemas."""

import pytest
from pydantic import ValidationError

from src.schemas.intent import IntentTask, QueryScope, SortOrder, StructuredIntent


def test_intent_task_enum_values():
    """Verify primary tasks match the system architecture."""
    assert IntentTask.RANKING == "ranking"
    assert IntentTask.TREND == "trend"
    assert IntentTask.FORECAST == "forecast"


def test_query_scope_valid():
    """Test valid query scope creation."""
    scope = QueryScope(
        store_id=5,
        item_id=12,
        forecast_horizon_days=30,
        limit=5,
        order=SortOrder.DESC,
        group_by="item",
    )
    assert scope.store_id == 5
    assert scope.item_id == 12
    assert scope.limit == 5
    assert scope.order == SortOrder.DESC


def test_query_scope_invalid_store_id():
    """Store ID must be constrained between 1 and 10."""
    with pytest.raises(ValidationError):
        QueryScope(store_id=15)

    with pytest.raises(ValidationError):
        QueryScope(store_id=0)


def test_query_scope_invalid_item_id():
    """Item ID must be constrained between 1 and 50."""
    with pytest.raises(ValidationError):
        QueryScope(item_id=55)

    with pytest.raises(ValidationError):
        QueryScope(item_id=-1)


def test_structured_intent_serialization():
    """Test JSON serialization and deserialization of StructuredIntent."""
    raw_json = """
    {
        "raw_query": "What are the top 5 items in Store 3?",
        "task": "ranking",
        "scope": {
            "store_id": 3,
            "limit": 5,
            "order": "desc",
            "group_by": "item"
        },
        "explanation": "Extracted top 5 items for Store 3."
    }
    """
    intent = StructuredIntent.model_validate_json(raw_json)
    assert intent.task == IntentTask.RANKING
    assert intent.scope.store_id == 3
    assert intent.scope.limit == 5
    assert intent.scope.order == SortOrder.DESC
    assert intent.scope.group_by == "item"
