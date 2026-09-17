"""Stock AI — Main CLI Application.

Demonstrates the Complete Two-Stage LLM Analytics Pipeline:
  1. User Query
  2. Query Parser (LLM 1) -> Structured Intent
  3. Analytics Engine (SQL / Stats / XGBoost) -> Unified Results
  4. LLM Explanation (LLM 2) -> Conversational Insights

Usage:
  python main.py "Show me the top 5 best performing stores"
  python main.py "Forecast sales for store 5 item 10 for the next 7 days"
  python main.py "Show sales trend for item 15 in store 2"
  python main.py  (Interactive mode)
"""

import json
import sys
import pandas as pd

from src.core.config import settings
from src.pipeline import StockAIPipeline


def run_pipeline(query: str, pipeline: StockAIPipeline) -> None:
    print("\n" + "=" * 80)
    print(f"USER QUERY: \"{query}\"")
    print("=" * 80)

    # Execute full pipeline
    response = pipeline.run(query)

    # 1. Structured Intent
    print("\n[STAGE 1: QUERY PARSER (LLM 1) -> STRUCTURED INTENT]")
    print(f"Task:  {response.intent.task.value.upper()}")
    print(f"Scope: {json.dumps(response.intent.scope.model_dump(mode='json', exclude_none=True))}")

    # 2. Deterministic Analytics Engine Results
    print("\n[STAGE 2: ANALYTICS ENGINE -> UNIFIED RESULTS]")
    records_df = pd.DataFrame(response.result.records)
    if not records_df.empty:
        # Display top 10 if there are many records (e.g. trend)
        if len(records_df) > 10:
            print(records_df.head(10).to_string(index=False))
            print(f"... ({len(records_df) - 10} more rows)")
        else:
            print(records_df.to_string(index=False))
    else:
        print("(No records found)")

    # 3. LLM Explanation
    print("\n[STAGE 3: LLM EXPLANATION (LLM 2)]")
    print(response.explanation)
    print("\n" + "=" * 80)


def main() -> None:
    pipeline = StockAIPipeline()

    if len(sys.argv) > 1:
        # Single command query
        query = " ".join(sys.argv[1:])
        run_pipeline(query, pipeline)
    else:
        # Run standard demo queries
        demo_queries = [
            "Show me the top 5 best performing stores",
            "Forecast sales for store 5 item 10 for the next 7 days",
            "Show sales trend for item 15 in store 2",
        ]
        print("Running Stock AI Two-Stage LLM Analytics Architecture Demo...")
        for q in demo_queries:
            run_pipeline(q, pipeline)


if __name__ == "__main__":
    main()
