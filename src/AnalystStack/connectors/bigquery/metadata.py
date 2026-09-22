"""Dedicated to schema extraction. Notice how we 'inject' the QueryManager so we don't repeat the to_dataframe logic"""

import pandas as pd

from AnalystStack.connectors.bigquery.query import QueryManager
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
        query_manager: The `AnalystStack.connectors.bigquery.query.QueryManager` used to run
            the underlying ``INFORMATION_SCHEMA`` queries.
        gbq_project_id: The project the data lives in, used to build fully-qualified
            ``project.dataset.INFORMATION_SCHEMA`` references. Must not be ``None`` -- it's
            interpolated directly into the generated SQL.
    """

    def __init__(self, query_manager: QueryManager, gbq_project_id: str):
        self.gbq_project_id = gbq_project_id
        self.query_manager = query_manager

    def fetch_tables(self, schema: str) -> pd.DataFrame:
        """Lists every base table in a BigQuery dataset, with structural metadata.

        Joins ``INFORMATION_SCHEMA.TABLES`` (for ``table_catalog``/``table_type``/creation
        time) with the ``__TABLES__`` pseudo-table (for exact ``row_count``/``size_bytes``/
        last-modified time) -- both are metadata-only lookups, so this never scans the
        tables' actual data.

        Args:
            schema: The BigQuery dataset to list tables from.

        Returns:
            A DataFrame with columns ``table_catalog``, ``table_schema``, ``table_name``,
            ``table_type``, ``row_count``, ``size_bytes``, ``created``, and ``last_altered``.
            ``row_count``/``size_bytes``/``created``/``last_altered`` are all exact for
            BigQuery. Empty (but still carrying these columns) if the dataset has no base
            tables.

        Raises:
            AnalystStack.exceptions.errors.ValidationError: If `schema` is not a valid
                identifier.
            AnalystStack.exceptions.errors.QueryExecutionError: If the underlying query
                fails.
        """
        validate_identifier(schema, "dataset ID")
        query = f"""
            SELECT
                t.table_catalog,
                t.table_schema,
                t.table_name,
                t.table_type,
                tb.row_count AS row_count,
                tb.size_bytes AS size_bytes,
                t.creation_time AS created,
                TIMESTAMP_MILLIS(tb.last_modified_time) AS last_altered
            FROM `{self.gbq_project_id}.{schema}.INFORMATION_SCHEMA.TABLES` t
            LEFT JOIN `{self.gbq_project_id}.{schema}.__TABLES__` tb
                ON t.table_name = tb.table_id
            WHERE t.table_type = 'BASE TABLE'
        """
        df = self.query_manager.execute_read(query)
        return df if not df.empty else pd.DataFrame(columns=_TABLES_COLUMNS)

    def fetch_columns(self, schema: str, table_id: str) -> pd.DataFrame:
        """Returns structural metadata for every column of a BigQuery table.

        Args:
            schema: The BigQuery dataset the table lives in.
            table_id: The table to inspect.

        Returns:
            A DataFrame with columns ``table_schema``, ``table_name``, ``column_name``,
            ``ordinal_position``, ``data_type`` (e.g. ``"INT64"``), ``is_nullable``, and
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
            FROM `{self.gbq_project_id}.{schema}.INFORMATION_SCHEMA.COLUMNS`
            WHERE table_name = '{table_id}'
            ORDER BY ordinal_position
        """
        df = self.query_manager.execute_read(query)
        return df if not df.empty else pd.DataFrame(columns=_COLUMNS_COLUMNS)
