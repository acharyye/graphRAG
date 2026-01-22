"""Unit tests for RAG components."""

import pytest
from unittest.mock import MagicMock, patch

from src.rag.confidence import ConfidenceLevel, ConfidenceScore, ConfidenceScorer


class TestConfidenceScorer:
    """Tests for ConfidenceScorer."""

    @pytest.fixture
    def scorer(self, test_settings):
        """Create confidence scorer."""
        return ConfidenceScorer(test_settings)

    def test_score_with_good_data(self, scorer):
        """Test scoring with comprehensive data."""
        context = [
            {
                "entity_type": "campaign",
                "name": "Test Campaign",
                "status": "active",
                "budget": 1000,
                "date": "2024-07-01",
            },
            {
                "entity_type": "metric",
                "impressions": 10000,
                "clicks": 300,
                "spend": 500,
                "date": "2024-07-01",
            },
        ] * 10  # Multiple data points

        query = "What was the performance of Test Campaign?"
        date_range = ("2024-07-01", "2024-07-31")

        score = scorer.score(query, context, date_range)

        assert score.overall > 0
        assert score.level in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM]
        assert "data_quantity" in score.factors

    def test_score_with_empty_context(self, scorer):
        """Test scoring with no data."""
        score = scorer.score("Test query", [], None)

        assert score.overall < 0.5
        assert score.level == ConfidenceLevel.INSUFFICIENT
        assert len(score.missing_data) > 0

    def test_score_with_limited_data(self, scorer):
        """Test scoring with limited data."""
        context = [
            {"name": "Test Campaign", "status": "active"},
        ]

        score = scorer.score("Test query", context, None)

        assert score.overall < 0.8
        assert score.level in [ConfidenceLevel.LOW, ConfidenceLevel.MEDIUM, ConfidenceLevel.INSUFFICIENT]

    def test_should_refuse(self, scorer):
        """Test refuse decision."""
        low_score = ConfidenceScore(
            overall=0.3,
            level=ConfidenceLevel.INSUFFICIENT,
            factors={},
            explanation="Test",
            missing_data=["No data"],
        )

        high_score = ConfidenceScore(
            overall=0.9,
            level=ConfidenceLevel.HIGH,
            factors={},
            explanation="Test",
            missing_data=[],
        )

        assert scorer.should_refuse(low_score) is True
        assert scorer.should_refuse(high_score) is False

    def test_format_confidence_for_response(self, scorer):
        """Test confidence formatting."""
        score = ConfidenceScore(
            overall=0.85,
            level=ConfidenceLevel.HIGH,
            factors={},
            explanation="Good data coverage",
            missing_data=[],
        )

        formatted = scorer.format_confidence_for_response(score)

        assert "High" in formatted
        assert "Confidence" in formatted


class TestRetrieval:
    """Tests for HybridRetriever."""

    @pytest.fixture
    def retriever(self, mock_neo4j_client, test_settings):
        """Create retriever with mock client."""
        from src.rag.retrieval import HybridRetriever

        return HybridRetriever(mock_neo4j_client, test_settings)

    def test_parse_query_intent_performance(self, retriever):
        """Test parsing performance query intent."""
        query = "What was the CTR for campaigns last month?"
        intent = retriever._parse_query_intent(query)

        assert intent["query_type"] == "performance"
        assert intent["time_period"] == "last_month"
        assert intent["entity_type"] == "campaign"

    def test_parse_query_intent_comparison(self, retriever):
        """Test parsing comparison query intent."""
        query = "Compare Google Ads vs Meta performance"
        intent = retriever._parse_query_intent(query)

        assert intent["query_type"] == "comparison"

    def test_parse_query_intent_financial(self, retriever):
        """Test parsing financial query intent."""
        query = "What was the ROAS this quarter?"
        intent = retriever._parse_query_intent(query)

        assert intent["query_type"] == "financial"
        assert intent["time_period"] == "quarter"

    def test_get_default_date_range(self, retriever):
        """Test default date range calculation."""
        intent = {"time_period": "last_month"}
        start, end = retriever._get_default_date_range(intent)

        assert start < end
        assert len(start) == 10  # YYYY-MM-DD format
        assert len(end) == 10

    def test_format_context_for_llm(self, retriever):
        """Test context formatting."""
        from src.rag.retrieval import RetrievalContext

        context = RetrievalContext(
            query="Test query",
            client_id="client-123",
            entities=[
                {"entity_type": "campaign", "name": "Test", "id": "camp-1", "status": "active"}
            ],
            metrics=[
                {
                    "entity_id": "camp-1",
                    "impressions": 1000,
                    "clicks": 50,
                    "spend": 100,
                }
            ],
            relationships=[],
            date_range=("2024-07-01", "2024-07-31"),
            metadata={},
        )

        formatted = retriever.format_context_for_llm(context)

        assert "2024-07-01" in formatted
        assert "Test" in formatted
        assert "campaign" in formatted.lower()


class TestPrompts:
    """Tests for prompt templates."""

    def test_system_prompt_exists(self):
        """Test that system prompt is defined."""
        from src.rag.prompts import SYSTEM_PROMPT

        assert len(SYSTEM_PROMPT) > 0
        assert "accuracy" in SYSTEM_PROMPT.lower() or "source" in SYSTEM_PROMPT.lower()

    def test_low_confidence_prompt_has_placeholders(self):
        """Test that low confidence prompt has required placeholders."""
        from src.rag.prompts import LOW_CONFIDENCE_PROMPT

        assert "{question}" in LOW_CONFIDENCE_PROMPT
        assert "{context}" in LOW_CONFIDENCE_PROMPT
        assert "{missing}" in LOW_CONFIDENCE_PROMPT

    def test_recommendation_prompt_has_placeholders(self):
        """Test that recommendation prompt has required placeholders."""
        from src.rag.prompts import RECOMMENDATION_PROMPT

        assert "{campaign_data}" in RECOMMENDATION_PROMPT
        assert "{metrics}" in RECOMMENDATION_PROMPT
