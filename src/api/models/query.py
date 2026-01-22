"""Pydantic models for query API."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ConfidenceLevel(str, Enum):
    """Confidence level for answers."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INSUFFICIENT = "insufficient"


class Source(BaseModel):
    """Source reference for an answer."""

    entity_type: str = Field(..., description="Type of entity (campaign, adset, ad, metric)")
    entity_id: str = Field(..., description="Entity identifier")
    entity_name: str | None = Field(None, description="Human-readable entity name")
    date_range: str | None = Field(None, description="Date range for the data")


class QueryRequest(BaseModel):
    """Request model for natural language queries."""

    query: str = Field(..., min_length=1, max_length=1000, description="Natural language query")
    client_id: str = Field(..., description="Client ID for data isolation")
    session_id: str | None = Field(None, description="Session ID for conversation memory")
    date_range: tuple[str, str] | None = Field(
        None, description="Date range override (start, end) in YYYY-MM-DD format"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "What was the ROAS for Summer Sale campaign last month?",
                    "client_id": "client_123",
                    "session_id": "session_abc",
                }
            ]
        }
    }


class ConfidenceDetails(BaseModel):
    """Detailed confidence breakdown."""

    overall: float = Field(..., ge=0, le=1, description="Overall confidence score")
    level: ConfidenceLevel = Field(..., description="Confidence level category")
    factors: dict[str, float] = Field(..., description="Individual confidence factors")
    explanation: str = Field(..., description="Human-readable explanation")


class QueryResponse(BaseModel):
    """Response model for natural language queries."""

    answer: str = Field(..., description="Generated answer text")
    confidence: ConfidenceDetails = Field(..., description="Confidence information")
    sources: list[Source] = Field(default_factory=list, description="Source references")
    query_id: str = Field(..., description="Unique query identifier")
    timestamp: datetime = Field(..., description="Response timestamp")
    drill_down_available: bool = Field(
        False, description="Whether drill-down is available for this query"
    )
    recommendations: list[str] | None = Field(
        None, description="Proactive AI recommendations"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "answer": "The Summer Sale campaign achieved a ROAS of 3.2x...",
                    "confidence": {
                        "overall": 0.85,
                        "level": "high",
                        "factors": {"data_quantity": 0.3, "data_recency": 0.2},
                        "explanation": "High confidence based on comprehensive data.",
                    },
                    "sources": [
                        {
                            "entity_type": "campaign",
                            "entity_id": "camp_123",
                            "entity_name": "Summer Sale",
                            "date_range": "2024-12-01 to 2024-12-31",
                        }
                    ],
                    "query_id": "query_abc123",
                    "timestamp": "2024-01-15T10:30:00Z",
                    "drill_down_available": True,
                    "recommendations": ["Consider increasing budget allocation..."],
                }
            ]
        }
    }


class DrillDownRequest(BaseModel):
    """Request model for drill-down queries."""

    entity_type: str = Field(..., description="Entity type to drill into")
    entity_id: str = Field(..., description="Entity ID to drill into")
    client_id: str = Field(..., description="Client ID for data isolation")
    date_range: tuple[str, str] | None = Field(None, description="Date range")


class DrillDownResponse(BaseModel):
    """Response model for drill-down queries."""

    entity: dict = Field(..., description="Entity details")
    children: list[dict] = Field(default_factory=list, description="Child entities")
    metrics: dict = Field(default_factory=dict, description="Aggregated metrics")
    breakdown: list[dict] = Field(
        default_factory=list, description="Detailed breakdown"
    )
