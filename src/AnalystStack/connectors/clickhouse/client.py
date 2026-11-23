"""The ClickHouse Engine (Composition Module)

Isolates connection logic. Read-only by construction: the server-side ``readonly=1`` setting
is passed on every connection, so the server refuses any write even if one reached it.
"""

from sqlalchemy import create_engine
from sqlalchemy.engine import URL, Engine

from AnalystStack.exceptions.errors import ConnectionError
from AnalystStack.utils.logging import get_logger

logger = get_logger(__name__)

DEFAULT_HTTP_PORT = 8123


class ClickHouseClientWrapper:
    """Builds and wraps a SQLAlchemy ``Engine`` for ClickHouse via ``clickhouse-connect``.

    Uses the ``clickhousedb`` SQLAlchemy dialect that ``clickhouse-connect`` registers (install
    the ``clickhouse`` extra). The connection is HTTP(S), so the port is the HTTP port, not
    the native-protocol port.

    Attributes:
        engine: The underlying SQLAlchemy ``Engine``.
    """

    def __init__(
        self,
        host: str,
        port: str | None = None,
        database: str | None = None,
        user: str | None = None,
        password: str | None = None,
        secure: bool = False,
    ):
        """Creates and validates the SQLAlchemy engine.

        Args:
            host: The ClickHouse server hostname.
            port: The HTTP(S) port (default 8123).
            database: The default database.
            user: The username.
            password: The password.
            secure: Use HTTPS.

        Raises:
            AnalystStack.exceptions.errors.ConnectionError: If the engine cannot be created or
                the test connection fails.
        """
        self.host = host
        self.database = database
        query = {"readonly": "1"}
        if secure:
            query["secure"] = "true"
        try:
            url = URL.create(
                "clickhousedb",
                username=user,
                password=password,
                host=host,
                port=int(port) if port else DEFAULT_HTTP_PORT,
                database=database,
                query=query,
            )
            self._engine: Engine = create_engine(url)
            with self._engine.connect():
                pass
            logger.info(f"ClickHouse client initialized for {self.host} - database: {self.database}")
        except Exception as e:
            logger.error(f"Failed to initialize ClickHouse client: {e}")
            raise ConnectionError(f"Client initialization failed: {e}") from e

    @property
    def engine(self) -> Engine:
        """The underlying SQLAlchemy `Engine` used to run reads."""
        return self._engine
