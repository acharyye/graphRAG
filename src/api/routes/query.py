"""Query API routes for natural language queries."""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from src.api.dependencies import (
    CurrentUser,
    GraphRAGDep,
    Neo4jDep,
    verify_client_access,
)
from src.api.models import (
    ConfidenceDetails,
    ConfidenceLevel,
    DrillDownRequest,
    DrillDownResponse,
    QueryRequest,
    QueryResponse,
    Source,
)
from src.services.audit import AuditService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["Query"])


@router.post("", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    current_user: CurrentUser,
    graphrag: GraphRAGDep,
    neo4j: Neo4jDep,
) -> QueryResponse:
    """Process a natural language query against the marketing data graph."""
    # Verify client access
    await verify_client_access(request.client_id, current_user)

    start_time = datetime.utcnow()

    try:
        # Execute query
        result = graphrag.query(
            query=request.query,
            client_id=request.client_id,
            user_role=current_user.role.value,
            session_id=request.session_id,
            date_range=request.date_range,
        )

        # Convert internal types to API models
        confidence = ConfidenceDetails(
            overall=result.confidence.overall,
            level=ConfidenceLevel(result.confidence.level.value),
            factors=result.confidence.factors,
            explanation=result.confidence.explanation,
        )

        sources = [
            Source(
                entity_type=s.entity_type,
                entity_id=s.entity_id,
                entity_name=s.entity_name,
                date_range=s.date_range,
            )
            for s in result.sources
        ]

        response = QueryResponse(
            answer=result.answer,
            confidence=confidence,
            sources=sources,
            query_id=result.query_id,
            timestamp=datetime.fromisoformat(result.timestamp),
            drill_down_available=result.drill_down_available,
            recommendations=result.recommendations,
        )

        # Log to audit
        response_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        audit_service = AuditService(neo4j)
        audit_service.log_query(
            user_id=current_user.id,
            client_id=request.client_id,
            query_text=request.query,
            response_text=result.answer[:500],  # Truncate for storage
            confidence_score=result.confidence.overall,
            response_time_ms=response_time_ms,
            session_id=request.session_id,
        )

        logger.info(
            f"Query processed in {response_time_ms}ms: {request.query[:50]}... "
            f"(confidence: {result.confidence.level.value})"
        )

        return response

    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query processing failed: {str(e)}",
        )


@router.post("/drill-down", response_model=DrillDownResponse)
async def drill_down(
    request: DrillDownRequest,
    current_user: CurrentUser,
    neo4j: Neo4jDep,
) -> DrillDownResponse:
    """Get detailed drill-down data for an entity.

    Only available to analysts and admins.
    """
    # Verify client access
    await verify_client_access(request.client_id, current_user)

    # Check role (analysts and admins only)
    if current_user.role.value not in ["analyst", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Drill-down access requires analyst or admin role",
        )

    start_date, end_date = request.date_range or ("2024-01-01", "2024-12-31")

    if request.entity_type == "campaign":
        # Get campaign details
        entity_query = """
        MATCH (c:Client {id: $client_id})-[:OWNS]->(camp:Campaign {id: $entity_id})
        RETURN camp
        """
        entity_result = neo4j.execute_query(
            entity_query,
            {"client_id": request.client_id, "entity_id": request.entity_id},
        )

        if not entity_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found",
            )

        entity = entity_result[0]["camp"]

        # Get child ad sets
        children_query = """
        MATCH (camp:Campaign {id: $entity_id})-[:CONTAINS]->(adset:AdSet)
        OPTIONAL MATCH (m:Metric {entity_type: 'adset', entity_id: adset.id})
        WHERE m.date >= date($start_date) AND m.date <= date($end_date)
        WITH adset, sum(m.impressions) AS impressions, sum(m.clicks) AS clicks,
             sum(m.conversions) AS conversions, sum(m.spend) AS spend
        RETURN adset.id AS id, adset.name AS name, adset.status AS status,
               impressions, clicks, conversions, spend
        """
        children = neo4j.execute_query(
            children_query,
            {
                "entity_id": request.entity_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )

        # Get aggregated metrics
        metrics_query = """
        MATCH (m:Metric {entity_type: 'campaign', entity_id: $entity_id})
        WHERE m.date >= date($start_date) AND m.date <= date($end_date)
        RETURN sum(m.impressions) AS impressions,
               sum(m.clicks) AS clicks,
               sum(m.conversions) AS conversions,
               sum(m.spend) AS spend,
               sum(m.revenue) AS revenue
        """
        metrics_result = neo4j.execute_query(
            metrics_query,
            {
                "entity_id": request.entity_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )

        metrics = metrics_result[0] if metrics_result else {}

        # Get daily breakdown
        breakdown_query = """
        MATCH (m:Metric {entity_type: 'campaign', entity_id: $entity_id})
        WHERE m.date >= date($start_date) AND m.date <= date($end_date)
        RETURN m.date AS date, m.impressions AS impressions, m.clicks AS clicks,
               m.conversions AS conversions, m.spend AS spend, m.revenue AS revenue
        ORDER BY date
        """
        breakdown = neo4j.execute_query(
            breakdown_query,
            {
                "entity_id": request.entity_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )

        return DrillDownResponse(
            entity=entity,
            children=children,
            metrics=metrics,
            breakdown=breakdown,
        )

    elif request.entity_type == "adset":
        # Similar logic for ad set drill-down to ads
        entity_query = """
        MATCH (adset:AdSet {id: $entity_id, client_id: $client_id})
        RETURN adset
        """
        entity_result = neo4j.execute_query(
            entity_query,
            {"client_id": request.client_id, "entity_id": request.entity_id},
        )

        if not entity_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ad set not found",
            )

        entity = entity_result[0]["adset"]

        # Get child ads
        children_query = """
        MATCH (adset:AdSet {id: $entity_id})-[:CONTAINS]->(ad:Ad)
        OPTIONAL MATCH (m:Metric {entity_type: 'ad', entity_id: ad.id})
        WHERE m.date >= date($start_date) AND m.date <= date($end_date)
        WITH ad, sum(m.impressions) AS impressions, sum(m.clicks) AS clicks,
             sum(m.conversions) AS conversions, sum(m.spend) AS spend
        RETURN ad.id AS id, ad.name AS name, ad.headline AS headline,
               ad.status AS status, impressions, clicks, conversions, spend
        """
        children = neo4j.execute_query(
            children_query,
            {
                "entity_id": request.entity_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )

        return DrillDownResponse(
            entity=entity,
            children=children,
            metrics={},
            breakdown=[],
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported entity type: {request.entity_type}",
        )


@router.delete("/session/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def clear_session(
    session_id: str,
    current_user: CurrentUser,
    graphrag: GraphRAGDep,
) -> None:
    """Clear conversation history for a session."""
    graphrag.clear_session(session_id)
    logger.info(f"Session cleared: {session_id} by user {current_user.email}")
