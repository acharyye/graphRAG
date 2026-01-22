#!/usr/bin/env python3
"""Manual data sync script."""

import argparse
import asyncio
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.connectors import GoogleAdsConnector, MetaAdsConnector
from src.graph.client import get_neo4j_client
from src.graph.ingest import DataIngester
from src.services.scheduler import get_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def sync_google_ads(client_id: str, account_id: str, start_date: date, end_date: date):
    """Sync Google Ads data."""
    connector = GoogleAdsConnector()

    if not connector.is_configured:
        logger.error("Google Ads is not configured")
        return

    logger.info(f"Syncing Google Ads for client {client_id}...")

    try:
        data = await connector.sync_all(account_id, client_id, start_date, end_date)

        # Ingest data
        neo4j = get_neo4j_client()
        ingester = DataIngester(neo4j)

        for campaign in data.get("campaigns", []):
            ingester.ingest_campaign(campaign, client_id)

        for adset in data.get("adsets", []):
            ingester.ingest_adset(adset, adset["campaign_id"], client_id)

        for ad in data.get("ads", []):
            ingester.ingest_ad(ad, ad["adset_id"], client_id)

        # Group and ingest metrics
        metrics_by_entity = {}
        for m in data.get("metrics", []):
            key = f"{m['entity_type']}_{m['entity_id']}"
            if key not in metrics_by_entity:
                metrics_by_entity[key] = []
            metrics_by_entity[key].append(m)

        for key, metrics in metrics_by_entity.items():
            entity_type, entity_id = key.split("_", 1)
            ingester.ingest_metrics(metrics, entity_type, entity_id, client_id)

        logger.info(
            f"Google Ads sync completed: {len(data.get('campaigns', []))} campaigns, "
            f"{len(data.get('metrics', []))} metrics"
        )

    except Exception as e:
        logger.error(f"Google Ads sync failed: {e}")
        raise


async def sync_meta_ads(client_id: str, account_id: str, start_date: date, end_date: date):
    """Sync Meta Ads data."""
    connector = MetaAdsConnector()

    if not connector.is_configured:
        logger.error("Meta Ads is not configured")
        return

    logger.info(f"Syncing Meta Ads for client {client_id}...")

    try:
        data = await connector.sync_all(account_id, client_id, start_date, end_date)

        # Ingest data
        neo4j = get_neo4j_client()
        ingester = DataIngester(neo4j)

        for campaign in data.get("campaigns", []):
            ingester.ingest_campaign(campaign, client_id)

        for adset in data.get("adsets", []):
            ingester.ingest_adset(adset, adset["campaign_id"], client_id)

        for ad in data.get("ads", []):
            ingester.ingest_ad(ad, ad["adset_id"], client_id)

        # Group and ingest metrics
        metrics_by_entity = {}
        for m in data.get("metrics", []):
            key = f"{m['entity_type']}_{m['entity_id']}"
            if key not in metrics_by_entity:
                metrics_by_entity[key] = []
            metrics_by_entity[key].append(m)

        for key, metrics in metrics_by_entity.items():
            entity_type, entity_id = key.split("_", 1)
            ingester.ingest_metrics(metrics, entity_type, entity_id, client_id)

        logger.info(
            f"Meta Ads sync completed: {len(data.get('campaigns', []))} campaigns, "
            f"{len(data.get('metrics', []))} metrics"
        )

    except Exception as e:
        logger.error(f"Meta Ads sync failed: {e}")
        raise


async def trigger_scheduled_sync(client_id: str | None = None):
    """Trigger the scheduled sync job."""
    scheduler = get_scheduler()
    scheduler.trigger_sync_now(client_id)
    logger.info("Sync triggered")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Manual data sync")
    parser.add_argument("--client-id", required=True, help="Client ID to sync")
    parser.add_argument("--platform", choices=["google", "meta", "all"], default="all")
    parser.add_argument("--account-id", help="Platform account ID")
    parser.add_argument(
        "--start-date",
        type=lambda s: date.fromisoformat(s),
        default=date.today() - timedelta(days=30),
        help="Start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date",
        type=lambda s: date.fromisoformat(s),
        default=date.today() - timedelta(days=1),
        help="End date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--use-scheduler",
        action="store_true",
        help="Use the scheduler to trigger sync",
    )

    args = parser.parse_args()

    if args.use_scheduler:
        asyncio.run(trigger_scheduled_sync(args.client_id))
    else:
        if not args.account_id:
            logger.error("--account-id is required when not using scheduler")
            sys.exit(1)

        if args.platform in ["google", "all"]:
            asyncio.run(
                sync_google_ads(
                    args.client_id, args.account_id, args.start_date, args.end_date
                )
            )

        if args.platform in ["meta", "all"]:
            asyncio.run(
                sync_meta_ads(
                    args.client_id, args.account_id, args.start_date, args.end_date
                )
            )


if __name__ == "__main__":
    main()
