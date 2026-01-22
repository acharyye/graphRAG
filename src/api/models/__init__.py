"""Pydantic models for API requests and responses."""

from .auth import (
    LoginRequest,
    LoginResponse,
    PasswordChangeRequest,
    TokenPayload,
    UserCreate,
    UserResponse,
    UserRole,
    UserUpdate,
)
from .client import (
    ClientCreate,
    ClientListResponse,
    ClientResponse,
    ClientSummary,
    ClientUpdate,
)
from .query import (
    ConfidenceDetails,
    ConfidenceLevel,
    DrillDownRequest,
    DrillDownResponse,
    QueryRequest,
    QueryResponse,
    Source,
)
from .report import (
    DateRange,
    ReportConfig,
    ReportFormat,
    ReportListResponse,
    ReportResponse,
    ReportSection,
    ReportStatus,
    ReportType,
    ScheduledReportConfig,
)

__all__ = [
    # Auth
    "LoginRequest",
    "LoginResponse",
    "PasswordChangeRequest",
    "TokenPayload",
    "UserCreate",
    "UserResponse",
    "UserRole",
    "UserUpdate",
    # Client
    "ClientCreate",
    "ClientListResponse",
    "ClientResponse",
    "ClientSummary",
    "ClientUpdate",
    # Query
    "ConfidenceDetails",
    "ConfidenceLevel",
    "DrillDownRequest",
    "DrillDownResponse",
    "QueryRequest",
    "QueryResponse",
    "Source",
    # Report
    "DateRange",
    "ReportConfig",
    "ReportFormat",
    "ReportListResponse",
    "ReportResponse",
    "ReportSection",
    "ReportStatus",
    "ReportType",
    "ScheduledReportConfig",
]
