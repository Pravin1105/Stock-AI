"""Base abstract class for all specialized analytics engines."""

from abc import ABC, abstractmethod
from src.schemas.intent import StructuredIntent
from src.schemas.results import UnifiedResult


class BaseAnalyticsEngine(ABC):
    """Abstract interface defining the execution contract for analytics engines."""

    @abstractmethod
    def execute(self, intent: StructuredIntent) -> UnifiedResult:
        """Executes analytical computation for the given structured intent.

        Args:
            intent: Validated structured intent with task and scope parameters.

        Returns:
            UnifiedResult containing records, summary statistics, and metadata.
        """
        pass
