"""Analytics Dispatcher routing structured intent to the appropriate analytical engine."""

from typing import Optional

from src.analytics.base import BaseAnalyticsEngine
from src.analytics.forecast import ForecastEngine
from src.analytics.ranking import RankingEngine
from src.analytics.trend import TrendEngine
from src.schemas.intent import IntentTask, StructuredIntent
from src.schemas.results import UnifiedResult


class AnalyticsDispatcher:
    """Central analytics engine orchestrator dispatching intents to specialized engines."""

    def __init__(
        self,
        ranking_engine: Optional[BaseAnalyticsEngine] = None,
        trend_engine: Optional[BaseAnalyticsEngine] = None,
        forecast_engine: Optional[BaseAnalyticsEngine] = None,
    ) -> None:
        self.ranking_engine = ranking_engine or RankingEngine()
        self.trend_engine = trend_engine or TrendEngine()
        self.forecast_engine = forecast_engine or ForecastEngine()

    def execute(self, intent: StructuredIntent) -> UnifiedResult:
        """Route the structured intent to the corresponding analytical compute engine.

        Args:
            intent: Validated StructuredIntent.

        Returns:
            UnifiedResult containing computed records and summary metrics.
        """
        if intent.task == IntentTask.RANKING:
            return self.ranking_engine.execute(intent)
        elif intent.task == IntentTask.TREND:
            return self.trend_engine.execute(intent)
        elif intent.task == IntentTask.FORECAST:
            return self.forecast_engine.execute(intent)
        else:
            raise ValueError(f"Unsupported analytical task: {intent.task}")
