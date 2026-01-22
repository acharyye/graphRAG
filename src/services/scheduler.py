"""Daily sync scheduler for automated data synchronization."""

import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config.settings import Settings, get_settings
from src.connectors import GoogleAdsConnector, MetaAdsConnector
from src.graph.client import Neo4jClient, get_neo4j_client
from src.graph.ingest import DataIngester
from src.services.audit import AuditService
from src.services.notifications import NotificationService

logger = logging.getLogger(__name__)


class SyncScheduler:
    """Manages scheduled data synchronization tasks."""

    def __init__(
        self,
        neo4j_client: Neo4jClient | None = None,
        settings: Settings | None = None,
    ):
        """Initialize the scheduler.

        Args:
            neo4j_client: Neo4j client instance.
            settings: Application settings.
        """
        self._neo4j = neo4j_client or get_neo4j_client()
        self._settings = settings or get_settings()
        self._scheduler = AsyncIOScheduler()
        self._notification_service = NotificationService(settings)
        self._audit_service = AuditService(neo4j_client)
        self._google_connector = GoogleAdsConnector(settings)
        self._meta_connector = MetaAdsConnector(settings)

    def start(self):
        """Start the scheduler."""
        # Schedule daily sync job
        self._scheduler.add_job(
            self._daily_sync_job,
            CronTrigger(
                hour=self._settings.SYNC_SCHEDULE_HOUR,
                minute=0,
            ),
            id="daily_sync",
            name="Daily Data Sync",
            replace_existing=True,
        )

        # Schedule data retention cleanup (run at 3 AM)
        self._scheduler.add_job(
            self._cleanup_job,
            CronTrigger(hour=3, minute=0),
            id="data_cleanup",
            name="Data Retention Cleanup",
            replace_existing=True,
        )

        # Schedule audit log cleanup (run at 4 AM on Sundays)
        self._scheduler.add_job(
            self._audit_cleanup_job,
            CronTrigger(day_of_week="sun", hour=4, minute=0),
            id="audit_cleanup",
            name="Audit Log Cleanup",
            replace_existing=True,
        )

        self._scheduler.start()
        logger.info(
            f"Scheduler started. Daily sync scheduled for {self._settings.SYNC_SCHEDULE_HOUR}:00"
        )

    def stop(self):
        """Stop the scheduler."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=True)
            logger.info("Scheduler stopped")

    async def _daily_sync_job(self):
        """Daily sync job that syncs all configured clients."""
        logger.info("Starting daily sync job...")

        # Get all active clients with sync configuration
        clients = self._get_clients_for_sync()

        for client in clients:
            try:
                await self._sync_client(client)
            except Exception as e:
                logger.error(f"Sync failed for client {client['id']}: {e}")
                await self._notification_service.notify_sync_failed(
                    client_name=client.get("name", client["id"]),
                    platform="all",
                    error_message=str(e),
                )

        logger.info("Daily sync job completed")

    async def _sync_client(self, client: dict[str, Any]):
        """Sync data for a single client.

        Args:
            client: Client data dictionary.
        """
        client_id = client["id"]
        client_name = client.get("name", client_id)

        # Calculate date range (yesterday)
        end_date = date.today() - timedelta(days=1)
        start_date = end_date - timedelta(days=7)  # Last 7 days to catch any delays

        logger.info(f"Syncing data for client {client_name}: {start_date} to {end_date}")

        total_campaigns = 0
        total_metrics = 0

        # Sync Google Ads if configured
        if self._google_connector.is_configured and client.get("google_ads_account_id"):
            try:
                data = await self._google_connector.sync_all(
                    account_id=client["google_ads_account_id"],
                    client_id=client_id,
                    start_date=start_date,
                    end_date=end_date,
                )
                await self._ingest_sync_data(data, client_id)
                total_campaigns += len(data.get("campaigns", []))
                total_metrics += len(data.get("metrics", []))
                logger.info(f"Google Ads sync completed for {client_name}")
            except Exception as e:
                logger.error(f"Google Ads sync failed for {client_name}: {e}")

        # Sync Meta Ads if configured
        if self._meta_connector.is_configured and client.get("meta_ads_account_id"):
            try:
                data = await self._meta_connector.sync_all(
                    account_id=client["meta_ads_account_id"],
                    client_id=client_id,
                    start_date=start_date,
                    end_date=end_date,
                )
                await self._ingest_sync_data(data, client_id)
                total_campaigns += len(data.get("campaigns", []))
                total_metrics += len(data.get("metrics", []))
                logger.info(f"Meta Ads sync completed for {client_name}")
            except Exception as e:
                logger.error(f"Meta Ads sync failed for {client_name}: {e}")

        # Send notification if data was synced
        if total_campaigns > 0 or total_metrics > 0:
            await self._notification_service.notify_sync_completed(
                client_name=client_name,
                platform="Google Ads + Meta",
                campaigns_synced=total_campaigns,
                metrics_synced=total_metrics,
            )

        # Log sync action
        self._audit_service.log_action(
            user_id="system",
            action_type="sync",
            resource_type="client",
            resource_id=client_id,
            details={
                "campaigns_synced": total_campaigns,
                "metrics_synced": total_metrics,
                "date_range": f"{start_date} to {end_date}",
            },
            client_id=client_id,
        )

    async def _ingest_sync_data(self, data: dict[str, Any], client_id: str):
        """Ingest synced data into the graph.

        Args:
            data: Synced data dictionary.
            client_id: Client ID.
        """
        ingester = DataIngester(self._neo4j)

        for campaign in data.get("campaigns", []):
            ingester.ingest_campaign(campaign, client_id)

        for adset in data.get("adsets", []):
            ingester.ingest_adset(adset, adset["campaign_id"], client_id)

        for ad in data.get("ads", []):
            ingester.ingest_ad(ad, ad["adset_id"], client_id)

        # Group metrics by entity
        metrics_by_entity: dict[str, list] = {}
        for m in data.get("metrics", []):
            key = f"{m['entity_type']}_{m['entity_id']}"
            if key not in metrics_by_entity:
                metrics_by_entity[key] = []
            metrics_by_entity[key].append(m)

        for key, metrics in metrics_by_entity.items():
            entity_type, entity_id = key.split("_", 1)
            ingester.ingest_metrics(metrics, entity_type, entity_id, client_id)

    def _get_clients_for_sync(self) -> list[dict[str, Any]]:
        """Get all clients configured for automatic sync.

        Returns:
            List of client dictionaries.
        """
        query = """
        MATCH (c:Client)
        WHERE c.status = 'active'
        RETURN c
        """
        result = self._neo4j.execute_query(query)
        return [r["c"] for r in result]

    async def _cleanup_job(self):
        """Clean up old data based on client retention settings."""
        logger.info("Starting data retention cleanup...")

        clients = self._get_clients_for_sync()

        for client in clients:
            retention_days = client.get(
                "data_retention_days", self._settings.DEFAULT_DATA_RETENTION_DAYS
            )
            deleted = self._neo4j.cleanup_old_metrics(client["id"], retention_days)

            if deleted > 0:
                logger.info(
                    f"Cleaned up {deleted} metrics for client {client.get('name', client['id'])} "
                    f"(retention: {retention_days} days)"
                )

        logger.info("Data retention cleanup completed")

    async def _audit_cleanup_job(self):
        """Clean up old audit logs."""
        logger.info("Starting audit log cleanup...")

        # Keep audit logs for 1 year
        deleted = self._audit_service.cleanup_old_logs(retention_days=365)

        logger.info(f"Audit log cleanup completed: {deleted} records deleted")

    def trigger_sync_now(self, client_id: str | None = None):
        """Trigger an immediate sync.

        Args:
            client_id: Optional specific client to sync.
        """
        if client_id:
            # Get specific client
            result = self._neo4j.execute_query(
                "MATCH (c:Client {id: $id}) RETURN c",
                {"id": client_id},
            )
            if result:
                asyncio.create_task(self._sync_client(result[0]["c"]))
        else:
            # Trigger full sync
            asyncio.create_task(self._daily_sync_job())

    def get_next_run_time(self) -> datetime | None:
        """Get the next scheduled sync time.

        Returns:
            Next run datetime or None.
        """
        job = self._scheduler.get_job("daily_sync")
        if job:
            return job.next_run_time
        return None

    def get_job_status(self) -> dict[str, Any]:
        """Get status of all scheduled jobs.

        Returns:
            Dictionary with job status information.
        """
        jobs = []
        for job in self._scheduler.get_jobs():
            jobs.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                }
            )

        return {
            "running": self._scheduler.running,
            "jobs": jobs,
        }


# Singleton instance
_scheduler: SyncScheduler | None = None


def get_scheduler() -> SyncScheduler:
    """Get the scheduler singleton."""
    global _scheduler
    if _scheduler is None:
        _scheduler = SyncScheduler()
    return _scheduler
