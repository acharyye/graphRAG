"""Meta Marketing API connector."""

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


class MetaAdsConnector(BaseConnector):
    """Connector for Meta (Facebook/Instagram) Marketing API."""

    def __init__(self, settings: Settings | None = None):
        """Initialize Meta Ads connector.

        Args:
            settings: Application settings.
        """
        super().__init__(settings)
        self._api = None

    @property
    def is_configured(self) -> bool:
        """Check if Meta Marketing API is configured."""
        return self._settings.meta_ads_configured

    async def authenticate(self) -> bool:
        """Authenticate with Meta Marketing API.

        Returns:
            True if authentication successful.

        Raises:
            AuthenticationError: If authentication fails.
        """
        if not self.is_configured:
            raise AuthenticationError("Meta Marketing API is not configured")

        try:
            from facebook_business.api import FacebookAdsApi

            FacebookAdsApi.init(
                app_id=self._settings.META_APP_ID,
                app_secret=self._settings.META_APP_SECRET,
                access_token=self._settings.META_ACCESS_TOKEN,
            )

            self._api = FacebookAdsApi.get_default_api()
            self._is_authenticated = True
            logger.info("Meta Marketing API authentication successful")
            return True

        except Exception as e:
            logger.error(f"Meta Marketing API authentication failed: {e}")
            raise AuthenticationError(f"Meta authentication failed: {e}")

    async def fetch_campaigns(
        self,
        account_id: str,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """Fetch campaigns from Meta.

        Args:
            account_id: Meta ad account ID.
            start_date: Start date.
            end_date: End date.

        Returns:
            List of campaign dictionaries.
        """
        if not self._api:
            raise AuthenticationError("Not authenticated")

        try:
            from facebook_business.adobjects.adaccount import AdAccount
            from facebook_business.adobjects.campaign import Campaign

            account = AdAccount(f"act_{account_id}")

            fields = [
                Campaign.Field.id,
                Campaign.Field.name,
                Campaign.Field.status,
                Campaign.Field.objective,
                Campaign.Field.start_time,
                Campaign.Field.stop_time,
                Campaign.Field.daily_budget,
                Campaign.Field.lifetime_budget,
            ]

            campaigns_data = account.get_campaigns(fields=fields)
            campaigns = []

            # Status mapping
            status_map = {
                "ACTIVE": "active",
                "PAUSED": "paused",
                "DELETED": "completed",
                "ARCHIVED": "completed",
            }

            # Objective mapping
            objective_map = {
                "BRAND_AWARENESS": "awareness",
                "REACH": "awareness",
                "TRAFFIC": "traffic",
                "ENGAGEMENT": "engagement",
                "APP_INSTALLS": "conversions",
                "VIDEO_VIEWS": "engagement",
                "LEAD_GENERATION": "leads",
                "CONVERSIONS": "conversions",
                "CATALOG_SALES": "sales",
                "STORE_TRAFFIC": "traffic",
                "OUTCOME_AWARENESS": "awareness",
                "OUTCOME_ENGAGEMENT": "engagement",
                "OUTCOME_LEADS": "leads",
                "OUTCOME_SALES": "sales",
                "OUTCOME_TRAFFIC": "traffic",
            }

            for campaign in campaigns_data:
                # Get budget (daily or lifetime)
                budget = 0
                if campaign.get(Campaign.Field.daily_budget):
                    budget = float(campaign[Campaign.Field.daily_budget]) / 100  # Cents
                elif campaign.get(Campaign.Field.lifetime_budget):
                    budget = float(campaign[Campaign.Field.lifetime_budget]) / 100

                campaigns.append(
                    {
                        "id": campaign[Campaign.Field.id],
                        "external_id": campaign[Campaign.Field.id],
                        "name": campaign[Campaign.Field.name],
                        "status": status_map.get(
                            campaign.get(Campaign.Field.status), "paused"
                        ),
                        "objective": objective_map.get(
                            campaign.get(Campaign.Field.objective), "conversions"
                        ),
                        "start_date": campaign.get(Campaign.Field.start_time, "")[:10],
                        "end_date": campaign.get(Campaign.Field.stop_time, "")[:10]
                        if campaign.get(Campaign.Field.stop_time)
                        else None,
                        "budget": budget,
                        "budget_currency": "USD",
                        "channel": "meta",
                    }
                )

            logger.info(f"Fetched {len(campaigns)} campaigns from Meta")
            return campaigns

        except Exception as e:
            error_str = str(e).lower()
            if "rate" in error_str or "limit" in error_str:
                raise RateLimitError(f"Meta rate limit: {e}")
            elif "token" in error_str or "permission" in error_str:
                raise AuthenticationError(f"Meta auth error: {e}")
            raise TemporaryError(f"Meta error: {e}")

    async def fetch_adsets(
        self,
        account_id: str,
        campaign_ids: list[str],
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """Fetch ad sets from Meta.

        Args:
            account_id: Meta ad account ID.
            campaign_ids: Campaign IDs to fetch ad sets for.
            start_date: Start date.
            end_date: End date.

        Returns:
            List of ad set dictionaries.
        """
        if not self._api:
            raise AuthenticationError("Not authenticated")

        try:
            from facebook_business.adobjects.adset import AdSet
            from facebook_business.adobjects.campaign import Campaign

            adsets = []
            status_map = {"ACTIVE": "active", "PAUSED": "paused"}

            fields = [
                AdSet.Field.id,
                AdSet.Field.name,
                AdSet.Field.status,
                AdSet.Field.campaign_id,
                AdSet.Field.daily_budget,
                AdSet.Field.lifetime_budget,
                AdSet.Field.targeting,
            ]

            for campaign_id in campaign_ids:
                campaign = Campaign(campaign_id)
                adsets_data = campaign.get_ad_sets(fields=fields)

                for adset in adsets_data:
                    budget = 0
                    if adset.get(AdSet.Field.daily_budget):
                        budget = float(adset[AdSet.Field.daily_budget]) / 100
                    elif adset.get(AdSet.Field.lifetime_budget):
                        budget = float(adset[AdSet.Field.lifetime_budget]) / 100

                    # Convert targeting to JSON string
                    targeting = "{}"
                    if adset.get(AdSet.Field.targeting):
                        import json

                        targeting = json.dumps(adset[AdSet.Field.targeting])

                    adsets.append(
                        {
                            "id": adset[AdSet.Field.id],
                            "external_id": adset[AdSet.Field.id],
                            "campaign_id": campaign_id,
                            "name": adset[AdSet.Field.name],
                            "status": status_map.get(
                                adset.get(AdSet.Field.status), "paused"
                            ),
                            "budget": budget,
                            "budget_currency": "USD",
                            "targeting": targeting,
                        }
                    )

            logger.info(f"Fetched {len(adsets)} ad sets from Meta")
            return adsets

        except Exception as e:
            error_str = str(e).lower()
            if "rate" in error_str or "limit" in error_str:
                raise RateLimitError(f"Meta rate limit: {e}")
            raise TemporaryError(f"Meta error: {e}")

    async def fetch_ads(
        self,
        account_id: str,
        adset_ids: list[str],
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """Fetch ads from Meta.

        Args:
            account_id: Meta ad account ID.
            adset_ids: Ad set IDs to fetch ads for.
            start_date: Start date.
            end_date: End date.

        Returns:
            List of ad dictionaries.
        """
        if not self._api:
            raise AuthenticationError("Not authenticated")

        try:
            from facebook_business.adobjects.ad import Ad
            from facebook_business.adobjects.adset import AdSet

            ads = []
            status_map = {"ACTIVE": "active", "PAUSED": "paused"}

            fields = [
                Ad.Field.id,
                Ad.Field.name,
                Ad.Field.status,
                Ad.Field.adset_id,
                Ad.Field.creative,
            ]

            for adset_id in adset_ids:
                adset = AdSet(adset_id)
                ads_data = adset.get_ads(fields=fields)

                for ad in ads_data:
                    # Determine creative type from creative object
                    creative_type = "image"
                    if ad.get(Ad.Field.creative):
                        creative = ad[Ad.Field.creative]
                        if "video" in str(creative).lower():
                            creative_type = "video"
                        elif "carousel" in str(creative).lower():
                            creative_type = "carousel"

                    ads.append(
                        {
                            "id": ad[Ad.Field.id],
                            "external_id": ad[Ad.Field.id],
                            "adset_id": adset_id,
                            "name": ad[Ad.Field.name],
                            "headline": "",  # Would need to fetch creative details
                            "description": "",
                            "creative_type": creative_type,
                            "status": status_map.get(
                                ad.get(Ad.Field.status), "paused"
                            ),
                        }
                    )

            logger.info(f"Fetched {len(ads)} ads from Meta")
            return ads

        except Exception as e:
            error_str = str(e).lower()
            if "rate" in error_str or "limit" in error_str:
                raise RateLimitError(f"Meta rate limit: {e}")
            raise TemporaryError(f"Meta error: {e}")

    async def fetch_metrics(
        self,
        account_id: str,
        entity_type: str,
        entity_ids: list[str],
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """Fetch performance insights from Meta.

        Args:
            account_id: Meta ad account ID.
            entity_type: Type of entity (campaign/adset/ad).
            entity_ids: Entity IDs to fetch metrics for.
            start_date: Start date.
            end_date: End date.

        Returns:
            List of daily metric dictionaries.
        """
        if not self._api or not entity_ids:
            return []

        try:
            from facebook_business.adobjects.ad import Ad
            from facebook_business.adobjects.adset import AdSet
            from facebook_business.adobjects.campaign import Campaign
            from facebook_business.adobjects.adsinsights import AdsInsights

            # Map entity types to classes
            class_map = {
                "campaign": Campaign,
                "adset": AdSet,
                "ad": Ad,
            }
            entity_class = class_map.get(entity_type, Campaign)

            fields = [
                AdsInsights.Field.impressions,
                AdsInsights.Field.clicks,
                AdsInsights.Field.conversions,
                AdsInsights.Field.spend,
                AdsInsights.Field.purchase_roas,
            ]

            params = {
                "time_range": {
                    "since": start_date.strftime("%Y-%m-%d"),
                    "until": end_date.strftime("%Y-%m-%d"),
                },
                "time_increment": 1,  # Daily breakdown
            }

            metrics = []

            for entity_id in entity_ids:
                entity = entity_class(entity_id)

                try:
                    insights = entity.get_insights(fields=fields, params=params)

                    for insight in insights:
                        spend = float(insight.get(AdsInsights.Field.spend, 0))

                        # Get conversions count
                        conversions = 0
                        if insight.get(AdsInsights.Field.conversions):
                            for conv in insight[AdsInsights.Field.conversions]:
                                conversions += int(conv.get("value", 0))

                        # Get revenue from ROAS
                        revenue = None
                        if insight.get(AdsInsights.Field.purchase_roas):
                            roas_data = insight[AdsInsights.Field.purchase_roas]
                            if roas_data and len(roas_data) > 0:
                                roas = float(roas_data[0].get("value", 0))
                                revenue = spend * roas

                        metrics.append(
                            {
                                "entity_id": entity_id,
                                "entity_type": entity_type,
                                "date": insight.get("date_start"),
                                "impressions": int(
                                    insight.get(AdsInsights.Field.impressions, 0)
                                ),
                                "clicks": int(
                                    insight.get(AdsInsights.Field.clicks, 0)
                                ),
                                "conversions": conversions,
                                "spend": spend,
                                "spend_currency": "USD",
                                "revenue": revenue,
                                "revenue_currency": "USD" if revenue else None,
                            }
                        )

                except Exception as e:
                    logger.warning(f"Failed to fetch insights for {entity_id}: {e}")
                    continue

            logger.info(
                f"Fetched {len(metrics)} metric records from Meta for {entity_type}"
            )
            return metrics

        except Exception as e:
            error_str = str(e).lower()
            if "rate" in error_str or "limit" in error_str:
                raise RateLimitError(f"Meta rate limit: {e}")
            raise TemporaryError(f"Meta error: {e}")

    def transform_to_graph_format(
        self,
        data: dict[str, Any],
        entity_type: str,
        client_id: str,
    ) -> dict[str, Any]:
        """Transform Meta data to graph schema format.

        Args:
            data: Raw Meta data.
            entity_type: Type of entity.
            client_id: Client ID.

        Returns:
            Transformed data.
        """
        transformed = {
            **data,
            "client_id": client_id,
            "channel": "meta",
        }

        if "external_id" not in transformed:
            transformed["external_id"] = data.get("id")

        return transformed
