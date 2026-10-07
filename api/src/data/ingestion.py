"""Data Ingestion Pipeline for validating, cleaning, deduplicating, and storing new sales data."""

import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import pandas as pd

from src.data.database import DatabaseManager


@dataclass
class ValidationResult:
    """Outcome of validating and cleaning an incoming sales dataset."""
    is_valid: bool
    clean_df: Optional[pd.DataFrame] = None
    rows_received: int = 0
    rows_valid: int = 0
    in_batch_duplicates: int = 0
    errors: List[str] = field(default_factory=list)


@dataclass
class IngestionSummary:
    """Summary metrics of an executed ingestion operation."""
    status: str  # "success", "partial", "failed"
    rows_received: int = 0
    rows_valid: int = 0
    rows_inserted: int = 0
    duplicates_handled: int = 0
    date_min: Optional[str] = None
    date_max: Optional[str] = None
    stores_affected: List[int] = field(default_factory=list)
    items_affected: List[int] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "rows_received": self.rows_received,
            "rows_valid": self.rows_valid,
            "rows_inserted": self.rows_inserted,
            "duplicates_handled": self.duplicates_handled,
            "date_range": {
                "start": self.date_min,
                "end": self.date_max,
            } if self.date_min and self.date_max else None,
            "stores_count": len(self.stores_affected),
            "items_count": len(self.items_affected),
            "errors": self.errors,
        }


class DataIngestionPipeline:
    """Validates, cleans, and loads CSV or tabular sales records into the central database."""

    REQUIRED_COLUMNS = {"date", "store", "item", "sales"}

    def __init__(self, db_manager: Optional[DatabaseManager] = None) -> None:
        self.db = db_manager or DatabaseManager.get_instance()

    def validate_and_clean(
        self, data: Union[pd.DataFrame, str, bytes, Path]
    ) -> ValidationResult:
        """Validate schema, types, non-negativity, and remove within-batch duplicates."""
        errors: List[str] = []

        # 1. Parse into DataFrame
        try:
            if isinstance(data, pd.DataFrame):
                df = data.copy()
            elif isinstance(data, (str, Path)) and (isinstance(data, Path) or Path(data).exists()):
                df = pd.read_csv(data)
            elif isinstance(data, str):
                df = pd.read_csv(io.StringIO(data))
            elif isinstance(data, bytes):
                df = pd.read_csv(io.BytesIO(data))
            else:
                return ValidationResult(
                    is_valid=False,
                    errors=["Unsupported data format for CSV ingestion."]
                )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Failed to parse CSV data: {str(e)}"]
            )

        rows_received = len(df)
        if rows_received == 0:
            return ValidationResult(
                is_valid=False,
                rows_received=0,
                errors=["Dataset is empty. At least one sales row is required."]
            )

        # Standardize column names to lowercase
        df.columns = [str(c).strip().lower() for c in df.columns]

        # 2. Check required columns
        missing_cols = self.REQUIRED_COLUMNS - set(df.columns)
        if missing_cols:
            return ValidationResult(
                is_valid=False,
                rows_received=rows_received,
                errors=[f"Missing required columns: {sorted(list(missing_cols))}"]
            )

        # 3. Clean and validate types
        clean_df = df[list(self.REQUIRED_COLUMNS)].copy()

        # Date validation
        try:
            clean_df["date"] = pd.to_datetime(clean_df["date"], errors="coerce")
            invalid_dates = clean_df["date"].isna().sum()
            if invalid_dates > 0:
                errors.append(f"Dropped {invalid_dates} rows with unparseable date values.")
            clean_df = clean_df.dropna(subset=["date"])
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                rows_received=rows_received,
                errors=[f"Date column parsing failed: {str(e)}"]
            )

        # Numeric conversions
        clean_df["store"] = pd.to_numeric(clean_df["store"], errors="coerce")
        clean_df["item"] = pd.to_numeric(clean_df["item"], errors="coerce")
        clean_df["sales"] = pd.to_numeric(clean_df["sales"], errors="coerce")

        null_mask = clean_df[["store", "item", "sales"]].isna().any(axis=1)
        if null_mask.sum() > 0:
            errors.append(f"Dropped {int(null_mask.sum())} rows with missing or non-numeric values.")
            clean_df = clean_df[~null_mask]

        if clean_df.empty:
            return ValidationResult(
                is_valid=False,
                rows_received=rows_received,
                errors=errors or ["No valid rows remained after data cleaning."]
            )

        # Value constraints: store > 0, item > 0, sales >= 0
        valid_range_mask = (clean_df["store"] > 0) & (clean_df["item"] > 0) & (clean_df["sales"] >= 0)
        invalid_ranges = (~valid_range_mask).sum()
        if invalid_ranges > 0:
            errors.append(f"Dropped {int(invalid_ranges)} rows with negative sales or non-positive store/item IDs.")
            clean_df = clean_df[valid_range_mask]

        clean_df["store"] = clean_df["store"].astype(int)
        clean_df["item"] = clean_df["item"].astype(int)
        clean_df["sales"] = clean_df["sales"].astype(float)
        clean_df["date"] = clean_df["date"].dt.strftime("%Y-%m-%d")

        # 4. In-batch duplicate detection on (store, item, date)
        dup_mask = clean_df.duplicated(subset=["store", "item", "date"], keep="last")
        in_batch_dups = int(dup_mask.sum())
        if in_batch_dups > 0:
            errors.append(f"Found {in_batch_dups} duplicate (store, item, date) rows in upload; keeping the latest.")
            clean_df = clean_df[~dup_mask]

        rows_valid = len(clean_df)
        return ValidationResult(
            is_valid=rows_valid > 0,
            clean_df=clean_df,
            rows_received=rows_received,
            rows_valid=rows_valid,
            in_batch_duplicates=in_batch_dups,
            errors=errors,
        )

    def ingest(
        self, data: Union[pd.DataFrame, str, bytes, Path], mode: str = "upsert"
    ) -> IngestionSummary:
        """Validate, clean, deduplicate, and store new sales records into the database."""
        val = self.validate_and_clean(data)
        if not val.is_valid or val.clean_df is None:
            return IngestionSummary(
                status="failed",
                rows_received=val.rows_received,
                rows_valid=0,
                rows_inserted=0,
                duplicates_handled=val.in_batch_duplicates,
                errors=val.errors or ["Data validation failed."],
            )

        clean_df = val.clean_df
        records = clean_df.to_dict(orient="records")

        # Insert records into SQLite central database
        inserted, duplicates = self.db.insert_sales_records(records, mode=mode)

        # Invalidate DataRepository in-memory cache so subsequent analytics see fresh data
        from src.data.repository import DataRepository
        repo = DataRepository.get_instance()
        repo.invalidate_cache()

        date_min = clean_df["date"].min()
        date_max = clean_df["date"].max()
        stores_affected = sorted(clean_df["store"].unique().tolist())
        items_affected = sorted(clean_df["item"].unique().tolist())

        total_dups = val.in_batch_duplicates + duplicates
        status = "partial" if val.errors else "success"

        return IngestionSummary(
            status=status,
            rows_received=val.rows_received,
            rows_valid=val.rows_valid,
            rows_inserted=inserted,
            duplicates_handled=total_dups,
            date_min=date_min,
            date_max=date_max,
            stores_affected=stores_affected,
            items_affected=items_affected,
            errors=val.errors,
        )
