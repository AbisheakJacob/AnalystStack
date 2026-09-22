"""The DuckDB Engine (Composition Module)

Isolates authentication and API connection logic"""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from AnalystStack.exceptions.errors import ConnectionError
from AnalystStack.utils.logging import get_logger

logger = get_logger(__name__)


class DuckDBClientWrapper:
    """Builds and wraps a SQLAlchemy ``Engine`` for DuckDB via the ``duckdb-engine`` dialect.

    DuckDB is an embedded, in-process database -- unlike every other connector in this
    package, there's no server to authenticate against, so this wrapper only needs a file
    path (or ``":memory:"``).

    Attributes:
        engine: The underlying SQLAlchemy ``Engine``, used by
            `AnalystStack.connectors.duckdb.query.QueryManager` and the metadata/profiling
            managers to run queries.
    """

    def __init__(self, database_path: str):
        """Creates and validates the SQLAlchemy engine for a DuckDB database.

        Args:
            database_path: Path to a DuckDB database file, or ``":memory:"`` for a
                transient, process-local database.

        Raises:
            AnalystStack.exceptions.errors.ConnectionError: If constructing the engine or
                opening the test connection fails (e.g. an unwritable path).
        """
        self.database_path = database_path
        try:
            self._engine: Engine = create_engine(f"duckdb:///{database_path}")
            with self._engine.connect():
                pass
            logger.info(f"DuckDB client initialized for {self.database_path}")
        except Exception as e:
            logger.error(f"Failed to initialize DuckDB client: {e}")
            raise ConnectionError(f"Client initialization failed: {e}") from e

    @property
    def engine(self) -> Engine:
        """The underlying SQLAlchemy `Engine` used to run reads and writes."""
        return self._engine
