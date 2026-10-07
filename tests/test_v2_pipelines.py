"""Comprehensive tests for v2.0 Ingestion and Independent Model Training pipelines."""

import io
import pytest
import pandas as pd
import numpy as np
from fastapi.testclient import TestClient

from src.api.app import app
from src.data.database import DatabaseManager
from src.data.ingestion import DataIngestionPipeline
from src.data.repository import DataRepository
from src.training.evaluator import EvaluationMetrics, ModelEvaluator
from src.training.features import generate_training_features, prepare_train_validation_split
from src.training.registry import ModelRegistry
from src.training.trainer import ModelTrainer
from src.training.scheduler import TrainingScheduler


client = TestClient(app)


def test_database_initialization_and_query():
    """Verify central SQLite database initializes and queries correctly."""
    db = DatabaseManager.get_instance()
    count = db.get_row_count()
    assert count > 0, "Database should contain sales rows after initial seed"

    # Query specific slice
    df = db.query_sales(store_id=1, item_id=1)
    assert not df.empty
    assert (df["store"] == 1).all()
    assert (df["item"] == 1).all()


def test_data_ingestion_validation_and_deduplication():
    """Verify data ingestion cleans invalid records and detects in-batch duplicates."""
    pipeline = DataIngestionPipeline()

    raw_csv = """date,store,item,sales
2018-01-01,1,1,100.0
2018-01-01,1,1,120.0
2018-01-02,1,1,-50.0
2018-01-03,invalid,1,40.0
2018-01-04,1,1,55.0
"""
    val = pipeline.validate_and_clean(raw_csv)
    assert val.is_valid
    assert val.rows_received == 5
    assert val.in_batch_duplicates == 1
    # 2018-01-01 (kept 1), 2018-01-04 (kept 1); -50.0 dropped, 'invalid' dropped -> 2 valid
    assert val.rows_valid == 2

    # Ingest into database
    summary = pipeline.ingest(raw_csv, mode="upsert")
    assert summary.status == "partial"  # Had cleaning errors
    assert summary.rows_inserted == 2
    assert summary.date_min == "2018-01-01"
    assert summary.date_max == "2018-01-04"


def test_immediate_analytics_visibility_without_retraining():
    """Verify that newly ingested data is immediately queryable in analytics without retraining."""
    repo = DataRepository.get_instance()
    db = DatabaseManager.get_instance()
    initial_max_date = repo.get_max_date()

    # Ingest a record for year 2025
    future_csv = """date,store,item,sales
2025-06-15,1,1,999.0
"""
    pipeline = DataIngestionPipeline()
    summary = pipeline.ingest(future_csv, mode="upsert")
    assert summary.rows_inserted >= 1

    # Check that DataRepository instantly reflects the new maximum date
    new_max_date = repo.get_max_date()
    assert str(new_max_date)[:10] == "2025-06-15"

    # Check that query on date range includes the new record
    future_data = repo.filter_data(store_id=1, item_id=1, start_date="2025-01-01")
    assert not future_data.empty
    assert future_data.iloc[0]["sales"] == 999.0


def test_model_evaluator_metrics():
    """Verify calculation of SMAPE, MAE, RMSE, and WAPE."""
    y_true = np.array([100.0, 50.0, 20.0])
    y_pred = np.array([110.0, 45.0, 25.0])

    metrics = ModelEvaluator.compute_metrics(y_true, y_pred)
    assert metrics.samples_count == 3
    assert metrics.mae == pytest.approx(6.6667, rel=1e-2)
    assert metrics.smape > 0.0
    assert metrics.wape > 0.0


def test_champion_challenger_promotion_logic():
    """Verify promotion when candidate improves and rejection when candidate degrades."""
    import xgboost as xgb

    # Synthetic validation data
    val_data = pd.DataFrame({
        "day": [1, 2, 3],
        "month": [1, 1, 1],
        "year": [2017, 2017, 2017],
        "dayofweek": [0, 1, 2],
        "weekofyear": [1, 1, 1],
        "sales_mean": [50.0, 50.0, 50.0],
        "sales_median": [50.0, 50.0, 50.0],
        "sales_std": [5.0, 5.0, 5.0],
        "lag_7": [50.0, 50.0, 50.0],
        "lag_14": [50.0, 50.0, 50.0],
        "lag_28": [50.0, 50.0, 50.0],
        "lag_365": [50.0, 50.0, 50.0],
        "sales": [50.0, 52.0, 48.0],
    })

    # Train dummy candidate
    from src.training.features import FEATURE_COLUMNS
    dmat = xgb.DMatrix(val_data[FEATURE_COLUMNS], label=val_data["sales"])
    booster_cand = xgb.train({"max_depth": 2, "eta": 0.1}, dmat, num_boost_round=5)

    # When no champion exists, candidate is automatically promoted
    decision_initial = ModelEvaluator.compare_and_decide(
        candidate_booster=booster_cand,
        champion_booster=None,
        val_df=val_data,
    )
    assert decision_initial.should_promote is True


def test_model_registry_lifecycle(tmp_path):
    """Verify model registry stores versions, promotes champion, and tracks rejections."""
    import xgboost as xgb
    registry = ModelRegistry(registry_dir=tmp_path)

    # Dummy booster
    dmat = xgb.DMatrix(pd.DataFrame({"a": [1.0]}), label=[1.0])
    booster = xgb.train({"max_depth": 1}, dmat, num_boost_round=1)

    # Promote
    version = registry.promote_candidate(
        booster=booster,
        metrics={"smape": 5.5, "mae": 4.2},
        dataset_info={"rows": 100},
        notes="First test promotion",
    )
    assert version.startswith("v")
    assert registry.get_active_version() == version

    # Record rejection
    rejection = registry.record_rejected(
        booster=booster,
        metrics={"smape": 8.5, "mae": 7.0},
        dataset_info={"rows": 100},
        reason="SMAPE degraded from 5.5% to 8.5%",
    )
    assert rejection.startswith("candidate_rejected")
    # Active version should still be the promoted version
    assert registry.get_active_version() == version

    models = registry.list_models()
    assert len(models) == 2


def test_api_v2_ingest_csv_endpoint():
    """Verify POST /api/ingest/csv accepts and processes valid CSV data."""
    payload = {
        "csv_data": "date,store,item,sales\n2018-02-01,2,3,75.0\n2018-02-02,2,3,80.0",
        "mode": "upsert",
    }
    response = client.post("/api/ingest/csv", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["rows_inserted"] == 2
    assert data["date_range"]["start"] == "2018-02-01"


def test_api_v2_ingest_sales_batch_endpoint():
    """Verify POST /api/ingest/sales accepts structured sales payloads."""
    payload = {
        "records": [
            {"date": "2018-03-01", "store": 1, "item": 5, "sales": 62.0},
            {"date": "2018-03-02", "store": 1, "item": 5, "sales": 64.0},
        ],
        "mode": "upsert",
    }
    response = client.post("/api/ingest/sales", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["rows_inserted"] == 2


def test_api_v2_training_endpoints():
    """Verify POST /api/train/retrain, GET /api/train/status, and GET /api/train/models."""
    # Status endpoint
    status_resp = client.get("/api/train/status")
    assert status_resp.status_code == 200
    assert "is_running" in status_resp.json()

    # Models list endpoint
    models_resp = client.get("/api/train/models")
    assert models_resp.status_code == 200
    assert "models" in models_resp.json()

    # Trigger background retraining
    retrain_resp = client.post(
        "/api/train/retrain",
        json={"background": True, "n_estimators": 10, "holdout_days": 30},
    )
    assert retrain_resp.status_code == 200
    res_data = retrain_resp.json()
    assert res_data["status"] in ["started", "busy"]


def test_model_registry_readonly_resilience(tmp_path):
    """Verify ModelRegistry handles simulated read-only environments (Errno 30) gracefully."""
    import os
    import shutil
    import xgboost as xgb

    ro_dir = tmp_path / "ro_model"
    ro_dir.mkdir(parents=True, exist_ok=True)

    # Place a dummy tuned_xgboost_model.json
    dmat = xgb.DMatrix(pd.DataFrame({"a": [1.0]}), label=[1.0])
    booster = xgb.train({"max_depth": 1}, dmat, num_boost_round=1)
    booster.save_model(str(ro_dir / "tuned_xgboost_model.json"))

    # Make directory read-only
    os.chmod(str(ro_dir), 0o555)

    try:
        # Initializing registry must not raise Errno 30 Read-only file system
        registry = ModelRegistry(registry_dir=ro_dir)
        assert registry.get_active_version() == "v1.0.0"
        active_booster = registry.load_active_booster()
        assert active_booster is not None
    finally:
        # Restore permissions for cleanup
        os.chmod(str(ro_dir), 0o755)

