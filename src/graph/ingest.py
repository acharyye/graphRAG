"""Data ingestion pipeline for loading data into Neo4j."""

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from .client import Neo4jClient, get_neo4j_client
from .schema import CampaignStatus, NodeLabel, RelationType

logger = logging.getLogger(__name__)


class DataIngester:
    """Handles ingestion of marketing data into Neo4j graph."""

    def __init__(self, client: Neo4jClient | None = None):
        """Initialize data ingester.

        Args:
            client: Neo4j client instance. Uses default if not provided.
        """
        self._client = client or get_neo4j_client()

    def ingest_client(self, client_data: dict[str, Any]) -> str:
        """Create or update a client node.

        Args:
            client_data: Client properties.

        Returns:
            Client ID.
        """
        client_id = client_data.get("id") or str(uuid4())
        now = datetime.utcnow().isoformat()

        query = """
        MERGE (c:Client {id: $id})
        ON CREATE SET
            c.name = $name,
            c.industry = $industry,
            c.contract_start = date($contract_start),
            c.budget = $budget,
            c.budget_currency = $budget_currency,
            c.status = $status,
            c.data_retention_days = $data_retention_days,
            c.created_at = datetime($now),
            c.updated_at = datetime($now)
        ON MATCH SET
            c.name = $name,
            c.industry = $industry,
            c.budget = $budget,
            c.budget_currency = $budget_currency,
            c.status = $status,
            c.data_retention_days = $data_retention_days,
            c.updated_at = datetime($now)
        RETURN c.id AS id
        """

        params = {
            "id": client_id,
            "name": client_data["name"],
            "industry": client_data.get("industry", "Unknown"),
            "contract_start": client_data.get("contract_start", now[:10]),
            "budget": float(client_data.get("budget", 0)),
            "budget_currency": client_data.get("budget_currency", "USD"),
            "status": client_data.get("status", "active"),
            "data_retention_days": int(client_data.get("data_retention_days", 365)),
            "now": now,
        }

        result = self._client.execute_query(query, params)
        logger.info(f"Ingested client: {client_data['name']} ({client_id})")
        return result[0]["id"]

    def ingest_campaign(self, campaign_data: dict[str, Any], client_id: str) -> str:
        """Create or update a campaign node.

        Args:
            campaign_data: Campaign properties.
            client_id: Parent client ID.

        Returns:
            Campaign ID.
        """
        campaign_id = campaign_data.get("id") or str(uuid4())
        now = datetime.utcnow().isoformat()

        query = """
        MATCH (client:Client {id: $client_id})
        MERGE (c:Campaign {id: $id})
        ON CREATE SET
            c.client_id = $client_id,
            c.external_id = $external_id,
            c.name = $name,
            c.objective = $objective,
            c.start_date = date($start_date),
            c.end_date = CASE WHEN $end_date IS NOT NULL THEN date($end_date) ELSE null END,
            c.budget = $budget,
            c.budget_currency = $budget_currency,
            c.daily_budget = $daily_budget,
            c.status = $status,
            c.channel = $channel,
            c.created_at = datetime($now),
            c.updated_at = datetime($now)
        ON MATCH SET
            c.name = $name,
            c.objective = $objective,
            c.budget = $budget,
            c.budget_currency = $budget_currency,
            c.daily_budget = $daily_budget,
            c.status = $status,
            c.updated_at = datetime($now)
        MERGE (client)-[:OWNS]->(c)
        WITH c
        MATCH (ch:Channel {name: $channel})
        MERGE (c)-[:RUNS_ON]->(ch)
        RETURN c.id AS id
        """

        params = {
            "id": campaign_id,
            "client_id": client_id,
            "external_id": campaign_data.get("external_id"),
            "name": campaign_data["name"],
            "objective": campaign_data.get("objective", "conversions"),
            "start_date": campaign_data["start_date"],
            "end_date": campaign_data.get("end_date"),
            "budget": float(campaign_data.get("budget", 0)),
            "budget_currency": campaign_data.get("budget_currency", "USD"),
            "daily_budget": campaign_data.get("daily_budget"),
            "status": campaign_data.get("status", CampaignStatus.ACTIVE.value),
            "channel": campaign_data.get("channel", "google_ads"),
            "now": now,
        }

        result = self._client.execute_query(query, params)
        logger.info(f"Ingested campaign: {campaign_data['name']} ({campaign_id})")
        return result[0]["id"]

    def ingest_adset(
        self, adset_data: dict[str, Any], campaign_id: str, client_id: str
    ) -> str:
        """Create or update an ad set node.

        Args:
            adset_data: Ad set properties.
            campaign_id: Parent campaign ID.
            client_id: Parent client ID.

        Returns:
            Ad set ID.
        """
        adset_id = adset_data.get("id") or str(uuid4())
        now = datetime.utcnow().isoformat()

        query = """
        MATCH (camp:Campaign {id: $campaign_id})
        MERGE (a:AdSet {id: $id})
        ON CREATE SET
            a.client_id = $client_id,
            a.campaign_id = $campaign_id,
            a.external_id = $external_id,
            a.name = $name,
            a.targeting = $targeting,
            a.budget = $budget,
            a.budget_currency = $budget_currency,
            a.status = $status,
            a.created_at = datetime($now),
            a.updated_at = datetime($now)
        ON MATCH SET
            a.name = $name,
            a.targeting = $targeting,
            a.budget = $budget,
            a.budget_currency = $budget_currency,
            a.status = $status,
            a.updated_at = datetime($now)
        MERGE (camp)-[:CONTAINS]->(a)
        RETURN a.id AS id
        """

        params = {
            "id": adset_id,
            "client_id": client_id,
            "campaign_id": campaign_id,
            "external_id": adset_data.get("external_id"),
            "name": adset_data["name"],
            "targeting": adset_data.get("targeting", "{}"),
            "budget": float(adset_data.get("budget", 0)),
            "budget_currency": adset_data.get("budget_currency", "USD"),
            "status": adset_data.get("status", "active"),
            "now": now,
        }

        result = self._client.execute_query(query, params)
        logger.info(f"Ingested ad set: {adset_data['name']} ({adset_id})")
        return result[0]["id"]

    def ingest_ad(self, ad_data: dict[str, Any], adset_id: str, client_id: str) -> str:
        """Create or update an ad node.

        Args:
            ad_data: Ad properties.
            adset_id: Parent ad set ID.
            client_id: Parent client ID.

        Returns:
            Ad ID.
        """
        ad_id = ad_data.get("id") or str(uuid4())
        now = datetime.utcnow().isoformat()

        query = """
        MATCH (adset:AdSet {id: $adset_id})
        MERGE (a:Ad {id: $id})
        ON CREATE SET
            a.client_id = $client_id,
            a.adset_id = $adset_id,
            a.external_id = $external_id,
            a.name = $name,
            a.headline = $headline,
            a.description = $description,
            a.creative_type = $creative_type,
            a.status = $status,
            a.created_at = datetime($now),
            a.updated_at = datetime($now)
        ON MATCH SET
            a.name = $name,
            a.headline = $headline,
            a.description = $description,
            a.status = $status,
            a.updated_at = datetime($now)
        MERGE (adset)-[:CONTAINS]->(a)
        RETURN a.id AS id
        """

        params = {
            "id": ad_id,
            "client_id": client_id,
            "adset_id": adset_id,
            "external_id": ad_data.get("external_id"),
            "name": ad_data["name"],
            "headline": ad_data.get("headline", ""),
            "description": ad_data.get("description", ""),
            "creative_type": ad_data.get("creative_type", "image"),
            "status": ad_data.get("status", "active"),
            "now": now,
        }

        result = self._client.execute_query(query, params)
        logger.info(f"Ingested ad: {ad_data['name']} ({ad_id})")
        return result[0]["id"]

    def ingest_metrics(
        self,
        metrics_data: list[dict[str, Any]],
        entity_type: str,
        entity_id: str,
        client_id: str,
    ) -> int:
        """Bulk ingest metrics for an entity.

        Args:
            metrics_data: List of metric records.
            entity_type: Type of entity (campaign/adset/ad).
            entity_id: Entity UUID.
            client_id: Client UUID.

        Returns:
            Number of metrics ingested.
        """
        query = """
        UNWIND $metrics AS metric
        MERGE (m:Metric {id: metric.id})
        ON CREATE SET
            m.client_id = $client_id,
            m.entity_type = $entity_type,
            m.entity_id = $entity_id,
            m.date = date(metric.date),
            m.impressions = metric.impressions,
            m.clicks = metric.clicks,
            m.conversions = metric.conversions,
            m.spend = metric.spend,
            m.spend_currency = metric.spend_currency,
            m.revenue = metric.revenue,
            m.revenue_currency = metric.revenue_currency,
            m.ctr = CASE WHEN metric.impressions > 0
                THEN toFloat(metric.clicks) / metric.impressions * 100
                ELSE 0 END,
            m.cpc = CASE WHEN metric.clicks > 0
                THEN metric.spend / metric.clicks
                ELSE 0 END,
            m.cpm = CASE WHEN metric.impressions > 0
                THEN metric.spend / metric.impressions * 1000
                ELSE 0 END,
            m.roas = CASE WHEN metric.spend > 0 AND metric.revenue IS NOT NULL
                THEN metric.revenue / metric.spend
                ELSE null END,
            m.created_at = datetime()
        ON MATCH SET
            m.impressions = metric.impressions,
            m.clicks = metric.clicks,
            m.conversions = metric.conversions,
            m.spend = metric.spend,
            m.revenue = metric.revenue,
            m.ctr = CASE WHEN metric.impressions > 0
                THEN toFloat(metric.clicks) / metric.impressions * 100
                ELSE 0 END,
            m.cpc = CASE WHEN metric.clicks > 0
                THEN metric.spend / metric.clicks
                ELSE 0 END,
            m.cpm = CASE WHEN metric.impressions > 0
                THEN metric.spend / metric.impressions * 1000
                ELSE 0 END,
            m.roas = CASE WHEN metric.spend > 0 AND metric.revenue IS NOT NULL
                THEN metric.revenue / metric.spend
                ELSE null END
        """

        # Prepare metrics with IDs
        prepared_metrics = []
        for m in metrics_data:
            metric_id = m.get("id") or f"{entity_id}_{m['date']}"
            prepared_metrics.append(
                {
                    "id": metric_id,
                    "date": m["date"],
                    "impressions": int(m.get("impressions", 0)),
                    "clicks": int(m.get("clicks", 0)),
                    "conversions": int(m.get("conversions", 0)),
                    "spend": float(m.get("spend", 0)),
                    "spend_currency": m.get("spend_currency", "USD"),
                    "revenue": m.get("revenue"),
                    "revenue_currency": m.get("revenue_currency"),
                }
            )

        params = {
            "metrics": prepared_metrics,
            "client_id": client_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
        }

        self._client.execute_query(query, params)
        logger.info(
            f"Ingested {len(prepared_metrics)} metrics for {entity_type} {entity_id}"
        )
        return len(prepared_metrics)

    def ingest_user(self, user_data: dict[str, Any]) -> str:
        """Create or update a user node.

        Args:
            user_data: User properties including hashed_password.

        Returns:
            User ID.
        """
        user_id = user_data.get("id") or str(uuid4())
        now = datetime.utcnow().isoformat()

        query = """
        MERGE (u:User {id: $id})
        ON CREATE SET
            u.email = $email,
            u.hashed_password = $hashed_password,
            u.name = $name,
            u.role = $role,
            u.client_ids = $client_ids,
            u.created_at = datetime($now),
            u.updated_at = datetime($now)
        ON MATCH SET
            u.name = $name,
            u.role = $role,
            u.client_ids = $client_ids,
            u.updated_at = datetime($now)
        RETURN u.id AS id
        """

        params = {
            "id": user_id,
            "email": user_data["email"],
            "hashed_password": user_data["hashed_password"],
            "name": user_data.get("name", ""),
            "role": user_data.get("role", "manager"),
            "client_ids": user_data.get("client_ids", []),
            "now": now,
        }

        result = self._client.execute_query(query, params)
        logger.info(f"Ingested user: {user_data['email']} ({user_id})")
        return result[0]["id"]
