"""Pytest configuration and fixtures."""

import os
import sys
from datetime import date, datetime
from typing import Generator
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config.settings import Settings


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings."""
    return Settings(
        NEO4J_URI="bolt://localhost:7687",
        NEO4J_USER="neo4j",
        NEO4J_PASSWORD="testpassword",
        ANTHROPIC_API_KEY="test-anthropic-key",
        VOYAGE_API_KEY="test-voyage-key",
        JWT_SECRET_KEY="test-jwt-secret",
        APP_ENV="development",
        DEBUG=True,
    )


@pytest.fixture
def mock_neo4j_client():
    """Create a mock Neo4j client."""
    client = MagicMock()
    client.verify_connectivity.return_value = True
    client.execute_query.return_value = []
    client.execute_write.return_value = {
        "nodes_created": 1,
        "nodes_deleted": 0,
        "relationships_created": 0,
        "relationships_deleted": 0,
        "properties_set": 5,
    }
    return client


@pytest.fixture
def sample_client_data() -> dict:
    """Create sample client data."""
    return {
        "id": str(uuid4()),
        "name": "Test Client",
        "industry": "E-commerce",
        "contract_start": "2024-01-01",
        "budget": 50000.0,
        "budget_currency": "USD",
        "status": "active",
        "data_retention_days": 365,
    }


@pytest.fixture
def sample_campaign_data(sample_client_data: dict) -> dict:
    """Create sample campaign data."""
    return {
        "id": str(uuid4()),
        "client_id": sample_client_data["id"],
        "external_id": "google_12345",
        "name": "Summer Sale Campaign",
        "objective": "conversions",
        "start_date": "2024-06-01",
        "end_date": "2024-08-31",
        "budget": 10000.0,
        "budget_currency": "USD",
        "daily_budget": 333.33,
        "status": "active",
        "channel": "google_ads",
    }


@pytest.fixture
def sample_metrics_data(sample_campaign_data: dict, sample_client_data: dict) -> list:
    """Create sample metrics data."""
    return [
        {
            "id": f"{sample_campaign_data['id']}_2024-07-01",
            "date": "2024-07-01",
            "impressions": 10000,
            "clicks": 300,
            "conversions": 15,
            "spend": 500.0,
            "spend_currency": "USD",
            "revenue": 1500.0,
            "revenue_currency": "USD",
        },
        {
            "id": f"{sample_campaign_data['id']}_2024-07-02",
            "date": "2024-07-02",
            "impressions": 12000,
            "clicks": 360,
            "conversions": 18,
            "spend": 550.0,
            "spend_currency": "USD",
            "revenue": 1800.0,
            "revenue_currency": "USD",
        },
    ]


@pytest.fixture
def sample_user_data(sample_client_data: dict) -> dict:
    """Create sample user data."""
    return {
        "id": str(uuid4()),
        "email": "test@agency.com",
        "hashed_password": "$2b$12$test_hash",
        "name": "Test User",
        "role": "manager",
        "client_ids": [sample_client_data["id"]],
    }


@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic client."""
    client = MagicMock()
    response = MagicMock()
    response.content = [MagicMock(text="This is a test response from Claude.")]
    client.messages.create.return_value = response
    return client


@pytest.fixture
def auth_headers(sample_user_data: dict, test_settings: Settings) -> dict:
    """Create authentication headers."""
    from src.api.dependencies import create_access_token
    from src.api.models import UserRole

    token = create_access_token(
        user_id=sample_user_data["id"],
        email=sample_user_data["email"],
        role=UserRole(sample_user_data["role"]),
        client_ids=sample_user_data["client_ids"],
        settings=test_settings,
    )

    return {"Authorization": f"Bearer {token}"}
