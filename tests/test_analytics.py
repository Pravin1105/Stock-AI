"""Unit tests for the Analytics Engines and Dispatcher."""

import pytest
from src.analytics.forecast import ForecastEngine
from src.analytics.ranking import RankingEngine
from src.analytics.router import AnalyticsDispatcher
from src.analytics.trend import TrendEngine
from src.schemas.intent import IntentTask, QueryScope, SortOrder, StructuredIntent
from src.schemas.results import UnifiedResult


@pytest.fixture(scope="module")
def dispatcher():
    """Fixture providing an initialized AnalyticsDispatcher."""
    return AnalyticsDispatcher()


def test_ranking_engine_top_stores(dispatcher):
    """Test ranking engine retrieves top stores sorted descending."""
    intent = StructuredIntent(
        raw_query="Top 5 stores by sales",
        task=IntentTask.RANKING,
        scope=QueryScope(limit=5, order=SortOrder.DESC, group_by="store"),
    )
    result = dispatcher.execute(intent)

    assert isinstance(result, UnifiedResult)
    assert result.status == "success"
    assert len(result.records) == 5
    assert "store" in result.columns
    assert "total_sales" in result.columns

    # Verify order is strictly descending
    sales = [r["total_sales"] for r in result.records]
    assert sales == sorted(sales, reverse=True)


def test_ranking_engine_bottom_items(dispatcher):
    """Test ranking engine retrieves bottom items in a specific store."""
    intent = StructuredIntent(
        raw_query="Bottom 3 items in store 1",
        task=IntentTask.RANKING,
        scope=QueryScope(store_id=1, limit=3, order=SortOrder.ASC, group_by="item"),
    )
    result = dispatcher.execute(intent)

    assert len(result.records) == 3
    assert "item" in result.columns
    sales = [r["total_sales"] for r in result.records]
    assert sales == sorted(sales, reverse=False)


def test_trend_engine(dispatcher):
    """Test trend engine computes time series with moving averages."""
    intent = StructuredIntent(
        raw_query="Trend for store 2 item 15",
        task=IntentTask.TREND,
        scope=QueryScope(store_id=2, item_id=15),
    )
    result = dispatcher.execute(intent)

    assert result.status == "success"
    assert len(result.records) > 0
    assert "pct_change" in result.columns
    assert "moving_avg" in result.columns
    assert result.summary.record_count == len(result.records)


def test_forecast_engine(dispatcher):
    """Test XGBoost forecast engine generates predictions."""
    intent = StructuredIntent(
        raw_query="Forecast store 5 item 10 for 7 days",
        task=IntentTask.FORECAST,
        scope=QueryScope(store_id=5, item_id=10, forecast_horizon_days=7),
    )
    result = dispatcher.execute(intent)

    assert result.status == "success"
    assert len(result.records) == 7
    assert result.metadata["horizon_days"] == 7
    for record in result.records:
        assert record["store"] == 5
        assert record["item"] == 10
        assert record["forecasted_sales"] > 0
