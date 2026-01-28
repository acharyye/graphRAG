"""Dashboard API routes."""

import logging
from typing import Any

from fastapi import APIRouter

from src.api.dependencies import CurrentUser, Neo4jDep, verify_client_access

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _convert_neo4j_value(value):
    """Convert Neo4j types to Python native types."""
    if value is None:
        return None
    if hasattr(value, 'to_native'):
        return value.to_native()
    return value


@router.get("/{client_id}")
async def get_dashboard_data(
    client_id: str,
    start_date: str,
    end_date: str,
    current_user: CurrentUser,
    neo4j: Neo4jDep,
) -> dict[str, Any]:
    """Get dashboard data for a client."""
    await verify_client_access(client_id, current_user)

    # Fetch summary metrics (metrics are connected via client_id property)
    summary_result = neo4j.execute_query("""
        MATCH (m:Metric)
        WHERE m.client_id = $client_id
          AND m.date >= date($start_date)
          AND m.date <= date($end_date)
        RETURN
            sum(m.spend) as total_spend,
            sum(m.impressions) as total_impressions,
            sum(m.clicks) as total_clicks,
            sum(m.conversions) as total_conversions,
            CASE WHEN sum(m.impressions) > 0 THEN sum(m.clicks) * 100.0 / sum(m.impressions) ELSE 0 END as avg_ctr,
            CASE WHEN sum(m.spend) > 0 THEN coalesce(sum(m.revenue), 0) / sum(m.spend) ELSE 0 END as roas
    """, {"client_id": client_id, "start_date": start_date, "end_date": end_date})

    summary = {}
    if summary_result:
        r = summary_result[0]
        summary = {
            "total_spend": _convert_neo4j_value(r.get("total_spend")) or 0,
            "total_impressions": _convert_neo4j_value(r.get("total_impressions")) or 0,
            "total_clicks": _convert_neo4j_value(r.get("total_clicks")) or 0,
            "total_conversions": _convert_neo4j_value(r.get("total_conversions")) or 0,
            "avg_ctr": _convert_neo4j_value(r.get("avg_ctr")) or 0,
            "roas": _convert_neo4j_value(r.get("roas")) or 0,
        }

    # Fetch daily metrics
    daily_result = neo4j.execute_query("""
        MATCH (m:Metric)
        WHERE m.client_id = $client_id
          AND m.date >= date($start_date)
          AND m.date <= date($end_date)
        WITH m.date as date, sum(m.spend) as spend, sum(m.conversions) as conversions
        RETURN toString(date) as date, spend, conversions
        ORDER BY date
    """, {"client_id": client_id, "start_date": start_date, "end_date": end_date})

    daily_metrics = []
    if daily_result:
        for r in daily_result:
            daily_metrics.append({
                "date": r.get("date"),
                "spend": _convert_neo4j_value(r.get("spend")) or 0,
                "conversions": _convert_neo4j_value(r.get("conversions")) or 0,
            })

    # Fetch channel breakdown
    channel_result = neo4j.execute_query("""
        MATCH (c:Client {id: $client_id})-[:OWNS]->(camp:Campaign)-[:RUNS_ON]->(ch:Channel)
        MATCH (m:Metric)
        WHERE m.entity_id = camp.id
          AND m.date >= date($start_date)
          AND m.date <= date($end_date)
        RETURN
            ch.name as channel,
            sum(m.spend) as spend,
            sum(m.conversions) as conversions
    """, {"client_id": client_id, "start_date": start_date, "end_date": end_date})

    channel_breakdown = []
    if channel_result:
        for r in channel_result:
            channel_breakdown.append({
                "channel": r.get("channel"),
                "spend": _convert_neo4j_value(r.get("spend")) or 0,
                "conversions": _convert_neo4j_value(r.get("conversions")) or 0,
            })

    # Fetch campaign performance
    campaign_result = neo4j.execute_query("""
        MATCH (c:Client {id: $client_id})-[:OWNS]->(camp:Campaign)-[:RUNS_ON]->(ch:Channel)
        OPTIONAL MATCH (m:Metric)
        WHERE m.entity_id = camp.id
          AND m.date >= date($start_date)
          AND m.date <= date($end_date)
        RETURN
            camp.name as name,
            ch.name as channel,
            camp.status as status,
            sum(m.spend) as spend,
            sum(m.clicks) as clicks,
            sum(m.conversions) as conversions,
            sum(m.impressions) as impressions,
            CASE WHEN sum(m.impressions) > 0 THEN sum(m.clicks) * 100.0 / sum(m.impressions) ELSE 0 END as ctr,
            CASE WHEN sum(m.spend) > 0 THEN coalesce(sum(m.revenue), 0) / sum(m.spend) ELSE 0 END as roas
        ORDER BY spend DESC
        LIMIT 20
    """, {"client_id": client_id, "start_date": start_date, "end_date": end_date})

    campaigns = []
    if campaign_result:
        for r in campaign_result:
            campaigns.append({
                "name": r.get("name"),
                "channel": r.get("channel"),
                "status": r.get("status") or "active",
                "spend": _convert_neo4j_value(r.get("spend")) or 0,
                "clicks": _convert_neo4j_value(r.get("clicks")) or 0,
                "conversions": _convert_neo4j_value(r.get("conversions")) or 0,
                "ctr": _convert_neo4j_value(r.get("ctr")) or 0,
                "roas": _convert_neo4j_value(r.get("roas")) or 0,
            })

    return {
        "client_id": client_id,
        "date_range": {"start": start_date, "end": end_date},
        "summary": summary,
        "daily_metrics": daily_metrics,
        "channel_breakdown": channel_breakdown,
        "campaigns": campaigns,
    }
