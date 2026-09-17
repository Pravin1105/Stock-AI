"""Deterministic SQL/Data aggregation engine for ranking tasks."""

from typing import List, Optional
import pandas as pd

from src.analytics.base import BaseAnalyticsEngine
from src.data.repository import DataRepository
from src.schemas.intent import IntentTask, SortOrder, StructuredIntent
from src.schemas.results import SummaryMetrics, UnifiedResult


class RankingEngine(BaseAnalyticsEngine):
    """Executes deterministic grouping, sorting, and ranking on historical sales data."""

    def __init__(self, repository: Optional[DataRepository] = None) -> None:
        self.repo = repository or DataRepository.get_instance()

    def execute(self, intent: StructuredIntent) -> UnifiedResult:
        if intent.task != IntentTask.RANKING:
            raise ValueError(f"RankingEngine cannot execute task: {intent.task}")

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
                task=IntentTask.RANKING,
                status="success",
                columns=[],
                records=[],
                summary=SummaryMetrics(record_count=0),
                metadata={"message": "No records matched the specified criteria."},
            )

        # Determine grouping dimension
        group_col = "item" if scope.group_by == "item" or scope.store_id is not None else "store"
        if scope.group_by in ["store", "item"]:
            group_col = scope.group_by

        ascending = (scope.order == SortOrder.ASC)
        limit = scope.limit if (scope.limit and scope.limit > 0) else 10

        # Aggregate total and mean sales
        agg_df = (
            df.groupby(group_col)["sales"]
            .agg(total_sales="sum", avg_daily_sales="mean")
            .reset_index()
            .sort_values(by="total_sales", ascending=ascending)
            .head(limit)
            .reset_index(drop=True)
        )

        # Add 1-based rank
        agg_df.insert(0, "rank", agg_df.index + 1)
        agg_df["total_sales"] = agg_df["total_sales"].round(2)
        agg_df["avg_daily_sales"] = agg_df["avg_daily_sales"].round(2)

        records = agg_df.to_dict(orient="records")
        columns = list(agg_df.columns)

        summary = SummaryMetrics(
            total_sales=float(agg_df["total_sales"].sum().round(2)),
            mean_sales=float(agg_df["total_sales"].mean().round(2)),
            min_sales=float(agg_df["total_sales"].min().round(2)),
            max_sales=float(agg_df["total_sales"].max().round(2)),
            record_count=len(records),
        )

        return UnifiedResult(
            intent=intent,
            task=IntentTask.RANKING,
            status="success",
            columns=columns,
            records=records,
            summary=summary,
            metadata={
                "grouped_by": group_col,
                "order": "ascending" if ascending else "descending",
                "limit": limit,
                "filtered_store_id": scope.store_id,
                "filtered_item_id": scope.item_id,
            },
        )
