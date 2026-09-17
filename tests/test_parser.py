"""Unit tests for query parsing and routing."""

from unittest.mock import MagicMock, patch
import pytest

from src.routing.parser import (
    GeminiQueryParser,
    QueryParserError,
    RuleBasedQueryParser,
)
from src.schemas.intent import IntentTask, SortOrder, StructuredIntent


def test_empty_query_raises_error():
    """Empty or whitespace queries must be rejected."""
    parser = RuleBasedQueryParser()
    with pytest.raises(ValueError):
        parser.parse("   ")


def test_rule_based_parser_ranking():
    """RuleBasedQueryParser correctly routes ranking queries."""
    parser = RuleBasedQueryParser()
    intent = parser.parse("Show me top 5 items in store 2")

    assert intent.task == IntentTask.RANKING
    assert intent.scope.store_id == 2
    assert intent.scope.limit == 5
    assert intent.scope.order == SortOrder.DESC
    assert intent.scope.group_by == "item"


def test_rule_based_parser_trend():
    """RuleBasedQueryParser correctly routes trend queries."""
    parser = RuleBasedQueryParser()
    intent = parser.parse("Show sales trend for item 15 in store 4 over time")

    assert intent.task == IntentTask.TREND
    assert intent.scope.store_id == 4
    assert intent.scope.item_id == 15


def test_rule_based_parser_forecast():
    """RuleBasedQueryParser correctly routes forecast queries."""
    parser = RuleBasedQueryParser()
    intent = parser.parse("Forecast sales for store 5 item 10 for the next 14 days")

    assert intent.task == IntentTask.FORECAST
    assert intent.scope.store_id == 5
    assert intent.scope.item_id == 10
    assert intent.scope.forecast_horizon_days == 14


@patch("src.routing.parser.genai.Client")
def test_gemini_query_parser_mocked(mock_client_cls):
    """Test GeminiQueryParser integration with mocked client returning structured JSON."""
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client

    mock_response = MagicMock()
    mock_response.text = """
    {
        "raw_query": "Forecast demand for store 1 item 5 next week",
        "task": "forecast",
        "scope": {
            "store_id": 1,
            "item_id": 5,
            "forecast_horizon_days": 7
        },
        "explanation": "Predicted future demand for store 1 and item 5 over 7 days."
    }
    """
    mock_client.models.generate_content.return_value = mock_response

    parser = GeminiQueryParser(api_key="fake-api-key")
    intent = parser.parse("Forecast demand for store 1 item 5 next week")

    assert isinstance(intent, StructuredIntent)
    assert intent.task == IntentTask.FORECAST
    assert intent.scope.store_id == 1
    assert intent.scope.item_id == 5
    assert intent.scope.forecast_horizon_days == 7


@patch("src.routing.parser.genai.Client")
def test_gemini_query_parser_invalid_json(mock_client_cls):
    """Test GeminiQueryParser raises QueryParserError when invalid response is returned."""
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client

    mock_response = MagicMock()
    mock_response.text = "This is not valid json"
    mock_client.models.generate_content.return_value = mock_response

    parser = GeminiQueryParser(api_key="fake-api-key")
    with pytest.raises(QueryParserError):
        parser.parse("Forecast demand for store 1")
