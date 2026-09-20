"""Unit and integration tests for FastAPI backend endpoints."""

from fastapi.testclient import TestClient
import pytest

from src.api.app import app

client = TestClient(app)


def test_health_check_endpoint():
    """Verify /api/health returns healthy status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert len(data["engines"]) == 3


def test_query_ranking_endpoint():
    """Verify /api/query processes ranking queries."""
    response = client.post("/api/query", json={"query": "Top 3 stores by sales"})
    assert response.status_code == 200
    data = response.json()

    assert data["intent"]["task"] == "ranking"
    assert data["result"]["status"] == "success"
    assert len(data["result"]["records"]) == 3
    assert "explanation" in data
    assert len(data["explanation"]) > 0


def test_query_forecast_endpoint():
    """Verify /api/query processes forecast queries via XGBoost."""
    response = client.post(
        "/api/query",
        json={"query": "Forecast sales for store 5 item 10 for the next 7 days"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["intent"]["task"] == "forecast"
    assert len(data["result"]["records"]) == 7
    assert "forecasted_sales" in data["result"]["records"][0]


def test_query_empty_string_fails():
    """Verify empty query returns 400 Bad Request."""
    response = client.post("/api/query", json={"query": "   "})
    assert response.status_code == 400


def test_vercel_entrypoint_routes():
    """Verify api/index.py routes for root and health check."""
    from api.index import app as vercel_app

    vercel_client = TestClient(vercel_app)
    res_root = vercel_client.get("/")
    assert res_root.status_code == 200
    res_health = vercel_client.get("/api/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"

