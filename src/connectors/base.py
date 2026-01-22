"""Base connector with retry logic and error handling."""

import logging
from abc import ABC, abstractmethod
from datetime import date
from typing import Any

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class ConnectorError(Exception):
    """Base exception for connector errors."""

    pass


class RateLimitError(ConnectorError):
    """Rate limit exceeded error."""

    pass


class AuthenticationError(ConnectorError):
    """Authentication failed error."""

    pass


class TemporaryError(ConnectorError):
    """Temporary error that can be retried."""

    pass


def create_retry_decorator(settings: Settings):
    """Create a retry decorator with settings-based configuration.

    Args:
        settings: Application settings.

    Returns:
        Configured retry decorator.
    """
    return retry(
        stop=stop_after_attempt(settings.RETRY_MAX_ATTEMPTS),
        wait=wait_exponential(
            multiplier=settings.RETRY_BASE_DELAY_SECONDS,
            min=1,
            max=60,
        ),
        retry=retry_if_exception_type((RateLimitError, TemporaryError)),
        before_sleep=lambda retry_state: logger.warning(
            f"Retry attempt {retry_state.attempt_number} after error: "
            f"{retry_state.outcome.exception()}"
        ),
    )


class BaseConnector(ABC):
    """Abstract base class for marketing platform connectors."""

    def __init__(self, settings: Settings | None = None):
        """Initialize the connector.

        Args:
            settings: Application settings. Uses default if not provided.
        """
        self._settings = settings or get_settings()
        self._retry = create_retry_decorator(self._settings)
        self._is_authenticated = False

    @property
    def is_configured(self) -> bool:
        """Check if the connector has required configuration."""
        return False

    @property
    def is_authenticated(self) -> bool:
        """Check if the connector is authenticated."""
        return self._is_authenticated

    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the platform.

        Returns:
            True if authentication successful.

        Raises:
            AuthenticationError: If authentication fails.
        """
        pass

    @abstractmethod
    async def fetch_campaigns(
        self,
        account_id: str,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """Fetch campaign data from the platform.

        Args:
            account_id: Platform account/customer ID.
            start_date: Start date for data fetch.
            end_date: End date for data fetch.

        Returns:
            List of campaign dictionaries.
        """
        pass

    @abstractmethod
    async def fetch_adsets(
        self,
        account_id: str,
        campaign_ids: list[str],
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """Fetch ad set data from the platform.

        Args:
            account_id: Platform account/customer ID.
            campaign_ids: List of campaign IDs to fetch ad sets for.
            start_date: Start date for data fetch.
            end_date: End date for data fetch.

        Returns:
            List of ad set dictionaries.
        """
        pass

    @abstractmethod
    async def fetch_ads(
        self,
        account_id: str,
        adset_ids: list[str],
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """Fetch ad data from the platform.

        Args:
            account_id: Platform account/customer ID.
            adset_ids: List of ad set IDs to fetch ads for.
            start_date: Start date for data fetch.
            end_date: End date for data fetch.

        Returns:
            List of ad dictionaries.
        """
        pass

    @abstractmethod
    async def fetch_metrics(
        self,
        account_id: str,
        entity_type: str,
        entity_ids: list[str],
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """Fetch performance metrics from the platform.

        Args:
            account_id: Platform account/customer ID.
            entity_type: Type of entity (campaign/adset/ad).
            entity_ids: List of entity IDs to fetch metrics for.
            start_date: Start date for metrics.
            end_date: End date for metrics.

        Returns:
            List of metric dictionaries with daily data.
        """
        pass

    def transform_to_graph_format(
        self,
        data: dict[str, Any],
        entity_type: str,
        client_id: str,
    ) -> dict[str, Any]:
        """Transform platform data to graph schema format.

        Args:
            data: Raw platform data.
            entity_type: Type of entity being transformed.
            client_id: Client ID to associate with the data.

        Returns:
            Transformed data matching graph schema.
        """
        # Default implementation - subclasses should override
        return {
            **data,
            "client_id": client_id,
        }

    async def sync_all(
        self,
        account_id: str,
        client_id: str,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        """Sync all data for an account.

        Args:
            account_id: Platform account ID.
            client_id: Internal client ID.
            start_date: Start date for sync.
            end_date: End date for sync.

        Returns:
            Dictionary with all synced data.
        """
        if not self.is_authenticated:
            await self.authenticate()

        logger.info(f"Starting sync for account {account_id}")

        # Fetch campaigns
        campaigns = await self.fetch_campaigns(account_id, start_date, end_date)
        campaign_ids = [c["id"] for c in campaigns]
        logger.info(f"Fetched {len(campaigns)} campaigns")

        # Fetch ad sets
        adsets = []
        if campaign_ids:
            adsets = await self.fetch_adsets(
                account_id, campaign_ids, start_date, end_date
            )
        adset_ids = [a["id"] for a in adsets]
        logger.info(f"Fetched {len(adsets)} ad sets")

        # Fetch ads
        ads = []
        if adset_ids:
            ads = await self.fetch_ads(account_id, adset_ids, start_date, end_date)
        logger.info(f"Fetched {len(ads)} ads")

        # Fetch metrics for all entities
        campaign_metrics = await self.fetch_metrics(
            account_id, "campaign", campaign_ids, start_date, end_date
        )
        adset_metrics = await self.fetch_metrics(
            account_id, "adset", adset_ids, start_date, end_date
        )
        ad_metrics = await self.fetch_metrics(
            account_id, "ad", [a["id"] for a in ads], start_date, end_date
        )
        logger.info(
            f"Fetched metrics: {len(campaign_metrics)} campaign, "
            f"{len(adset_metrics)} adset, {len(ad_metrics)} ad"
        )

        # Transform all data
        return {
            "campaigns": [
                self.transform_to_graph_format(c, "campaign", client_id)
                for c in campaigns
            ],
            "adsets": [
                self.transform_to_graph_format(a, "adset", client_id) for a in adsets
            ],
            "ads": [self.transform_to_graph_format(a, "ad", client_id) for a in ads],
            "metrics": campaign_metrics + adset_metrics + ad_metrics,
        }
