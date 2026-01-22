"""Pydantic models for report generation."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ReportType(str, Enum):
    """Types of reports available."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    CUSTOM = "custom"


class ReportFormat(str, Enum):
    """Export formats for reports."""

    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    GOOGLE_DOCS = "google_docs"
    GOOGLE_SHEETS = "google_sheets"


class ReportSection(str, Enum):
    """Sections that can be included in reports."""

    SUMMARY = "summary"
    CAMPAIGNS = "campaigns"
    AD_SETS = "ad_sets"
    ADS = "ads"
    TRENDS = "trends"
    RECOMMENDATIONS = "recommendations"
    CHANNEL_BREAKDOWN = "channel_breakdown"


class DateRange(BaseModel):
    """Date range specification."""

    start: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    end: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")


class ReportConfig(BaseModel):
    """Configuration for report generation."""

    client_id: str = Field(..., description="Client ID for the report")
    report_type: ReportType = Field(default=ReportType.MONTHLY)
    format: ReportFormat = Field(default=ReportFormat.PDF)
    date_range: DateRange = Field(..., description="Report date range")
    sections: list[ReportSection] = Field(
        default_factory=lambda: [
            ReportSection.SUMMARY,
            ReportSection.CAMPAIGNS,
            ReportSection.TRENDS,
        ],
        description="Sections to include",
    )
    include_recommendations: bool = Field(
        default=True, description="Include AI recommendations"
    )
    compare_to_previous: bool = Field(
        default=True, description="Include comparison to previous period"
    )
    campaign_ids: list[str] | None = Field(
        None, description="Specific campaigns to include (all if None)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "client_id": "client_123",
                    "report_type": "monthly",
                    "format": "pdf",
                    "date_range": {"start": "2024-12-01", "end": "2024-12-31"},
                    "sections": ["summary", "campaigns", "trends", "recommendations"],
                    "include_recommendations": True,
                    "compare_to_previous": True,
                }
            ]
        }
    }


class ReportStatus(str, Enum):
    """Report generation status."""

    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportResponse(BaseModel):
    """Response model for report generation."""

    report_id: str = Field(..., description="Unique report identifier")
    status: ReportStatus = Field(..., description="Report generation status")
    client_id: str
    report_type: ReportType
    format: ReportFormat
    date_range: DateRange
    created_at: datetime
    completed_at: datetime | None = None
    download_url: str | None = Field(None, description="URL to download the report")
    file_size_bytes: int | None = None
    error_message: str | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "report_id": "report_abc123",
                    "status": "completed",
                    "client_id": "client_123",
                    "report_type": "monthly",
                    "format": "pdf",
                    "date_range": {"start": "2024-12-01", "end": "2024-12-31"},
                    "created_at": "2024-01-15T10:30:00Z",
                    "completed_at": "2024-01-15T10:31:00Z",
                    "download_url": "/api/reports/report_abc123/download",
                    "file_size_bytes": 524288,
                }
            ]
        }
    }


class ReportListResponse(BaseModel):
    """Response model for report list."""

    reports: list[ReportResponse]
    total: int


class ScheduledReportConfig(BaseModel):
    """Configuration for scheduled reports."""

    client_id: str
    report_type: ReportType
    format: ReportFormat
    schedule: str = Field(
        ...,
        description="Cron expression for schedule",
        pattern=r"^(\*|[0-9,\-\/]+)\s+(\*|[0-9,\-\/]+)\s+(\*|[0-9,\-\/]+)\s+(\*|[0-9,\-\/]+)\s+(\*|[0-9,\-\/]+)$",
    )
    recipients: list[str] = Field(
        default_factory=list, description="Email addresses for delivery"
    )
    slack_channel: str | None = Field(None, description="Slack channel for delivery")
    enabled: bool = True
