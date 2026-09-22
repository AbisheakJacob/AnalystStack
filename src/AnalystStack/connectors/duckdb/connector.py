"""The Facade (The Final Connector)

This is what your end-users will interact with. it inherits from BaseConnector to fulfill the contract,
but it offloads the actual work to the managers
"""

import pandas as pd

from AnalystStack.config.settings import DuckDBSettings
from AnalystStack.connectors.base import BaseConnector
from AnalystStack.connectors.duckdb.client import DuckDBClientWrapper
from AnalystStack.connectors.duckdb.metadata import MetadataManager
from AnalystStack.connectors.duckdb.profiling import ProfilerManager
from AnalystStack.connectors.duckdb.query import QueryManager
from AnalystStack.utils.validation import validate_table_reference


class DuckDBConnector(BaseConnector):
    """Facade combining DuckDB client, query, metadata, and profiling logic.

    DuckDB is an embedded, in-process database -- unlike every other connector in this
    package, there's no server to connect to and no credentials required, making this the
    only connector constructible with zero configuration. A natural choice for local
    development, ad hoc analysis, or as a lightweight target in tests.

    Args:
        database_path: Path to a DuckDB database file. Falls back to the
            ``DUCKDB_DATABASE_PATH`` environment variable, and then to ``":memory:"`` (a
            transient, process-local database that disappears when the connector is
            garbage-collected), if omitted.

    Raises:
        AnalystStack.exceptions.errors.ConnectionError: If the underlying SQLAlchemy engine
            fails to connect (e.g. an unwritable path).

    Example:
        ```python
        from AnalystStack.connectors import DuckDBConnector

        db = DuckDBConnector()  # in-memory, zero configuration
        db.write_data(df, schema="main", table_id="orders", if_exists="replace")

        print(db.list_tables("main"))
        print(db.list_columns("main", "orders"))
        print(db.profile_columns("main", "orders"))
        ```
    """

    def __init__(self, database_path: str | None = None):
        settings = DuckDBSettings()
        self.database_path = database_path or settings.database_path or ":memory:"

        # initialize the underlying components
        self._client_wrapper = DuckDBClientWrapper(self.database_path)
        self._query_manager = QueryManager(self._client_wrapper)
        self._metadata_manager = MetadataManager(self._query_manager)
        self._profiler_manager = ProfilerManager(self._query_manager, self._metadata_manager)

    def read_data(self, query: str) -> pd.DataFrame:
        """Executes a SQL query against DuckDB and returns the result as a DataFrame.

        Args:
            query: A DuckDB SQL query string.

        Returns:
            The query result as a DataFrame.

        Raises:
            AnalystStack.exceptions.errors.QueryExecutionError: If the query fails to
                execute.
        """
        return self._query_manager.execute_read(query)

    def write_data(self, df: pd.DataFrame, schema: str, table_id: str, if_exists: str = "append") -> None:
        """Writes a DataFrame to a DuckDB table.

        Args:
            df: The DataFrame to write.
            schema: The schema the destination table lives in (``"main"`` always exists by
                default; other schemas must be created first, e.g. via
                ``db.read_data("CREATE SCHEMA IF NOT EXISTS analytics")``).
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
        """Lists every base table in a DuckDB schema, with structural metadata.

        Args:
            schema: The schema to list tables from.

        Returns:
            A DataFrame with columns ``table_catalog``, ``table_schema``, ``table_name``,
            ``table_type`` (always ``"BASE TABLE"``), ``row_count`` (DuckDB's estimate,
            not exact), ``size_bytes`` (always ``pd.NA``), ``created`` (always ``pd.NA``),
            and ``last_altered`` (always ``pd.NA``). Empty (but still carrying these
            columns) if the schema has no base tables.

        Raises:
            AnalystStack.exceptions.errors.ValidationError: If `schema` is not a valid
                identifier.
            AnalystStack.exceptions.errors.QueryExecutionError: If the underlying query
                fails.
        """
        return self._metadata_manager.fetch_tables(schema)

    def list_columns(self, schema: str, table_id: str) -> pd.DataFrame:
        """Returns structural metadata for every column of a DuckDB table.

        Args:
            schema: The schema the table lives in.
            table_id: The table to inspect.

        Returns:
            A DataFrame with columns ``table_schema``, ``table_name``, ``column_name``,
            ``ordinal_position``, ``data_type`` (e.g. ``"INTEGER"``), ``is_nullable``, and
            ``column_default``, one row per column, ordered by ``ordinal_position``. Empty
            (but still carrying these columns) if the table has no columns or does not
            exist.

        Raises:
            AnalystStack.exceptions.errors.ValidationError: If `schema` or `table_id` is
                not a valid identifier.
            AnalystStack.exceptions.errors.QueryExecutionError: If the underlying query
                fails.
        """
        return self._metadata_manager.fetch_columns(schema, table_id)

    def profile_columns(self, schema: str, table_id: str) -> pd.DataFrame:
        """Profiles every column of a DuckDB table: structural metadata plus fill rate.

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
