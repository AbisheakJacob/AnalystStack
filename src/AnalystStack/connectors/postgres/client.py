"""The Postgres Engine (Composition Module)

Isolates authentication and API connection logic"""

from sqlalchemy import create_engine
from sqlalchemy.engine import URL, Engine

from AnalystStack.exceptions.errors import ConnectionError
from AnalystStack.utils.logging import get_logger

logger = get_logger(__name__)


class PostgresClientWrapper:
    """Builds and wraps a SQLAlchemy ``Engine`` for Postgres via the ``psycopg2`` driver.

    Owns the low-level connection: constructing the SQLAlchemy ``URL``, creating the
    ``Engine``, and eagerly opening a test connection so failures surface immediately at
    construction time rather than on the first query.

    Attributes:
        engine: The underlying SQLAlchemy ``Engine``, used by
            `AnalystStack.connectors.postgres.query.QueryManager` and the metadata/profiling
            managers to run queries.
    """

    def __init__(
        self,
        host: str,
        port: str | None = None,
        database: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ):
        """Creates and validates the SQLAlchemy engine for a Postgres database.

        Args:
            host: The Postgres server hostname.
            port: The Postgres server port.
            database: The database to connect to.
            user: The username to authenticate with.
            password: The password to authenticate with.

        Raises:
            AnalystStack.exceptions.errors.ConnectionError: If constructing the engine or
                opening the test connection fails (e.g. invalid credentials or an
                unreachable host).
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password

        try:
            url = URL.create(
                "postgresql+psycopg2",
                username=user,
                password=password,
                host=host,
                port=int(port) if port else None,
                database=database,
            )
            self._engine: Engine = create_engine(url)
            with self._engine.connect():
                pass
            logger.info(f"Postgres client initialized for {self.host}:{self.port} - database: {self.database}")
        except Exception as e:
            logger.error(f"Failed to initialize Postgres client: {e}")
            raise ConnectionError(f"Client initialization failed: {e}") from e

    @property
    def engine(self) -> Engine:
        """The underlying SQLAlchemy `Engine` used to run reads and writes."""
        return self._engine
