"""Model evaluation and Champion vs. Challenger comparison module."""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple
import numpy as np
import pandas as pd
import xgboost as xgb

from src.training.features import FEATURE_COLUMNS


@dataclass
class EvaluationMetrics:
    """Comprehensive performance metrics on a holdout evaluation dataset."""
    smape: float
    mae: float
    rmse: float
    wape: float
    samples_count: int

    def to_dict(self) -> Dict[str, float]:
        return {
            "smape": round(self.smape, 4),
            "mae": round(self.mae, 4),
            "rmse": round(self.rmse, 4),
            "wape": round(self.wape, 4),
            "samples_count": self.samples_count,
        }


@dataclass
class ComparisonResult:
    """Champion vs. Challenger governance outcome."""
    should_promote: bool
    candidate_metrics: EvaluationMetrics
    champion_metrics: Optional[EvaluationMetrics]
    improvement_pct: float
    decision_reason: str


class ModelEvaluator:
    """Evaluates XGBoost models and enforces champion-challenger promotion governance."""

    @staticmethod
    def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> EvaluationMetrics:
        """Compute SMAPE, MAE, RMSE, and WAPE across truth and predictions."""
        y_true = np.asarray(y_true, dtype=float)
        y_pred = np.maximum(np.asarray(y_pred, dtype=float), 0.0)  # Demand cannot be negative

        n = len(y_true)
        if n == 0:
            return EvaluationMetrics(smape=0.0, mae=0.0, rmse=0.0, wape=0.0, samples_count=0)

        # SMAPE
        denominator = np.abs(y_true) + np.abs(y_pred) + 1e-8
        smape = float(np.mean(200.0 * np.abs(y_pred - y_true) / denominator))

        # MAE
        mae = float(np.mean(np.abs(y_true - y_pred)))

        # RMSE
        rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))

        # WAPE
        sum_true = float(np.sum(y_true))
        wape = float((np.sum(np.abs(y_true - y_pred)) / (sum_true + 1e-8)) * 100.0)

        return EvaluationMetrics(
            smape=smape,
            mae=mae,
            rmse=rmse,
            wape=wape,
            samples_count=n,
        )

    @classmethod
    def evaluate_model(
        cls, booster: xgb.Booster, eval_df: pd.DataFrame
    ) -> EvaluationMetrics:
        """Evaluate an XGBoost booster on an evaluation DataFrame containing FEATURE_COLUMNS and sales."""
        x_eval = eval_df[FEATURE_COLUMNS]
        y_true = eval_df["sales"].values

        dmat = xgb.DMatrix(x_eval)
        y_pred = booster.predict(dmat)

        return cls.compute_metrics(y_true, y_pred)

    @classmethod
    def compare_and_decide(
        cls,
        candidate_booster: xgb.Booster,
        champion_booster: Optional[xgb.Booster],
        val_df: pd.DataFrame,
        tolerance_pct: float = 0.0,
    ) -> ComparisonResult:
        """Compare candidate (challenger) against incumbent champion model on holdout set."""
        candidate_metrics = cls.evaluate_model(candidate_booster, val_df)

        if champion_booster is None:
            return ComparisonResult(
                should_promote=True,
                candidate_metrics=candidate_metrics,
                champion_metrics=None,
                improvement_pct=100.0,
                decision_reason="No incumbent champion model found. Candidate promoted automatically.",
            )

        champion_metrics = cls.evaluate_model(champion_booster, val_df)

        # Baseline: SMAPE lower is better
        champ_smape = champion_metrics.smape
        cand_smape = candidate_metrics.smape

        improvement = ((champ_smape - cand_smape) / (champ_smape + 1e-8)) * 100.0

        # Promotion rule: candidate must beat or be within tolerance of champion
        if cand_smape <= champ_smape * (1.0 + tolerance_pct / 100.0):
            reason = (
                f"Candidate model promoted: SMAPE improved from {champ_smape:.3f}% to {cand_smape:.3f}% "
                f"({improvement:+.2f}% relative improvement, MAE: {candidate_metrics.mae:.2f} vs {champion_metrics.mae:.2f})."
            )
            should_promote = True
        else:
            reason = (
                f"Candidate model rejected: SMAPE degraded from {champ_smape:.3f}% (Champion) to {cand_smape:.3f}% (Candidate) "
                f"({improvement:+.2f}% relative change)."
            )
            should_promote = False

        return ComparisonResult(
            should_promote=should_promote,
            candidate_metrics=candidate_metrics,
            champion_metrics=champion_metrics,
            improvement_pct=round(improvement, 2),
            decision_reason=reason,
        )
