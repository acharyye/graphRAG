"""Audit logging service for query tracking and compliance."""

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from src.graph.client import Neo4jClient, get_neo4j_client

logger = logging.getLogger(__name__)


class AuditService:
    """Service for logging and retrieving audit records."""

    def __init__(self, neo4j_client: Neo4jClient | None = None):
        """Initialize audit service.

        Args:
            neo4j_client: Neo4j client instance.
        """
        self._neo4j = neo4j_client or get_neo4j_client()

    def log_query(
        self,
        user_id: str,
        client_id: str,
        query_text: str,
        response_text: str,
        confidence_score: float,
        response_time_ms: int,
        session_id: str | None = None,
    ) -> str:
        """Log a query to the audit trail.

        Args:
            user_id: User who made the query.
            client_id: Client context.
            query_text: The query text.
            response_text: The response (truncated).
            confidence_score: Confidence score of the answer.
            response_time_ms: Response time in milliseconds.
            session_id: Optional session identifier.

        Returns:
            Audit log ID.
        """
        audit_id = str(uuid4())
        timestamp = datetime.utcnow().isoformat()

        query = """
        CREATE (a:AuditLog {
            id: $id,
            user_id: $user_id,
            client_id: $client_id,
            query_text: $query_text,
            response_text: $response_text,
            confidence_score: $confidence_score,
            response_time_ms: $response_time_ms,
            session_id: $session_id,
            timestamp: datetime($timestamp)
        })
        RETURN a.id AS id
        """

        params = {
            "id": audit_id,
            "user_id": user_id,
            "client_id": client_id,
            "query_text": query_text[:1000],  # Limit query text
            "response_text": response_text[:2000],  # Limit response text
            "confidence_score": confidence_score,
            "response_time_ms": response_time_ms,
            "session_id": session_id,
            "timestamp": timestamp,
        }

        self._neo4j.execute_query(query, params)
        logger.debug(f"Audit log created: {audit_id}")
        return audit_id

    def log_action(
        self,
        user_id: str,
        action_type: str,
        resource_type: str,
        resource_id: str,
        details: dict[str, Any] | None = None,
        client_id: str | None = None,
    ) -> str:
        """Log a general action (create, update, delete, etc.).

        Args:
            user_id: User who performed the action.
            action_type: Type of action (create, update, delete, export, etc.).
            resource_type: Type of resource affected.
            resource_id: ID of the resource.
            details: Additional details about the action.
            client_id: Client context if applicable.

        Returns:
            Audit log ID.
        """
        import json

        audit_id = str(uuid4())
        timestamp = datetime.utcnow().isoformat()

        query = """
        CREATE (a:AuditLog {
            id: $id,
            user_id: $user_id,
            client_id: $client_id,
            action_type: $action_type,
            resource_type: $resource_type,
            resource_id: $resource_id,
            details: $details,
            timestamp: datetime($timestamp)
        })
        RETURN a.id AS id
        """

        params = {
            "id": audit_id,
            "user_id": user_id,
            "client_id": client_id,
            "action_type": action_type,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": json.dumps(details) if details else None,
            "timestamp": timestamp,
        }

        self._neo4j.execute_query(query, params)
        logger.debug(f"Action audit log created: {audit_id} ({action_type} {resource_type})")
        return audit_id

    def get_logs_by_client(
        self,
        client_id: str,
        start_date: str,
        end_date: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get audit logs for a client.

        Args:
            client_id: Client ID.
            start_date: Start date (YYYY-MM-DD).
            end_date: End date (YYYY-MM-DD).
            limit: Maximum records to return.

        Returns:
            List of audit log records.
        """
        query = """
        MATCH (a:AuditLog {client_id: $client_id})
        WHERE a.timestamp >= datetime($start_date)
            AND a.timestamp <= datetime($end_date + 'T23:59:59')
        RETURN a
        ORDER BY a.timestamp DESC
        LIMIT $limit
        """

        result = self._neo4j.execute_query(
            query,
            {
                "client_id": client_id,
                "start_date": start_date,
                "end_date": end_date,
                "limit": limit,
            },
        )

        return [r["a"] for r in result]

    def get_logs_by_user(
        self,
        user_id: str,
        start_date: str,
        end_date: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get audit logs for a user.

        Args:
            user_id: User ID.
            start_date: Start date (YYYY-MM-DD).
            end_date: End date (YYYY-MM-DD).
            limit: Maximum records to return.

        Returns:
            List of audit log records.
        """
        query = """
        MATCH (a:AuditLog {user_id: $user_id})
        WHERE a.timestamp >= datetime($start_date)
            AND a.timestamp <= datetime($end_date + 'T23:59:59')
        RETURN a
        ORDER BY a.timestamp DESC
        LIMIT $limit
        """

        result = self._neo4j.execute_query(
            query,
            {
                "user_id": user_id,
                "start_date": start_date,
                "end_date": end_date,
                "limit": limit,
            },
        )

        return [r["a"] for r in result]

    def get_query_stats(
        self,
        client_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Get query statistics.

        Args:
            client_id: Optional client ID filter.
            start_date: Optional start date.
            end_date: Optional end date.

        Returns:
            Dictionary with query statistics.
        """
        where_clauses = []
        params: dict[str, Any] = {}

        if client_id:
            where_clauses.append("a.client_id = $client_id")
            params["client_id"] = client_id

        if start_date:
            where_clauses.append("a.timestamp >= datetime($start_date)")
            params["start_date"] = start_date

        if end_date:
            where_clauses.append("a.timestamp <= datetime($end_date + 'T23:59:59')")
            params["end_date"] = end_date

        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        query = f"""
        MATCH (a:AuditLog)
        {where_clause}
        WHERE a.query_text IS NOT NULL
        RETURN
            count(a) AS total_queries,
            avg(a.confidence_score) AS avg_confidence,
            avg(a.response_time_ms) AS avg_response_time_ms,
            count(DISTINCT a.user_id) AS unique_users,
            count(DISTINCT a.session_id) AS unique_sessions
        """

        result = self._neo4j.execute_query(query, params)

        if result:
            stats = result[0]
            return {
                "total_queries": stats.get("total_queries", 0),
                "avg_confidence": round(stats.get("avg_confidence", 0) or 0, 3),
                "avg_response_time_ms": round(stats.get("avg_response_time_ms", 0) or 0, 1),
                "unique_users": stats.get("unique_users", 0),
                "unique_sessions": stats.get("unique_sessions", 0),
            }

        return {
            "total_queries": 0,
            "avg_confidence": 0,
            "avg_response_time_ms": 0,
            "unique_users": 0,
            "unique_sessions": 0,
        }

    def cleanup_old_logs(self, retention_days: int) -> int:
        """Delete audit logs older than retention period.

        Args:
            retention_days: Number of days to retain.

        Returns:
            Number of deleted records.
        """
        query = """
        MATCH (a:AuditLog)
        WHERE a.timestamp < datetime() - duration({days: $retention_days})
        WITH a LIMIT 10000
        DELETE a
        RETURN count(*) AS deleted
        """

        result = self._neo4j.execute_query(query, {"retention_days": retention_days})
        deleted = result[0]["deleted"] if result else 0

        logger.info(f"Cleaned up {deleted} old audit logs (retention: {retention_days} days)")
        return deleted

    def export_logs(
        self,
        client_id: str,
        start_date: str,
        end_date: str,
        format: str = "json",
    ) -> str | bytes:
        """Export audit logs for compliance.

        Args:
            client_id: Client ID.
            start_date: Start date.
            end_date: End date.
            format: Export format (json or csv).

        Returns:
            Exported data.
        """
        logs = self.get_logs_by_client(client_id, start_date, end_date, limit=10000)

        if format == "csv":
            import csv
            import io

            output = io.StringIO()
            if logs:
                writer = csv.DictWriter(output, fieldnames=logs[0].keys())
                writer.writeheader()
                writer.writerows(logs)
            return output.getvalue()

        else:  # json
            import json

            return json.dumps(logs, default=str, indent=2)
