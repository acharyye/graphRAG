"""Report generation API routes."""

import logging
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from fastapi.responses import StreamingResponse

from src.api.dependencies import CurrentUser, Neo4jDep, SettingsDep, verify_client_access
from src.api.models import (
    ReportConfig,
    ReportListResponse,
    ReportResponse,
    ReportStatus,
)
from src.services.reports import ReportService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["Reports"])

# In-memory store for report status (use Redis in production)
_report_store: dict[str, ReportResponse] = {}


@router.post("", response_model=ReportResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_report(
    config: ReportConfig,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    neo4j: Neo4jDep,
    settings: SettingsDep,
) -> ReportResponse:
    """Generate a report for a client."""
    await verify_client_access(config.client_id, current_user)

    report_id = str(uuid4())

    report = ReportResponse(
        report_id=report_id,
        status=ReportStatus.PENDING,
        client_id=config.client_id,
        report_type=config.report_type,
        format=config.format,
        date_range=config.date_range,
        created_at=datetime.utcnow(),
    )

    _report_store[report_id] = report

    # Generate report in background
    background_tasks.add_task(
        _generate_report_task,
        report_id,
        config,
        neo4j,
        current_user.id,
    )

    logger.info(f"Report generation started: {report_id}")

    return report


@router.get("", response_model=ReportListResponse)
async def list_reports(
    current_user: CurrentUser,
    client_id: str | None = None,
    limit: int = 20,
) -> ReportListResponse:
    """List generated reports."""
    reports = []

    for report in _report_store.values():
        # Filter by client access
        if report.client_id not in current_user.client_ids:
            if current_user.role.value != "admin":
                continue

        # Filter by client_id if specified
        if client_id and report.client_id != client_id:
            continue

        reports.append(report)

    # Sort by created_at descending
    reports.sort(key=lambda r: r.created_at, reverse=True)

    return ReportListResponse(
        reports=reports[:limit],
        total=len(reports),
    )


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    current_user: CurrentUser,
) -> ReportResponse:
    """Get report status and details."""
    if report_id not in _report_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    report = _report_store[report_id]

    # Verify access
    if report.client_id not in current_user.client_ids:
        if current_user.role.value != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

    return report


@router.get("/{report_id}/download")
async def download_report(
    report_id: str,
    current_user: CurrentUser,
) -> StreamingResponse:
    """Download a generated report."""
    if report_id not in _report_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    report = _report_store[report_id]

    # Verify access
    if report.client_id not in current_user.client_ids:
        if current_user.role.value != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

    if report.status != ReportStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Report is not ready: {report.status}",
        )

    # Get the generated file (in production, this would be from blob storage)
    service = ReportService()
    file_path = service.get_report_path(report_id)

    if not file_path or not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report file not found",
        )

    # Determine content type
    content_types = {
        "pdf": "application/pdf",
        "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "csv": "text/csv",
    }

    content_type = content_types.get(report.format.value, "application/octet-stream")

    def iterfile():
        with open(file_path, "rb") as f:
            yield from f

    filename = f"report_{report.client_id}_{report.date_range.start}_{report.date_range.end}.{report.format.value}"
    if report.format.value == "excel":
        filename = filename.replace(".excel", ".xlsx")

    return StreamingResponse(
        iterfile(),
        media_type=content_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: str,
    current_user: CurrentUser,
) -> None:
    """Delete a generated report."""
    if report_id not in _report_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    report = _report_store[report_id]

    # Verify access (admin only for delete)
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    # Delete file if exists
    service = ReportService()
    file_path = service.get_report_path(report_id)
    if file_path and file_path.exists():
        file_path.unlink()

    del _report_store[report_id]
    logger.info(f"Report deleted: {report_id}")


async def _generate_report_task(
    report_id: str,
    config: ReportConfig,
    neo4j: Neo4jDep,
    user_id: str,
) -> None:
    """Background task to generate a report."""
    try:
        _report_store[report_id].status = ReportStatus.GENERATING

        service = ReportService(neo4j)

        # Generate the report
        result = await service.generate(
            report_id=report_id,
            client_id=config.client_id,
            report_type=config.report_type,
            format=config.format,
            start_date=config.date_range.start,
            end_date=config.date_range.end,
            sections=config.sections,
            include_recommendations=config.include_recommendations,
            compare_to_previous=config.compare_to_previous,
            campaign_ids=config.campaign_ids,
        )

        _report_store[report_id].status = ReportStatus.COMPLETED
        _report_store[report_id].completed_at = datetime.utcnow()
        _report_store[report_id].download_url = f"/api/reports/{report_id}/download"
        _report_store[report_id].file_size_bytes = result.get("file_size", 0)

        logger.info(f"Report generated: {report_id}")

    except Exception as e:
        logger.error(f"Report generation failed: {report_id} - {e}")
        _report_store[report_id].status = ReportStatus.FAILED
        _report_store[report_id].error_message = str(e)
