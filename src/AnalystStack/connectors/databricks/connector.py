"""The Facade (The Final Connector)

This is what your end-users will interact with. it inherits from BaseConnector to fulfill the contract,
but it offloads the actual work to the managers
"""

import pandas as pd

from AnalystStack.config.settings import DatabricksSettings
from AnalystStack.connectors.base import BaseConnector
from AnalystStack.connectors.databricks.client import DatabricksClientWrapper
from AnalystStack.connectors.databricks.metadata import MetadataManager
from AnalystStack.connectors.databricks.profiling import ProfilerManager
from AnalystStack.connectors.databricks.query import QueryManager
from AnalystStack.exceptions.errors import ConfigurationError
from AnalystStack.utils.validation import validate_table_reference


class DatabricksConnector(BaseConnector):
    """Facade combining Databricks client, query, metadata, and profiling logic.

    Reads and writes through a SQLAlchemy ``Engine`` using the ``databricks-sqlalchemy``
    dialect, so `read_data` / `write_data` share the same ``pandas.read_sql`` /
    ``DataFrame.to_sql`` code path used by every other connector in this package (see
    `AnalystStack.connectors.base.BaseConnector`).

    Note:
        Catalog and schema are fixed at connection time. The ``databricks-sqlalchemy``
        dialect binds a connection to one catalog and schema, so both `catalog` and
        `schema` are required constructor arguments rather than being passed per call
        (unlike `schema` in `read_data`/`write_data`/`get_datatypes`/`get_fillrate` on the
        other connectors, which is a per-call argument).

    Args:
        server_hostname: The Databricks workspace hostname. Falls back to the
            ``DATABRICKS_SERVER_HOSTNAME`` environment variable if omitted.
        http_path: The HTTP path of the SQL warehouse/cluster to connect to. Falls back to
            the ``DATABRICKS_HTTP_PATH`` environment variable if omitted.
        access_token: A Databricks personal access token. Falls back to the
            ``DATABRICKS_ACCESS_TOKEN`` environment variable if omitted.
        catalog: The Unity Catalog catalog to bind the connection to. Falls back to the
            ``DATABRICKS_CATALOG`` environment variable if omitted.
        schema: The schema to bind the connection to. Falls back to the
            ``DATABRICKS_SCHEMA`` environment variable if omitted.

    Raises:
        AnalystStack.exceptions.errors.ConfigurationError: If any of `server_hostname`,
            `http_path`, `access_token`, `catalog`, or `schema` is missing after falling
            back to environment variables.
        AnalystStack.exceptions.errors.ConnectionError: If the underlying SQLAlchemy engine
            fails to connect.

    Example:
        ```python
        from AnalystStack.connectors import DatabricksConnector

        db = DatabricksConnector(
            server_hostname="my-workspace.cloud.databricks.com",
            http_path="/sql/1.0/warehouses/abc123",
            access_token="dapi...",
            catalog="main",
            schema="analytics",
        )

        df = db.read_data("SELECT * FROM orders LIMIT 1000")
        db.write_data(df, schema="analytics", table_id="orders_copy", if_exists="replace")

        print(db.list_tables("analytics"))
        print(db.list_columns("analytics", "orders"))
        print(db.profile_columns("analytics", "orders"))
        ```
    """

    def __init__(
        self,
        server_hostname: str | None = None,
        http_path: str | None = None,
        access_token: str | None = None,
        catalog: str | None = None,
        schema: str | None = None,
    ):

        settings = DatabricksSettings()
        self.server_hostname = server_hostname or settings.server_hostname
        self.http_path = http_path or settings.http_path
        self.access_token = access_token or settings.access_token
        self.catalog = catalog or settings.catalog
        self.schema = schema or settings.schema

        if (
            not self.server_hostname
            or not self.http_path
            or not self.access_token
            or not self.catalog
            or not self.schema
        ):
            raise ConfigurationError(
                "A Databricks server_hostname, http_path, access_token, catalog, and schema must be "
                "provided or set in env variables."
            )

        # initialize the underlying components
        self._client_wrapper = DatabricksClientWrapper(
            self.server_hostname, self.http_path, self.access_token, self.catalog, self.schema
        )
        self._query_manager = QueryManager(self._client_wrapper)
        self._metadata_manager = MetadataManager(self._query_manager)
        self._profiler_manager = ProfilerManager(self._query_manager, self._metadata_manager)

    def read_data(self, query: str) -> pd.DataFrame:
        """Executes a SQL query against Databricks and returns the result as a DataFrame.

        Args:
            query: A SQL query string, evaluated against the catalog/schema this connector
                was constructed with.

        Returns:
            The query result as a DataFrame.

        Raises:
            AnalystStack.exceptions.errors.QueryExecutionError: If the query fails to
                execute.
        """
        return self._query_manager.execute_read(query)

    def write_data(self, df: pd.DataFrame, schema: str, table_id: str, if_exists: str = "append") -> None:
        """Writes a DataFrame to a Databricks table.

        Args:
            df: The DataFrame to write.
            schema: The schema the destination table lives in. Must belong to the catalog
                this connector was constructed with, since catalog/schema are fixed at
                connection time.
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
        """Lists every base table in a Databricks schema, with structural metadata.

        Args:
            schema: The schema to list tables from.

        Returns:
            A DataFrame with columns ``table_catalog``, ``table_schema``, ``table_name``,
            ``table_type``, ``row_count`` (always ``pd.NA`` -- see note below),
            ``size_bytes`` (always ``pd.NA``), ``created``, and ``last_altered`` (the last
            two are native Unity Catalog columns). ``row_count``/``size_bytes`` would
            require a ``DESCRIBE DETAIL`` per table, an N+1 query cost this method
            deliberately avoids. Empty (but still carrying these columns) if the schema has
            no base tables.

        Raises:
            AnalystStack.exceptions.errors.ValidationError: If `schema` is not a valid
                identifier.
            AnalystStack.exceptions.errors.QueryExecutionError: If the underlying
                ``information_schema`` query fails.
        """
        return self._metadata_manager.fetch_tables(schema)

    def list_columns(self, schema: str, table_id: str) -> pd.DataFrame:
        """Returns structural metadata for every column of a Databricks table.

        Args:
            schema: The schema the table lives in.
            table_id: The table to inspect.

        Returns:
            A DataFrame with columns ``table_schema``, ``table_name``, ``column_name``,
            ``ordinal_position``, ``data_type`` (e.g. ``"int"``), ``is_nullable``, and
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
        """Profiles every column of a Databricks table: structural metadata plus fill rate.

        Args:
            schema: The schema the table lives in.
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
