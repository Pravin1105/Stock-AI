"""Statistical engine for trend, trajectory, and time-series analysis."""

from typing import Optional
import pandas as pd

from src.analytics.base import BaseAnalyticsEngine
from src.data.repository import DataRepository
from src.schemas.intent import IntentTask, StructuredIntent
from src.schemas.results import SummaryMetrics, UnifiedResult


class TrendEngine(BaseAnalyticsEngine):
    """Executes time-series aggregation, moving averages, and growth rate computations."""

    def __init__(self, repository: Optional[DataRepository] = None) -> None:
        self.repo = repository or DataRepository.get_instance()

    def execute(self, intent: StructuredIntent) -> UnifiedResult:
        if intent.task != IntentTask.TREND:
            raise ValueError(f"TrendEngine cannot execute task: {intent.task}")

        scope = intent.scope
        df = self.repo.filter_data(
            store_id=scope.store_id,
            item_id=scope.item_id,
            start_date=scope.start_date,
            end_date=scope.end_date,
        )

        if df.empty:
            return UnifiedResult(
                intent=intent,
                task=IntentTask.TREND,
                status="success",
                columns=[],
                records=[],
                summary=SummaryMetrics(record_count=0),
                metadata={"message": "No data found for trend calculation."},
            )

        # Resample frequency based on data length
        date_span_days = (df["date"].max() - df["date"].min()).days

        if date_span_days > 90:
            # Aggregate by month for macro trends
            df["period"] = df["date"].dt.to_period("M").dt.to_timestamp()
            freq_label = "monthly"
        else:
            # Daily granularity for micro trends
            df["period"] = df["date"]
            freq_label = "daily"

        time_df = (
            df.groupby("period")["sales"]
            .agg(total_sales="sum", avg_sales="mean")
            .reset_index()
            .sort_values("period")
            .reset_index(drop=True)
        )

        # Calculate period-over-period percentage change and 3-period moving average
        time_df["pct_change"] = (time_df["total_sales"].pct_change() * 100).round(2).fillna(0.0)
        time_df["moving_avg"] = time_df["total_sales"].rolling(window=3, min_periods=1).mean().round(2)
        time_df["date"] = time_df["period"].dt.strftime("%Y-%m-%d" if freq_label == "daily" else "%Y-%m")
        time_df["total_sales"] = time_df["total_sales"].round(2)
        time_df["avg_sales"] = time_df["avg_sales"].round(2)

        display_cols = ["date", "total_sales", "avg_sales", "pct_change", "moving_avg"]
        records = time_df[display_cols].to_dict(orient="records")

        summary = SummaryMetrics(
            total_sales=float(time_df["total_sales"].sum().round(2)),
            mean_sales=float(time_df["total_sales"].mean().round(2)),
            median_sales=float(time_df["total_sales"].median().round(2)),
            min_sales=float(time_df["total_sales"].min().round(2)),
            max_sales=float(time_df["total_sales"].max().round(2)),
            record_count=len(records),
        )

        return UnifiedResult(
            intent=intent,
            task=IntentTask.TREND,
            status="success",
            columns=display_cols,
            records=records,
            summary=summary,
            metadata={
                "granularity": freq_label,
                "store_id": scope.store_id,
                "item_id": scope.item_id,
                "start_date": scope.start_date,
                "end_date": scope.end_date,
            },
        )
