"""OAuth and platform connection management routes."""

import logging
import secrets
from typing import Any
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from config.settings import get_settings
from src.api.dependencies import AdminUser, Neo4jDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/connections", tags=["Platform Connections"])


# --- Models ---

class ConnectionStatus(BaseModel):
    platform: str
    connected: bool
    account_id: str | None = None
    account_name: str | None = None
    last_sync: str | None = None
    sync_status: str | None = None


class ConnectionListResponse(BaseModel):
    connections: list[ConnectionStatus]


class ManualTokenInput(BaseModel):
    platform: str
    credentials: dict[str, str]


class SyncRequest(BaseModel):
    platform: str
    client_id: str
    start_date: str
    end_date: str
    account_id: str


# --- Helpers ---

def _convert_neo4j_datetime(value):
    if value is None:
        return None
    if hasattr(value, 'to_native'):
        return str(value.to_native())
    return str(value) if value else None


# --- Google Ads OAuth ---

@router.get("/google-ads/auth-url")
async def get_google_auth_url(
    current_user: AdminUser,
) -> dict[str, str]:
    """Generate Google Ads OAuth authorization URL."""
    settings = get_settings()

    if not settings.google_ads_configured:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google Ads credentials not configured. Set GOOGLE_ADS_CLIENT_ID and GOOGLE_ADS_CLIENT_SECRET in .env",
        )

    state = secrets.token_urlsafe(32)

    params = {
        "client_id": settings.GOOGLE_ADS_CLIENT_ID,
        "redirect_uri": "http://localhost:8000/api/connections/google-ads/callback",
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/adwords",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }

    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    return {"auth_url": auth_url, "state": state}


@router.get("/google-ads/callback")
async def google_ads_callback(
    code: str,
    state: str,
    neo4j: Neo4jDep,
) -> dict[str, str]:
    """Handle Google Ads OAuth callback."""
    import requests

    settings = get_settings()

    # Exchange code for tokens
    token_response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": settings.GOOGLE_ADS_CLIENT_ID,
            "client_secret": settings.GOOGLE_ADS_CLIENT_SECRET,
            "redirect_uri": "http://localhost:8000/api/connections/google-ads/callback",
            "grant_type": "authorization_code",
        },
        timeout=30,
    )

    if token_response.status_code != 200:
        logger.error(f"Google token exchange failed: {token_response.text}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange authorization code for tokens",
        )

    tokens = token_response.json()

    # Store connection in Neo4j
    neo4j.execute_query("""
        MERGE (conn:Connection {platform: 'google_ads'})
        SET conn.refresh_token = $refresh_token,
            conn.access_token = $access_token,
            conn.connected = true,
            conn.connected_at = datetime(),
            conn.updated_at = datetime()
    """, {
        "refresh_token": tokens.get("refresh_token", ""),
        "access_token": tokens.get("access_token", ""),
    })

    logger.info("Google Ads OAuth connection established")
    return {"status": "connected", "platform": "google_ads"}


# --- Meta OAuth ---

@router.get("/meta/auth-url")
async def get_meta_auth_url(
    current_user: AdminUser,
) -> dict[str, str]:
    """Generate Meta OAuth authorization URL."""
    settings = get_settings()

    if not settings.meta_ads_configured:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Meta credentials not configured. Set META_APP_ID and META_APP_SECRET in .env",
        )

    state = secrets.token_urlsafe(32)

    params = {
        "client_id": settings.META_APP_ID,
        "redirect_uri": "http://localhost:8000/api/connections/meta/callback",
        "response_type": "code",
        "scope": "ads_management,ads_read,read_insights",
        "state": state,
    }

    auth_url = f"https://www.facebook.com/v18.0/dialog/oauth?{urlencode(params)}"

    return {"auth_url": auth_url, "state": state}


@router.get("/meta/callback")
async def meta_callback(
    code: str,
    state: str,
    neo4j: Neo4jDep,
) -> dict[str, str]:
    """Handle Meta OAuth callback."""
    import requests

    settings = get_settings()

    # Exchange code for short-lived token
    token_response = requests.get(
        "https://graph.facebook.com/v18.0/oauth/access_token",
        params={
            "client_id": settings.META_APP_ID,
            "client_secret": settings.META_APP_SECRET,
            "redirect_uri": "http://localhost:8000/api/connections/meta/callback",
            "code": code,
        },
        timeout=30,
    )

    if token_response.status_code != 200:
        logger.error(f"Meta token exchange failed: {token_response.text}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange authorization code for tokens",
        )

    short_token = token_response.json().get("access_token")

    # Exchange for long-lived token
    long_token_response = requests.get(
        "https://graph.facebook.com/v18.0/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": settings.META_APP_ID,
            "client_secret": settings.META_APP_SECRET,
            "fb_exchange_token": short_token,
        },
        timeout=30,
    )

    if long_token_response.status_code == 200:
        long_token = long_token_response.json().get("access_token", short_token)
    else:
        long_token = short_token

    # Store connection
    neo4j.execute_query("""
        MERGE (conn:Connection {platform: 'meta'})
        SET conn.access_token = $access_token,
            conn.connected = true,
            conn.connected_at = datetime(),
            conn.updated_at = datetime()
    """, {"access_token": long_token})

    logger.info("Meta OAuth connection established")
    return {"status": "connected", "platform": "meta"}


# --- Manual Token Entry ---

@router.post("/manual")
async def set_manual_credentials(
    input: ManualTokenInput,
    current_user: AdminUser,
    neo4j: Neo4jDep,
) -> dict[str, str]:
    """Manually set platform credentials (for API keys/tokens obtained externally)."""
    platform = input.platform.lower()

    if platform not in ("google_ads", "meta"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Platform must be 'google_ads' or 'meta'",
        )

    # Build SET clause from credentials
    set_parts = ["conn.connected = true", "conn.connected_at = datetime()", "conn.updated_at = datetime()"]
    params = {"platform": platform}

    for key, value in input.credentials.items():
        safe_key = key.replace("-", "_").replace(" ", "_")
        set_parts.append(f"conn.{safe_key} = ${safe_key}")
        params[safe_key] = value

    query = f"""
        MERGE (conn:Connection {{platform: $platform}})
        SET {', '.join(set_parts)}
    """
    neo4j.execute_query(query, params)

    logger.info(f"Manual credentials set for {platform}")
    return {"status": "connected", "platform": platform}


# --- Connection Status ---

@router.get("", response_model=ConnectionListResponse)
async def list_connections(
    current_user: AdminUser,
    neo4j: Neo4jDep,
) -> ConnectionListResponse:
    """List all platform connections and their status."""
    result = neo4j.execute_query("""
        MATCH (conn:Connection)
        RETURN conn.platform as platform,
               conn.connected as connected,
               conn.account_id as account_id,
               conn.account_name as account_name,
               conn.last_sync as last_sync,
               conn.sync_status as sync_status
        ORDER BY conn.platform
    """)

    connections = []
    platforms_found = set()

    if result:
        for r in result:
            platform = r.get("platform")
            platforms_found.add(platform)
            connections.append(ConnectionStatus(
                platform=platform,
                connected=r.get("connected", False),
                account_id=r.get("account_id"),
                account_name=r.get("account_name"),
                last_sync=_convert_neo4j_datetime(r.get("last_sync")),
                sync_status=r.get("sync_status"),
            ))

    # Add missing platforms as disconnected
    for platform in ("google_ads", "meta"):
        if platform not in platforms_found:
            connections.append(ConnectionStatus(
                platform=platform,
                connected=False,
            ))

    return ConnectionListResponse(connections=connections)


@router.delete("/{platform}")
async def disconnect_platform(
    platform: str,
    current_user: AdminUser,
    neo4j: Neo4jDep,
) -> dict[str, str]:
    """Disconnect a platform and remove stored credentials."""
    neo4j.execute_query("""
        MATCH (conn:Connection {platform: $platform})
        DELETE conn
    """, {"platform": platform})

    logger.info(f"Platform disconnected: {platform}")
    return {"status": "disconnected", "platform": platform}


# --- Manual Sync ---

@router.post("/sync")
async def trigger_sync(
    sync_request: SyncRequest,
    current_user: AdminUser,
    neo4j: Neo4jDep,
) -> dict[str, Any]:
    """Trigger a manual data sync for a platform."""
    from datetime import date
    from src.connectors import GoogleAdsConnector, MetaAdsConnector
    from src.graph.ingest import DataIngester

    platform = sync_request.platform.lower()

    if platform == "google_ads":
        connector = GoogleAdsConnector()
    elif platform == "meta":
        connector = MetaAdsConnector()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Platform must be 'google_ads' or 'meta'",
        )

    if not connector.is_configured:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{platform} is not configured. Add credentials first.",
        )

    try:
        # Run sync
        data = await connector.sync_all(
            sync_request.account_id,
            sync_request.client_id,
            date.fromisoformat(sync_request.start_date),
            date.fromisoformat(sync_request.end_date),
        )

        # Ingest data
        ingester = DataIngester(neo4j)

        for campaign in data.get("campaigns", []):
            ingester.ingest_campaign(campaign, sync_request.client_id)
        for adset in data.get("adsets", []):
            ingester.ingest_adset(adset, adset["campaign_id"], sync_request.client_id)
        for ad in data.get("ads", []):
            ingester.ingest_ad(ad, ad["adset_id"], sync_request.client_id)

        metrics_by_entity: dict[str, list] = {}
        for m in data.get("metrics", []):
            key = f"{m['entity_type']}_{m['entity_id']}"
            if key not in metrics_by_entity:
                metrics_by_entity[key] = []
            metrics_by_entity[key].append(m)

        for key, metrics in metrics_by_entity.items():
            entity_type, entity_id = key.split("_", 1)
            ingester.ingest_metrics(metrics, entity_type, entity_id, sync_request.client_id)

        # Update connection last_sync
        neo4j.execute_query("""
            MERGE (conn:Connection {platform: $platform})
            SET conn.last_sync = datetime(),
                conn.sync_status = 'success'
        """, {"platform": platform})

        result = {
            "status": "completed",
            "platform": platform,
            "campaigns": len(data.get("campaigns", [])),
            "adsets": len(data.get("adsets", [])),
            "ads": len(data.get("ads", [])),
            "metrics": len(data.get("metrics", [])),
        }

        logger.info(f"Sync completed for {platform}: {result}")
        return result

    except Exception as e:
        # Update connection with error
        neo4j.execute_query("""
            MERGE (conn:Connection {platform: $platform})
            SET conn.last_sync = datetime(),
                conn.sync_status = $error
        """, {"platform": platform, "error": f"error: {str(e)}"})

        logger.error(f"Sync failed for {platform}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sync failed: {str(e)}",
        )
