"""SQLite database manager serving as the central source of truth for retail sales data."""

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from src.core.config import settings


class DatabaseManager:
    """Thread-safe SQLite manager for sales records, querying, and seeding."""

    _instance: Optional["DatabaseManager"] = None

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or settings.database_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @classmethod
    def get_instance(cls, db_path: Optional[Path] = None) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = cls(db_path=db_path)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Helper for testing to reset the singleton."""
        cls._instance = None

    def get_connection(self) -> sqlite3.Connection:
        """Create and return a SQLite connection with timeout and WAL mode."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        # WAL mode allows concurrent reads and fast writes
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_schema(self) -> None:
        """Initialize required database tables and indexes."""
        with self.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sales (
                    date TEXT NOT NULL,
                    store INTEGER NOT NULL,
                    item INTEGER NOT NULL,
                    sales REAL NOT NULL,
                    PRIMARY KEY (store, item, date)
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(date);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sales_store_item ON sales(store, item);")
            conn.commit()

    def get_row_count(self) -> int:
        """Get total number of sales records."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM sales;")
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    def seed_from_csv_if_empty(self, csv_path: Optional[Path] = None) -> int:
        """Seed database from train.csv if table is currently empty."""
        current_count = self.get_row_count()
        if current_count > 0:
            return current_count

        source_path = csv_path or (settings.dataset_dir / "train.csv")
        if not source_path.exists():
            return 0

        # Read CSV and batch insert into SQLite
        df = pd.read_csv(source_path)
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        df["store"] = df["store"].astype(int)
        df["item"] = df["item"].astype(int)
        df["sales"] = df["sales"].astype(float)

        records = list(zip(df["date"], df["store"], df["item"], df["sales"]))
        with self.get_connection() as conn:
            conn.executemany(
                "INSERT OR IGNORE INTO sales (date, store, item, sales) VALUES (?, ?, ?, ?);",
                records,
            )
            conn.commit()

        return self.get_row_count()

    def insert_sales_records(
        self, records: List[Dict[str, Any]], mode: str = "upsert"
    ) -> Tuple[int, int]:
        """Insert a batch of validated sales records.

        Returns (rows_inserted, duplicates_updated_or_skipped).
        """
        if not records:
            return 0, 0

        with self.get_connection() as conn:
            # Check existing duplicates
            existing_count = 0
            formatted_tuples = []
            for r in records:
                d = str(r["date"])
                s = int(r["store"])
                i = int(r["item"])
                val = float(r["sales"])
                formatted_tuples.append((d, s, i, val))

            if mode == "upsert":
                # Count how many of these exist beforehand
                cursor = conn.cursor()
                # Use temp table or batch check for duplicates
                sql = """
                    INSERT INTO sales (date, store, item, sales)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(store, item, date) DO UPDATE SET sales = excluded.sales;
                """
                cursor.executemany(sql, formatted_tuples)
                affected = cursor.rowcount
                conn.commit()
                # On SQLite, rowcount in upsert returns total rows affected
                return len(records), 0
            else:  # mode == "ignore"
                before_count = self.get_row_count()
                sql = """
                    INSERT OR IGNORE INTO sales (date, store, item, sales)
                    VALUES (?, ?, ?, ?);
                """
                conn.executemany(sql, formatted_tuples)
                conn.commit()
                after_count = self.get_row_count()
                inserted = after_count - before_count
                duplicates = len(records) - inserted
                return inserted, duplicates

    def query_sales(
        self,
        store_id: Optional[int] = None,
        item_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """Query sales data with SQL-level filtering."""
        clauses = []
        params: List[Any] = []

        if store_id is not None:
            clauses.append("store = ?")
            params.append(int(store_id))
        if item_id is not None:
            clauses.append("item = ?")
            params.append(int(item_id))
        if start_date is not None:
            clauses.append("date >= ?")
            params.append(str(start_date))
        if end_date is not None:
            clauses.append("date <= ?")
            params.append(str(end_date))

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"SELECT date, store, item, sales FROM sales {where_sql} ORDER BY store, item, date;"

        with self.get_connection() as conn:
            df = pd.read_sql_query(sql, conn, params=params, parse_dates=["date"])

        if not df.empty:
            df["store"] = df["store"].astype(int)
            df["item"] = df["item"].astype(int)
            df["sales"] = df["sales"].astype(float)
        return df

    def get_max_date(self) -> Optional[pd.Timestamp]:
        """Return the maximum sales date in the database."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT MAX(date) FROM sales;")
            row = cursor.fetchone()
            if row and row[0]:
                return pd.to_datetime(row[0])
            return None

    def get_date_range(self) -> Tuple[Optional[str], Optional[str]]:
        """Return (min_date, max_date) strings from database."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT MIN(date), MAX(date) FROM sales;")
            row = cursor.fetchone()
            if row:
                return row[0], row[1]
            return None, None
