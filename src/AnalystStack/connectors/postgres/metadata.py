"""Dedicated to schema extraction. Notice how we 'inject' the QueryManager so we don't repeat the to_dataframe logic"""

import pandas as pd

from AnalystStack.connectors.postgres.query import QueryManager
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
    """Handles schema and structural metadata extraction from INFORMATION_SCHEMA.

    Args:
        query_manager: The `AnalystStack.connectors.postgres.query.QueryManager` used to run
            the underlying ``information_schema`` queries.
    """

    def __init__(self, query_manager: QueryManager):
        self.query_manager = query_manager

    def fetch_tables(self, schema: str) -> pd.DataFrame:
        """Lists every base table in a Postgres schema, with structural metadata.

        Joins ``information_schema.tables`` with ``pg_catalog.pg_class``/``pg_namespace`` to
        pick up ``row_count`` and ``size_bytes``. Postgres tracks neither a table's creation
        nor last-modification timestamp by default, so ``created``/``last_altered`` are
        always ``pd.NA``.

        Args:
            schema: The Postgres schema to list tables from.

        Returns:
            A DataFrame with columns ``table_catalog``, ``table_schema``, ``table_name``,
            ``table_type``, ``row_count``, ``size_bytes``, ``created``, and ``last_altered``.
            ``row_count`` is Postgres's planner estimate (``pg_class.reltuples``), not an
            exact count -- run ``ANALYZE`` on the table beforehand for an up-to-date
            estimate. ``size_bytes`` (``pg_total_relation_size``, table + indexes + TOAST) is
            exact. ``created``/``last_altered`` are always ``pd.NA``. Empty (but still
            carrying these columns) if the schema has no base tables.

        Raises:
            AnalystStack.exceptions.errors.ValidationError: If `schema` is not a valid
                identifier.
            AnalystStack.exceptions.errors.QueryExecutionError: If the underlying query
                fails.
        """
        validate_identifier(schema, "schema")
        query = f"""
            SELECT
                t.table_catalog,
                t.table_schema,
                t.table_name,
                t.table_type,
                c.reltuples::bigint AS row_count,
                pg_total_relation_size(c.oid) AS size_bytes,
                NULL::timestamp AS created,
                NULL::timestamp AS last_altered
            FROM information_schema.tables t
            JOIN pg_catalog.pg_namespace n ON n.nspname = t.table_schema
            JOIN pg_catalog.pg_class c ON c.relnamespace = n.oid AND c.relname = t.table_name
            WHERE t.table_schema = '{schema}' AND t.table_type = 'BASE TABLE'
        """
        df = self.query_manager.execute_read(query)
        return df if not df.empty else pd.DataFrame(columns=_TABLES_COLUMNS)

    def fetch_columns(self, schema: str, table_id: str) -> pd.DataFrame:
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
            AnalystStack.exceptions.errors.QueryExecutionError: If the underlying query
                fails.
        """
        validate_table_reference(schema, table_id)
        query = f"""
            SELECT table_schema, table_name, column_name, ordinal_position, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = '{schema}' AND table_name = '{table_id}'
            ORDER BY ordinal_position
        """
        df = self.query_manager.execute_read(query)
        return df if not df.empty else pd.DataFrame(columns=_COLUMNS_COLUMNS)
