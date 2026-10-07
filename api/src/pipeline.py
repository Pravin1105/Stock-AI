"""End-to-End Stock AI Analytics Pipeline coordinating routing, execution, and explanation."""

from dataclasses import dataclass
from typing import Optional

from src.analytics.router import AnalyticsDispatcher
from src.core.config import settings
from src.explanation.explainer import (
    BaseExplainer,
    GeminiExplainer,
    TemplateExplainer,
    get_explainer,
)
from src.routing.parser import (
    BaseQueryParser,
    GeminiQueryParser,
    RuleBasedQueryParser,
    get_query_parser,
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
    provider: Optional[str] = None
    model: Optional[str] = None


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
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        self.default_provider = (provider or settings.default_provider or "gemini").lower()
        self.default_model = model
        self.default_api_key = api_key

        self.custom_parser = parser
        self.dispatcher = dispatcher or AnalyticsDispatcher()
        self.custom_explainer = explainer

        # Initialize base parser and explainer
        if parser is not None:
            self.parser = parser
        else:
            self.parser = get_query_parser(
                provider=self.default_provider,
                model=self.default_model,
                api_key=self.default_api_key,
            )

        if explainer is not None:
            self.explainer = explainer
        else:
            self.explainer = get_explainer(
                provider=self.default_provider,
                model=self.default_model,
                api_key=self.default_api_key,
            )

    def run(
        self,
        query: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> PipelineResponse:
        """Execute the end-to-end analytical pipeline for a natural language user query.

        Args:
            query: Raw user question (e.g. "Top 5 stores by sales").
            provider: Optional LLM provider override ('gemini', 'openai', 'anthropic', 'groq').
            model: Optional model name override.
            api_key: Optional user-provided API key (BYOK).

        Returns:
            PipelineResponse object with intent, tabular result, narrative, and model attribution.
        """
        active_provider = (provider or self.default_provider).lower()
        active_model = model or self.default_model
        active_key = api_key or self.default_api_key

        # Resolve Parser (use request-specific parser if custom provider/model/key specified)
        if self.custom_parser is not None and not (provider or model or api_key):
            active_parser = self.custom_parser
        elif provider or model or api_key:
            active_parser = get_query_parser(
                provider=active_provider,
                model=active_model,
                api_key=active_key,
            )
        else:
            active_parser = self.parser

        # Step 1: Parse Intent (LLM 1 with deterministic fallback)
        try:
            intent = active_parser.parse(query)
        except Exception as parse_err:
            fallback_parser = RuleBasedQueryParser()
            intent = fallback_parser.parse(query)
            if not intent.explanation:
                intent.explanation = f"Routed via rule-based fallback due to parser error: {parse_err}"

        # Step 2: Deterministic Retrieval / Analytics Engine
        result = self.dispatcher.execute(intent)

        # Resolve Explainer (use request-specific explainer if custom provider/model/key specified)
        if self.custom_explainer is not None and not (provider or model or api_key):
            active_explainer = self.custom_explainer
        elif provider or model or api_key:
            active_explainer = get_explainer(
                provider=active_provider,
                model=active_model,
                api_key=active_key,
            )
        else:
            active_explainer = self.explainer

        # Step 3: Explanation & Synthesis (LLM 2 with template fallback)
        explanation = active_explainer.explain(result)

        resolved_model = (
            getattr(active_parser, "model", None)
            or getattr(active_explainer, "model", None)
            or active_model
        )

        return PipelineResponse(
            query=query,
            intent=intent,
            result=result,
            explanation=explanation,
            provider=active_provider,
            model=resolved_model,
        )

