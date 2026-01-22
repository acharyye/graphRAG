"""Unit tests for data connectors."""

import pytest

from src.connectors.mock_data import MockDataGenerator


class TestMockDataGenerator:
    """Tests for MockDataGenerator."""

    def test_generate_clients(self):
        """Test client generation."""
        generator = MockDataGenerator(seed=42)
        clients = generator.generate_clients(count=3)

        assert len(clients) == 3
        for client in clients:
            assert "id" in client
            assert "name" in client
            assert "industry" in client
            assert "budget" in client
            assert "budget_currency" in client
            assert "status" in client
            assert client["status"] == "active"

    def test_generate_campaigns(self):
        """Test campaign generation."""
        generator = MockDataGenerator(seed=42)
        client_id = "test-client-123"

        campaigns = generator.generate_campaigns(client_id, count=4)

        assert len(campaigns) == 4
        for campaign in campaigns:
            assert campaign["client_id"] == client_id
            assert "name" in campaign
            assert "objective" in campaign
            assert "channel" in campaign
            assert campaign["channel"] in ["google_ads", "meta"]

    def test_generate_adsets(self):
        """Test ad set generation."""
        generator = MockDataGenerator(seed=42)
        campaign_id = "test-campaign-123"
        client_id = "test-client-123"

        adsets = generator.generate_adsets(campaign_id, client_id, count=3)

        assert len(adsets) == 3
        for adset in adsets:
            assert adset["campaign_id"] == campaign_id
            assert adset["client_id"] == client_id
            assert "name" in adset
            assert "targeting" in adset

    def test_generate_ads(self):
        """Test ad generation."""
        generator = MockDataGenerator(seed=42)
        adset_id = "test-adset-123"
        client_id = "test-client-123"

        ads = generator.generate_ads(adset_id, client_id, count=5)

        assert len(ads) == 5
        for ad in ads:
            assert ad["adset_id"] == adset_id
            assert ad["client_id"] == client_id
            assert "headline" in ad
            assert "creative_type" in ad

    def test_generate_metrics(self):
        """Test metrics generation."""
        generator = MockDataGenerator(seed=42)
        entity_id = "test-campaign-123"
        client_id = "test-client-123"

        metrics = generator.generate_metrics(
            entity_id, "campaign", client_id, days=30
        )

        assert len(metrics) == 30
        for metric in metrics:
            assert "date" in metric
            assert "impressions" in metric
            assert "clicks" in metric
            assert "conversions" in metric
            assert "spend" in metric
            assert metric["impressions"] >= 0
            assert metric["clicks"] >= 0
            assert metric["spend"] >= 0

    def test_generate_full_dataset(self):
        """Test full dataset generation."""
        generator = MockDataGenerator(seed=42)

        data = generator.generate_full_dataset(
            num_clients=2,
            campaigns_per_client=2,
            adsets_per_campaign=2,
            ads_per_adset=2,
            metric_days=7,
        )

        assert len(data["clients"]) == 2
        assert len(data["campaigns"]) == 4  # 2 clients * 2 campaigns
        assert len(data["adsets"]) == 8  # 4 campaigns * 2 adsets
        assert len(data["ads"]) == 16  # 8 adsets * 2 ads
        assert len(data["metrics"]) > 0

    def test_generate_users(self):
        """Test user generation."""
        generator = MockDataGenerator(seed=42)
        clients = generator.generate_clients(count=3)
        hashed_password = "test_hash"

        users = generator.generate_users(clients, hashed_password)

        assert len(users) >= 4  # Admin + managers + analyst + executive
        roles = [u["role"] for u in users]
        assert "admin" in roles
        assert "manager" in roles
        assert "analyst" in roles
        assert "executive" in roles

    def test_reproducibility_with_seed(self):
        """Test that same seed produces same data structure."""
        gen1 = MockDataGenerator(seed=42)
        gen2 = MockDataGenerator(seed=42)

        clients1 = gen1.generate_clients(count=3)
        clients2 = gen2.generate_clients(count=3)

        # With the same seed, should get same number of clients
        assert len(clients1) == len(clients2)
        # Both should have valid structure
        for c1, c2 in zip(clients1, clients2):
            assert "id" in c1 and "id" in c2
            assert "name" in c1 and "name" in c2
            assert "industry" in c1 and "industry" in c2
