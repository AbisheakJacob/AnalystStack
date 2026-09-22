"""Dedicated to schema extraction, via DuckDB's own catalog table functions rather than
``information_schema`` -- see `MetadataManager.fetch_tables` for why."""

import pandas as pd

from AnalystStack.connectors.duckdb.query import QueryManager
from AnalystStack.utils.validation import validate_identifier, validate_table_reference

_TABLES_COLUMNS = [
    "table_catalog",
    "table_schema",
    "table_name",
    "table_type",
    "row_count",
    "size_bytes",
    "created",
    "last_altered",
]

_COLUMNS_COLUMNS = [
    "table_schema",
    "table_name",
    "column_name",
    "ordinal_position",
    "data_type",
    "is_nullable",
    "column_default",
]


class MetadataManager:
    """Handles schema and structural metadata extraction from DuckDB's catalog functions.

    Args:
        query_manager: The `AnalystStack.connectors.duckdb.query.QueryManager` used to run
            the underlying catalog queries.
    """

    def __init__(self, query_manager: QueryManager):
        self.query_manager = query_manager

    def fetch_tables(self, schema: str) -> pd.DataFrame:
        """Lists every base table in a DuckDB schema, with structural metadata.

        Uses ``duckdb_tables()``, DuckDB's own catalog table function, rather than
        ``information_schema.tables``: it already only lists tables (never views), and
        exposes ``estimated_size`` -- a row-count estimate with no full table scan -- that
        generic ``information_schema`` doesn't. DuckDB doesn't track a table's size in bytes
        or its creation/modification timestamps, so those columns are always ``pd.NA``.

        Args:
            schema: The schema to list tables from.

        Returns:
            A DataFrame with columns ``table_catalog``, ``table_schema``, ``table_name``,
            ``table_type`` (always ``"BASE TABLE"``), ``row_count`` (DuckDB's estimate),
            ``size_bytes`` (always ``pd.NA``), ``created`` (always ``pd.NA``), and
            ``last_altered`` (always ``pd.NA``). Empty (but still carrying these columns) if
            the schema has no base tables.

        Raises:
            AnalystStack.exceptions.errors.ValidationError: If `schema` is not a valid
                identifier.
            AnalystStack.exceptions.errors.QueryExecutionError: If the underlying query
                fails.
        """
        validate_identifier(schema, "schema")
        query = f"""
            SELECT
                database_name AS table_catalog,
                schema_name AS table_schema,
                table_name,
                estimated_size AS row_count
            FROM duckdb_tables()
            WHERE schema_name = '{schema}'
        """
        df = self.query_manager.execute_read(query)
        if df.empty:
            return pd.DataFrame(columns=_TABLES_COLUMNS)
        df["table_type"] = "BASE TABLE"
        df["size_bytes"] = pd.NA
        df["created"] = pd.NA
        df["last_altered"] = pd.NA
        return df[_TABLES_COLUMNS]

    def fetch_columns(self, schema: str, table_id: str) -> pd.DataFrame:
        """Returns structural metadata for every column of a DuckDB table.

        Uses ``duckdb_columns()``, DuckDB's own catalog table function.

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
        validate_table_reference(schema, table_id)
        query = f"""
            SELECT
                schema_name AS table_schema,
                table_name,
                column_name,
                column_index AS ordinal_position,
                data_type,
                is_nullable,
                column_default
            FROM duckdb_columns()
            WHERE schema_name = '{schema}' AND table_name = '{table_id}'
            ORDER BY column_index
        """
        df = self.query_manager.execute_read(query)
        return df if not df.empty else pd.DataFrame(columns=_COLUMNS_COLUMNS)
