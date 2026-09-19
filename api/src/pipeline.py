"""End-to-End Stock AI Analytics Pipeline coordinating routing, execution, and explanation."""

from dataclasses import dataclass
from typing import Optional

from src.analytics.router import AnalyticsDispatcher
from src.core.config import settings
from src.explanation.explainer import (
    BaseExplainer,
    GeminiExplainer,
    TemplateExplainer,
)
from src.routing.parser import (
    BaseQueryParser,
    GeminiQueryParser,
    RuleBasedQueryParser,
)
from src.schemas.intent import StructuredIntent
from src.schemas.results import UnifiedResult


@dataclass
class PipelineResponse:
    """Final output payload containing the intent, raw tabular results, and natural narrative."""

    query: str
    intent: StructuredIntent
    result: UnifiedResult
    explanation: str


class StockAIPipeline:
    """Orchestrates the full Two-Stage LLM Analytics Architecture:

    1. User Query -> Query Parser (LLM 1) -> Structured Intent
    2. Structured Intent -> Analytics Dispatcher -> Deterministic Engine (SQL/Stats/XGBoost)
    3. Engine Output -> Unified Result
    4. Unified Result -> LLM Explainer (LLM 2) -> Final Answer & Insights
    """

    def __init__(
        self,
        parser: Optional[BaseQueryParser] = None,
        dispatcher: Optional[AnalyticsDispatcher] = None,
        explainer: Optional[BaseExplainer] = None,
    ) -> None:
        # Default to Gemini if API key is present, otherwise fallback to deterministic engines
        if parser is not None:
            self.parser = parser
        elif settings.gemini_api_key:
            self.parser = GeminiQueryParser()
        else:
            self.parser = RuleBasedQueryParser()

        self.dispatcher = dispatcher or AnalyticsDispatcher()

        if explainer is not None:
            self.explainer = explainer
        elif settings.gemini_api_key:
            self.explainer = GeminiExplainer()
        else:
            self.explainer = TemplateExplainer()

    def run(self, query: str) -> PipelineResponse:
        """Execute the end-to-end analytical pipeline for a natural language user query.

        Args:
            query: Raw user question (e.g. "Top 5 stores by sales").

        Returns:
            PipelineResponse object with intent, tabular result, and narrative explanation.
        """
        # Step 1: Parse Intent (LLM 1)
        intent = self.parser.parse(query)

        # Step 2: Deterministic Retrieval / Analytics Engine
        result = self.dispatcher.execute(intent)

        # Step 3: Explanation & Synthesis (LLM 2)
        explanation = self.explainer.explain(result)

        return PipelineResponse(
            query=query,
            intent=intent,
            result=result,
            explanation=explanation,
        )
