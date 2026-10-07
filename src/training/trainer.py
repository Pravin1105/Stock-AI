"""Autonomous Model Training pipeline executing feature engineering, XGBoost training, and champion-challenger evaluation."""

from dataclasses import dataclass
from typing import Any, Dict, Optional
import pandas as pd
import xgboost as xgb

from src.data.database import DatabaseManager
from src.training.evaluator import EvaluationMetrics, ModelEvaluator
from src.training.features import FEATURE_COLUMNS, generate_training_features, prepare_train_validation_split
from src.training.registry import ModelRegistry


@dataclass
class TrainingJobResult:
    """Outcome of an executed training and evaluation run."""
    status: str  # "promoted", "rejected", "failed"
    promoted: bool
    version: Optional[str] = None
    candidate_metrics: Optional[Dict[str, float]] = None
    champion_metrics: Optional[Dict[str, float]] = None
    improvement_pct: float = 0.0
    decision_reason: str = ""
    rows_trained: int = 0
    rows_evaluated: int = 0
    date_range_trained: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "promoted": self.promoted,
            "version": self.version,
            "candidate_metrics": self.candidate_metrics,
            "champion_metrics": self.champion_metrics,
            "improvement_pct": self.improvement_pct,
            "decision_reason": self.decision_reason,
            "rows_trained": self.rows_trained,
            "rows_evaluated": self.rows_evaluated,
            "date_range_trained": self.date_range_trained,
        }


class ModelTrainer:
    """Orchestrates independent model retraining on accumulated database sales data."""

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        registry: Optional[ModelRegistry] = None,
    ) -> None:
        self.db = db_manager or DatabaseManager.get_instance()
        self.registry = registry or ModelRegistry.get_instance()

    def run_training_job(
        self,
        holdout_days: int = 90,
        n_estimators: int = 60,
        max_depth: int = 6,
        learning_rate: float = 0.08,
        tolerance_pct: float = 0.0,
    ) -> TrainingJobResult:
        """Execute end-to-end retraining, feature engineering, and governance evaluation."""
        # 1. Fetch raw data from the central database
        df_raw = self.db.query_sales()
        if df_raw.empty:
            return TrainingJobResult(
                status="failed",
                promoted=False,
                decision_reason="No sales records found in database to train on.",
            )

        total_rows = len(df_raw)
        min_date, max_date = self.db.get_date_range()

        # 2. Split temporally into training and holdout validation sets
        train_raw, val_raw = prepare_train_validation_split(df_raw, holdout_days=holdout_days)
        if len(train_raw) == 0 or len(val_raw) == 0:
            return TrainingJobResult(
                status="failed",
                promoted=False,
                decision_reason=f"Insufficient date range to split {holdout_days} holdout days.",
            )

        # 3. Feature engineering
        train_feat = generate_training_features(train_raw).dropna(subset=FEATURE_COLUMNS + ["sales"])
        val_feat = generate_training_features(val_raw).dropna(subset=FEATURE_COLUMNS + ["sales"])

        if train_feat.empty or val_feat.empty:
            return TrainingJobResult(
                status="failed",
                promoted=False,
                decision_reason="Feature generation yielded empty dataset.",
            )

        # 4. Train candidate XGBoost booster
        dtrain = xgb.DMatrix(train_feat[FEATURE_COLUMNS], label=train_feat["sales"])
        dval = xgb.DMatrix(val_feat[FEATURE_COLUMNS], label=val_feat["sales"])

        params = {
            "objective": "reg:squarederror",
            "eval_metric": "mae",
            "max_depth": max_depth,
            "eta": learning_rate,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "seed": 42,
        }

        candidate_booster = xgb.train(
            params,
            dtrain,
            num_boost_round=n_estimators,
            evals=[(dval, "val")],
            verbose_eval=False,
        )

        # 5. Evaluate Champion vs. Challenger on the validation holdout set
        champion_booster = self.registry.load_active_booster()
        comparison = ModelEvaluator.compare_and_decide(
            candidate_booster=candidate_booster,
            champion_booster=champion_booster,
            val_df=val_feat,
            tolerance_pct=tolerance_pct,
        )

        dataset_info = {
            "total_rows": total_rows,
            "train_rows": len(train_feat),
            "val_rows": len(val_feat),
            "date_range": f"{min_date} to {max_date}",
            "holdout_days": holdout_days,
        }

        # 6. Apply promotion or rejection in Model Registry
        if comparison.should_promote:
            new_version = self.registry.promote_candidate(
                booster=candidate_booster,
                metrics=comparison.candidate_metrics.to_dict(),
                dataset_info=dataset_info,
                notes=comparison.decision_reason,
            )
            return TrainingJobResult(
                status="promoted",
                promoted=True,
                version=new_version,
                candidate_metrics=comparison.candidate_metrics.to_dict(),
                champion_metrics=comparison.champion_metrics.to_dict() if comparison.champion_metrics else None,
                improvement_pct=comparison.improvement_pct,
                decision_reason=comparison.decision_reason,
                rows_trained=len(train_feat),
                rows_evaluated=len(val_feat),
                date_range_trained=f"{min_date} to {max_date}",
            )
        else:
            rejected_version = self.registry.record_rejected(
                booster=candidate_booster,
                metrics=comparison.candidate_metrics.to_dict(),
                dataset_info=dataset_info,
                reason=comparison.decision_reason,
            )
            return TrainingJobResult(
                status="rejected",
                promoted=False,
                version=rejected_version,
                candidate_metrics=comparison.candidate_metrics.to_dict(),
                champion_metrics=comparison.champion_metrics.to_dict() if comparison.champion_metrics else None,
                improvement_pct=comparison.improvement_pct,
                decision_reason=comparison.decision_reason,
                rows_trained=len(train_feat),
                rows_evaluated=len(val_feat),
                date_range_trained=f"{min_date} to {max_date}",
            )
