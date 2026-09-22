"""The Facade (The Final Connector)

This is what your end-users will interact with. it inherits from BaseConnector to fulfill the contract,
but it offloads the actual work to the managers
"""

import pandas as pd

from AnalystStack.config.settings import SnowflakeSettings
from AnalystStack.connectors.base import BaseConnector
from AnalystStack.connectors.snowflake.client import SnowflakeClientWrapper
from AnalystStack.connectors.snowflake.metadata import MetadataManager
from AnalystStack.connectors.snowflake.profiling import ProfilerManager
from AnalystStack.connectors.snowflake.query import QueryManager
from AnalystStack.exceptions.errors import ConfigurationError
from AnalystStack.utils.validation import validate_table_reference


class SnowflakeConnector(BaseConnector):
    """Facade combining Snowflake client, query, metadata, and profiling logic.

    Reads and writes through a SQLAlchemy ``Engine`` using the ``snowflake-sqlalchemy``
    dialect, so `read_data` / `write_data` share the same ``pandas.read_sql`` /
    ``DataFrame.to_sql`` code path used by every other connector in this package (see
    `AnalystStack.connectors.base.BaseConnector`). Of every connector in this package,
    Snowflake has the richest metadata: `list_tables` returns exact row counts, byte sizes,
    and timestamps directly from a single ``INFORMATION_SCHEMA`` query.

    Args:
        account: The Snowflake account identifier. Falls back to the
            ``SNOWFLAKE_ACCOUNT`` environment variable if omitted.
        user: The username to authenticate with. Falls back to the ``SNOWFLAKE_USER``
            environment variable if omitted.
        password: The password to authenticate with. Falls back to the
            ``SNOWFLAKE_PASSWORD`` environment variable if omitted.
        database: The database to connect to. Falls back to the ``SNOWFLAKE_DATABASE``
            environment variable if omitted.
        warehouse: The virtual warehouse to run queries on. Falls back to the
            ``SNOWFLAKE_WAREHOUSE`` environment variable if omitted.
        schema: The schema to default to. Falls back to the ``SNOWFLAKE_SCHEMA``
            environment variable, and is otherwise optional.
        role: The role to assume for this session. Falls back to the ``SNOWFLAKE_ROLE``
            environment variable, and is otherwise optional.

    Raises:
        AnalystStack.exceptions.errors.ConfigurationError: If `account`, `user`,
            `password`, `database`, or `warehouse` is missing after falling back to
            environment variables.
        AnalystStack.exceptions.errors.ConnectionError: If the underlying SQLAlchemy engine
            fails to connect.

    Example:
        ```python
        from AnalystStack.connectors import SnowflakeConnector

        sf = SnowflakeConnector(
            account="xy12345",
            user="analyst",
            password="secret",
            database="analytics",
            warehouse="compute_wh",
        )

        df = sf.read_data("SELECT * FROM public.orders LIMIT 1000")
        sf.write_data(df, schema="public", table_id="orders_copy", if_exists="replace")

        print(sf.list_tables("public"))
        print(sf.list_columns("public", "orders"))
        print(sf.profile_columns("public", "orders"))
        ```
    """

    def __init__(
        self,
        account: str | None = None,
        user: str | None = None,
        password: str | None = None,
        database: str | None = None,
        warehouse: str | None = None,
        schema: str | None = None,
        role: str | None = None,
    ):
        # fallback to environment settings if not explicitly provided
        settings = SnowflakeSettings()
        self.account = account or settings.account
        self.user = user or settings.user
        self.password = password or settings.password
        self.database = database or settings.database
        self.warehouse = warehouse or settings.warehouse
        self.schema = schema or settings.schema
        self.role = role or settings.role

        if not self.account or not self.user or not self.password or not self.database or not self.warehouse:
            raise ConfigurationError(
                "A Snowflake account / user / password / database / warehouse must be "
                "provided or set in environment variables."
            )

        # initialize the underlying components
        self._client_wrapper = SnowflakeClientWrapper(
            self.account, self.user, self.password, self.database, self.warehouse, self.schema, self.role
        )
        self._query_manager = QueryManager(self._client_wrapper)
        self._metadata_manager = MetadataManager(self._query_manager)
        self._profiler_manager = ProfilerManager(self._query_manager, self._metadata_manager)

    def read_data(self, query: str) -> pd.DataFrame:
        """Executes a SQL query against Snowflake and returns the result as a DataFrame.

        Args:
            query: A Snowflake SQL query string.

        Returns:
            The query result as a DataFrame.

        Raises:
            AnalystStack.exceptions.errors.QueryExecutionError: If the query fails to
                execute.
        """
        return self._query_manager.execute_read(query)

    def write_data(self, df: pd.DataFrame, schema: str, table_id: str, if_exists: str = "append") -> None:
        """Writes a DataFrame to a Snowflake table.

        Args:
            df: The DataFrame to write.
            schema: The Snowflake schema the destination table lives in.
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
        """Lists every base table in a Snowflake schema, with structural metadata.

        Args:
            schema: The Snowflake schema to list tables from.

        Returns:
            A DataFrame with columns ``table_catalog``, ``table_schema``, ``table_name``,
            ``table_type``, ``row_count``, ``size_bytes``, ``created``, and
            ``last_altered`` -- all exact, sourced directly from
            ``INFORMATION_SCHEMA.TABLES``. Empty (but still carrying these columns) if the
            schema has no base tables.

        Raises:
            AnalystStack.exceptions.errors.ValidationError: If `schema` is not a valid
                identifier.
            AnalystStack.exceptions.errors.QueryExecutionError: If the underlying
                ``INFORMATION_SCHEMA`` query fails.
        """
        return self._metadata_manager.fetch_tables(schema)

    def list_columns(self, schema: str, table_id: str) -> pd.DataFrame:
        """Returns structural metadata for every column of a Snowflake table.

        Args:
            schema: The Snowflake schema the table lives in.
            table_id: The table to inspect.

        Returns:
            A DataFrame with columns ``table_schema``, ``table_name``, ``column_name``,
            ``ordinal_position``, ``data_type`` (e.g. ``"NUMBER"``), ``is_nullable``, and
            ``column_default``, one row per column, ordered by ``ordinal_position``. Empty
            (but still carrying these columns) if the table has no columns or does not
            exist.

        Raises:
            AnalystStack.exceptions.errors.ValidationError: If `schema` or `table_id` is
                not a valid identifier.
            AnalystStack.exceptions.errors.QueryExecutionError: If the underlying
                ``INFORMATION_SCHEMA`` query fails.
        """
        return self._metadata_manager.fetch_columns(schema, table_id)

    def profile_columns(self, schema: str, table_id: str) -> pd.DataFrame:
        """Profiles every column of a Snowflake table: structural metadata plus fill rate.

        Args:
            schema: The Snowflake schema the table lives in.
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
        return self._profiler_manager.profile_columns(schema, table_id)
