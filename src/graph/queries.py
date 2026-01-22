"""Cypher query templates for common operations."""

from dataclasses import dataclass
from typing import Any


@dataclass
class CypherQueries:
    """Collection of Cypher query templates.

    All queries include client_id filtering for strict tenant isolation.
    """

    # Client Queries
    GET_CLIENT = """
    MATCH (c:Client {id: $client_id})
    RETURN c
    """

    GET_ALL_CLIENTS = """
    MATCH (c:Client)
    WHERE c.status = 'active'
    RETURN c
    ORDER BY c.name
    """

    # Campaign Queries
    GET_CAMPAIGNS_BY_CLIENT = """
    MATCH (c:Client {id: $client_id})-[:OWNS]->(camp:Campaign)
    RETURN camp
    ORDER BY camp.start_date DESC
    """

    GET_ACTIVE_CAMPAIGNS = """
    MATCH (c:Client {id: $client_id})-[:OWNS]->(camp:Campaign)
    WHERE camp.status = 'active'
    RETURN camp
    ORDER BY camp.start_date DESC
    """

    GET_CAMPAIGN_PERFORMANCE = """
    MATCH (c:Client {id: $client_id})-[:OWNS]->(camp:Campaign {id: $campaign_id})
    OPTIONAL MATCH (m:Metric {entity_type: 'campaign', entity_id: camp.id})
    WHERE m.date >= date($start_date) AND m.date <= date($end_date)
    WITH camp, m
    RETURN camp,
        sum(m.impressions) AS total_impressions,
        sum(m.clicks) AS total_clicks,
        sum(m.conversions) AS total_conversions,
        sum(m.spend) AS total_spend,
        sum(m.revenue) AS total_revenue,
        CASE WHEN sum(m.impressions) > 0
            THEN toFloat(sum(m.clicks)) / sum(m.impressions) * 100
            ELSE 0 END AS avg_ctr,
        CASE WHEN sum(m.clicks) > 0
            THEN sum(m.spend) / sum(m.clicks)
            ELSE 0 END AS avg_cpc,
        CASE WHEN sum(m.spend) > 0 AND sum(m.revenue) IS NOT NULL
            THEN sum(m.revenue) / sum(m.spend)
            ELSE null END AS roas
    """

    # Aggregate Performance Queries
    GET_CLIENT_SUMMARY = """
    MATCH (c:Client {id: $client_id})
    OPTIONAL MATCH (c)-[:OWNS]->(camp:Campaign)
    OPTIONAL MATCH (m:Metric {client_id: $client_id})
    WHERE m.date >= date($start_date) AND m.date <= date($end_date)
    WITH c, count(DISTINCT camp) AS campaign_count, m
    RETURN c.name AS client_name,
        campaign_count,
        sum(m.impressions) AS total_impressions,
        sum(m.clicks) AS total_clicks,
        sum(m.conversions) AS total_conversions,
        sum(m.spend) AS total_spend,
        sum(m.revenue) AS total_revenue,
        CASE WHEN sum(m.impressions) > 0
            THEN toFloat(sum(m.clicks)) / sum(m.impressions) * 100
            ELSE 0 END AS avg_ctr,
        CASE WHEN sum(m.spend) > 0 AND sum(m.revenue) IS NOT NULL
            THEN sum(m.revenue) / sum(m.spend)
            ELSE null END AS roas
    """

    GET_DAILY_METRICS = """
    MATCH (m:Metric {client_id: $client_id})
    WHERE m.date >= date($start_date) AND m.date <= date($end_date)
    RETURN m.date AS date,
        sum(m.impressions) AS impressions,
        sum(m.clicks) AS clicks,
        sum(m.conversions) AS conversions,
        sum(m.spend) AS spend,
        sum(m.revenue) AS revenue
    ORDER BY date
    """

    GET_CAMPAIGN_COMPARISON = """
    MATCH (c:Client {id: $client_id})-[:OWNS]->(camp:Campaign)
    WHERE camp.status IN $statuses
    OPTIONAL MATCH (m:Metric {entity_type: 'campaign', entity_id: camp.id})
    WHERE m.date >= date($start_date) AND m.date <= date($end_date)
    WITH camp, m
    RETURN camp.id AS campaign_id,
        camp.name AS campaign_name,
        camp.objective AS objective,
        camp.status AS status,
        camp.channel AS channel,
        sum(m.impressions) AS impressions,
        sum(m.clicks) AS clicks,
        sum(m.conversions) AS conversions,
        sum(m.spend) AS spend,
        sum(m.revenue) AS revenue,
        CASE WHEN sum(m.impressions) > 0
            THEN toFloat(sum(m.clicks)) / sum(m.impressions) * 100
            ELSE 0 END AS ctr,
        CASE WHEN sum(m.spend) > 0 AND sum(m.revenue) IS NOT NULL
            THEN sum(m.revenue) / sum(m.spend)
            ELSE null END AS roas
    ORDER BY spend DESC
    """

    # Top/Bottom Performers
    GET_TOP_CAMPAIGNS = """
    MATCH (c:Client {id: $client_id})-[:OWNS]->(camp:Campaign)
    WHERE camp.status = 'active'
    OPTIONAL MATCH (m:Metric {entity_type: 'campaign', entity_id: camp.id})
    WHERE m.date >= date($start_date) AND m.date <= date($end_date)
    WITH camp, sum(m.revenue) AS revenue, sum(m.spend) AS spend
    WHERE spend > 0 AND revenue IS NOT NULL
    RETURN camp.id AS campaign_id,
        camp.name AS campaign_name,
        revenue,
        spend,
        revenue / spend AS roas
    ORDER BY roas DESC
    LIMIT $limit
    """

    GET_UNDERPERFORMING_CAMPAIGNS = """
    MATCH (c:Client {id: $client_id})-[:OWNS]->(camp:Campaign)
    WHERE camp.status = 'active'
    OPTIONAL MATCH (m:Metric {entity_type: 'campaign', entity_id: camp.id})
    WHERE m.date >= date($start_date) AND m.date <= date($end_date)
    WITH camp, sum(m.revenue) AS revenue, sum(m.spend) AS spend, sum(m.conversions) AS conversions
    WHERE spend > $min_spend
    RETURN camp.id AS campaign_id,
        camp.name AS campaign_name,
        revenue,
        spend,
        conversions,
        CASE WHEN spend > 0 AND revenue IS NOT NULL
            THEN revenue / spend
            ELSE 0 END AS roas
    ORDER BY roas ASC
    LIMIT $limit
    """

    # Channel Analysis
    GET_CHANNEL_BREAKDOWN = """
    MATCH (c:Client {id: $client_id})-[:OWNS]->(camp:Campaign)-[:RUNS_ON]->(ch:Channel)
    OPTIONAL MATCH (m:Metric {entity_type: 'campaign', entity_id: camp.id})
    WHERE m.date >= date($start_date) AND m.date <= date($end_date)
    WITH ch.name AS channel, m
    RETURN channel,
        sum(m.impressions) AS impressions,
        sum(m.clicks) AS clicks,
        sum(m.conversions) AS conversions,
        sum(m.spend) AS spend,
        sum(m.revenue) AS revenue,
        CASE WHEN sum(m.spend) > 0 AND sum(m.revenue) IS NOT NULL
            THEN sum(m.revenue) / sum(m.spend)
            ELSE null END AS roas
    ORDER BY spend DESC
    """

    # Ad Set and Ad Queries
    GET_ADSETS_BY_CAMPAIGN = """
    MATCH (camp:Campaign {id: $campaign_id, client_id: $client_id})-[:CONTAINS]->(adset:AdSet)
    OPTIONAL MATCH (m:Metric {entity_type: 'adset', entity_id: adset.id})
    WHERE m.date >= date($start_date) AND m.date <= date($end_date)
    WITH adset, m
    RETURN adset.id AS adset_id,
        adset.name AS adset_name,
        adset.status AS status,
        sum(m.impressions) AS impressions,
        sum(m.clicks) AS clicks,
        sum(m.conversions) AS conversions,
        sum(m.spend) AS spend
    ORDER BY spend DESC
    """

    GET_ADS_BY_ADSET = """
    MATCH (adset:AdSet {id: $adset_id, client_id: $client_id})-[:CONTAINS]->(ad:Ad)
    OPTIONAL MATCH (m:Metric {entity_type: 'ad', entity_id: ad.id})
    WHERE m.date >= date($start_date) AND m.date <= date($end_date)
    WITH ad, m
    RETURN ad.id AS ad_id,
        ad.name AS ad_name,
        ad.headline AS headline,
        ad.creative_type AS creative_type,
        ad.status AS status,
        sum(m.impressions) AS impressions,
        sum(m.clicks) AS clicks,
        sum(m.conversions) AS conversions,
        sum(m.spend) AS spend
    ORDER BY conversions DESC
    """

    # User Queries
    GET_USER_BY_EMAIL = """
    MATCH (u:User {email: $email})
    RETURN u
    """

    GET_USER_BY_ID = """
    MATCH (u:User {id: $user_id})
    RETURN u
    """

    # Audit Log Queries
    GET_AUDIT_LOGS = """
    MATCH (a:AuditLog {client_id: $client_id})
    WHERE a.timestamp >= datetime($start_date) AND a.timestamp <= datetime($end_date)
    RETURN a
    ORDER BY a.timestamp DESC
    LIMIT $limit
    """

    GET_USER_AUDIT_LOGS = """
    MATCH (a:AuditLog {user_id: $user_id})
    WHERE a.timestamp >= datetime($start_date) AND a.timestamp <= datetime($end_date)
    RETURN a
    ORDER BY a.timestamp DESC
    LIMIT $limit
    """

    # Search Queries (for RAG context retrieval)
    SEARCH_CAMPAIGNS_BY_NAME = """
    MATCH (c:Client {id: $client_id})-[:OWNS]->(camp:Campaign)
    WHERE toLower(camp.name) CONTAINS toLower($search_term)
    RETURN camp
    LIMIT 10
    """

    SEARCH_ALL_ENTITIES = """
    MATCH (c:Client {id: $client_id})
    OPTIONAL MATCH (c)-[:OWNS]->(camp:Campaign)
    WHERE toLower(camp.name) CONTAINS toLower($search_term)
    OPTIONAL MATCH (camp)-[:CONTAINS]->(adset:AdSet)
    WHERE toLower(adset.name) CONTAINS toLower($search_term)
    OPTIONAL MATCH (adset)-[:CONTAINS]->(ad:Ad)
    WHERE toLower(ad.name) CONTAINS toLower($search_term)
        OR toLower(ad.headline) CONTAINS toLower($search_term)
    RETURN collect(DISTINCT camp) AS campaigns,
        collect(DISTINCT adset) AS adsets,
        collect(DISTINCT ad) AS ads
    """

    # Graph Context for RAG
    GET_CAMPAIGN_FULL_CONTEXT = """
    MATCH (c:Client {id: $client_id})-[:OWNS]->(camp:Campaign {id: $campaign_id})
    OPTIONAL MATCH (camp)-[:RUNS_ON]->(ch:Channel)
    OPTIONAL MATCH (camp)-[:CONTAINS]->(adset:AdSet)
    OPTIONAL MATCH (adset)-[:CONTAINS]->(ad:Ad)
    OPTIONAL MATCH (m:Metric {entity_type: 'campaign', entity_id: camp.id})
    WHERE m.date >= date($start_date) AND m.date <= date($end_date)
    RETURN camp,
        ch.display_name AS channel_name,
        collect(DISTINCT {id: adset.id, name: adset.name, status: adset.status}) AS adsets,
        collect(DISTINCT {id: ad.id, name: ad.name, headline: ad.headline}) AS ads,
        {
            impressions: sum(m.impressions),
            clicks: sum(m.clicks),
            conversions: sum(m.conversions),
            spend: sum(m.spend),
            revenue: sum(m.revenue)
        } AS metrics
    """


def build_dynamic_query(
    base_query: str,
    filters: dict[str, Any],
    order_by: str | None = None,
    limit: int | None = None,
) -> tuple[str, dict[str, Any]]:
    """Build a dynamic Cypher query with optional filters.

    Args:
        base_query: Base Cypher query template.
        filters: Dictionary of filter conditions.
        order_by: Optional ORDER BY clause.
        limit: Optional result limit.

    Returns:
        Tuple of (query_string, parameters).
    """
    params = {}
    where_clauses = []

    for key, value in filters.items():
        if value is not None:
            param_name = f"filter_{key}"
            where_clauses.append(f"n.{key} = ${param_name}")
            params[param_name] = value

    query = base_query
    if where_clauses:
        query += f" WHERE {' AND '.join(where_clauses)}"
    if order_by:
        query += f" ORDER BY {order_by}"
    if limit:
        query += f" LIMIT {limit}"

    return query, params
