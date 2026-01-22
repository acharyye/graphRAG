"""Mock data generator for MVP testing."""

import random
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4


class MockDataGenerator:
    """Generates realistic marketing data for testing."""

    # Sample data pools
    INDUSTRIES = [
        "E-commerce",
        "SaaS",
        "Healthcare",
        "Finance",
        "Retail",
        "Travel",
        "Education",
        "Real Estate",
    ]

    COMPANY_NAMES = [
        ("Apex Retail", "Retail"),
        ("TechFlow SaaS", "SaaS"),
        ("HealthFirst Clinic", "Healthcare"),
        ("GlobalFinance Corp", "Finance"),
        ("Wanderlust Travel", "Travel"),
    ]

    CAMPAIGN_PREFIXES = [
        "Summer Sale",
        "Brand Awareness",
        "Lead Gen",
        "Retargeting",
        "Holiday Special",
        "New Product Launch",
        "Customer Acquisition",
        "Engagement Boost",
    ]

    CAMPAIGN_OBJECTIVES = [
        "awareness",
        "traffic",
        "engagement",
        "leads",
        "conversions",
        "sales",
    ]

    AD_HEADLINES = [
        "Save Big Today!",
        "Limited Time Offer",
        "Discover Something New",
        "Transform Your Business",
        "Get Started Free",
        "Exclusive Deal Inside",
        "Don't Miss Out",
        "See What's New",
    ]

    AD_DESCRIPTIONS = [
        "Click to learn more about our amazing products and services.",
        "Join thousands of satisfied customers today.",
        "Experience the difference with our premium solutions.",
        "Start your free trial and see results immediately.",
        "Quality you can trust at prices you'll love.",
    ]

    CURRENCIES = ["USD", "EUR", "GBP"]

    TARGETING_OPTIONS = [
        '{"age": "25-44", "interests": ["technology", "business"]}',
        '{"age": "18-34", "interests": ["fashion", "lifestyle"]}',
        '{"age": "35-54", "interests": ["finance", "investing"]}',
        '{"age": "25-54", "location": "United States", "interests": ["shopping"]}',
        '{"age": "18-24", "interests": ["gaming", "entertainment"]}',
    ]

    def __init__(self, seed: int | None = None):
        """Initialize the generator.

        Args:
            seed: Random seed for reproducibility.
        """
        if seed is not None:
            random.seed(seed)

    def generate_clients(self, count: int = 5) -> list[dict[str, Any]]:
        """Generate client data.

        Args:
            count: Number of clients to generate.

        Returns:
            List of client dictionaries.
        """
        clients = []
        used_names = set()

        for _ in range(count):
            # Pick unique company
            available = [c for c in self.COMPANY_NAMES if c[0] not in used_names]
            if not available:
                name = f"Client {uuid4().hex[:6]}"
                industry = random.choice(self.INDUSTRIES)
            else:
                name, industry = random.choice(available)
                used_names.add(name)

            currency = random.choice(self.CURRENCIES)
            contract_start = datetime.now() - timedelta(days=random.randint(90, 365))

            clients.append(
                {
                    "id": str(uuid4()),
                    "name": name,
                    "industry": industry,
                    "contract_start": contract_start.strftime("%Y-%m-%d"),
                    "budget": random.randint(10000, 100000),
                    "budget_currency": currency,
                    "status": "active",
                    "data_retention_days": random.choice([180, 365, 730]),
                }
            )

        return clients

    def generate_campaigns(
        self,
        client_id: str,
        count: int = 4,
        currency: str = "USD",
    ) -> list[dict[str, Any]]:
        """Generate campaign data for a client.

        Args:
            client_id: Parent client ID.
            count: Number of campaigns to generate.
            currency: Budget currency.

        Returns:
            List of campaign dictionaries.
        """
        campaigns = []
        channels = ["google_ads", "meta"]

        for i in range(count):
            prefix = random.choice(self.CAMPAIGN_PREFIXES)
            objective = random.choice(self.CAMPAIGN_OBJECTIVES)
            channel = channels[i % len(channels)]
            start_date = datetime.now() - timedelta(days=random.randint(30, 90))
            end_date = start_date + timedelta(days=random.randint(30, 90))
            status = random.choices(
                ["active", "paused", "completed"],
                weights=[0.6, 0.2, 0.2],
            )[0]

            if end_date < datetime.now():
                status = "completed"

            budget = random.randint(1000, 20000)

            campaigns.append(
                {
                    "id": str(uuid4()),
                    "client_id": client_id,
                    "external_id": f"{channel}_{uuid4().hex[:8]}",
                    "name": f"{prefix} - {channel.replace('_', ' ').title()}",
                    "objective": objective,
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d"),
                    "budget": budget,
                    "budget_currency": currency,
                    "daily_budget": budget / 30,
                    "status": status,
                    "channel": channel,
                }
            )

        return campaigns

    def generate_adsets(
        self,
        campaign_id: str,
        client_id: str,
        count: int = 3,
        currency: str = "USD",
    ) -> list[dict[str, Any]]:
        """Generate ad set data for a campaign.

        Args:
            campaign_id: Parent campaign ID.
            client_id: Parent client ID.
            count: Number of ad sets to generate.
            currency: Budget currency.

        Returns:
            List of ad set dictionaries.
        """
        adsets = []
        audiences = ["Broad", "Interest-Based", "Lookalike", "Retargeting", "Custom"]

        for i in range(count):
            audience = audiences[i % len(audiences)]
            budget = random.randint(200, 2000)

            adsets.append(
                {
                    "id": str(uuid4()),
                    "client_id": client_id,
                    "campaign_id": campaign_id,
                    "external_id": f"adset_{uuid4().hex[:8]}",
                    "name": f"{audience} Audience",
                    "targeting": random.choice(self.TARGETING_OPTIONS),
                    "budget": budget,
                    "budget_currency": currency,
                    "status": random.choices(
                        ["active", "paused"], weights=[0.8, 0.2]
                    )[0],
                }
            )

        return adsets

    def generate_ads(
        self,
        adset_id: str,
        client_id: str,
        count: int = 5,
    ) -> list[dict[str, Any]]:
        """Generate ad data for an ad set.

        Args:
            adset_id: Parent ad set ID.
            client_id: Parent client ID.
            count: Number of ads to generate.

        Returns:
            List of ad dictionaries.
        """
        ads = []
        creative_types = ["image", "video", "carousel"]

        for i in range(count):
            creative_type = creative_types[i % len(creative_types)]

            ads.append(
                {
                    "id": str(uuid4()),
                    "client_id": client_id,
                    "adset_id": adset_id,
                    "external_id": f"ad_{uuid4().hex[:8]}",
                    "name": f"Ad Variant {chr(65 + i)}",
                    "headline": random.choice(self.AD_HEADLINES),
                    "description": random.choice(self.AD_DESCRIPTIONS),
                    "creative_type": creative_type,
                    "status": random.choices(
                        ["active", "paused"], weights=[0.85, 0.15]
                    )[0],
                }
            )

        return ads

    def generate_metrics(
        self,
        entity_id: str,
        entity_type: str,
        client_id: str,
        days: int = 90,
        currency: str = "USD",
        include_revenue: bool = True,
    ) -> list[dict[str, Any]]:
        """Generate daily metrics for an entity.

        Args:
            entity_id: Entity UUID.
            entity_type: Type of entity (campaign/adset/ad).
            client_id: Client UUID.
            days: Number of days of data.
            currency: Spend/revenue currency.
            include_revenue: Whether to include revenue data.

        Returns:
            List of metric dictionaries.
        """
        metrics = []
        base_impressions = random.randint(1000, 10000)
        base_ctr = random.uniform(0.5, 3.0)  # 0.5% to 3%
        base_cvr = random.uniform(1.0, 10.0)  # 1% to 10% of clicks
        base_cpc = random.uniform(0.5, 5.0)  # $0.50 to $5.00
        base_aov = random.uniform(50, 200)  # Average order value

        # Add some variance and trend
        trend_factor = random.uniform(-0.002, 0.005)  # Daily trend

        for day in range(days):
            date = (datetime.now() - timedelta(days=days - day)).strftime("%Y-%m-%d")

            # Add daily and weekly seasonality
            day_of_week = (datetime.now() - timedelta(days=days - day)).weekday()
            weekend_factor = 0.7 if day_of_week >= 5 else 1.0
            daily_variance = random.uniform(0.7, 1.3)

            # Calculate metrics with trend
            trend_multiplier = 1 + (trend_factor * day)

            impressions = int(
                base_impressions * weekend_factor * daily_variance * trend_multiplier
            )
            clicks = int(impressions * (base_ctr / 100) * random.uniform(0.8, 1.2))
            conversions = int(clicks * (base_cvr / 100) * random.uniform(0.7, 1.3))
            spend = round(clicks * base_cpc * random.uniform(0.9, 1.1), 2)

            metric = {
                "id": f"{entity_id}_{date}",
                "date": date,
                "impressions": max(0, impressions),
                "clicks": max(0, clicks),
                "conversions": max(0, conversions),
                "spend": max(0, spend),
                "spend_currency": currency,
            }

            if include_revenue and conversions > 0:
                revenue = round(
                    conversions * base_aov * random.uniform(0.8, 1.2), 2
                )
                metric["revenue"] = revenue
                metric["revenue_currency"] = currency

            metrics.append(metric)

        return metrics

    def generate_full_dataset(
        self,
        num_clients: int = 5,
        campaigns_per_client: int = 4,
        adsets_per_campaign: int = 3,
        ads_per_adset: int = 5,
        metric_days: int = 90,
    ) -> dict[str, Any]:
        """Generate a complete dataset for testing.

        Args:
            num_clients: Number of clients.
            campaigns_per_client: Campaigns per client.
            adsets_per_campaign: Ad sets per campaign.
            ads_per_adset: Ads per ad set.
            metric_days: Days of metric history.

        Returns:
            Dictionary with all generated data.
        """
        data = {
            "clients": [],
            "campaigns": [],
            "adsets": [],
            "ads": [],
            "metrics": [],
        }

        clients = self.generate_clients(num_clients)
        data["clients"] = clients

        for client in clients:
            client_id = client["id"]
            currency = client["budget_currency"]

            campaigns = self.generate_campaigns(
                client_id, campaigns_per_client, currency
            )
            data["campaigns"].extend(campaigns)

            for campaign in campaigns:
                campaign_id = campaign["id"]

                # Generate campaign-level metrics
                campaign_metrics = self.generate_metrics(
                    campaign_id,
                    "campaign",
                    client_id,
                    metric_days,
                    currency,
                    include_revenue=campaign["objective"] in ["conversions", "sales"],
                )
                data["metrics"].extend(campaign_metrics)

                adsets = self.generate_adsets(
                    campaign_id, client_id, adsets_per_campaign, currency
                )
                data["adsets"].extend(adsets)

                for adset in adsets:
                    adset_id = adset["id"]

                    # Generate adset-level metrics (subset of campaign)
                    adset_metrics = self.generate_metrics(
                        adset_id,
                        "adset",
                        client_id,
                        metric_days,
                        currency,
                        include_revenue=False,
                    )
                    # Scale down adset metrics
                    for m in adset_metrics:
                        m["impressions"] = int(m["impressions"] / adsets_per_campaign)
                        m["clicks"] = int(m["clicks"] / adsets_per_campaign)
                        m["conversions"] = int(m["conversions"] / adsets_per_campaign)
                        m["spend"] = round(m["spend"] / adsets_per_campaign, 2)
                    data["metrics"].extend(adset_metrics)

                    ads = self.generate_ads(adset_id, client_id, ads_per_adset)
                    data["ads"].extend(ads)

        return data

    def generate_users(
        self, clients: list[dict[str, Any]], hashed_password: str
    ) -> list[dict[str, Any]]:
        """Generate sample users for testing.

        Args:
            clients: List of client data (to assign access).
            hashed_password: Pre-hashed password for all users.

        Returns:
            List of user dictionaries.
        """
        users = []

        # Admin user with access to all clients
        users.append(
            {
                "id": str(uuid4()),
                "email": "admin@agency.com",
                "hashed_password": hashed_password,
                "name": "Admin User",
                "role": "admin",
                "client_ids": [c["id"] for c in clients],
            }
        )

        # One account manager per client
        for i, client in enumerate(clients):
            users.append(
                {
                    "id": str(uuid4()),
                    "email": f"manager{i + 1}@agency.com",
                    "hashed_password": hashed_password,
                    "name": f"Account Manager {i + 1}",
                    "role": "manager",
                    "client_ids": [client["id"]],
                }
            )

        # Analyst with access to first 3 clients
        users.append(
            {
                "id": str(uuid4()),
                "email": "analyst@agency.com",
                "hashed_password": hashed_password,
                "name": "Data Analyst",
                "role": "analyst",
                "client_ids": [c["id"] for c in clients[:3]],
            }
        )

        # Executive with read-only access to all
        users.append(
            {
                "id": str(uuid4()),
                "email": "executive@agency.com",
                "hashed_password": hashed_password,
                "name": "Executive User",
                "role": "executive",
                "client_ids": [c["id"] for c in clients],
            }
        )

        return users
