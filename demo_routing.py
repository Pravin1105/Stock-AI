"""Interactive & CLI Demo for Task 1: Query Parser / Intent Routing.

Usage:
    python demo_routing.py "Top 5 items in Store 2"
    python demo_routing.py "Forecast sales for Store 5 Item 10 next 14 days"
    python demo_routing.py (runs built-in test suite of sample queries)
"""

import json
import sys
from typing import List

from src.core.config import settings
from src.routing.parser import BaseQueryParser, GeminiQueryParser, RuleBasedQueryParser


def get_parser() -> BaseQueryParser:
    """Instantiate the best available parser based on environment."""
    if settings.gemini_api_key:
        print("Using [GeminiQueryParser] (live Gemini model: {})".format(settings.gemini_model))
        return GeminiQueryParser()
    else:
        print("GEMINI_API_KEY not detected. Using [RuleBasedQueryParser] (deterministic baseline).")
        print("Tip: Add GEMINI_API_KEY to .env to use live Gemini LLM parsing.\n")
        return RuleBasedQueryParser()


def run_demo(queries: List[str]) -> None:
    parser = get_parser()

    print("=" * 70)
    print("TASK 1: QUERY ROUTING & INTENT PARSING DEMO")
    print("=" * 70)

    for i, query in enumerate(queries, 1):
        print(f"\n[{i}] Query: \"{query}\"")
        try:
            intent = parser.parse(query)
            print("    -> Task Identified:  ", intent.task.value.upper())
            print("    -> Structured Intent:")
            intent_json = json.dumps(intent.model_dump(mode="json", exclude_none=True), indent=8)
            print("    " + intent_json.replace("\n", "\n    "))
        except Exception as e:
            print(f"    [ERROR] Failed to parse query: {e}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run single custom query passed via CLI
        user_query = " ".join(sys.argv[1:])
        run_demo([user_query])
    else:
        # Run standard benchmark queries covering all 3 architectural tasks
        sample_queries = [
            "What are the top 5 selling items in Store 3?",
            "Which store had the lowest sales overall in 2017?",
            "Show me the sales trend for item 15 in store 2 over time",
            "How has store 4 performed over the past months?",
            "Predict demand for Store 5 Item 10 for the next 14 days",
            "Forecast sales for store 1 item 1 next week",
        ]
        run_demo(sample_queries)
