"""Unit tests for graph components."""

import pytest
from unittest.mock import MagicMock, patch

from src.graph.schema import (
    CampaignObjective,
    CampaignStatus,
    GraphSchema,
    NodeLabel,
    RelationType,
)


class TestGraphSchema:
    """Tests for GraphSchema."""

    def test_constraints_defined(self):
        """Test that constraints are defined."""
        schema = GraphSchema()

        assert len(schema.CONSTRAINTS) > 0
        for constraint in schema.CONSTRAINTS:
            assert "CREATE CONSTRAINT" in constraint
            assert "IF NOT EXISTS" in constraint

    def test_indexes_defined(self):
        """Test that indexes are defined."""
        schema = GraphSchema()

        assert len(schema.INDEXES) > 0
        for index in schema.INDEXES:
            assert "CREATE INDEX" in index
            assert "IF NOT EXISTS" in index

    def test_get_all_statements(self):
        """Test getting all schema statements."""
        schema = GraphSchema()
        statements = schema.get_all_statements()

        assert len(statements) == len(schema.CONSTRAINTS) + len(schema.INDEXES)

    def test_client_constraint_exists(self):
        """Test that client uniqueness constraint exists."""
        schema = GraphSchema()
        client_constraints = [c for c in schema.CONSTRAINTS if "Client" in c]

        assert len(client_constraints) > 0
        assert any("id" in c for c in client_constraints)

    def test_metric_indexes_for_query_speed(self):
        """Test that metric indexes exist for query performance."""
        schema = GraphSchema()
        metric_indexes = [i for i in schema.INDEXES if "Metric" in i]

        # Should have indexes on client_id and date for isolation and filtering
        assert len(metric_indexes) >= 2


class TestNodeLabel:
    """Tests for NodeLabel enum."""

    def test_all_labels_defined(self):
        """Test that all expected labels are defined."""
        # Map expected values to their enum names
        expected_mapping = {
            "Client": "CLIENT",
            "Campaign": "CAMPAIGN",
            "AdSet": "AD_SET",
            "Ad": "AD",
            "Channel": "CHANNEL",
            "Metric": "METRIC",
            "User": "USER",
            "AuditLog": "AUDIT_LOG",
        }

        for value, enum_name in expected_mapping.items():
            assert hasattr(NodeLabel, enum_name), f"Missing NodeLabel.{enum_name}"

    def test_label_values(self):
        """Test label string values."""
        assert NodeLabel.CLIENT.value == "Client"
        assert NodeLabel.CAMPAIGN.value == "Campaign"
        assert NodeLabel.METRIC.value == "Metric"


class TestRelationType:
    """Tests for RelationType enum."""

    def test_all_relations_defined(self):
        """Test that all expected relations are defined."""
        expected = ["OWNS", "CONTAINS", "RUNS_ON", "HAS_METRIC", "WORKS_FOR", "QUERIED"]

        for rel in expected:
            assert hasattr(RelationType, rel)


class TestCampaignStatus:
    """Tests for CampaignStatus enum."""

    def test_status_values(self):
        """Test campaign status values."""
        assert CampaignStatus.ACTIVE.value == "active"
        assert CampaignStatus.PAUSED.value == "paused"
        assert CampaignStatus.COMPLETED.value == "completed"
        assert CampaignStatus.DRAFT.value == "draft"


class TestCampaignObjective:
    """Tests for CampaignObjective enum."""

    def test_objective_values(self):
        """Test campaign objective values."""
        objectives = [o.value for o in CampaignObjective]

        assert "awareness" in objectives
        assert "traffic" in objectives
        assert "conversions" in objectives
        assert "leads" in objectives


class TestDataIngester:
    """Tests for DataIngester."""

    @pytest.fixture
    def ingester(self, mock_neo4j_client):
        """Create ingester with mock client."""
        from src.graph.ingest import DataIngester

        mock_neo4j_client.execute_query.return_value = [{"id": "test-id"}]
        return DataIngester(mock_neo4j_client)

    def test_ingest_client(self, ingester, sample_client_data):
        """Test client ingestion."""
        result = ingester.ingest_client(sample_client_data)

        assert result == "test-id"
        ingester._client.execute_query.assert_called_once()

    def test_ingest_campaign(self, ingester, sample_campaign_data, sample_client_data):
        """Test campaign ingestion."""
        result = ingester.ingest_campaign(sample_campaign_data, sample_client_data["id"])

        assert result == "test-id"
        ingester._client.execute_query.assert_called()

    def test_ingest_metrics(self, ingester, sample_metrics_data, sample_campaign_data, sample_client_data):
        """Test metrics ingestion."""
        result = ingester.ingest_metrics(
            sample_metrics_data,
            "campaign",
            sample_campaign_data["id"],
            sample_client_data["id"],
        )

        assert result == len(sample_metrics_data)
