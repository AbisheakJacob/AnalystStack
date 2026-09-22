"""Dedicated to schema extraction. Notice how we 'inject' the QueryManager so we don't repeat the to_dataframe logic"""

import pandas as pd

from AnalystStack.connectors.databricks.query import QueryManager
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
        query_manager: The `AnalystStack.connectors.databricks.query.QueryManager` used to
            run the underlying ``information_schema`` queries.
    """

    def __init__(self, query_manager: QueryManager):
        self.query_manager = query_manager

    def fetch_tables(self, schema: str) -> pd.DataFrame:
        """Lists every base table in a Databricks schema, with structural metadata.

        Unity Catalog's ``information_schema.tables`` natively tracks ``created``/
        ``last_altered`` timestamps, so those come free. ``row_count``/``size_bytes`` would
        require a ``DESCRIBE DETAIL`` per table (an extra query per row -- an N+1 cost this
        method deliberately avoids), so they are always ``pd.NA`` for now.

        Args:
            schema: The schema to list tables from.

        Returns:
            A DataFrame with columns ``table_catalog``, ``table_schema``, ``table_name``,
            ``table_type``, ``row_count`` (always ``pd.NA``), ``size_bytes`` (always
            ``pd.NA``), ``created``, and ``last_altered``. Empty (but still carrying these
            columns) if the schema has no base tables.

        Raises:
            AnalystStack.exceptions.errors.ValidationError: If `schema` is not a valid
                identifier.
            AnalystStack.exceptions.errors.QueryExecutionError: If the underlying query
                fails.
        """
        validate_identifier(schema, "schema")
        query = f"""
            SELECT table_catalog, table_schema, table_name, table_type, created, last_altered
            FROM information_schema.tables
            WHERE table_schema = '{schema}' AND table_type = 'BASE TABLE'
        """
        df = self.query_manager.execute_read(query)
        if df.empty:
            return pd.DataFrame(columns=_TABLES_COLUMNS)
        df["row_count"] = pd.NA
        df["size_bytes"] = pd.NA
        return df[_TABLES_COLUMNS]

    def fetch_columns(self, schema: str, table_id: str) -> pd.DataFrame:
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
