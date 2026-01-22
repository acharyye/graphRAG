"""Neo4j client wrapper with connection management and schema initialization."""

import logging
from contextlib import contextmanager
from typing import Any, Generator

from neo4j import GraphDatabase, Session
from neo4j.exceptions import ServiceUnavailable

from config.settings import Settings, get_settings

from .schema import GraphSchema

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Neo4j database client with connection pooling and schema management."""

    def __init__(self, settings: Settings | None = None):
        """Initialize Neo4j client.

        Args:
            settings: Application settings. Uses default if not provided.
        """
        self._settings = settings or get_settings()
        self._driver = None
        self._schema = GraphSchema()

    @property
    def driver(self):
        """Get or create the Neo4j driver."""
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                self._settings.NEO4J_URI,
                auth=(self._settings.NEO4J_USER, self._settings.NEO4J_PASSWORD),
                max_connection_lifetime=3600,
                max_connection_pool_size=50,
                connection_acquisition_timeout=60,
            )
        return self._driver

    def close(self):
        """Close the driver connection."""
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    def verify_connectivity(self) -> bool:
        """Verify database connectivity."""
        try:
            self.driver.verify_connectivity()
            logger.info("Neo4j connection verified")
            return True
        except ServiceUnavailable as e:
            logger.error(f"Neo4j connection failed: {e}")
            return False

    @contextmanager
    def session(self, database: str = "neo4j") -> Generator[Session, None, None]:
        """Get a database session context manager.

        Args:
            database: Database name to connect to.

        Yields:
            Neo4j session.
        """
        session = self.driver.session(database=database)
        try:
            yield session
        finally:
            session.close()

    def initialize_schema(self) -> None:
        """Initialize database schema with constraints and indexes."""
        logger.info("Initializing Neo4j schema...")
        statements = self._schema.get_all_statements()

        with self.session() as session:
            for statement in statements:
                try:
                    session.run(statement)
                    logger.debug(f"Executed: {statement}")
                except Exception as e:
                    logger.warning(f"Schema statement failed (may already exist): {e}")

        # Create channel nodes
        self._create_channels()
        logger.info("Schema initialization complete")

    def _create_channels(self) -> None:
        """Create default channel nodes."""
        channels = [
            {"name": "google_ads", "display_name": "Google Ads"},
            {"name": "meta", "display_name": "Meta (Facebook/Instagram)"},
        ]

        with self.session() as session:
            for channel in channels:
                session.run(
                    """
                    MERGE (c:Channel {name: $name})
                    ON CREATE SET c.display_name = $display_name
                    """,
                    **channel,
                )
        logger.info("Channel nodes created/verified")

    def execute_query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        database: str = "neo4j",
    ) -> list[dict[str, Any]]:
        """Execute a Cypher query and return results.

        Args:
            query: Cypher query string.
            parameters: Query parameters.
            database: Database name.

        Returns:
            List of result records as dictionaries.
        """
        with self.session(database=database) as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

    def execute_write(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        database: str = "neo4j",
    ) -> dict[str, Any]:
        """Execute a write query and return summary.

        Args:
            query: Cypher query string.
            parameters: Query parameters.
            database: Database name.

        Returns:
            Query summary with counters.
        """
        with self.session(database=database) as session:
            result = session.run(query, parameters or {})
            summary = result.consume()
            return {
                "nodes_created": summary.counters.nodes_created,
                "nodes_deleted": summary.counters.nodes_deleted,
                "relationships_created": summary.counters.relationships_created,
                "relationships_deleted": summary.counters.relationships_deleted,
                "properties_set": summary.counters.properties_set,
            }

    def get_client_data(
        self,
        client_id: str,
        include_metrics: bool = True,
    ) -> dict[str, Any]:
        """Get all data for a specific client (with isolation).

        Args:
            client_id: Client UUID.
            include_metrics: Whether to include metrics data.

        Returns:
            Dictionary with client, campaigns, ad sets, ads, and optionally metrics.
        """
        # Get client
        client_query = """
        MATCH (c:Client {id: $client_id})
        RETURN c
        """

        # Get campaigns
        campaigns_query = """
        MATCH (c:Client {id: $client_id})-[:OWNS]->(camp:Campaign)
        RETURN camp
        ORDER BY camp.start_date DESC
        """

        # Get ad sets
        adsets_query = """
        MATCH (c:Client {id: $client_id})-[:OWNS]->(camp:Campaign)-[:CONTAINS]->(adset:AdSet)
        RETURN adset, camp.id AS campaign_id
        """

        # Get ads
        ads_query = """
        MATCH (a:Ad {client_id: $client_id})
        RETURN a
        """

        params = {"client_id": client_id}

        client = self.execute_query(client_query, params)
        campaigns = self.execute_query(campaigns_query, params)
        adsets = self.execute_query(adsets_query, params)
        ads = self.execute_query(ads_query, params)

        result = {
            "client": client[0]["c"] if client else None,
            "campaigns": [r["camp"] for r in campaigns],
            "ad_sets": adsets,
            "ads": [r["a"] for r in ads],
        }

        if include_metrics:
            metrics_query = """
            MATCH (m:Metric {client_id: $client_id})
            RETURN m
            ORDER BY m.date DESC
            LIMIT 1000
            """
            metrics = self.execute_query(metrics_query, params)
            result["metrics"] = [r["m"] for r in metrics]

        return result

    def delete_client_data(self, client_id: str) -> dict[str, Any]:
        """Delete all data for a client (GDPR compliance).

        Args:
            client_id: Client UUID.

        Returns:
            Deletion summary.
        """
        query = """
        MATCH (c:Client {id: $client_id})
        OPTIONAL MATCH (c)-[r1]->(camp:Campaign)
        OPTIONAL MATCH (camp)-[r2]->(adset:AdSet)
        OPTIONAL MATCH (adset)-[r3]->(ad:Ad)
        OPTIONAL MATCH (m:Metric {client_id: $client_id})
        OPTIONAL MATCH (a:AuditLog {client_id: $client_id})
        DETACH DELETE c, camp, adset, ad, m, a
        """
        return self.execute_write(query, {"client_id": client_id})

    def cleanup_old_metrics(self, client_id: str, retention_days: int) -> int:
        """Delete metrics older than retention period.

        Args:
            client_id: Client UUID.
            retention_days: Number of days to retain.

        Returns:
            Number of deleted metrics.
        """
        query = """
        MATCH (m:Metric {client_id: $client_id})
        WHERE m.date < date() - duration({days: $retention_days})
        WITH m LIMIT 10000
        DETACH DELETE m
        RETURN count(*) AS deleted
        """
        result = self.execute_query(
            query, {"client_id": client_id, "retention_days": retention_days}
        )
        return result[0]["deleted"] if result else 0


# Singleton instance
_client: Neo4jClient | None = None


def get_neo4j_client() -> Neo4jClient:
    """Get the Neo4j client singleton."""
    global _client
    if _client is None:
        _client = Neo4jClient()
    return _client
