"""Confidence scoring for RAG answers."""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

from config.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class ConfidenceLevel(str, Enum):
    """Confidence level categories."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INSUFFICIENT = "insufficient"


@dataclass
class ConfidenceScore:
    """Confidence score with breakdown."""

    overall: float  # 0.0 to 1.0
    level: ConfidenceLevel
    factors: dict[str, float]
    explanation: str
    missing_data: list[str]


class ConfidenceScorer:
    """Calculate confidence scores for RAG answers."""

    def __init__(self, settings: Settings | None = None):
        """Initialize confidence scorer.

        Args:
            settings: Application settings.
        """
        self._settings = settings or get_settings()
        self._threshold = self._settings.CONFIDENCE_THRESHOLD

    def score(
        self,
        query: str,
        context: list[dict[str, Any]],
        date_range: tuple[str, str] | None = None,
    ) -> ConfidenceScore:
        """Calculate confidence score for a query with given context.

        Args:
            query: User's query.
            context: Retrieved context documents/nodes.
            date_range: Optional date range for the query.

        Returns:
            ConfidenceScore with overall score and factors.
        """
        factors = {}
        missing_data = []

        # Factor 1: Data quantity (0-0.3)
        quantity_score = self._score_data_quantity(context)
        factors["data_quantity"] = quantity_score
        if quantity_score < 0.15:
            missing_data.append("Limited data points available")

        # Factor 2: Data recency (0-0.2)
        recency_score = self._score_data_recency(context, date_range)
        factors["data_recency"] = recency_score
        if recency_score < 0.1:
            missing_data.append("Data may be outdated or missing recent metrics")

        # Factor 3: Query specificity match (0-0.2)
        specificity_score = self._score_query_specificity(query, context)
        factors["query_match"] = specificity_score
        if specificity_score < 0.1:
            missing_data.append("Query terms not well matched in available data")

        # Factor 4: Data completeness (0-0.2)
        completeness_score = self._score_data_completeness(context)
        factors["data_completeness"] = completeness_score
        if completeness_score < 0.1:
            missing_data.append("Some expected fields are missing")

        # Factor 5: Source diversity (0-0.1)
        diversity_score = self._score_source_diversity(context)
        factors["source_diversity"] = diversity_score

        # Calculate overall score
        overall = sum(factors.values())

        # Determine confidence level
        if overall >= 0.8:
            level = ConfidenceLevel.HIGH
        elif overall >= 0.6:
            level = ConfidenceLevel.MEDIUM
        elif overall >= self._threshold:
            level = ConfidenceLevel.LOW
        else:
            level = ConfidenceLevel.INSUFFICIENT

        # Generate explanation
        explanation = self._generate_explanation(level, factors, missing_data)

        logger.info(
            f"Confidence score: {overall:.2f} ({level.value}) for query: {query[:50]}..."
        )

        return ConfidenceScore(
            overall=overall,
            level=level,
            factors=factors,
            explanation=explanation,
            missing_data=missing_data,
        )

    def _score_data_quantity(self, context: list[dict[str, Any]]) -> float:
        """Score based on amount of relevant data.

        Args:
            context: Retrieved context.

        Returns:
            Score from 0.0 to 0.3.
        """
        if not context:
            return 0.0

        # Count meaningful data points
        count = len(context)

        # Progressive scoring
        if count >= 20:
            return 0.3
        elif count >= 10:
            return 0.25
        elif count >= 5:
            return 0.2
        elif count >= 2:
            return 0.15
        else:
            return 0.1

    def _score_data_recency(
        self,
        context: list[dict[str, Any]],
        date_range: tuple[str, str] | None,
    ) -> float:
        """Score based on data freshness.

        Args:
            context: Retrieved context.
            date_range: Query date range.

        Returns:
            Score from 0.0 to 0.2.
        """
        if not context:
            return 0.0

        # Look for date fields in context
        dates_found = []
        for item in context:
            if isinstance(item, dict):
                for key in ["date", "created_at", "updated_at", "start_date"]:
                    if key in item and item[key]:
                        dates_found.append(str(item[key]))

        if not dates_found:
            return 0.1  # Partial score if no dates but has data

        # If we have a date range, check coverage
        if date_range:
            start, end = date_range
            has_start = any(start <= d for d in dates_found)
            has_end = any(d <= end for d in dates_found)
            if has_start and has_end:
                return 0.2
            elif has_start or has_end:
                return 0.15
            return 0.1

        return 0.15  # Default if dates exist but no range specified

    def _score_query_specificity(
        self, query: str, context: list[dict[str, Any]]
    ) -> float:
        """Score based on how well context matches query terms.

        Args:
            query: User query.
            context: Retrieved context.

        Returns:
            Score from 0.0 to 0.2.
        """
        if not context or not query:
            return 0.0

        # Extract meaningful words from query
        query_terms = set(
            word.lower()
            for word in query.split()
            if len(word) > 3 and word.lower() not in {"what", "show", "give", "tell"}
        )

        if not query_terms:
            return 0.1

        # Check context for matching terms
        context_text = str(context).lower()
        matches = sum(1 for term in query_terms if term in context_text)

        match_ratio = matches / len(query_terms) if query_terms else 0
        return min(0.2, match_ratio * 0.25)

    def _score_data_completeness(self, context: list[dict[str, Any]]) -> float:
        """Score based on completeness of retrieved data.

        Args:
            context: Retrieved context.

        Returns:
            Score from 0.0 to 0.2.
        """
        if not context:
            return 0.0

        # Expected fields for different entity types
        expected_fields = {
            "campaign": {"name", "status", "budget", "objective"},
            "metric": {"impressions", "clicks", "spend", "date"},
            "client": {"name", "industry", "budget"},
        }

        completeness_scores = []

        for item in context:
            if not isinstance(item, dict):
                continue

            # Determine entity type
            item_type = item.get("entity_type", "")
            if "campaign" in str(item).lower():
                expected = expected_fields.get("campaign", set())
            elif "metric" in str(item).lower() or "impressions" in item:
                expected = expected_fields.get("metric", set())
            else:
                expected = expected_fields.get("client", set())

            if expected:
                present = sum(1 for f in expected if f in item and item[f] is not None)
                completeness_scores.append(present / len(expected))

        if not completeness_scores:
            return 0.1

        avg_completeness = sum(completeness_scores) / len(completeness_scores)
        return min(0.2, avg_completeness * 0.2)

    def _score_source_diversity(self, context: list[dict[str, Any]]) -> float:
        """Score based on diversity of data sources.

        Args:
            context: Retrieved context.

        Returns:
            Score from 0.0 to 0.1.
        """
        if not context:
            return 0.0

        # Look for different entity types
        entity_types = set()
        for item in context:
            if isinstance(item, dict):
                if "campaign" in str(item).lower():
                    entity_types.add("campaign")
                if "adset" in str(item).lower() or "ad_set" in str(item).lower():
                    entity_types.add("adset")
                if "metric" in str(item).lower() or "impressions" in item:
                    entity_types.add("metric")

        diversity_ratio = len(entity_types) / 4  # Max expected types
        return min(0.1, diversity_ratio * 0.1)

    def _generate_explanation(
        self,
        level: ConfidenceLevel,
        factors: dict[str, float],
        missing_data: list[str],
    ) -> str:
        """Generate human-readable explanation of confidence score.

        Args:
            level: Confidence level.
            factors: Score factors.
            missing_data: List of missing data items.

        Returns:
            Explanation string.
        """
        explanations = {
            ConfidenceLevel.HIGH: "High confidence based on comprehensive data coverage.",
            ConfidenceLevel.MEDIUM: "Medium confidence. Some data points may be missing.",
            ConfidenceLevel.LOW: "Low confidence. Limited data available for this query.",
            ConfidenceLevel.INSUFFICIENT: "Insufficient data to provide a reliable answer.",
        }

        explanation = explanations[level]

        if missing_data:
            explanation += " Missing: " + "; ".join(missing_data[:2])

        return explanation

    def should_refuse(self, score: ConfidenceScore) -> bool:
        """Determine if the system should refuse to answer.

        Args:
            score: Confidence score.

        Returns:
            True if answer should be refused.
        """
        return score.level == ConfidenceLevel.INSUFFICIENT

    def format_confidence_for_response(self, score: ConfidenceScore) -> str:
        """Format confidence score for inclusion in response.

        Args:
            score: Confidence score.

        Returns:
            Formatted string.
        """
        level_indicators = {
            ConfidenceLevel.HIGH: "High",
            ConfidenceLevel.MEDIUM: "Medium",
            ConfidenceLevel.LOW: "Low",
            ConfidenceLevel.INSUFFICIENT: "Insufficient",
        }

        result = f"**Confidence**: {level_indicators[score.level]}"
        if score.missing_data:
            result += f" ({score.explanation})"

        return result
