"""Google Ads API connector."""

import logging
from datetime import date
from typing import Any

from config.settings import Settings, get_settings

from .base import (
    AuthenticationError,
    BaseConnector,
    RateLimitError,
    TemporaryError,
)

logger = logging.getLogger(__name__)


class GoogleAdsConnector(BaseConnector):
    """Connector for Google Ads API."""

    def __init__(self, settings: Settings | None = None):
        """Initialize Google Ads connector.

        Args:
            settings: Application settings.
        """
        super().__init__(settings)
        self._client = None

    @property
    def is_configured(self) -> bool:
        """Check if Google Ads API is configured."""
        return self._settings.google_ads_configured

    async def authenticate(self) -> bool:
        """Authenticate with Google Ads API.

        Returns:
            True if authentication successful.

        Raises:
            AuthenticationError: If authentication fails.
        """
        if not self.is_configured:
            raise AuthenticationError("Google Ads API is not configured")

        try:
            # Import here to avoid dependency issues if not configured
            from google.ads.googleads.client import GoogleAdsClient

            # Build credentials dict
            credentials = {
                "developer_token": self._settings.GOOGLE_ADS_DEVELOPER_TOKEN,
                "client_id": self._settings.GOOGLE_ADS_CLIENT_ID,
                "client_secret": self._settings.GOOGLE_ADS_CLIENT_SECRET,
                "refresh_token": self._settings.GOOGLE_ADS_REFRESH_TOKEN,
                "use_proto_plus": True,
            }

            if self._settings.GOOGLE_ADS_LOGIN_CUSTOMER_ID:
                credentials["login_customer_id"] = (
                    self._settings.GOOGLE_ADS_LOGIN_CUSTOMER_ID
                )

            self._client = GoogleAdsClient.load_from_dict(credentials)
            self._is_authenticated = True
            logger.info("Google Ads authentication successful")
            return True

        except Exception as e:
            logger.error(f"Google Ads authentication failed: {e}")
            raise AuthenticationError(f"Google Ads authentication failed: {e}")

    async def fetch_campaigns(
        self,
        account_id: str,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """Fetch campaigns from Google Ads.

        Args:
            account_id: Google Ads customer ID.
            start_date: Start date for data.
            end_date: End date for data.

        Returns:
            List of campaign dictionaries.
        """
        if not self._client:
            raise AuthenticationError("Not authenticated")

        ga_service = self._client.get_service("GoogleAdsService")

        query = """
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type,
                campaign.start_date,
                campaign.end_date,
                campaign_budget.amount_micros
            FROM campaign
            WHERE campaign.status != 'REMOVED'
        """

        campaigns = []

        try:
            response = ga_service.search(customer_id=account_id, query=query)

            for row in response:
                campaign = row.campaign
                budget = row.campaign_budget

                # Map status
                status_map = {
                    2: "active",  # ENABLED
                    3: "paused",  # PAUSED
                }

                # Map objective from channel type
                objective_map = {
                    2: "traffic",  # SEARCH
                    3: "awareness",  # DISPLAY
                    6: "conversions",  # SHOPPING
                    7: "traffic",  # VIDEO
                }

                campaigns.append(
                    {
                        "id": str(campaign.id),
                        "external_id": str(campaign.id),
                        "name": campaign.name,
                        "status": status_map.get(campaign.status, "paused"),
                        "objective": objective_map.get(
                            campaign.advertising_channel_type, "conversions"
                        ),
                        "start_date": campaign.start_date,
                        "end_date": campaign.end_date if campaign.end_date else None,
                        "budget": budget.amount_micros / 1_000_000
                        if budget.amount_micros
                        else 0,
                        "budget_currency": "USD",  # Default, would need account info
                        "channel": "google_ads",
                    }
                )

            logger.info(f"Fetched {len(campaigns)} campaigns from Google Ads")
            return campaigns

        except Exception as e:
            error_str = str(e).lower()
            if "rate" in error_str or "quota" in error_str:
                raise RateLimitError(f"Google Ads rate limit: {e}")
            elif "unauthorized" in error_str or "permission" in error_str:
                raise AuthenticationError(f"Google Ads auth error: {e}")
            elif "unavailable" in error_str or "timeout" in error_str:
                raise TemporaryError(f"Google Ads temporary error: {e}")
            raise

    async def fetch_adsets(
        self,
        account_id: str,
        campaign_ids: list[str],
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """Fetch ad groups from Google Ads.

        Args:
            account_id: Google Ads customer ID.
            campaign_ids: Campaign IDs to fetch ad groups for.
            start_date: Start date.
            end_date: End date.

        Returns:
            List of ad group dictionaries (mapped to adset schema).
        """
        if not self._client:
            raise AuthenticationError("Not authenticated")

        ga_service = self._client.get_service("GoogleAdsService")

        campaign_filter = ", ".join(f"'{cid}'" for cid in campaign_ids)
        query = f"""
            SELECT
                ad_group.id,
                ad_group.name,
                ad_group.status,
                ad_group.campaign,
                ad_group.cpc_bid_micros
            FROM ad_group
            WHERE ad_group.status != 'REMOVED'
                AND ad_group.campaign IN ({campaign_filter})
        """

        adsets = []

        try:
            response = ga_service.search(customer_id=account_id, query=query)

            for row in response:
                ad_group = row.ad_group

                status_map = {2: "active", 3: "paused"}

                # Extract campaign ID from resource name
                campaign_id = ad_group.campaign.split("/")[-1]

                adsets.append(
                    {
                        "id": str(ad_group.id),
                        "external_id": str(ad_group.id),
                        "campaign_id": campaign_id,
                        "name": ad_group.name,
                        "status": status_map.get(ad_group.status, "paused"),
                        "budget": ad_group.cpc_bid_micros / 1_000_000
                        if ad_group.cpc_bid_micros
                        else 0,
                        "budget_currency": "USD",
                        "targeting": "{}",
                    }
                )

            logger.info(f"Fetched {len(adsets)} ad groups from Google Ads")
            return adsets

        except Exception as e:
            error_str = str(e).lower()
            if "rate" in error_str or "quota" in error_str:
                raise RateLimitError(f"Google Ads rate limit: {e}")
            raise TemporaryError(f"Google Ads error: {e}")

    async def fetch_ads(
        self,
        account_id: str,
        adset_ids: list[str],
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """Fetch ads from Google Ads.

        Args:
            account_id: Google Ads customer ID.
            adset_ids: Ad group IDs to fetch ads for.
            start_date: Start date.
            end_date: End date.

        Returns:
            List of ad dictionaries.
        """
        if not self._client:
            raise AuthenticationError("Not authenticated")

        ga_service = self._client.get_service("GoogleAdsService")

        adgroup_filter = ", ".join(f"'{aid}'" for aid in adset_ids)
        query = f"""
            SELECT
                ad_group_ad.ad.id,
                ad_group_ad.ad.name,
                ad_group_ad.status,
                ad_group_ad.ad_group,
                ad_group_ad.ad.type,
                ad_group_ad.ad.responsive_search_ad.headlines,
                ad_group_ad.ad.responsive_search_ad.descriptions
            FROM ad_group_ad
            WHERE ad_group_ad.status != 'REMOVED'
                AND ad_group_ad.ad_group IN ({adgroup_filter})
        """

        ads = []

        try:
            response = ga_service.search(customer_id=account_id, query=query)

            for row in response:
                ad = row.ad_group_ad.ad
                status_map = {2: "active", 3: "paused"}

                # Extract ad group ID
                adset_id = row.ad_group_ad.ad_group.split("/")[-1]

                # Get headline and description
                headline = ""
                description = ""
                if ad.responsive_search_ad:
                    if ad.responsive_search_ad.headlines:
                        headline = ad.responsive_search_ad.headlines[0].text
                    if ad.responsive_search_ad.descriptions:
                        description = ad.responsive_search_ad.descriptions[0].text

                # Map ad type
                type_map = {
                    2: "text",  # TEXT_AD
                    3: "image",  # EXPANDED_TEXT_AD
                    15: "text",  # RESPONSIVE_SEARCH_AD
                }

                ads.append(
                    {
                        "id": str(ad.id),
                        "external_id": str(ad.id),
                        "adset_id": adset_id,
                        "name": ad.name or f"Ad {ad.id}",
                        "headline": headline,
                        "description": description,
                        "creative_type": type_map.get(ad.type, "text"),
                        "status": status_map.get(row.ad_group_ad.status, "paused"),
                    }
                )

            logger.info(f"Fetched {len(ads)} ads from Google Ads")
            return ads

        except Exception as e:
            error_str = str(e).lower()
            if "rate" in error_str or "quota" in error_str:
                raise RateLimitError(f"Google Ads rate limit: {e}")
            raise TemporaryError(f"Google Ads error: {e}")

    async def fetch_metrics(
        self,
        account_id: str,
        entity_type: str,
        entity_ids: list[str],
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """Fetch performance metrics from Google Ads.

        Args:
            account_id: Google Ads customer ID.
            entity_type: Type of entity (campaign/adset/ad).
            entity_ids: Entity IDs to fetch metrics for.
            start_date: Start date.
            end_date: End date.

        Returns:
            List of daily metric dictionaries.
        """
        if not self._client or not entity_ids:
            return []

        ga_service = self._client.get_service("GoogleAdsService")

        # Map entity types to Google Ads resources
        resource_map = {
            "campaign": "campaign",
            "adset": "ad_group",
            "ad": "ad_group_ad",
        }
        resource = resource_map.get(entity_type, "campaign")

        id_filter = ", ".join(f"'{eid}'" for eid in entity_ids)
        id_field = f"{resource}.id" if resource != "ad_group_ad" else "ad_group_ad.ad.id"

        query = f"""
            SELECT
                {id_field},
                segments.date,
                metrics.impressions,
                metrics.clicks,
                metrics.conversions,
                metrics.cost_micros,
                metrics.conversions_value
            FROM {resource}
            WHERE {id_field} IN ({id_filter})
                AND segments.date BETWEEN '{start_date}' AND '{end_date}'
        """

        metrics = []

        try:
            response = ga_service.search(customer_id=account_id, query=query)

            for row in response:
                # Get entity ID based on type
                if entity_type == "campaign":
                    entity_id = str(row.campaign.id)
                elif entity_type == "adset":
                    entity_id = str(row.ad_group.id)
                else:
                    entity_id = str(row.ad_group_ad.ad.id)

                m = row.metrics
                metrics.append(
                    {
                        "entity_id": entity_id,
                        "entity_type": entity_type,
                        "date": row.segments.date,
                        "impressions": m.impressions,
                        "clicks": m.clicks,
                        "conversions": int(m.conversions),
                        "spend": m.cost_micros / 1_000_000,
                        "spend_currency": "USD",
                        "revenue": m.conversions_value if m.conversions_value else None,
                        "revenue_currency": "USD" if m.conversions_value else None,
                    }
                )

            logger.info(
                f"Fetched {len(metrics)} metric records from Google Ads for {entity_type}"
            )
            return metrics

        except Exception as e:
            error_str = str(e).lower()
            if "rate" in error_str or "quota" in error_str:
                raise RateLimitError(f"Google Ads rate limit: {e}")
            raise TemporaryError(f"Google Ads error: {e}")

    def transform_to_graph_format(
        self,
        data: dict[str, Any],
        entity_type: str,
        client_id: str,
    ) -> dict[str, Any]:
        """Transform Google Ads data to graph schema format.

        Args:
            data: Raw Google Ads data.
            entity_type: Type of entity.
            client_id: Client ID.

        Returns:
            Transformed data.
        """
        transformed = {
            **data,
            "client_id": client_id,
            "channel": "google_ads",
        }

        # Ensure external_id is set
        if "external_id" not in transformed:
            transformed["external_id"] = data.get("id")

        return transformed
