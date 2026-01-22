"""Unit tests for API components."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

from src.api.models import (
    ClientCreate,
    ClientResponse,
    ConfidenceDetails,
    ConfidenceLevel,
    QueryRequest,
    QueryResponse,
    ReportConfig,
    ReportFormat,
    ReportType,
    Source,
    UserRole,
)


class TestQueryModels:
    """Tests for query API models."""

    def test_query_request_validation(self):
        """Test QueryRequest validation."""
        request = QueryRequest(
            query="What was ROAS last month?",
            client_id="client-123",
            session_id="session-456",
        )

        assert request.query == "What was ROAS last month?"
        assert request.client_id == "client-123"
        assert request.session_id == "session-456"

    def test_query_request_empty_query_fails(self):
        """Test that empty query fails validation."""
        with pytest.raises(ValueError):
            QueryRequest(query="", client_id="client-123")

    def test_source_model(self):
        """Test Source model."""
        source = Source(
            entity_type="campaign",
            entity_id="camp-123",
            entity_name="Summer Sale",
            date_range="2024-07-01 to 2024-07-31",
        )

        assert source.entity_type == "campaign"
        assert source.entity_name == "Summer Sale"

    def test_confidence_details(self):
        """Test ConfidenceDetails model."""
        confidence = ConfidenceDetails(
            overall=0.85,
            level=ConfidenceLevel.HIGH,
            factors={"data_quantity": 0.3, "data_recency": 0.2},
            explanation="Good data coverage",
        )

        assert confidence.overall == 0.85
        assert confidence.level == ConfidenceLevel.HIGH
        assert len(confidence.factors) == 2

    def test_query_response(self):
        """Test QueryResponse model."""
        response = QueryResponse(
            answer="The ROAS was 3.5x",
            confidence=ConfidenceDetails(
                overall=0.9,
                level=ConfidenceLevel.HIGH,
                factors={},
                explanation="Test",
            ),
            sources=[
                Source(
                    entity_type="campaign",
                    entity_id="camp-123",
                    entity_name="Test",
                    date_range=None,
                )
            ],
            query_id="query-123",
            timestamp=datetime.utcnow(),
            drill_down_available=True,
            recommendations=["Increase budget"],
        )

        assert response.drill_down_available is True
        assert len(response.recommendations) == 1


class TestClientModels:
    """Tests for client API models."""

    def test_client_create(self):
        """Test ClientCreate model."""
        client = ClientCreate(
            name="Test Client",
            industry="E-commerce",
            budget=50000,
            budget_currency="USD",
            data_retention_days=365,
        )

        assert client.name == "Test Client"
        assert client.budget == 50000

    def test_client_create_defaults(self):
        """Test ClientCreate defaults."""
        client = ClientCreate(name="Test")

        assert client.industry == "Unknown"
        assert client.budget == 0
        assert client.budget_currency == "USD"
        assert client.data_retention_days == 365

    def test_client_response(self):
        """Test ClientResponse model."""
        from datetime import date

        response = ClientResponse(
            id="client-123",
            name="Test Client",
            industry="E-commerce",
            budget=50000,
            budget_currency="USD",
            data_retention_days=365,
            contract_start=date(2024, 1, 1),
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        assert response.id == "client-123"
        assert response.status == "active"


class TestReportModels:
    """Tests for report API models."""

    def test_report_config(self):
        """Test ReportConfig model."""
        from src.api.models import DateRange, ReportSection

        config = ReportConfig(
            client_id="client-123",
            report_type=ReportType.MONTHLY,
            format=ReportFormat.PDF,
            date_range=DateRange(start="2024-07-01", end="2024-07-31"),
            sections=[ReportSection.SUMMARY, ReportSection.CAMPAIGNS],
        )

        assert config.client_id == "client-123"
        assert config.format == ReportFormat.PDF
        assert len(config.sections) == 2

    def test_report_format_enum(self):
        """Test ReportFormat enum values."""
        assert ReportFormat.PDF.value == "pdf"
        assert ReportFormat.EXCEL.value == "excel"
        assert ReportFormat.CSV.value == "csv"

    def test_report_type_enum(self):
        """Test ReportType enum values."""
        assert ReportType.DAILY.value == "daily"
        assert ReportType.WEEKLY.value == "weekly"
        assert ReportType.MONTHLY.value == "monthly"


class TestAuthModels:
    """Tests for authentication models."""

    def test_user_role_enum(self):
        """Test UserRole enum values."""
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.ANALYST.value == "analyst"
        assert UserRole.MANAGER.value == "manager"
        assert UserRole.EXECUTIVE.value == "executive"


class TestDependencies:
    """Tests for API dependencies."""

    @pytest.mark.skip(reason="passlib/bcrypt version compatibility issue in test env")
    def test_password_hashing(self):
        """Test password hashing functions."""
        from src.api.dependencies import hash_password, verify_password

        password = "testpass123"  # Use shorter password to avoid bcrypt 72-byte limit
        hashed = hash_password(password)

        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("wrongpass", hashed) is False

    def test_create_access_token(self, test_settings):
        """Test JWT token creation."""
        from src.api.dependencies import create_access_token, decode_token

        token = create_access_token(
            user_id="user-123",
            email="test@test.com",
            role=UserRole.MANAGER,
            client_ids=["client-1", "client-2"],
            settings=test_settings,
        )

        assert token is not None
        assert len(token) > 0

        # Decode and verify
        payload = decode_token(token, test_settings)
        assert payload.sub == "user-123"
        assert payload.email == "test@test.com"
        assert payload.role == UserRole.MANAGER
        assert len(payload.client_ids) == 2

    def test_decode_invalid_token(self, test_settings):
        """Test decoding invalid token raises exception."""
        from fastapi import HTTPException
        from src.api.dependencies import decode_token

        with pytest.raises(HTTPException) as exc_info:
            decode_token("invalid-token", test_settings)

        assert exc_info.value.status_code == 401
