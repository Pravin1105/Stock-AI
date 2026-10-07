"""Data repository providing access and filtering over the retail sales dataset.

Uses SQLite DatabaseManager as the central source of truth with in-memory caching.
"""

from pathlib import Path
from typing import Dict, Optional
import pandas as pd

from src.core.config import settings
from src.data.database import DatabaseManager


class DataRepository:
    """Manages querying and caching historical sales data backed by the central database."""

    _instance: Optional["DataRepository"] = None
    _df: Optional[pd.DataFrame] = None
    _stats_cache: Optional[pd.DataFrame] = None

    def __init__(self, data_path: Optional[Path] = None, db_manager: Optional[DatabaseManager] = None) -> None:
        """Initialize repository with dataset file path and database manager."""
        self.data_path = data_path or (settings.dataset_dir / "train.csv")
        self.db = db_manager or DatabaseManager.get_instance()
        # Seed database from train.csv if empty
        if self.data_path.exists():
            self.db.seed_from_csv_if_empty(self.data_path)

    @classmethod
    def get_instance(cls, data_path: Optional[Path] = None) -> "DataRepository":
        """Singleton accessor for the repository."""
        if cls._instance is None:
            cls._instance = cls(data_path=data_path)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Helper for test suites to reset repository state."""
        cls._instance = None

    def invalidate_cache(self) -> None:
        """Clear cached DataFrames and statistics when new data is ingested."""
        self._df = None
        self._stats_cache = None

    def load_data(self) -> pd.DataFrame:
        """Load and cache the full sales dataset from the central database."""
        if self._df is None:
            df = self.db.query_sales()
            if df.empty and self.data_path.exists():
                df = pd.read_csv(self.data_path, parse_dates=["date"])
                df["store"] = df["store"].astype(int)
                df["item"] = df["item"].astype(int)
                df["sales"] = df["sales"].astype(float)
            df = df.sort_values(["store", "item", "date"]).reset_index(drop=True)
            self._df = df
        return self._df

    def filter_data(
        self,
        store_id: Optional[int] = None,
        item_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """Filter dataset by store, item, and date ranges."""
        # Query database directly using indexes if full dataframe isn't cached yet
        if self._df is None:
            return self.db.query_sales(
                store_id=store_id,
                item_id=item_id,
                start_date=start_date,
                end_date=end_date,
            )

        df = self.load_data()
        mask = pd.Series(True, index=df.index)

        if store_id is not None:
            mask &= df["store"] == store_id
        if item_id is not None:
            mask &= df["item"] == item_id
        if start_date is not None:
            mask &= df["date"] >= pd.to_datetime(start_date)
        if end_date is not None:
            mask &= df["date"] <= pd.to_datetime(end_date)

        return df[mask].copy()

    def get_store_item_stats(self, store_id: int, item_id: int) -> Dict[str, float]:
        """Compute or retrieve precomputed sales mean, median, and std for a (store, item) pair."""
        if self._stats_cache is None:
            df = self.load_data()
            if df.empty:
                return {"sales_mean": 0.0, "sales_median": 0.0, "sales_std": 0.0}
            aggs = (
                df.groupby(["store", "item"])["sales"]
                .agg(["mean", "median", "std"])
                .reset_index()
            )
            aggs.columns = ["store", "item", "sales_mean", "sales_median", "sales_std"]
            self._stats_cache = aggs.set_index(["store", "item"])

        idx = (store_id, item_id)
        if idx in self._stats_cache.index:
            row = self._stats_cache.loc[idx]
            return {
                "sales_mean": float(row["sales_mean"]),
                "sales_median": float(row["sales_median"]),
                "sales_std": float(row["sales_std"]) if pd.notna(row["sales_std"]) else 0.0,
            }
        return {"sales_mean": 0.0, "sales_median": 0.0, "sales_std": 0.0}

    def get_recent_sales_series(self, store_id: int, item_id: int) -> pd.Series:
        """Get the full historical daily sales series for a (store, item) pair indexed by date."""
        filtered = self.filter_data(store_id=store_id, item_id=item_id)
        if filtered.empty:
            return pd.Series(dtype=float)
        return filtered.set_index("date")["sales"].sort_index()

    def get_max_date(self) -> pd.Timestamp:
        """Return the latest date available in the historical dataset."""
        max_dt = self.db.get_max_date()
        if max_dt is not None:
            return max_dt
        df = self.load_data()
        return df["date"].max()
