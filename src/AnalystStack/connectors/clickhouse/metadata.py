"""Schema extraction for ClickHouse, from the ``system`` tables."""

import pandas as pd

from AnalystStack.connectors.clickhouse.query import QueryManager
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
    """Handles schema and structural metadata extraction from ``system.tables`` / ``system.columns``.

    Args:
        query_manager: The `AnalystStack.connectors.clickhouse.query.QueryManager` used to run
            the underlying queries.
    """

    def __init__(self, query_manager: QueryManager):
        self.query_manager = query_manager

    def fetch_tables(self, schema: str) -> pd.DataFrame:
        """Lists every base table in a ClickHouse database, with structural metadata.

        Views, materialized views, dictionaries and temporary tables are excluded.

        Args:
            schema: The ClickHouse database to list tables from.

        Returns:
            A DataFrame with columns ``table_catalog``, ``table_schema``, ``table_name``,
            ``table_type``, ``row_count`` (``total_rows``, which ClickHouse may report as null
            for some engines), ``size_bytes`` (``total_bytes``), ``created`` (always
            ``pd.NA``) and ``last_altered`` (``metadata_modification_time``).

        Raises:
            AnalystStack.exceptions.errors.ValidationError: If `schema` is not a valid identifier.
            AnalystStack.exceptions.errors.QueryExecutionError: If the underlying query fails.
        """
        validate_identifier(schema, "schema")
        query = f"""
            SELECT
                database AS table_catalog,
                database AS table_schema,
                name AS table_name,
                'BASE TABLE' AS table_type,
                total_rows AS row_count,
                total_bytes AS size_bytes,
                CAST(NULL AS Nullable(DateTime)) AS created,
                metadata_modification_time AS last_altered
            FROM system.tables
            WHERE database = '{schema}'
              AND is_temporary = 0
              AND engine NOT IN ('View', 'MaterializedView', 'LiveView', 'Dictionary')
            ORDER BY name
        """
        df = self.query_manager.execute_read(query)
        return df if not df.empty else pd.DataFrame(columns=_TABLES_COLUMNS)

    def fetch_columns(self, schema: str, table_id: str) -> pd.DataFrame:
        """Returns structural metadata for every column of a ClickHouse table.

        Args:
            schema: The ClickHouse database the table lives in.
            table_id: The table to inspect.

        Returns:
            A DataFrame with columns ``table_schema``, ``table_name``, ``column_name``,
            ``ordinal_position``, ``data_type`` (the ClickHouse type string), ``is_nullable``
            (``"YES"`` when the type is ``Nullable(...)``) and ``column_default``, ordered by
            position.

        Raises:
            AnalystStack.exceptions.errors.ValidationError: If a name is not a valid identifier.
            AnalystStack.exceptions.errors.QueryExecutionError: If the underlying query fails.
        """
        validate_table_reference(schema, table_id)
        query = f"""
            SELECT
                database AS table_schema,
                table AS table_name,
                name AS column_name,
                position AS ordinal_position,
                type AS data_type,
                if(startsWith(type, 'Nullable('), 'YES', 'NO') AS is_nullable,
                default_expression AS column_default
            FROM system.columns
            WHERE database = '{schema}' AND table = '{table_id}'
            ORDER BY position
        """
        df = self.query_manager.execute_read(query)
        return df if not df.empty else pd.DataFrame(columns=_COLUMNS_COLUMNS)
