"""The Snowflake Engine (Composition Module)

Isolates authentication and API connection logic"""

from sqlalchemy import create_engine
from sqlalchemy.engine import URL, Engine

from AnalystStack.exceptions.errors import ConnectionError
from AnalystStack.utils.logging import get_logger

logger = get_logger(__name__)


class SnowflakeClientWrapper:
    """Builds and wraps a SQLAlchemy ``Engine`` for Snowflake via the
    ``snowflake-sqlalchemy`` dialect.

    Owns the low-level connection: constructing the SQLAlchemy ``URL``, creating the
    ``Engine``, and eagerly opening a test connection so failures surface immediately at
    construction time rather than on the first query.

    Attributes:
        engine: The underlying SQLAlchemy ``Engine``, used by
            `AnalystStack.connectors.snowflake.query.QueryManager` and the
            metadata/profiling managers to run queries.
    """

    def __init__(
        self,
        account: str,
        user: str,
        password: str,
        database: str,
        warehouse: str,
        schema: str | None = None,
        role: str | None = None,
    ):
        """Creates and validates the SQLAlchemy engine for a Snowflake account.

        Args:
            account: The Snowflake account identifier.
            user: The username to authenticate with.
            password: The password to authenticate with.
            database: The database to connect to.
            warehouse: The virtual warehouse to run queries on.
            schema: The schema to default to. Optional -- every query/metadata call in this
                package takes a fully-qualified ``schema`` argument regardless, so this only
                affects unqualified references you write yourself.
            role: The role to assume for this session. Optional -- defaults to the user's
                default role.

        Raises:
            AnalystStack.exceptions.errors.ConnectionError: If constructing the engine or
                opening the test connection fails (e.g. invalid credentials or an unknown
                account/warehouse).
        """
        self.account = account
        self.user = user
        self.database = database
        self.warehouse = warehouse
        self.schema = schema
        self.role = role

        try:
            query = {"warehouse": warehouse}
            if role:
                query["role"] = role
            url = URL.create(
                "snowflake",
                username=user,
                password=password,
                host=account,
                database=f"{database}/{schema}" if schema else database,
                query=query,
            )
            self._engine: Engine = create_engine(url)
            with self._engine.connect():
                pass
            logger.info(f"Snowflake client initialized for account {self.account}, database {self.database}")
        except Exception as e:
            logger.error(f"Failed to initialize Snowflake client: {e}")
            raise ConnectionError(f"Client initialization failed: {e}") from e

    @property
    def engine(self) -> Engine:
        """The underlying SQLAlchemy `Engine` used to run reads and writes."""
        return self._engine
