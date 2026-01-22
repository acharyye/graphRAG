"""GraphRAG engine combining graph retrieval with Claude LLM."""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import uuid4

from anthropic import Anthropic

from config.settings import Settings, get_settings
from src.graph.client import Neo4jClient, get_neo4j_client

from .confidence import ConfidenceScore, ConfidenceScorer
from .prompts import (
    FOLLOW_UP_PROMPT,
    LOW_CONFIDENCE_PROMPT,
    RECOMMENDATION_PROMPT,
    SYSTEM_PROMPT,
)
from .retrieval import HybridRetriever, RetrievalContext

logger = logging.getLogger(__name__)


@dataclass
class Source:
    """Source reference for an answer."""

    entity_type: str
    entity_id: str
    entity_name: str | None
    date_range: str | None


@dataclass
class QueryResult:
    """Result of a GraphRAG query."""

    answer: str
    confidence: ConfidenceScore
    sources: list[Source]
    query_id: str
    timestamp: str
    context_summary: str
    drill_down_available: bool
    recommendations: list[str] | None = None


class ConversationMemory:
    """Manages conversation history for follow-up questions."""

    def __init__(self, max_turns: int = 10):
        """Initialize conversation memory.

        Args:
            max_turns: Maximum conversation turns to remember.
        """
        self._max_turns = max_turns
        self._sessions: dict[str, list[dict[str, Any]]] = {}

    def add_turn(
        self,
        session_id: str,
        query: str,
        answer: str,
        context: RetrievalContext,
    ) -> None:
        """Add a conversation turn.

        Args:
            session_id: Session identifier.
            query: User query.
            answer: System answer.
            context: Retrieved context.
        """
        if session_id not in self._sessions:
            self._sessions[session_id] = []

        self._sessions[session_id].append(
            {
                "query": query,
                "answer": answer,
                "context": context,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        # Trim to max turns
        if len(self._sessions[session_id]) > self._max_turns:
            self._sessions[session_id] = self._sessions[session_id][-self._max_turns:]

    def get_history(self, session_id: str) -> list[dict[str, Any]]:
        """Get conversation history.

        Args:
            session_id: Session identifier.

        Returns:
            List of conversation turns.
        """
        return self._sessions.get(session_id, [])

    def get_last_context(self, session_id: str) -> RetrievalContext | None:
        """Get the last retrieval context.

        Args:
            session_id: Session identifier.

        Returns:
            Last context or None.
        """
        history = self.get_history(session_id)
        if history:
            return history[-1].get("context")
        return None

    def clear(self, session_id: str) -> None:
        """Clear session history.

        Args:
            session_id: Session identifier.
        """
        if session_id in self._sessions:
            del self._sessions[session_id]


class GraphRAGEngine:
    """Main GraphRAG engine for marketing analytics queries."""

    def __init__(
        self,
        neo4j_client: Neo4jClient | None = None,
        settings: Settings | None = None,
    ):
        """Initialize the GraphRAG engine.

        Args:
            neo4j_client: Neo4j client instance.
            settings: Application settings.
        """
        self._settings = settings or get_settings()
        self._neo4j = neo4j_client or get_neo4j_client()
        self._retriever = HybridRetriever(self._neo4j, self._settings)
        self._confidence_scorer = ConfidenceScorer(self._settings)
        self._memory = ConversationMemory()
        self._anthropic = Anthropic(api_key=self._settings.ANTHROPIC_API_KEY)

    def query(
        self,
        query: str,
        client_id: str,
        user_role: str = "manager",
        session_id: str | None = None,
        date_range: tuple[str, str] | None = None,
    ) -> QueryResult:
        """Process a natural language query.

        Args:
            query: User's query.
            client_id: Client ID for data isolation.
            user_role: User's role (affects drill-down access).
            session_id: Session ID for conversation memory.
            date_range: Optional date range override.

        Returns:
            QueryResult with answer, sources, and confidence.
        """
        query_id = str(uuid4())
        timestamp = datetime.utcnow().isoformat()

        logger.info(f"Processing query {query_id}: {query[:50]}...")

        # Check for follow-up context
        is_follow_up = False
        previous_context = None
        if session_id:
            previous_context = self._memory.get_last_context(session_id)
            if previous_context and self._is_follow_up_query(query):
                is_follow_up = True

        # Retrieve context
        if is_follow_up and previous_context:
            context = self._retriever.retrieve_for_follow_up(
                query, client_id, previous_context
            )
        else:
            context = self._retriever.retrieve(query, client_id, date_range)

        # Score confidence
        confidence = self._confidence_scorer.score(
            query,
            context.entities + context.metrics,
            context.date_range,
        )

        # Check if we should refuse to answer
        if self._confidence_scorer.should_refuse(confidence):
            answer = self._generate_low_confidence_response(query, context, confidence)
            sources = []
            recommendations = None
        else:
            # Generate answer with LLM
            answer = self._generate_answer(query, context, is_follow_up, previous_context)

            # Extract sources
            sources = self._extract_sources(context)

            # Generate recommendations if appropriate
            recommendations = None
            if self._should_include_recommendations(query, context):
                recommendations = self._generate_recommendations(context)

        # Store in conversation memory
        if session_id:
            self._memory.add_turn(session_id, query, answer, context)

        # Determine drill-down availability
        drill_down_available = user_role in ["analyst", "admin"] and len(
            context.relationships
        ) > 0

        # Format context summary
        context_summary = self._retriever.format_context_for_llm(context)

        return QueryResult(
            answer=answer,
            confidence=confidence,
            sources=sources,
            query_id=query_id,
            timestamp=timestamp,
            context_summary=context_summary,
            drill_down_available=drill_down_available,
            recommendations=recommendations,
        )

    def _is_follow_up_query(self, query: str) -> bool:
        """Check if query is a follow-up to previous conversation.

        Args:
            query: User query.

        Returns:
            True if likely a follow-up.
        """
        follow_up_indicators = [
            "more",
            "detail",
            "explain",
            "why",
            "how",
            "what about",
            "and",
            "also",
            "that",
            "this",
            "these",
            "those",
            "it",
            "they",
            "them",
        ]
        query_lower = query.lower()
        return any(ind in query_lower for ind in follow_up_indicators)

    def _generate_answer(
        self,
        query: str,
        context: RetrievalContext,
        is_follow_up: bool,
        previous_context: RetrievalContext | None,
    ) -> str:
        """Generate answer using Claude.

        Args:
            query: User query.
            context: Retrieved context.
            is_follow_up: Whether this is a follow-up query.
            previous_context: Previous context if follow-up.

        Returns:
            Generated answer.
        """
        # Format context for the prompt
        context_str = self._retriever.format_context_for_llm(context)

        # Build messages
        messages = []

        if is_follow_up and previous_context:
            # Include previous conversation context
            history = self._memory.get_history(
                context.metadata.get("session_id", "")
            )
            for turn in history[-3:]:  # Last 3 turns
                messages.append({"role": "user", "content": turn["query"]})
                messages.append({"role": "assistant", "content": turn["answer"]})

        # Add current query with context
        user_message = f"""Based on the following data context, answer the user's question.

## Data Context
{context_str}

## User Question
{query}

Provide a detailed answer with specific metrics and dates. Always cite your sources."""

        messages.append({"role": "user", "content": user_message})

        # Call Claude
        response = self._anthropic.messages.create(
            model=self._settings.ANTHROPIC_MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=messages,
        )

        answer = response.content[0].text
        logger.info(f"Generated answer with {len(answer)} characters")
        return answer

    def _generate_low_confidence_response(
        self,
        query: str,
        context: RetrievalContext,
        confidence: ConfidenceScore,
    ) -> str:
        """Generate response when confidence is too low.

        Args:
            query: User query.
            context: Retrieved context.
            confidence: Confidence score.

        Returns:
            Low-confidence response.
        """
        prompt = LOW_CONFIDENCE_PROMPT.format(
            question=query,
            context=self._retriever.format_context_for_llm(context),
            missing=", ".join(confidence.missing_data),
        )

        response = self._anthropic.messages.create(
            model=self._settings.ANTHROPIC_MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text

    def _extract_sources(self, context: RetrievalContext) -> list[Source]:
        """Extract source references from context.

        Args:
            context: Retrieved context.

        Returns:
            List of source references.
        """
        sources = []
        seen_ids = set()

        # Add entity sources
        for entity in context.entities[:10]:
            entity_id = entity.get("id")
            if entity_id and entity_id not in seen_ids:
                seen_ids.add(entity_id)
                sources.append(
                    Source(
                        entity_type=entity.get("entity_type", "entity"),
                        entity_id=entity_id,
                        entity_name=entity.get("name"),
                        date_range=f"{context.date_range[0]} to {context.date_range[1]}"
                        if context.date_range
                        else None,
                    )
                )

        return sources

    def _should_include_recommendations(
        self, query: str, context: RetrievalContext
    ) -> bool:
        """Determine if recommendations should be included.

        Args:
            query: User query.
            context: Retrieved context.

        Returns:
            True if recommendations should be included.
        """
        # Include for performance queries with sufficient data
        query_intent = context.metadata.get("query_intent", {})
        return (
            query_intent.get("query_type") in ["performance", "financial", "ranking"]
            and len(context.metrics) >= 10
        )

    def _generate_recommendations(self, context: RetrievalContext) -> list[str]:
        """Generate proactive recommendations.

        Args:
            context: Retrieved context.

        Returns:
            List of recommendations.
        """
        prompt = RECOMMENDATION_PROMPT.format(
            campaign_data=str(context.entities[:5]),
            metrics=self._retriever.format_context_for_llm(context),
            benchmarks="Industry average CTR: 2%, CPC: $1.50, ROAS: 3x (typical for e-commerce)",
        )

        response = self._anthropic.messages.create(
            model=self._settings.ANTHROPIC_MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse recommendations from response
        recommendations_text = response.content[0].text
        recommendations = [
            line.strip()
            for line in recommendations_text.split("\n")
            if line.strip() and (line.strip().startswith("-") or line.strip()[0].isdigit())
        ]

        return recommendations[:3]  # Limit to 3 recommendations

    def clear_session(self, session_id: str) -> None:
        """Clear conversation memory for a session.

        Args:
            session_id: Session identifier.
        """
        self._memory.clear(session_id)
        logger.info(f"Cleared session: {session_id}")


# Singleton instance
_engine: GraphRAGEngine | None = None


def get_graphrag_engine() -> GraphRAGEngine:
    """Get the GraphRAG engine singleton."""
    global _engine
    if _engine is None:
        _engine = GraphRAGEngine()
    return _engine
