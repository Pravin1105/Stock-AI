"""Interactive & CLI Demo for Task 2: Data Retrieval & Analytics Engine Execution.

Usage:
    python demo_retrieval.py "Show me the top 5 best performing stores"
    python demo_retrieval.py "Top 3 selling items in store 1"
    python demo_retrieval.py "Show sales trend for item 15 in store 2"
    python demo_retrieval.py "Predict demand for store 5 item 10 for the next 7 days"
    python demo_retrieval.py (runs default query)
"""

import json
import sys
import pandas as pd

from src.analytics.router import AnalyticsDispatcher
from src.core.config import settings
from src.routing.parser import BaseQueryParser, GeminiQueryParser, RuleBasedQueryParser


def get_parser() -> BaseQueryParser:
    """Instantiate the best available parser."""
    if settings.gemini_api_key:
        print(f"[Query Parser]: Gemini ({settings.gemini_model})")
        return GeminiQueryParser()
    else:
        print("[Query Parser]: RuleBasedQueryParser (offline baseline)")
        return RuleBasedQueryParser()


def run_pipeline(query: str) -> None:
    parser = get_parser()
    dispatcher = AnalyticsDispatcher()

    print("\n" + "=" * 75)
    print(f"USER QUERY: \"{query}\"")
    print("=" * 75)

    # 1. Task 1: Parse Intent
    print("\n--- [STEP 1: QUERY ROUTING] ---")
    intent = parser.parse(query)
    print(f"Task:  {intent.task.value.upper()}")
    print(f"Scope: {json.dumps(intent.scope.model_dump(mode='json', exclude_none=True))}")

    # 2. Task 2: Execute Retrieval / Analytics Engine
    print("\n--- [STEP 2: ANALYTICS ENGINE RETRIEVAL] ---")
    result = dispatcher.execute(intent)

    if result.status != "success":
        print(f"Execution Error: {result.error_message}")
        return

    # Print tabular results cleanly
    records_df = pd.DataFrame(result.records)
    print(f"\nRetrieved {len(result.records)} records:")
    if not records_df.empty:
        print(records_df.to_string(index=False))
    else:
        print("(No records found)")

    # Print summary metrics
    print("\n--- [SUMMARY METRICS] ---")
    summary_dict = result.summary.model_dump(exclude_none=True)
    for k, v in summary_dict.items():
        print(f"• {k.replace('_', ' ').capitalize()}: {v}")

    print("\n" + "=" * 75)


if __name__ == "__main__":
    query_input = "Show me the top 5 best performing stores"
    if len(sys.argv) > 1:
        query_input = " ".join(sys.argv[1:])

    run_pipeline(query_input)
