"""The Databricks Engine (Composition Module)

Isolates authentication and API connection logic"""

from sqlalchemy import create_engine
from sqlalchemy.engine import URL, Engine

from AnalystStack.exceptions.errors import ConnectionError
from AnalystStack.utils.logging import get_logger

logger = get_logger(__name__)


class DatabricksClientWrapper:
    """Builds and wraps a SQLAlchemy ``Engine`` for Databricks via the
    ``databricks-sqlalchemy`` dialect.

    Owns the low-level connection: constructing the SQLAlchemy ``URL``, creating the
    ``Engine``, and eagerly opening a test connection so failures surface immediately at
    construction time rather than on the first query.

    Note:
        `catalog` and `schema` are bound into the SQLAlchemy connection URL, so -- unlike
        BigQuery/Postgres -- a single wrapper (and therefore a single `DatabricksConnector`)
        is scoped to exactly one catalog and schema for its lifetime.

    Attributes:
        engine: The underlying SQLAlchemy ``Engine``, used by
            `AnalystStack.connectors.databricks.query.QueryManager` and the
            metadata/profiling managers to run queries.
    """

    def __init__(self, server_hostname: str, http_path: str, access_token: str, catalog: str, schema: str):
        """Creates and validates the SQLAlchemy engine for a Databricks SQL warehouse.

        Args:
            server_hostname: The Databricks workspace hostname.
            http_path: The HTTP path of the SQL warehouse/cluster to connect to.
            access_token: A Databricks personal access token, sent as the connection
                password (the connection username is always ``"token"``).
            catalog: The Unity Catalog catalog to bind the connection to.
            schema: The schema to bind the connection to.

        Raises:
            AnalystStack.exceptions.errors.ConnectionError: If constructing the engine or
                opening the test connection fails (e.g. an invalid token or unreachable
                warehouse).
        """
        self.server_hostname = server_hostname
        self.http_path = http_path
        self.access_token = access_token
        self.catalog = catalog
        self.schema = schema

        try:
            url = URL.create(
                "databricks",
                username="token",
                password=access_token,
                host=server_hostname,
                query={"http_path": http_path, "catalog": catalog, "schema": schema},
            )
            self._engine: Engine = create_engine(url)
            with self._engine.connect():
                pass
            logger.info(f"Databricks client initialized for server hostname {self.server_hostname}")
        except Exception as e:
            logger.error(f"Failed to initialize Databricks client: {e}")
            raise ConnectionError(f"Client initialization failed: {e}") from e

    @property
    def engine(self) -> Engine:
        """The underlying SQLAlchemy `Engine` used to run reads and writes."""
        return self._engine
