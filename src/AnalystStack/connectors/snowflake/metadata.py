"""Dedicated to schema extraction. Notice how we 'inject' the QueryManager so we don't repeat the to_dataframe logic"""

import pandas as pd

from AnalystStack.connectors.snowflake.query import QueryManager
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

# Snowflake stores unquoted identifiers uppercase and returns result headers in that stored
# case by default, regardless of how a column was referenced in the SELECT list -- every
# column below needs an explicit lowercase alias to keep result headers consistent with
# every other connector in this package.


class MetadataManager:
    """Handles schema and structural metadata extraction from INFORMATION_SCHEMA.

    Args:
        query_manager: The `AnalystStack.connectors.snowflake.query.QueryManager` used to
            run the underlying ``INFORMATION_SCHEMA`` queries.
    """

    def __init__(self, query_manager: QueryManager):
        self.query_manager = query_manager

    def fetch_tables(self, schema: str) -> pd.DataFrame:
        """Lists every base table in a Snowflake schema, with structural metadata.

        Snowflake's ``INFORMATION_SCHEMA.TABLES`` uniquely exposes exact ``ROW_COUNT``,
        ``BYTES``, ``CREATED``, and ``LAST_ALTERED`` for every table directly -- no second
        query or join needed, unlike every other connector in this package.

        Args:
            schema: The Snowflake schema to list tables from.

        Returns:
            A DataFrame with columns ``table_catalog``, ``table_schema``, ``table_name``,
            ``table_type``, ``row_count``, ``size_bytes``, ``created``, and
            ``last_altered`` -- all exact. Empty (but still carrying these columns) if the
            schema has no base tables.

        Raises:
            AnalystStack.exceptions.errors.ValidationError: If `schema` is not a valid
                identifier.
            AnalystStack.exceptions.errors.QueryExecutionError: If the underlying query
                fails.
        """
        validate_identifier(schema, "schema")
        query = f"""
            SELECT
                table_catalog AS table_catalog,
                table_schema AS table_schema,
                table_name AS table_name,
                table_type AS table_type,
                row_count AS row_count,
                bytes AS size_bytes,
                created AS created,
                last_altered AS last_altered
            FROM information_schema.tables
            WHERE table_schema = '{schema}' AND table_type = 'BASE TABLE'
        """
        df = self.query_manager.execute_read(query)
        return df if not df.empty else pd.DataFrame(columns=_TABLES_COLUMNS)

    def fetch_columns(self, schema: str, table_id: str) -> pd.DataFrame:
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
            AnalystStack.exceptions.errors.QueryExecutionError: If the underlying query
                fails.
        """
        validate_table_reference(schema, table_id)
        query = f"""
            SELECT
                table_schema AS table_schema,
                table_name AS table_name,
                column_name AS column_name,
                ordinal_position AS ordinal_position,
                data_type AS data_type,
                is_nullable AS is_nullable,
                column_default AS column_default
            FROM information_schema.columns
            WHERE table_schema = '{schema}' AND table_name = '{table_id}'
            ORDER BY ordinal_position
        """
        df = self.query_manager.execute_read(query)
        return df if not df.empty else pd.DataFrame(columns=_COLUMNS_COLUMNS)
