"""Hybrid retrieval combining graph traversal and vector search."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from config.settings import Settings, get_settings
from src.graph.client import Neo4jClient, get_neo4j_client
from src.graph.queries import CypherQueries

logger = logging.getLogger(__name__)


@dataclass
class RetrievalContext:
    """Context retrieved for a query."""

    query: str
    client_id: str
    entities: list[dict[str, Any]]
    metrics: list[dict[str, Any]]
    relationships: list[dict[str, Any]]
    date_range: tuple[str, str] | None
    metadata: dict[str, Any]


class HybridRetriever:
    """Combines graph traversal with optional vector search."""

    def __init__(
        self,
        neo4j_client: Neo4jClient | None = None,
        settings: Settings | None = None,
    ):
        """Initialize the retriever.

        Args:
            neo4j_client: Neo4j client instance.
            settings: Application settings.
        """
        self._neo4j = neo4j_client or get_neo4j_client()
        self._settings = settings or get_settings()
        self._queries = CypherQueries()

    def retrieve(
        self,
        query: str,
        client_id: str,
        date_range: tuple[str, str] | None = None,
        max_results: int | None = None,
    ) -> RetrievalContext:
        """Retrieve relevant context for a query.

        Args:
            query: User's natural language query.
            client_id: Client ID for isolation.
            date_range: Optional date range (start, end) in YYYY-MM-DD format.
            max_results: Maximum results to return.

        Returns:
            RetrievalContext with relevant data.
        """
        max_results = max_results or self._settings.MAX_QUERY_RESULTS

        # Parse query to understand intent
        query_intent = self._parse_query_intent(query)

        # Set default date range if not specified
        if not date_range:
            date_range = self._get_default_date_range(query_intent)

        entities = []
        metrics = []
        relationships = []

        # Step 1: Entity retrieval based on query terms
        entities = self._retrieve_entities(query, client_id, query_intent)

        # Step 2: Metrics retrieval
        metrics = self._retrieve_metrics(
            client_id,
            date_range,
            query_intent,
            [e.get("id") for e in entities if e.get("id")],
        )

        # Step 3: Relationship context
        relationships = self._retrieve_relationships(
            client_id, [e.get("id") for e in entities if e.get("id")]
        )

        logger.info(
            f"Retrieved {len(entities)} entities, {len(metrics)} metrics, "
            f"{len(relationships)} relationships for query: {query[:50]}..."
        )

        return RetrievalContext(
            query=query,
            client_id=client_id,
            entities=entities[:max_results],
            metrics=metrics[:max_results * 10],  # More metrics than entities
            relationships=relationships[:max_results],
            date_range=date_range,
            metadata={
                "query_intent": query_intent,
                "retrieval_timestamp": datetime.utcnow().isoformat(),
            },
        )

    def _parse_query_intent(self, query: str) -> dict[str, Any]:
        """Parse query to understand user intent.

        Args:
            query: User query.

        Returns:
            Intent dictionary with parsed components.
        """
        query_lower = query.lower()

        # Determine query type
        query_type = "general"
        if any(w in query_lower for w in ["compare", "vs", "versus", "difference"]):
            query_type = "comparison"
        elif any(w in query_lower for w in ["trend", "over time", "history"]):
            query_type = "trend"
        elif any(w in query_lower for w in ["top", "best", "worst", "bottom"]):
            query_type = "ranking"
        elif any(
            w in query_lower
            for w in ["spend", "cost", "budget", "roas", "roi", "revenue"]
        ):
            query_type = "financial"
        elif any(w in query_lower for w in ["click", "impression", "ctr", "cpc"]):
            query_type = "performance"
        elif any(w in query_lower for w in ["recommend", "suggest", "improve"]):
            query_type = "recommendation"

        # Extract time references
        time_period = None
        if "last month" in query_lower:
            time_period = "last_month"
        elif "last week" in query_lower:
            time_period = "last_week"
        elif "today" in query_lower:
            time_period = "today"
        elif "yesterday" in query_lower:
            time_period = "yesterday"
        elif "this month" in query_lower:
            time_period = "this_month"
        elif "this quarter" in query_lower or "q1" in query_lower or "q2" in query_lower:
            time_period = "quarter"
        elif "this year" in query_lower or "ytd" in query_lower:
            time_period = "year"

        # Extract entity references
        entity_type = "all"
        if "campaign" in query_lower:
            entity_type = "campaign"
        elif "ad set" in query_lower or "adset" in query_lower:
            entity_type = "adset"
        elif "ad" in query_lower and "campaign" not in query_lower:
            entity_type = "ad"

        # Extract channel references
        channel = None
        if "google" in query_lower:
            channel = "google_ads"
        elif "meta" in query_lower or "facebook" in query_lower or "instagram" in query_lower:
            channel = "meta"

        return {
            "query_type": query_type,
            "time_period": time_period,
            "entity_type": entity_type,
            "channel": channel,
        }

    def _get_default_date_range(
        self, query_intent: dict[str, Any]
    ) -> tuple[str, str]:
        """Get default date range based on query intent.

        Args:
            query_intent: Parsed query intent.

        Returns:
            Tuple of (start_date, end_date) in YYYY-MM-DD format.
        """
        today = datetime.now()

        time_period = query_intent.get("time_period")

        if time_period == "today":
            start = end = today
        elif time_period == "yesterday":
            start = end = today - timedelta(days=1)
        elif time_period == "last_week":
            start = today - timedelta(days=7)
            end = today
        elif time_period == "this_month":
            start = today.replace(day=1)
            end = today
        elif time_period == "last_month":
            first_of_month = today.replace(day=1)
            end = first_of_month - timedelta(days=1)
            start = end.replace(day=1)
        elif time_period == "quarter":
            quarter_month = ((today.month - 1) // 3) * 3 + 1
            start = today.replace(month=quarter_month, day=1)
            end = today
        elif time_period == "year":
            start = today.replace(month=1, day=1)
            end = today
        else:
            # Default to last 30 days
            start = today - timedelta(days=30)
            end = today

        return (start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))

    def _retrieve_entities(
        self,
        query: str,
        client_id: str,
        query_intent: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Retrieve relevant entities from the graph.

        Args:
            query: User query.
            client_id: Client ID.
            query_intent: Parsed query intent.

        Returns:
            List of entity dictionaries.
        """
        entities = []
        entity_type = query_intent.get("entity_type", "all")
        channel = query_intent.get("channel")

        # Get campaigns
        if entity_type in ["all", "campaign"]:
            campaign_query = """
            MATCH (c:Client {id: $client_id})-[:OWNS]->(camp:Campaign)
            WHERE ($channel IS NULL OR camp.channel = $channel)
            RETURN camp
            ORDER BY camp.start_date DESC
            LIMIT 50
            """
            campaigns = self._neo4j.execute_query(
                campaign_query, {"client_id": client_id, "channel": channel}
            )
            for c in campaigns:
                if c.get("camp"):
                    entities.append({**c["camp"], "entity_type": "campaign"})

        # Get ad sets
        if entity_type in ["all", "adset"]:
            adset_query = """
            MATCH (a:AdSet {client_id: $client_id})
            RETURN a
            LIMIT 50
            """
            adsets = self._neo4j.execute_query(adset_query, {"client_id": client_id})
            for a in adsets:
                if a.get("a"):
                    entities.append({**a["a"], "entity_type": "adset"})

        # Search by name if query contains specific terms
        search_terms = [
            word for word in query.split() if len(word) > 3 and word.isalpha()
        ]
        if search_terms:
            for term in search_terms[:3]:  # Limit search terms
                search_query = """
                MATCH (c:Client {id: $client_id})-[:OWNS]->(camp:Campaign)
                WHERE toLower(camp.name) CONTAINS toLower($term)
                RETURN camp
                LIMIT 10
                """
                results = self._neo4j.execute_query(
                    search_query, {"client_id": client_id, "term": term}
                )
                for r in results:
                    if r.get("camp") and r["camp"] not in [
                        e for e in entities if e.get("id") == r["camp"].get("id")
                    ]:
                        entities.append({**r["camp"], "entity_type": "campaign"})

        return entities

    def _retrieve_metrics(
        self,
        client_id: str,
        date_range: tuple[str, str],
        query_intent: dict[str, Any],
        entity_ids: list[str],
    ) -> list[dict[str, Any]]:
        """Retrieve metrics from the graph.

        Args:
            client_id: Client ID.
            date_range: Date range tuple.
            query_intent: Parsed query intent.
            entity_ids: Entity IDs to get metrics for.

        Returns:
            List of metric dictionaries.
        """
        start_date, end_date = date_range

        # Get aggregated metrics for client
        summary_query = """
        MATCH (m:Metric {client_id: $client_id})
        WHERE m.date >= date($start_date) AND m.date <= date($end_date)
        RETURN m
        ORDER BY m.date DESC
        LIMIT 500
        """
        metrics = self._neo4j.execute_query(
            summary_query,
            {"client_id": client_id, "start_date": start_date, "end_date": end_date},
        )

        result = []
        for m in metrics:
            if m.get("m"):
                result.append(m["m"])

        # If specific entities, filter metrics
        if entity_ids:
            result = [m for m in result if m.get("entity_id") in entity_ids] or result

        return result

    def _retrieve_relationships(
        self,
        client_id: str,
        entity_ids: list[str],
    ) -> list[dict[str, Any]]:
        """Retrieve relationship context from the graph.

        Args:
            client_id: Client ID.
            entity_ids: Entity IDs to get relationships for.

        Returns:
            List of relationship dictionaries.
        """
        if not entity_ids:
            return []

        # Get campaign -> adset -> ad hierarchy
        hierarchy_query = """
        MATCH (c:Client {id: $client_id})-[:OWNS]->(camp:Campaign)
        WHERE camp.id IN $entity_ids
        OPTIONAL MATCH (camp)-[:CONTAINS]->(adset:AdSet)
        OPTIONAL MATCH (adset)-[:CONTAINS]->(ad:Ad)
        RETURN camp.id AS campaign_id,
            camp.name AS campaign_name,
            collect(DISTINCT {id: adset.id, name: adset.name}) AS adsets,
            collect(DISTINCT {id: ad.id, name: ad.name}) AS ads
        """

        results = self._neo4j.execute_query(
            hierarchy_query, {"client_id": client_id, "entity_ids": entity_ids[:20]}
        )

        return results

    def retrieve_for_follow_up(
        self,
        query: str,
        client_id: str,
        previous_context: RetrievalContext,
    ) -> RetrievalContext:
        """Retrieve context for a follow-up question.

        Args:
            query: Follow-up query.
            client_id: Client ID.
            previous_context: Context from previous query.

        Returns:
            Combined context.
        """
        # Get new context
        new_context = self.retrieve(
            query, client_id, previous_context.date_range
        )

        # Merge with previous context, prioritizing new
        combined_entities = new_context.entities + [
            e
            for e in previous_context.entities
            if e.get("id") not in [n.get("id") for n in new_context.entities]
        ]

        combined_metrics = new_context.metrics + [
            m
            for m in previous_context.metrics
            if m.get("id") not in [n.get("id") for n in new_context.metrics]
        ]

        return RetrievalContext(
            query=query,
            client_id=client_id,
            entities=combined_entities[: self._settings.MAX_QUERY_RESULTS],
            metrics=combined_metrics[: self._settings.MAX_QUERY_RESULTS * 10],
            relationships=new_context.relationships + previous_context.relationships,
            date_range=new_context.date_range,
            metadata={
                **new_context.metadata,
                "is_follow_up": True,
                "previous_query": previous_context.query,
            },
        )

    def format_context_for_llm(self, context: RetrievalContext) -> str:
        """Format retrieved context for LLM consumption.

        Args:
            context: Retrieved context.

        Returns:
            Formatted string for LLM prompt.
        """
        parts = []

        # Add date range context
        if context.date_range:
            parts.append(
                f"Data period: {context.date_range[0]} to {context.date_range[1]}"
            )

        # Add entities
        if context.entities:
            parts.append("\n## Campaigns and Entities:")
            for entity in context.entities[:20]:  # Limit for token budget
                entity_type = entity.get("entity_type", "entity")
                name = entity.get("name", "Unknown")
                status = entity.get("status", "")
                parts.append(f"- [{entity_type.upper()}] {name} (ID: {entity.get('id', 'N/A')}, Status: {status})")
                if entity.get("objective"):
                    parts.append(f"  Objective: {entity['objective']}")
                if entity.get("budget"):
                    parts.append(
                        f"  Budget: {entity['budget']} {entity.get('budget_currency', 'USD')}"
                    )

        # Add metrics summary
        if context.metrics:
            parts.append("\n## Performance Metrics:")

            # Aggregate by entity
            metrics_by_entity = {}
            for m in context.metrics:
                entity_id = m.get("entity_id", "unknown")
                if entity_id not in metrics_by_entity:
                    metrics_by_entity[entity_id] = {
                        "impressions": 0,
                        "clicks": 0,
                        "conversions": 0,
                        "spend": 0,
                        "revenue": 0,
                        "dates": [],
                    }
                metrics_by_entity[entity_id]["impressions"] += m.get("impressions", 0)
                metrics_by_entity[entity_id]["clicks"] += m.get("clicks", 0)
                metrics_by_entity[entity_id]["conversions"] += m.get("conversions", 0)
                metrics_by_entity[entity_id]["spend"] += m.get("spend", 0)
                if m.get("revenue"):
                    metrics_by_entity[entity_id]["revenue"] += m.get("revenue", 0)
                if m.get("date"):
                    metrics_by_entity[entity_id]["dates"].append(str(m["date"]))

            for entity_id, agg in list(metrics_by_entity.items())[:10]:
                # Find entity name
                entity_name = next(
                    (e.get("name") for e in context.entities if e.get("id") == entity_id),
                    entity_id,
                )

                ctr = (
                    agg["clicks"] / agg["impressions"] * 100
                    if agg["impressions"] > 0
                    else 0
                )
                cpc = agg["spend"] / agg["clicks"] if agg["clicks"] > 0 else 0
                roas = agg["revenue"] / agg["spend"] if agg["spend"] > 0 and agg["revenue"] > 0 else None

                parts.append(f"\n### {entity_name}")
                parts.append(f"- Impressions: {agg['impressions']:,}")
                parts.append(f"- Clicks: {agg['clicks']:,}")
                parts.append(f"- CTR: {ctr:.2f}%")
                parts.append(f"- Conversions: {agg['conversions']:,}")
                parts.append(f"- Spend: ${agg['spend']:,.2f}")
                parts.append(f"- CPC: ${cpc:.2f}")
                if roas:
                    parts.append(f"- Revenue: ${agg['revenue']:,.2f}")
                    parts.append(f"- ROAS: {roas:.2f}x")

        # Add relationships
        if context.relationships:
            parts.append("\n## Campaign Structure:")
            for rel in context.relationships[:5]:
                parts.append(f"- Campaign: {rel.get('campaign_name', 'Unknown')}")
                if rel.get("adsets"):
                    adsets = [a.get("name") for a in rel["adsets"] if a.get("name")]
                    if adsets:
                        parts.append(f"  Ad Sets: {', '.join(adsets[:5])}")

        return "\n".join(parts)
