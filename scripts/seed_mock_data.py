#!/usr/bin/env python3
"""Seed Neo4j database with mock data for testing."""

import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import hashlib

from src.connectors.mock_data import MockDataGenerator
from src.graph.client import get_neo4j_client
from src.graph.ingest import DataIngester

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def simple_hash(password: str) -> str:
    """Simple hash for test data (not for production)."""
    return hashlib.sha256(password.encode()).hexdigest()


def main():
    """Seed the database with mock data."""
    logger.info("Starting mock data seeding...")

    # Initialize components
    neo4j_client = get_neo4j_client()
    ingester = DataIngester(neo4j_client)
    generator = MockDataGenerator(seed=42)  # Fixed seed for reproducibility

    # Verify connectivity
    if not neo4j_client.verify_connectivity():
        logger.error("Cannot connect to Neo4j. Is it running?")
        sys.exit(1)

    # Initialize schema
    logger.info("Initializing schema...")
    neo4j_client.initialize_schema()

    # Generate mock data
    logger.info("Generating mock data...")
    data = generator.generate_full_dataset(
        num_clients=5,
        campaigns_per_client=4,
        adsets_per_campaign=3,
        ads_per_adset=5,
        metric_days=90,
    )

    # Ingest clients
    logger.info(f"Ingesting {len(data['clients'])} clients...")
    for client in data["clients"]:
        ingester.ingest_client(client)

    # Ingest campaigns
    logger.info(f"Ingesting {len(data['campaigns'])} campaigns...")
    for campaign in data["campaigns"]:
        ingester.ingest_campaign(campaign, campaign["client_id"])

    # Ingest ad sets
    logger.info(f"Ingesting {len(data['adsets'])} ad sets...")
    for adset in data["adsets"]:
        ingester.ingest_adset(adset, adset["campaign_id"], adset["client_id"])

    # Ingest ads
    logger.info(f"Ingesting {len(data['ads'])} ads...")
    for ad in data["ads"]:
        ingester.ingest_ad(ad, ad["adset_id"], ad["client_id"])

    # Ingest metrics (batched by entity)
    logger.info(f"Ingesting {len(data['metrics'])} metric records...")
    metrics_by_entity = {}
    for metric in data["metrics"]:
        key = metric["id"].rsplit("_", 1)[0]  # Entity ID
        if key not in metrics_by_entity:
            metrics_by_entity[key] = []
        metrics_by_entity[key].append(metric)

    # Find entity info for each metric batch
    entity_info = {}
    for campaign in data["campaigns"]:
        entity_info[campaign["id"]] = ("campaign", campaign["client_id"])
    for adset in data["adsets"]:
        entity_info[adset["id"]] = ("adset", adset["client_id"])
    for ad in data["ads"]:
        entity_info[ad["id"]] = ("ad", ad["client_id"])

    for entity_id, metrics in metrics_by_entity.items():
        if entity_id in entity_info:
            entity_type, client_id = entity_info[entity_id]
            ingester.ingest_metrics(metrics, entity_type, entity_id, client_id)

    # Generate and ingest users
    logger.info("Generating and ingesting users...")
    hashed_password = simple_hash("password123")  # Default test password
    users = generator.generate_users(data["clients"], hashed_password)
    for user in users:
        ingester.ingest_user(user)

    logger.info("=" * 50)
    logger.info("Mock data seeding complete!")
    logger.info(f"  Clients: {len(data['clients'])}")
    logger.info(f"  Campaigns: {len(data['campaigns'])}")
    logger.info(f"  Ad Sets: {len(data['adsets'])}")
    logger.info(f"  Ads: {len(data['ads'])}")
    logger.info(f"  Metrics: {len(data['metrics'])}")
    logger.info(f"  Users: {len(users)}")
    logger.info("=" * 50)
    logger.info("\nTest credentials:")
    logger.info("  admin@agency.com / password123 (all clients)")
    logger.info("  analyst@agency.com / password123 (first 3 clients)")
    logger.info("  manager1@agency.com / password123 (client 1)")

    # Close connection
    neo4j_client.close()


if __name__ == "__main__":
    main()
