"""Pydantic models for client management."""

from datetime import date, datetime

from pydantic import BaseModel, Field


class ClientBase(BaseModel):
    """Base client model."""

    name: str = Field(..., min_length=1, max_length=255)
    industry: str = Field(default="Unknown")
    budget: float = Field(ge=0, default=0)
    budget_currency: str = Field(default="USD", max_length=3)
    data_retention_days: int = Field(ge=30, le=3650, default=365)


class ClientCreate(ClientBase):
    """Client creation model."""

    contract_start: date = Field(default_factory=date.today)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "Acme Corp",
                    "industry": "E-commerce",
                    "budget": 50000,
                    "budget_currency": "USD",
                    "data_retention_days": 365,
                    "contract_start": "2024-01-01",
                }
            ]
        }
    }


class ClientUpdate(BaseModel):
    """Client update model."""

    name: str | None = Field(None, min_length=1, max_length=255)
    industry: str | None = None
    budget: float | None = Field(None, ge=0)
    budget_currency: str | None = Field(None, max_length=3)
    data_retention_days: int | None = Field(None, ge=30, le=3650)
    status: str | None = Field(None, pattern="^(active|inactive)$")


class ClientResponse(ClientBase):
    """Client response model."""

    id: str
    contract_start: date
    status: str = "active"
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": "client_123",
                    "name": "Acme Corp",
                    "industry": "E-commerce",
                    "budget": 50000,
                    "budget_currency": "USD",
                    "data_retention_days": 365,
                    "contract_start": "2024-01-01",
                    "status": "active",
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                }
            ]
        }
    }


class ClientListResponse(BaseModel):
    """Response model for client list."""

    clients: list[ClientResponse]
    total: int


class ClientSummary(BaseModel):
    """Summary statistics for a client."""

    client_id: str
    client_name: str
    active_campaigns: int
    total_spend: float
    spend_currency: str
    total_impressions: int
    total_clicks: int
    total_conversions: int
    avg_ctr: float
    avg_cpc: float
    roas: float | None
    date_range: tuple[str, str]
