"""Data ingestion API routes."""

import logging
from datetime import date
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, status

from src.api.dependencies import AdminUser, CurrentUser, Neo4jDep, verify_client_access
from src.api.models import ClientCreate, ClientListResponse, ClientResponse, ClientUpdate
from src.connectors import GoogleAdsConnector, MetaAdsConnector, MockDataGenerator
from src.graph.ingest import DataIngester

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["Data Ingestion"])


@router.post("/clients", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    client: ClientCreate,
    current_user: AdminUser,
    neo4j: Neo4jDep,
) -> ClientResponse:
    """Create a new client (admin only)."""
    ingester = DataIngester(neo4j)

    client_data = {
        "name": client.name,
        "industry": client.industry,
        "contract_start": client.contract_start.isoformat(),
        "budget": client.budget,
        "budget_currency": client.budget_currency,
        "data_retention_days": client.data_retention_days,
        "status": "active",
    }

    client_id = ingester.ingest_client(client_data)

    # Fetch created client
    result = neo4j.execute_query(
        "MATCH (c:Client {id: $id}) RETURN c",
        {"id": client_id},
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create client",
        )

    c = result[0]["c"]
    logger.info(f"Client created: {client.name} ({client_id})")

    return ClientResponse(
        id=c["id"],
        name=c["name"],
        industry=c.get("industry", "Unknown"),
        budget=c.get("budget", 0),
        budget_currency=c.get("budget_currency", "USD"),
        data_retention_days=c.get("data_retention_days", 365),
        contract_start=c.get("contract_start", date.today()),
        status=c.get("status", "active"),
        created_at=c.get("created_at"),
        updated_at=c.get("updated_at"),
    )


@router.get("/clients", response_model=ClientListResponse)
async def list_clients(
    current_user: CurrentUser,
    neo4j: Neo4jDep,
) -> ClientListResponse:
    """List clients accessible to the current user."""
    if current_user.role.value == "admin":
        # Admins see all clients
        result = neo4j.execute_query(
            "MATCH (c:Client) RETURN c ORDER BY c.name"
        )
    else:
        # Other users see only their assigned clients
        result = neo4j.execute_query(
            "MATCH (c:Client) WHERE c.id IN $client_ids RETURN c ORDER BY c.name",
            {"client_ids": current_user.client_ids},
        )

    clients = []
    for r in result:
        c = r["c"]
        clients.append(
            ClientResponse(
                id=c["id"],
                name=c["name"],
                industry=c.get("industry", "Unknown"),
                budget=c.get("budget", 0),
                budget_currency=c.get("budget_currency", "USD"),
                data_retention_days=c.get("data_retention_days", 365),
                contract_start=c.get("contract_start", date.today()),
                status=c.get("status", "active"),
                created_at=c.get("created_at"),
                updated_at=c.get("updated_at"),
            )
        )

    return ClientListResponse(clients=clients, total=len(clients))


@router.patch("/clients/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: str,
    update: ClientUpdate,
    current_user: AdminUser,
    neo4j: Neo4jDep,
) -> ClientResponse:
    """Update client details (admin only)."""
    # Build update query dynamically
    updates = []
    params = {"client_id": client_id}

    if update.name is not None:
        updates.append("c.name = $name")
        params["name"] = update.name
    if update.industry is not None:
        updates.append("c.industry = $industry")
        params["industry"] = update.industry
    if update.budget is not None:
        updates.append("c.budget = $budget")
        params["budget"] = update.budget
    if update.budget_currency is not None:
        updates.append("c.budget_currency = $budget_currency")
        params["budget_currency"] = update.budget_currency
    if update.data_retention_days is not None:
        updates.append("c.data_retention_days = $data_retention_days")
        params["data_retention_days"] = update.data_retention_days
    if update.status is not None:
        updates.append("c.status = $status")
        params["status"] = update.status

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    updates.append("c.updated_at = datetime()")

    query = f"""
    MATCH (c:Client {{id: $client_id}})
    SET {', '.join(updates)}
    RETURN c
    """

    result = neo4j.execute_query(query, params)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    c = result[0]["c"]
    logger.info(f"Client updated: {client_id}")

    return ClientResponse(
        id=c["id"],
        name=c["name"],
        industry=c.get("industry", "Unknown"),
        budget=c.get("budget", 0),
        budget_currency=c.get("budget_currency", "USD"),
        data_retention_days=c.get("data_retention_days", 365),
        contract_start=c.get("contract_start", date.today()),
        status=c.get("status", "active"),
        created_at=c.get("created_at"),
        updated_at=c.get("updated_at"),
    )


@router.delete("/clients/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: str,
    current_user: AdminUser,
    neo4j: Neo4jDep,
) -> None:
    """Delete a client and all associated data (GDPR compliance)."""
    result = neo4j.delete_client_data(client_id)
    logger.info(f"Client deleted: {client_id} (nodes: {result.get('nodes_deleted', 0)})")


@router.post("/sync/google-ads/{client_id}")
async def sync_google_ads(
    client_id: str,
    start_date: str,
    end_date: str,
    account_id: str,
    background_tasks: BackgroundTasks,
    current_user: AdminUser,
    neo4j: Neo4jDep,
) -> dict[str, Any]:
    """Trigger Google Ads data sync for a client."""
    connector = GoogleAdsConnector()

    if not connector.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Ads API is not configured",
        )

    # Run sync in background
    background_tasks.add_task(
        _run_sync,
        connector,
        account_id,
        client_id,
        date.fromisoformat(start_date),
        date.fromisoformat(end_date),
        neo4j,
    )

    return {
        "status": "sync_started",
        "client_id": client_id,
        "platform": "google_ads",
        "account_id": account_id,
    }


@router.post("/sync/meta/{client_id}")
async def sync_meta_ads(
    client_id: str,
    start_date: str,
    end_date: str,
    account_id: str,
    background_tasks: BackgroundTasks,
    current_user: AdminUser,
    neo4j: Neo4jDep,
) -> dict[str, Any]:
    """Trigger Meta Ads data sync for a client."""
    connector = MetaAdsConnector()

    if not connector.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Meta Marketing API is not configured",
        )

    # Run sync in background
    background_tasks.add_task(
        _run_sync,
        connector,
        account_id,
        client_id,
        date.fromisoformat(start_date),
        date.fromisoformat(end_date),
        neo4j,
    )

    return {
        "status": "sync_started",
        "client_id": client_id,
        "platform": "meta",
        "account_id": account_id,
    }


@router.post("/mock/{client_id}")
async def ingest_mock_data(
    client_id: str,
    current_user: AdminUser,
    neo4j: Neo4jDep,
    campaigns: int = 4,
    days: int = 90,
) -> dict[str, Any]:
    """Generate and ingest mock data for a client (development only)."""
    generator = MockDataGenerator()
    ingester = DataIngester(neo4j)

    # Generate data
    campaigns_data = generator.generate_campaigns(client_id, campaigns)

    total_metrics = 0
    for campaign in campaigns_data:
        campaign_id = ingester.ingest_campaign(campaign, client_id)

        # Generate ad sets
        adsets = generator.generate_adsets(campaign_id, client_id, 3)
        for adset in adsets:
            adset_id = ingester.ingest_adset(adset, campaign_id, client_id)

            # Generate ads
            ads = generator.generate_ads(adset_id, client_id, 5)
            for ad in ads:
                ingester.ingest_ad(ad, adset_id, client_id)

        # Generate metrics
        metrics = generator.generate_metrics(campaign_id, "campaign", client_id, days)
        ingester.ingest_metrics(metrics, "campaign", campaign_id, client_id)
        total_metrics += len(metrics)

    logger.info(
        f"Mock data ingested for client {client_id}: {len(campaigns_data)} campaigns"
    )

    return {
        "status": "completed",
        "client_id": client_id,
        "campaigns": len(campaigns_data),
        "metrics": total_metrics,
    }


@router.post("/csv/{client_id}")
async def upload_csv(
    client_id: str,
    file: UploadFile,
    current_user: CurrentUser,
    neo4j: Neo4jDep,
) -> dict[str, Any]:
    """Upload CSV data for a client."""
    await verify_client_access(client_id, current_user)

    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV",
        )

    # Read and parse CSV
    import csv
    import io

    content = await file.read()
    text = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))

    ingester = DataIngester(neo4j)
    rows_processed = 0

    for row in reader:
        # Detect row type and ingest
        if "campaign_id" in row and "impressions" in row:
            # Metrics row
            metrics = [
                {
                    "date": row.get("date"),
                    "impressions": int(row.get("impressions", 0)),
                    "clicks": int(row.get("clicks", 0)),
                    "conversions": int(row.get("conversions", 0)),
                    "spend": float(row.get("spend", 0)),
                    "revenue": float(row.get("revenue")) if row.get("revenue") else None,
                    "spend_currency": row.get("currency", "USD"),
                }
            ]
            ingester.ingest_metrics(
                metrics,
                "campaign",
                row["campaign_id"],
                client_id,
            )
        elif "name" in row and "objective" in row:
            # Campaign row
            ingester.ingest_campaign(
                {
                    "name": row["name"],
                    "objective": row.get("objective", "conversions"),
                    "start_date": row.get("start_date"),
                    "end_date": row.get("end_date"),
                    "budget": float(row.get("budget", 0)),
                    "channel": row.get("channel", "google_ads"),
                },
                client_id,
            )

        rows_processed += 1

    logger.info(f"CSV uploaded for client {client_id}: {rows_processed} rows")

    return {
        "status": "completed",
        "client_id": client_id,
        "rows_processed": rows_processed,
        "filename": file.filename,
    }


async def _run_sync(
    connector,
    account_id: str,
    client_id: str,
    start_date: date,
    end_date: date,
    neo4j: Neo4jDep,
) -> None:
    """Background task to run data sync."""
    try:
        data = await connector.sync_all(account_id, client_id, start_date, end_date)

        ingester = DataIngester(neo4j)

        for campaign in data["campaigns"]:
            ingester.ingest_campaign(campaign, client_id)

        for adset in data["adsets"]:
            ingester.ingest_adset(adset, adset["campaign_id"], client_id)

        for ad in data["ads"]:
            ingester.ingest_ad(ad, ad["adset_id"], client_id)

        # Group metrics by entity and ingest
        metrics_by_entity: dict[str, list] = {}
        for m in data["metrics"]:
            key = f"{m['entity_type']}_{m['entity_id']}"
            if key not in metrics_by_entity:
                metrics_by_entity[key] = []
            metrics_by_entity[key].append(m)

        for key, metrics in metrics_by_entity.items():
            entity_type, entity_id = key.split("_", 1)
            ingester.ingest_metrics(metrics, entity_type, entity_id, client_id)

        logger.info(
            f"Sync completed for client {client_id}: "
            f"{len(data['campaigns'])} campaigns, "
            f"{len(data['metrics'])} metrics"
        )

    except Exception as e:
        logger.error(f"Sync failed for client {client_id}: {e}")
