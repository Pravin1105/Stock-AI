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


def test_models_catalog_endpoint():
    """Verify /api/models returns all 4 providers and metadata."""
    response = client.get("/api/models")
    assert response.status_code == 200
    data = response.json()
    assert "default_provider" in data
    assert "providers" in data

    providers = data["providers"]
    for expected_p in ["gemini", "openai", "anthropic", "groq"]:
        assert expected_p in providers
        assert "name" in providers[expected_p]
        assert "default_model" in providers[expected_p]
        assert len(providers[expected_p]["models"]) > 0
        assert "has_server_key" in providers[expected_p]


def test_query_with_byok_and_provider_routing():
    """Verify /api/query respects provider and returns provider attribution."""
    response = client.post(
        "/api/query",
        json={
            "query": "Top 2 stores by sales",
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",
            "api_key": "dummy-groq-key",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "groq"
    assert data["model"] == "llama-3.3-70b-versatile"
    assert data["result"]["status"] == "success"
    assert len(data["result"]["records"]) == 2


def test_cometchat_config_endpoint():
    """Verify /api/cometchat/config returns client-safe configuration without server secrets."""
    response = client.get("/api/cometchat/config")
    assert response.status_code == 200
    data = response.json()
    assert "app_id" in data
    assert "region" in data
    assert "is_configured" in data
    assert "default_users" in data
    assert len(data["default_users"]) == 2
    assert {u["uid"] for u in data["default_users"]} == {"analyst_1", "analyst_2"}
    # Ensure secrets are never returned in public config
    assert "rest_api_key" not in data
    assert "apiKey" not in data


def test_cometchat_token_endpoint():
    """Verify /api/cometchat/token handles user authentication token requests safely."""
    response = client.post("/api/cometchat/token", json={"uid": "analyst_1", "name": "Senior Demand Analyst"})
    assert response.status_code == 200
    data = response.json()
    assert data["uid"] == "analyst_1"
    assert "auth_token" in data
    assert data["status"] in ("success", "mock_mode")


def test_cometchat_token_empty_uid_fails():
    """Verify empty UID returns 422 Unprocessable Entity."""
    response = client.post("/api/cometchat/token", json={"uid": ""})
    assert response.status_code == 422


def test_voice_transcribe_success():
    """Verify voice transcription endpoint succeeds with valid base64 audio."""
    import base64
    fake_audio = base64.b64encode(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00fakeaudiodata12345").decode("utf-8")
    response = client.post(
        "/api/voice/transcribe",
        json={
            "audio_base64": fake_audio,
            "mime_type": "audio/webm",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "transcript" in data
    assert len(data["transcript"]) > 0
    assert "provider" in data


def test_voice_transcribe_empty_fails():
    """Verify empty audio payload is rejected."""
    response = client.post(
        "/api/voice/transcribe",
        json={
            "audio_base64": "",
            "mime_type": "audio/webm",
        },
    )
    assert response.status_code == 422


def test_voice_transcribe_invalid_base64_fails():
    """Verify corrupted non-base64 input returns 400."""
    response = client.post(
        "/api/voice/transcribe",
        json={
            "audio_base64": "!!!not_valid_base64???",
            "mime_type": "audio/webm",
        },
    )
    assert response.status_code == 400


def test_end_to_end_voice_to_query_workflow():
    """Verify end-to-end workflow: audio transcription -> user review -> analytics query execution."""
    import base64
    audio_sample = base64.b64encode(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00mockvoiceaudioforecastingquery").decode("utf-8")

    # Step 1: Transcribe spoken audio
    transcribe_res = client.post(
        "/api/voice/transcribe",
        json={"audio_base64": audio_sample, "mime_type": "audio/webm"},
    )
    assert transcribe_res.status_code == 200
    t_data = transcribe_res.json()
    assert "transcript" in t_data
    raw_transcript = t_data["transcript"]

    # Step 2: User reviews and approves query (e.g. "Forecast sales for store 5 item 10 for the next 7 days")
    approved_query = raw_transcript

    # Step 3: Dispatch to analytical pipeline
    query_res = client.post("/api/query", json={"query": approved_query})
    assert query_res.status_code == 200
    q_data = query_res.json()
    assert q_data["intent"]["task"] in ("forecast", "ranking", "trend")
    assert q_data["result"]["status"] == "success"
    assert "records" in q_data["result"]
    assert len(q_data["explanation"]) > 0


def test_voice_query_size_limit_rejection():
    """Verify audio exceeding 10MB limit is rejected with 400."""
    import base64
    # Create fake audio bytes slightly over 10MB
    oversized_bytes = b"0" * (10 * 1024 * 1024 + 1024)
    oversized_b64 = base64.b64encode(oversized_bytes).decode("utf-8")
    response = client.post(
        "/api/voice/transcribe",
        json={"audio_base64": oversized_b64, "mime_type": "audio/webm"},
    )
    assert response.status_code == 400
    assert "10MB limit" in response.json()["detail"]


def test_cometchat_config_secrets_isolation():
    """Verify CometChat public config endpoint never leaks server REST API keys."""
    response = client.get("/api/cometchat/config")
    assert response.status_code == 200
    data = response.json()
    assert "rest_api_key" not in data
    assert "apiKey" not in data
    assert "secret" not in data
    assert "COMETCHAT_REST_API_KEY" not in str(data)





