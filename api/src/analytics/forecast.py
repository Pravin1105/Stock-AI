"""Machine learning inference engine powered by tuned XGBoost."""

from pathlib import Path
from typing import List, Optional
import numpy as np
import pandas as pd
import xgboost as xgb

from src.analytics.base import BaseAnalyticsEngine
from src.core.config import settings
from src.data.repository import DataRepository
from src.schemas.intent import IntentTask, StructuredIntent
from src.schemas.results import SummaryMetrics, UnifiedResult

FEATURES = [
    "day", "month", "year", "dayofweek", "weekofyear",
    "sales_mean", "sales_median", "sales_std",
    "lag_7", "lag_14", "lag_28", "lag_365"
]


class ForecastEngine(BaseAnalyticsEngine):
    """Executes time-series demand forecasting using the trained XGBoost model."""

    def __init__(
        self,
        model_path: Optional[Path] = None,
        repository: Optional[DataRepository] = None,
    ) -> None:
        self.model_path = model_path or (settings.model_dir / "tuned_xgboost_model.json")
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model file not found at: {self.model_path}")

        self.model = xgb.Booster()
        self.model.load_model(str(self.model_path))
        self.repo = repository or DataRepository.get_instance()

    def execute(self, intent: StructuredIntent) -> UnifiedResult:
        if intent.task != IntentTask.FORECAST:
            raise ValueError(f"ForecastEngine cannot execute task: {intent.task}")

        scope = intent.scope
        store_id = scope.store_id or 1
        item_id = scope.item_id or 1
        horizon = scope.forecast_horizon_days or 7
        # Cap horizon between 1 and 90 days for stability
        horizon = max(1, min(horizon, 90))

        # Retrieve historical stats & series for lag lookups
        stats = self.repo.get_store_item_stats(store_id, item_id)
        hist_series = self.repo.get_recent_sales_series(store_id, item_id)
        max_hist_date = self.repo.get_max_date()

        # Generate future prediction dates
        start_forecast_date = max_hist_date + pd.Timedelta(days=1)
        future_dates = pd.date_range(start=start_forecast_date, periods=horizon, freq="D")

        # In-memory dictionary tracking both history and future predictions for lag computation
        sales_timeline = dict(hist_series.items())

        records: List[dict] = []
        for f_date in future_dates:
            # Extract date features
            day = f_date.day
            month = f_date.month
            year = f_date.year
            dayofweek = f_date.dayofweek
            weekofyear = int(f_date.isocalendar().week)

            # Compute lags (7, 14, 28, 365 days prior)
            def get_lag(n_days: int) -> float:
                target_dt = f_date - pd.Timedelta(days=n_days)
                if target_dt in sales_timeline:
                    return float(sales_timeline[target_dt])
                # Fallback to mean sales if lag is out of bounds
                return float(stats.get("sales_mean", 0.0))

            lag_7 = get_lag(7)
            lag_14 = get_lag(14)
            lag_28 = get_lag(28)
            lag_365 = get_lag(365)

            row_features = {
                "day": day,
                "month": month,
                "year": year,
                "dayofweek": dayofweek,
                "weekofyear": weekofyear,
                "sales_mean": stats.get("sales_mean", 0.0),
                "sales_median": stats.get("sales_median", 0.0),
                "sales_std": stats.get("sales_std", 0.0),
                "lag_7": lag_7,
                "lag_14": lag_14,
                "lag_28": lag_28,
                "lag_365": lag_365,
            }

            feat_df = pd.DataFrame([row_features])[FEATURES].fillna(0)
            dmat = xgb.DMatrix(feat_df)
            raw_pred = self.model.predict(dmat)[0]
            # Invert log1p transformation used during training
            pred_sales = max(0.0, float(np.expm1(raw_pred)))
            pred_sales = round(pred_sales, 2)

            # Save in timeline for subsequent autoregressive lags
            sales_timeline[f_date] = pred_sales

            records.append({
                "date": f_date.strftime("%Y-%m-%d"),
                "store": store_id,
                "item": item_id,
                "forecasted_sales": pred_sales,
            })

        pred_series = pd.Series([r["forecasted_sales"] for r in records])
        summary = SummaryMetrics(
            total_sales=float(pred_series.sum().round(2)),
            mean_sales=float(pred_series.mean().round(2)),
            median_sales=float(pred_series.median().round(2)),
            min_sales=float(pred_series.min().round(2)),
            max_sales=float(pred_series.max().round(2)),
            record_count=len(records),
        )

        display_cols = ["date", "store", "item", "forecasted_sales"]
        return UnifiedResult(
            intent=intent,
            task=IntentTask.FORECAST,
            status="success",
            columns=display_cols,
            records=records,
            summary=summary,
            metadata={
                "model": "tuned_xgboost_model.json",
                "store_id": store_id,
                "item_id": item_id,
                "horizon_days": horizon,
                "start_date": records[0]["date"],
                "end_date": records[-1]["date"],
            },
        )
