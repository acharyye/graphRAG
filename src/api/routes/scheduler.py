"""Scheduled reports and sync management routes."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.api.dependencies import CurrentUser, Neo4jDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/schedules", tags=["Scheduled Tasks"])


def _convert_neo4j_datetime(value):
    if value is None:
        return None
    if hasattr(value, 'to_native'):
        return str(value.to_native())
    return str(value) if value else None


# --- Models ---

class ReportScheduleCreate(BaseModel):
    client_id: str
    frequency: str = Field(..., pattern="^(daily|weekly|monthly)$")
    report_type: str = "monthly"
    format: str = Field(default="pdf", pattern="^(pdf|excel|csv)$")
    email: str
    sections: list[str] = ["summary", "campaigns", "trends", "recommendations"]
    time_of_day: str = Field(default="09:00", pattern=r"^\d{2}:\d{2}$")
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    day_of_month: int | None = Field(default=None, ge=1, le=28)
    enabled: bool = True


class ReportScheduleResponse(BaseModel):
    id: str
    client_id: str
    client_name: str | None = None
    frequency: str
    report_type: str
    format: str
    email: str
    sections: list[str]
    time_of_day: str
    day_of_week: int | None = None
    day_of_month: int | None = None
    enabled: bool
    last_run: str | None = None
    next_run: str | None = None
    created_at: str | None = None


class SyncScheduleCreate(BaseModel):
    client_id: str
    platform: str = Field(..., pattern="^(google_ads|meta)$")
    account_id: str
    frequency_hours: int = Field(default=24, ge=1, le=168)
    enabled: bool = True


class SyncScheduleResponse(BaseModel):
    id: str
    client_id: str
    platform: str
    account_id: str
    frequency_hours: int
    enabled: bool
    last_run: str | None = None
    next_run: str | None = None
    status: str | None = None


# --- Report Schedules ---

@router.post("/reports", response_model=ReportScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_report_schedule(
    schedule: ReportScheduleCreate,
    current_user: CurrentUser,
    neo4j: Neo4jDep,
) -> ReportScheduleResponse:
    """Create a scheduled report."""
    import uuid

    schedule_id = str(uuid.uuid4())

    # Get client name
    client_result = neo4j.execute_query(
        "MATCH (c:Client {id: $client_id}) RETURN c.name as name",
        {"client_id": schedule.client_id},
    )
    client_name = client_result[0]["name"] if client_result else None

    neo4j.execute_query("""
        CREATE (s:ReportSchedule {
            id: $id,
            client_id: $client_id,
            frequency: $frequency,
            report_type: $report_type,
            format: $format,
            email: $email,
            sections: $sections,
            time_of_day: $time_of_day,
            day_of_week: $day_of_week,
            day_of_month: $day_of_month,
            enabled: $enabled,
            created_by: $created_by,
            created_at: datetime(),
            updated_at: datetime()
        })
    """, {
        "id": schedule_id,
        "client_id": schedule.client_id,
        "frequency": schedule.frequency,
        "report_type": schedule.report_type,
        "format": schedule.format,
        "email": schedule.email,
        "sections": schedule.sections,
        "time_of_day": schedule.time_of_day,
        "day_of_week": schedule.day_of_week,
        "day_of_month": schedule.day_of_month,
        "enabled": schedule.enabled,
        "created_by": current_user.email,
    })

    logger.info(f"Report schedule created: {schedule_id} for client {schedule.client_id}")

    return ReportScheduleResponse(
        id=schedule_id,
        client_id=schedule.client_id,
        client_name=client_name,
        frequency=schedule.frequency,
        report_type=schedule.report_type,
        format=schedule.format,
        email=schedule.email,
        sections=schedule.sections,
        time_of_day=schedule.time_of_day,
        day_of_week=schedule.day_of_week,
        day_of_month=schedule.day_of_month,
        enabled=schedule.enabled,
    )


@router.get("/reports", response_model=list[ReportScheduleResponse])
async def list_report_schedules(
    current_user: CurrentUser,
    neo4j: Neo4jDep,
    client_id: str | None = None,
) -> list[ReportScheduleResponse]:
    """List all report schedules."""
    if client_id:
        result = neo4j.execute_query("""
            MATCH (s:ReportSchedule {client_id: $client_id})
            OPTIONAL MATCH (c:Client {id: s.client_id})
            RETURN s, c.name as client_name
            ORDER BY s.created_at DESC
        """, {"client_id": client_id})
    else:
        result = neo4j.execute_query("""
            MATCH (s:ReportSchedule)
            OPTIONAL MATCH (c:Client {id: s.client_id})
            RETURN s, c.name as client_name
            ORDER BY s.created_at DESC
        """)

    schedules = []
    if result:
        for r in result:
            s = r["s"]
            schedules.append(ReportScheduleResponse(
                id=s["id"],
                client_id=s["client_id"],
                client_name=r.get("client_name"),
                frequency=s["frequency"],
                report_type=s.get("report_type", "monthly"),
                format=s.get("format", "pdf"),
                email=s["email"],
                sections=list(s.get("sections", [])),
                time_of_day=s.get("time_of_day", "09:00"),
                day_of_week=s.get("day_of_week"),
                day_of_month=s.get("day_of_month"),
                enabled=s.get("enabled", True),
                last_run=_convert_neo4j_datetime(s.get("last_run")),
                next_run=_convert_neo4j_datetime(s.get("next_run")),
                created_at=_convert_neo4j_datetime(s.get("created_at")),
            ))

    return schedules


@router.patch("/reports/{schedule_id}")
async def update_report_schedule(
    schedule_id: str,
    enabled: bool,
    current_user: CurrentUser,
    neo4j: Neo4jDep,
) -> dict[str, str]:
    """Enable or disable a report schedule."""
    result = neo4j.execute_query("""
        MATCH (s:ReportSchedule {id: $id})
        SET s.enabled = $enabled, s.updated_at = datetime()
        RETURN s.id as id
    """, {"id": schedule_id, "enabled": enabled})

    if not result:
        raise HTTPException(status_code=404, detail="Schedule not found")

    action = "enabled" if enabled else "disabled"
    logger.info(f"Report schedule {schedule_id} {action}")
    return {"status": action, "schedule_id": schedule_id}


@router.delete("/reports/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report_schedule(
    schedule_id: str,
    current_user: CurrentUser,
    neo4j: Neo4jDep,
) -> None:
    """Delete a report schedule."""
    neo4j.execute_query(
        "MATCH (s:ReportSchedule {id: $id}) DELETE s",
        {"id": schedule_id},
    )
    logger.info(f"Report schedule deleted: {schedule_id}")


# --- Sync Schedules ---

@router.post("/sync", response_model=SyncScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_sync_schedule(
    schedule: SyncScheduleCreate,
    current_user: CurrentUser,
    neo4j: Neo4jDep,
) -> SyncScheduleResponse:
    """Create a data sync schedule."""
    import uuid

    schedule_id = str(uuid.uuid4())

    neo4j.execute_query("""
        CREATE (s:SyncSchedule {
            id: $id,
            client_id: $client_id,
            platform: $platform,
            account_id: $account_id,
            frequency_hours: $frequency_hours,
            enabled: $enabled,
            created_by: $created_by,
            created_at: datetime(),
            updated_at: datetime()
        })
    """, {
        "id": schedule_id,
        "client_id": schedule.client_id,
        "platform": schedule.platform,
        "account_id": schedule.account_id,
        "frequency_hours": schedule.frequency_hours,
        "enabled": schedule.enabled,
        "created_by": current_user.email,
    })

    logger.info(f"Sync schedule created: {schedule_id}")

    return SyncScheduleResponse(
        id=schedule_id,
        client_id=schedule.client_id,
        platform=schedule.platform,
        account_id=schedule.account_id,
        frequency_hours=schedule.frequency_hours,
        enabled=schedule.enabled,
    )


@router.get("/sync", response_model=list[SyncScheduleResponse])
async def list_sync_schedules(
    current_user: CurrentUser,
    neo4j: Neo4jDep,
) -> list[SyncScheduleResponse]:
    """List all sync schedules."""
    result = neo4j.execute_query("""
        MATCH (s:SyncSchedule)
        RETURN s
        ORDER BY s.created_at DESC
    """)

    schedules = []
    if result:
        for r in result:
            s = r["s"]
            schedules.append(SyncScheduleResponse(
                id=s["id"],
                client_id=s["client_id"],
                platform=s["platform"],
                account_id=s["account_id"],
                frequency_hours=s.get("frequency_hours", 24),
                enabled=s.get("enabled", True),
                last_run=_convert_neo4j_datetime(s.get("last_run")),
                next_run=_convert_neo4j_datetime(s.get("next_run")),
                status=s.get("status"),
            ))

    return schedules


@router.delete("/sync/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sync_schedule(
    schedule_id: str,
    current_user: CurrentUser,
    neo4j: Neo4jDep,
) -> None:
    """Delete a sync schedule."""
    neo4j.execute_query(
        "MATCH (s:SyncSchedule {id: $id}) DELETE s",
        {"id": schedule_id},
    )
    logger.info(f"Sync schedule deleted: {schedule_id}")


# --- Email Delivery ---

@router.post("/reports/{schedule_id}/send-now")
async def send_report_now(
    schedule_id: str,
    current_user: CurrentUser,
    neo4j: Neo4jDep,
) -> dict[str, Any]:
    """Manually trigger sending a scheduled report now."""
    result = neo4j.execute_query("""
        MATCH (s:ReportSchedule {id: $id})
        RETURN s
    """, {"id": schedule_id})

    if not result:
        raise HTTPException(status_code=404, detail="Schedule not found")

    schedule = result[0]["s"]
    email_result = await _send_report_email(schedule, neo4j)

    # Update last_run
    neo4j.execute_query("""
        MATCH (s:ReportSchedule {id: $id})
        SET s.last_run = datetime()
    """, {"id": schedule_id})

    return email_result


async def _send_report_email(schedule, neo4j) -> dict[str, Any]:
    """Generate and send a report via email."""
    from config.settings import get_settings
    settings = get_settings()

    email = schedule.get("email", "")
    client_id = schedule.get("client_id", "")
    report_format = schedule.get("format", "pdf")

    # Get client name
    client_result = neo4j.execute_query(
        "MATCH (c:Client {id: $id}) RETURN c.name as name",
        {"id": client_id},
    )
    client_name = client_result[0]["name"] if client_result else "Unknown Client"

    if settings.email_configured:
        try:
            import sendgrid
            from sendgrid.helpers.mail import Mail, Content

            sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)

            message = Mail(
                from_email=settings.SENDGRID_FROM_EMAIL,
                to_emails=email,
                subject=f"Marketing Report - {client_name} ({schedule.get('frequency', 'manual').title()})",
                plain_text_content=Content(
                    "text/plain",
                    f"Your {schedule.get('frequency', '')} marketing report for {client_name} is ready.\n\n"
                    f"Report type: {schedule.get('report_type', 'monthly')}\n"
                    f"Format: {report_format.upper()}\n\n"
                    "Log in to the Marketing GraphRAG dashboard to view and download the full report.\n\n"
                    "---\nThis is an automated report from Marketing GraphRAG."
                ),
            )

            response = sg.send(message)
            logger.info(f"Report email sent to {email}: status {response.status_code}")

            return {
                "status": "sent",
                "email": email,
                "client": client_name,
                "status_code": response.status_code,
            }
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return {"status": "failed", "error": str(e)}
    else:
        logger.info(f"Email not configured. Would send report to {email} for {client_name}")
        return {
            "status": "skipped",
            "reason": "SendGrid not configured. Set SENDGRID_API_KEY and SENDGRID_FROM_EMAIL in .env",
            "email": email,
            "client": client_name,
        }
