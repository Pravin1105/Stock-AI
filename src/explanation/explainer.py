"""LLM and template explanation engines for converting analytical results to natural language."""

import json
from abc import ABC, abstractmethod
from typing import Optional

from google import genai
from google.genai import types

from src.core.config import settings
from src.explanation.prompts import EXPLANATION_SYSTEM_PROMPT
from src.schemas.intent import IntentTask
from src.schemas.results import UnifiedResult


class BaseExplainer(ABC):
    """Abstract interface defining the narrative generation contract."""

    @abstractmethod
    def explain(self, result: UnifiedResult) -> str:
        """Synthesize analytical results into a natural language response.

        Args:
            result: The UnifiedResult object from the Analytics Engine.

        Returns:
            A clean, markdown-formatted narrative explanation.
        """
        pass


class GeminiExplainer(BaseExplainer):
    """Production explanation engine powered by Google Gemini."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or settings.gemini_api_key
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is required for GeminiExplainer. Set it in .env or pass directly."
            )
        self.model = model or settings.gemini_model
        self.client = genai.Client(api_key=self.api_key)

    def explain(self, result: UnifiedResult) -> str:
        if result.status != "success":
            return f"Unable to generate explanation due to an execution error: {result.error_message}"

        if not result.records:
            return "No data records were found matching your query criteria."

        # Construct analytical context payload
        context = {
            "user_query": result.intent.raw_query,
            "task_type": result.task.value,
            "summary_metrics": result.summary.model_dump(exclude_none=True),
            "metadata": result.metadata,
            "data_records": result.records[:25],  # Cap records for context efficiency
        }

        prompt = (
            f"Generate an insightful business explanation for the following analytical results:\n\n"
            f"```json\n{json.dumps(context, indent=2)}\n```"
        )

        try:
            config = types.GenerateContentConfig(
                system_instruction=EXPLANATION_SYSTEM_PROMPT,
                temperature=0.3,
            )
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )
            return response.text.strip() if response.text else "No explanation generated."
        except Exception as err:
            # Fallback to deterministic template in case of network or API error
            fallback = TemplateExplainer()
            return f"{fallback.explain(result)}\n\n*(Note: Generated via fallback explainer due to: {err})*"


class TemplateExplainer(BaseExplainer):
    """Deterministic, rule-based template explainer used for offline environments and testing."""

    def explain(self, result: UnifiedResult) -> str:
        if result.status != "success":
            return f"Execution Error: {result.error_message}"

        if not result.records:
            return "No matching records found for the requested query."

        query = result.intent.raw_query
        task = result.task

        if task == IntentTask.RANKING:
            return self._explain_ranking(result)
        elif task == IntentTask.TREND:
            return self._explain_trend(result)
        elif task == IntentTask.FORECAST:
            return self._explain_forecast(result)
        else:
            return f"Retrieved {len(result.records)} records."

    def _explain_ranking(self, result: UnifiedResult) -> str:
        records = result.records
        group_by = result.metadata.get("grouped_by", "entity")
        order = result.metadata.get("order", "descending")
        direction_word = "top" if order == "descending" else "lowest"

        top_entity = records[0].get(group_by, "N/A")
        top_sales = records[0].get("total_sales", 0.0)

        lines = [
            f"Here are the **{direction_word} performing {group_by}s** based on historical sales data:",
            "",
            f"- **#1 {group_by.title()} {top_entity}** led with **{top_sales:,.2f}** in total sales.",
        ]

        if len(records) > 1:
            for r in records[1:5]:
                entity = r.get(group_by, "N/A")
                sales = r.get("total_sales", 0.0)
                rank = r.get("rank", "-")
                lines.append(f"- **#{rank} {group_by.title()} {entity}**: {sales:,.2f} sales")

        if result.summary.total_sales:
            lines.append("")
            lines.append(
                f"**Summary**: Combined sales across these {len(records)} {group_by}s total **{result.summary.total_sales:,.2f}**, "
                f"with an average of **{result.summary.mean_sales:,.2f}** per {group_by}."
            )

        return "\n".join(lines)

    def _explain_trend(self, result: UnifiedResult) -> str:
        records = result.records
        granularity = result.metadata.get("granularity", "period")
        first_date = records[0].get("date", "start")
        last_date = records[-1].get("date", "end")

        lines = [
            f"Historical sales trend from **{first_date}** to **{last_date}** ({granularity}):",
            "",
            f"- **Total Period Sales**: {result.summary.total_sales:,.2f}",
            f"- **Average Sales per {granularity.title()[:-2] if granularity.endswith('ly') else granularity}**: {result.summary.mean_sales:,.2f}",
            f"- **Peak Volume**: {result.summary.max_sales:,.2f}",
            f"- **Trough Volume**: {result.summary.min_sales:,.2f}",
        ]
        return "\n".join(lines)

    def _explain_forecast(self, result: UnifiedResult) -> str:
        records = result.records
        store = result.metadata.get("store_id", "N/A")
        item = result.metadata.get("item_id", "N/A")
        horizon = result.metadata.get("horizon_days", len(records))

        total_pred = result.summary.total_sales or 0.0
        daily_avg = result.summary.mean_sales or 0.0

        lines = [
            f"Projected demand for **Store {store}, Item {item}** over the next **{horizon} days**:",
            "",
            f"- **Total Projected Demand**: **{total_pred:,.2f}** units",
            f"- **Expected Daily Average**: **{daily_avg:,.2f}** units/day",
            f"- **Projected Daily Range**: Between {result.summary.min_sales:,.2f} and {result.summary.max_sales:,.2f} units",
            "",
            f"Forecast generated using the trained gradient-boosted XGBoost model starting from **{records[0]['date']}** to **{records[-1]['date']}**.",
        ]
        return "\n".join(lines)
