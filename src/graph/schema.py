"""Neo4j graph schema definitions and initialization."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class NodeLabel(str, Enum):
    """Node labels in the graph."""

    CLIENT = "Client"
    CAMPAIGN = "Campaign"
    AD_SET = "AdSet"
    AD = "Ad"
    CHANNEL = "Channel"
    METRIC = "Metric"
    USER = "User"
    AUDIT_LOG = "AuditLog"


class RelationType(str, Enum):
    """Relationship types in the graph."""

    OWNS = "OWNS"  # Client -> Campaign
    CONTAINS = "CONTAINS"  # Campaign -> AdSet, AdSet -> Ad
    RUNS_ON = "RUNS_ON"  # Campaign -> Channel
    HAS_METRIC = "HAS_METRIC"  # Campaign/AdSet/Ad -> Metric
    WORKS_FOR = "WORKS_FOR"  # User -> Client
    QUERIED = "QUERIED"  # User -> AuditLog


class CampaignStatus(str, Enum):
    """Campaign status values."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    DRAFT = "draft"


class CampaignObjective(str, Enum):
    """Campaign objective types."""

    AWARENESS = "awareness"
    TRAFFIC = "traffic"
    ENGAGEMENT = "engagement"
    LEADS = "leads"
    CONVERSIONS = "conversions"
    SALES = "sales"


@dataclass
class GraphSchema:
    """Neo4j schema management."""

    # Constraints for data integrity and uniqueness
    CONSTRAINTS: list[str] = None

    # Indexes for query performance
    INDEXES: list[str] = None

    def __post_init__(self):
        self.CONSTRAINTS = [
            # Uniqueness constraints
            "CREATE CONSTRAINT client_id IF NOT EXISTS FOR (c:Client) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT campaign_id IF NOT EXISTS FOR (c:Campaign) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT adset_id IF NOT EXISTS FOR (a:AdSet) REQUIRE a.id IS UNIQUE",
            "CREATE CONSTRAINT ad_id IF NOT EXISTS FOR (a:Ad) REQUIRE a.id IS UNIQUE",
            "CREATE CONSTRAINT channel_name IF NOT EXISTS FOR (c:Channel) REQUIRE c.name IS UNIQUE",
            "CREATE CONSTRAINT user_email IF NOT EXISTS FOR (u:User) REQUIRE u.email IS UNIQUE",
            "CREATE CONSTRAINT audit_id IF NOT EXISTS FOR (a:AuditLog) REQUIRE a.id IS UNIQUE",
            # Metric composite uniqueness (entity + date)
            "CREATE CONSTRAINT metric_id IF NOT EXISTS FOR (m:Metric) REQUIRE m.id IS UNIQUE",
        ]

        self.INDEXES = [
            # Client indexes
            "CREATE INDEX client_name IF NOT EXISTS FOR (c:Client) ON (c.name)",
            "CREATE INDEX client_status IF NOT EXISTS FOR (c:Client) ON (c.status)",
            # Campaign indexes
            "CREATE INDEX campaign_client IF NOT EXISTS FOR (c:Campaign) ON (c.client_id)",
            "CREATE INDEX campaign_status IF NOT EXISTS FOR (c:Campaign) ON (c.status)",
            "CREATE INDEX campaign_objective IF NOT EXISTS FOR (c:Campaign) ON (c.objective)",
            "CREATE INDEX campaign_dates IF NOT EXISTS FOR (c:Campaign) ON (c.start_date, c.end_date)",
            # AdSet indexes
            "CREATE INDEX adset_client IF NOT EXISTS FOR (a:AdSet) ON (a.client_id)",
            "CREATE INDEX adset_campaign IF NOT EXISTS FOR (a:AdSet) ON (a.campaign_id)",
            # Ad indexes
            "CREATE INDEX ad_client IF NOT EXISTS FOR (a:Ad) ON (a.client_id)",
            "CREATE INDEX ad_adset IF NOT EXISTS FOR (a:Ad) ON (a.adset_id)",
            # Metric indexes (optimized for query speed)
            "CREATE INDEX metric_client IF NOT EXISTS FOR (m:Metric) ON (m.client_id)",
            "CREATE INDEX metric_date IF NOT EXISTS FOR (m:Metric) ON (m.date)",
            "CREATE INDEX metric_entity IF NOT EXISTS FOR (m:Metric) ON (m.entity_type, m.entity_id)",
            # Audit log indexes
            "CREATE INDEX audit_user IF NOT EXISTS FOR (a:AuditLog) ON (a.user_id)",
            "CREATE INDEX audit_client IF NOT EXISTS FOR (a:AuditLog) ON (a.client_id)",
            "CREATE INDEX audit_timestamp IF NOT EXISTS FOR (a:AuditLog) ON (a.timestamp)",
            # User indexes
            "CREATE INDEX user_role IF NOT EXISTS FOR (u:User) ON (u.role)",
        ]

    def get_all_statements(self) -> list[str]:
        """Get all schema creation statements."""
        return self.CONSTRAINTS + self.INDEXES


# Node property definitions for reference
NODE_PROPERTIES: dict[str, dict[str, Any]] = {
    NodeLabel.CLIENT: {
        "id": "string (UUID)",
        "name": "string",
        "industry": "string",
        "contract_start": "date",
        "contract_end": "date (optional)",
        "budget": "float",
        "budget_currency": "string (ISO 4217)",
        "status": "string (active/inactive)",
        "data_retention_days": "integer",
        "created_at": "datetime",
        "updated_at": "datetime",
    },
    NodeLabel.CAMPAIGN: {
        "id": "string (UUID)",
        "client_id": "string (UUID, for isolation)",
        "external_id": "string (platform ID)",
        "name": "string",
        "objective": "string (CampaignObjective)",
        "start_date": "date",
        "end_date": "date (optional)",
        "budget": "float",
        "budget_currency": "string (ISO 4217)",
        "daily_budget": "float (optional)",
        "status": "string (CampaignStatus)",
        "channel": "string (google_ads/meta)",
        "created_at": "datetime",
        "updated_at": "datetime",
    },
    NodeLabel.AD_SET: {
        "id": "string (UUID)",
        "client_id": "string (UUID, for isolation)",
        "campaign_id": "string (UUID)",
        "external_id": "string (platform ID)",
        "name": "string",
        "targeting": "string (JSON)",
        "budget": "float",
        "budget_currency": "string (ISO 4217)",
        "status": "string",
        "created_at": "datetime",
        "updated_at": "datetime",
    },
    NodeLabel.AD: {
        "id": "string (UUID)",
        "client_id": "string (UUID, for isolation)",
        "adset_id": "string (UUID)",
        "external_id": "string (platform ID)",
        "name": "string",
        "headline": "string",
        "description": "string",
        "creative_type": "string (image/video/carousel)",
        "status": "string",
        "created_at": "datetime",
        "updated_at": "datetime",
    },
    NodeLabel.CHANNEL: {
        "name": "string (google_ads/meta)",
        "display_name": "string",
    },
    NodeLabel.METRIC: {
        "id": "string (UUID)",
        "client_id": "string (UUID, for isolation)",
        "entity_type": "string (campaign/adset/ad)",
        "entity_id": "string (UUID)",
        "date": "date",
        "impressions": "integer",
        "clicks": "integer",
        "conversions": "integer",
        "spend": "float",
        "spend_currency": "string (ISO 4217)",
        "revenue": "float (optional)",
        "revenue_currency": "string (ISO 4217, optional)",
        "ctr": "float (calculated)",
        "cpc": "float (calculated)",
        "cpm": "float (calculated)",
        "roas": "float (calculated, optional)",
        "created_at": "datetime",
    },
    NodeLabel.USER: {
        "id": "string (UUID)",
        "email": "string",
        "hashed_password": "string",
        "name": "string",
        "role": "string (admin/analyst/manager/executive)",
        "client_ids": "list[string] (accessible clients)",
        "created_at": "datetime",
        "updated_at": "datetime",
    },
    NodeLabel.AUDIT_LOG: {
        "id": "string (UUID)",
        "user_id": "string (UUID)",
        "client_id": "string (UUID)",
        "query_text": "string",
        "response_text": "string (truncated)",
        "confidence_score": "float",
        "response_time_ms": "integer",
        "timestamp": "datetime",
        "session_id": "string (optional)",
    },
}
