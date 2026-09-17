"""Unit tests for explanation engines and the end-to-end pipeline."""

from unittest.mock import MagicMock, patch
import pytest

from src.analytics.router import AnalyticsDispatcher
from src.explanation.explainer import GeminiExplainer, TemplateExplainer
from src.pipeline import StockAIPipeline
from src.schemas.intent import IntentTask, QueryScope, SortOrder, StructuredIntent
from src.schemas.results import SummaryMetrics, UnifiedResult


def test_template_explainer_ranking():
    """Verify TemplateExplainer formats ranking data with markdown."""
    intent = StructuredIntent(
        raw_query="Top 2 stores",
        task=IntentTask.RANKING,
        scope=QueryScope(limit=2, order=SortOrder.DESC, group_by="store"),
    )
    result = UnifiedResult(
        intent=intent,
        task=IntentTask.RANKING,
        columns=["rank", "store", "total_sales"],
        records=[
            {"rank": 1, "store": 2, "total_sales": 6120128.0},
            {"rank": 2, "store": 8, "total_sales": 5856169.0},
        ],
        summary=SummaryMetrics(total_sales=11976297.0, mean_sales=5988148.5, record_count=2),
        metadata={"grouped_by": "store", "order": "descending"},
    )

    explainer = TemplateExplainer()
    narrative = explainer.explain(result)

    assert "Store 2" in narrative
    assert "6,120,128.00" in narrative
    assert "Store 8" in narrative


def test_template_explainer_forecast():
    """Verify TemplateExplainer formats forecast predictions."""
    intent = StructuredIntent(
        raw_query="Forecast store 5 item 10",
        task=IntentTask.FORECAST,
        scope=QueryScope(store_id=5, item_id=10, forecast_horizon_days=7),
    )
    result = UnifiedResult(
        intent=intent,
        task=IntentTask.FORECAST,
        columns=["date", "store", "item", "forecasted_sales"],
        records=[
            {"date": "2018-01-01", "store": 5, "item": 10, "forecasted_sales": 32.92},
            {"date": "2018-01-02", "store": 5, "item": 10, "forecasted_sales": 38.23},
        ],
        summary=SummaryMetrics(total_sales=71.15, mean_sales=35.58, min_sales=32.92, max_sales=38.23, record_count=2),
        metadata={"store_id": 5, "item_id": 10, "horizon_days": 7},
    )

    explainer = TemplateExplainer()
    narrative = explainer.explain(result)

    assert "Store 5" in narrative
    assert "Item 10" in narrative
    assert "71.15" in narrative


@patch("src.explanation.explainer.genai.Client")
def test_gemini_explainer_mocked(mock_client_cls):
    """Verify GeminiExplainer calls generate_content and extracts text."""
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client

    mock_response = MagicMock()
    mock_response.text = "Store 2 was the top performing store with over 6.1 million in sales."
    mock_client.models.generate_content.return_value = mock_response

    intent = StructuredIntent(
        raw_query="Top store",
        task=IntentTask.RANKING,
        scope=QueryScope(limit=1, order=SortOrder.DESC, group_by="store"),
    )
    result = UnifiedResult(
        intent=intent,
        task=IntentTask.RANKING,
        columns=["rank", "store", "total_sales"],
        records=[{"rank": 1, "store": 2, "total_sales": 6120128.0}],
        summary=SummaryMetrics(total_sales=6120128.0, record_count=1),
        metadata={"grouped_by": "store"},
    )

    explainer = GeminiExplainer(api_key="fake-key")
    narrative = explainer.explain(result)

    assert "Store 2 was the top performing store" in narrative


def test_stock_ai_pipeline_end_to_end():
    """Verify full pipeline runs query -> intent -> analytics -> narrative."""
    pipeline = StockAIPipeline(explainer=TemplateExplainer())
    response = pipeline.run("Show me the top 3 best performing stores")

    assert response.intent.task == IntentTask.RANKING
    assert len(response.result.records) == 3
    assert "Store 2" in response.explanation
    assert response.result.records[0]["store"] == 2
