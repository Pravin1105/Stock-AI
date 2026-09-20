"""Query parser implementations for routing user requests to analytical tasks."""

import json
import re
from abc import ABC, abstractmethod
from typing import Optional

from google import genai
from google.genai import types
from pydantic import ValidationError

from src.core.config import settings
from src.routing.prompts import QUERY_PARSER_SYSTEM_PROMPT
from src.schemas.intent import IntentTask, QueryScope, SortOrder, StructuredIntent


class QueryParserError(Exception):
    """Base exception for query parsing errors."""
    pass


class BaseQueryParser(ABC):
    """Abstract base class defining the contract for query parsers."""

    @abstractmethod
    def parse(self, query: str) -> StructuredIntent:
        """Parse a natural language query into a validated StructuredIntent.

        Args:
            query: Unstructured user query string.

        Returns:
            StructuredIntent containing the task and scope.

        Raises:
            QueryParserError: If parsing fails or output is invalid.
        """
        pass


class GeminiQueryParser(BaseQueryParser):
    """Production Query Parser powered by Google's Gemini LLM.

    Utilizes structured JSON output enforcement to guarantee adherence to the
    StructuredIntent schema without mathematical or data hallucinations.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        """Initialize the Gemini client.

        Args:
            api_key: Optional API key. If not provided, reads from settings or env.
            model: Optional Gemini model name (defaults to settings.gemini_model).
        """
        self.api_key = api_key or settings.gemini_api_key
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is required. Please set it in your environment or .env file."
            )
        self.model = model or settings.gemini_model
        self.client = genai.Client(api_key=self.api_key)

    def parse(self, query: str) -> StructuredIntent:
        """Parses the user query using Gemini with structured output validation."""
        clean_query = query.strip()
        if not clean_query:
            raise ValueError("Query string cannot be empty.")

        config = types.GenerateContentConfig(
            system_instruction=QUERY_PARSER_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=StructuredIntent,
            temperature=0.0,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

        prompt = f"Extract structured intent and scope for this user query:\n\n{clean_query}"
        candidate_models = [self.model]
        for fallback_m in ["gemini-2.0-flash", "gemini-1.5-flash"]:
            if fallback_m not in candidate_models:
                candidate_models.append(fallback_m)

        last_error: Optional[Exception] = None
        for m in candidate_models:
            try:
                response = self.client.models.generate_content(
                    model=m,
                    contents=prompt,
                    config=config,
                )

                if not response.text:
                    continue

                try:
                    intent = StructuredIntent.model_validate_json(response.text)
                    intent.raw_query = clean_query
                    return intent
                except ValidationError as val_err:
                    raise QueryParserError(
                        f"Model response failed schema validation: {val_err}"
                    ) from val_err
            except QueryParserError:
                raise
            except Exception as err:
                last_error = err
                continue

        raise QueryParserError(f"Gemini Query Parser error: {last_error}")


class RuleBasedQueryParser(BaseQueryParser):
    """Deterministic, rule-based parser used for offline testing and baseline verification.

    Extracts stores, items, and tasks using regex pattern matching.
    """

    def parse(self, query: str) -> StructuredIntent:
        clean_query = query.strip()
        if not clean_query:
            raise ValueError("Query string cannot be empty.")

        lower_query = clean_query.lower()

        # 1. Determine Task
        if any(w in lower_query for w in ["forecast", "predict", "future", "next"]):
            task = IntentTask.FORECAST
        elif any(w in lower_query for w in ["trend", "trajectory", "history", "over time", "pattern"]):
            task = IntentTask.TREND
        else:
            # Default to ranking for top/bottom/sales comparisons
            task = IntentTask.RANKING

        # 2. Extract Scope
        store_match = re.search(r"store\s*#?\s*(\d+)", lower_query)
        store_id = int(store_match.group(1)) if store_match else None

        item_match = re.search(r"item\s*#?\s*(\d+)", lower_query)
        item_id = int(item_match.group(1)) if item_match else None

        limit_match = re.search(r"(?:top|bottom|first|last)\s*(\d+)", lower_query)
        limit = int(limit_match.group(1)) if limit_match else 10 if task == IntentTask.RANKING else None

        order = SortOrder.ASC if any(w in lower_query for w in ["bottom", "lowest", "least", "worst"]) else SortOrder.DESC

        # Horizon
        horizon_days = None
        if task == IntentTask.FORECAST:
            horizon_match = re.search(r"(\d+)\s*days?", lower_query)
            if horizon_match:
                horizon_days = int(horizon_match.group(1))
            elif "week" in lower_query:
                horizon_days = 7
            elif "month" in lower_query:
                horizon_days = 30
            else:
                horizon_days = 7

        group_by = None
        if task == IntentTask.RANKING:
            if "store" in lower_query and "item" not in lower_query:
                group_by = "store"
            else:
                group_by = "item"

        scope = QueryScope(
            store_id=store_id,
            item_id=item_id,
            forecast_horizon_days=horizon_days,
            limit=limit,
            order=order if task == IntentTask.RANKING else None,
            group_by=group_by,
        )

        return StructuredIntent(
            raw_query=clean_query,
            task=task,
            scope=scope,
            explanation=f"Deterministically routed to {task.value} with scope {scope.model_dump(mode='json', exclude_none=True)}.",
        )
