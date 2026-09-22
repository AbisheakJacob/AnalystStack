"""The Facade (The Final Connector)

This is what your end-users will interact with. it inherits from BaseConnector to fulfill the contract,
but it offloads the actual work to the managers
"""

import pandas as pd

from AnalystStack.config.settings import PostgresSettings
from AnalystStack.connectors.base import BaseConnector
from AnalystStack.connectors.postgres.client import PostgresClientWrapper
from AnalystStack.connectors.postgres.metadata import MetadataManager
from AnalystStack.connectors.postgres.profiling import ProfileManager
from AnalystStack.connectors.postgres.query import QueryManager
from AnalystStack.exceptions.errors import ConfigurationError
from AnalystStack.utils.validation import validate_table_reference


class PostgresConnector(BaseConnector):
    """Facade combining Postgres client, query, metadata, and profiling logic.

    Reads and writes through a SQLAlchemy ``Engine`` using the built-in ``psycopg2`` driver,
    so `read_data` / `write_data` share the same ``pandas.read_sql`` / ``DataFrame.to_sql``
    code path used by every other connector in this package (see
    `AnalystStack.connectors.base.BaseConnector`).

    Args:
        host: The Postgres server hostname. Falls back to the ``POSTGRES_HOST`` environment
            variable if omitted.
        port: The Postgres server port. Falls back to the ``POSTGRES_PORT`` environment
            variable if omitted.
        database: The database to connect to. Falls back to the ``POSTGRES_DATABASE``
            environment variable if omitted.
        user: The username to authenticate with. Falls back to the ``POSTGRES_USER``
            environment variable if omitted.
        password: The password to authenticate with. Falls back to the ``POSTGRES_PASSWORD``
            environment variable if omitted.

    Raises:
        AnalystStack.exceptions.errors.ConfigurationError: If any of `host`, `port`,
            `database`, `user`, or `password` is missing after falling back to environment
            variables.
        AnalystStack.exceptions.errors.ConnectionError: If the underlying SQLAlchemy engine
            fails to connect.

    Example:
        ```python
        from AnalystStack.connectors import PostgresConnector

        pg = PostgresConnector(
            host="localhost",
            port="5432",
            database="analytics",
            user="analyst",
            password="secret",
        )

        df = pg.read_data("SELECT * FROM public.orders LIMIT 1000")
        pg.write_data(df, schema="public", table_id="orders_copy", if_exists="replace")

        print(pg.list_tables("public"))
        print(pg.list_columns("public", "orders"))
        print(pg.profile_columns("public", "orders"))
        ```
    """

    def __init__(
        self,
        host: str | None = None,
        port: str | None = None,
        database: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ):
        # fallback to environment settings if not explicitly provided
        settings = PostgresSettings()
        self.host = host or settings.host
        self.port = port or settings.port
        self.database = database or settings.database
        self.user = user or settings.user
        self.password = password or settings.password

        if not self.host or not self.port or not self.database or not self.user or not self.password:
            raise ConfigurationError(
                "A postgres host / port / database / user / password must be provided or set in environment variables"
            )

        # initialize the underlying components
        self._client_wrapper = PostgresClientWrapper(self.host, self.port, self.database, self.user, self.password)
        self._query_manager = QueryManager(self._client_wrapper)
        self._metadata_manager = MetadataManager(self._query_manager)
        self._profile_manager = ProfileManager(self._query_manager, self._metadata_manager)

    def read_data(self, query: str) -> pd.DataFrame:
        """Executes a SQL query against Postgres and returns the result as a DataFrame.

        Args:
            query: A PostgreSQL query string.

        Returns:
            The query result as a DataFrame.

        Raises:
            AnalystStack.exceptions.errors.QueryExecutionError: If the query fails to
                execute.
        """
        return self._query_manager.execute_read(query)

    def write_data(self, df: pd.DataFrame, schema: str, table_id: str, if_exists: str = "append") -> None:
        """Writes a DataFrame to a Postgres table.

        Args:
            df: The DataFrame to write.
            schema: The Postgres schema the destination table lives in.
            table_id: The destination table name.
            if_exists: Behavior if the table already exists: ``"append"`` (default),
                ``"replace"``, or ``"fail"``.

        Raises:
            AnalystStack.exceptions.errors.ValidationError: If `schema` or `table_id` is
                not a valid identifier.
            AnalystStack.exceptions.errors.QueryExecutionError: If the write fails.
        """
        validate_table_reference(schema, table_id)
        self._query_manager.execute_write(df, schema, table_id, if_exists)

    def list_tables(self, schema: str) -> pd.DataFrame:
        """Lists every base table in a Postgres schema, with structural metadata.

        Args:
            schema: The Postgres schema to list tables from.

        Returns:
            A DataFrame with columns ``table_catalog``, ``table_schema``, ``table_name``,
            ``table_type``, ``row_count`` (Postgres's planner estimate, not exact),
            ``size_bytes`` (exact), ``created`` (always ``pd.NA`` -- Postgres doesn't track
            this), and ``last_altered`` (always ``pd.NA``). Empty (but still carrying these
            columns) if the schema has no base tables.

        Raises:
            AnalystStack.exceptions.errors.ValidationError: If `schema` is not a valid
                identifier.
            AnalystStack.exceptions.errors.QueryExecutionError: If the underlying
                ``information_schema`` query fails.
        """
        return self._metadata_manager.fetch_tables(schema)

    def list_columns(self, schema: str, table_id: str) -> pd.DataFrame:
        """Returns structural metadata for every column of a Postgres table.

        Args:
            schema: The Postgres schema the table lives in.
            table_id: The table to inspect.

        Returns:
            A DataFrame with columns ``table_schema``, ``table_name``, ``column_name``,
            ``ordinal_position``, ``data_type`` (e.g. ``"integer"``), ``is_nullable``, and
            ``column_default``, one row per column, ordered by ``ordinal_position``. Empty
            (but still carrying these columns) if the table has no columns or does not
            exist.

        Raises:
            AnalystStack.exceptions.errors.ValidationError: If `schema` or `table_id` is
                not a valid identifier.
            AnalystStack.exceptions.errors.QueryExecutionError: If the underlying
                ``information_schema`` query fails.
        """
        return self._metadata_manager.fetch_columns(schema, table_id)

    def profile_columns(self, schema: str, table_id: str) -> pd.DataFrame:
        """Profiles every column of a Postgres table: structural metadata plus fill rate.

        Args:
            schema: The Postgres schema the table lives in.
            table_id: The table to profile.

        Returns:
            `list_columns`'s output, with four columns appended: ``row_count`` (the table's
            exact row count from a live ``COUNT(*)``, repeated on every row),
            ``non_null_count``, ``null_count``, and ``fill_rate_pct`` (0-100, rounded to 2
            decimal places, e.g. ``98.5``). Empty (but still carrying these columns) if the
            table has no columns.

        Raises:
            AnalystStack.exceptions.errors.ValidationError: If `schema` or `table_id` is
                not a valid identifier.
            AnalystStack.exceptions.errors.QueryExecutionError: If the underlying query
                fails.
        """
        return self._profile_manager.profile_columns(schema, table_id)
