"""Dedicated to heavy analytical queries like calculating fill rates"""

import pandas as pd

from AnalystStack.connectors.duckdb.metadata import MetadataManager
from AnalystStack.connectors.duckdb.query import QueryManager
from AnalystStack.utils.validation import validate_table_reference

_PROFILE_COLUMNS = [
    "table_schema",
    "table_name",
    "column_name",
    "ordinal_position",
    "data_type",
    "is_nullable",
    "column_default",
    "row_count",
    "non_null_count",
    "null_count",
    "fill_rate_pct",
]


class ProfilerManager:
    """Generates data quality statistics and profiles.

    Args:
        query_manager: The `AnalystStack.connectors.duckdb.query.QueryManager` used to run
            the generated profiling query.
        metadata_manager: The `AnalystStack.connectors.duckdb.metadata.MetadataManager`
            used to discover the table's columns before profiling them.
    """

    def __init__(self, query_manager: QueryManager, metadata_manager: MetadataManager):
        self.query_manager = query_manager
        self.metadata_manager = metadata_manager

    def profile_columns(self, schema: str, table_id: str) -> pd.DataFrame:
        """Profiles every column of a DuckDB table: structural metadata plus fill rate.

        Args:
            schema: The schema the table lives in.
            table_id: The table to profile.

        Returns:
            `MetadataManager.fetch_columns`'s output, with four columns appended:
            ``row_count`` (the table's exact row count from a live ``COUNT(*)``, repeated on
            every row), ``non_null_count``, ``null_count``, and ``fill_rate_pct`` (0-100,
            rounded to 2 decimal places). Empty (but still carrying these columns) if the
            table has no columns.

        Raises:
            AnalystStack.exceptions.errors.ValidationError: If `schema` or `table_id` is
                not a valid identifier.
            AnalystStack.exceptions.errors.QueryExecutionError: If the underlying query
                fails.
        """
        validate_table_reference(schema, table_id)
        columns_df = self.metadata_manager.fetch_columns(schema, table_id)
        if columns_df.empty:
            return pd.DataFrame(columns=_PROFILE_COLUMNS)

        column_names = columns_df["column_name"].tolist()
        selects = [f'SUM(CASE WHEN "{col}" IS NOT NULL THEN 1 ELSE 0 END) AS "{col}"' for col in column_names]
        sql_select = ",\n".join(selects)
        query = f'SELECT COUNT(*) AS row_count,\n{sql_select}\nFROM "{schema}"."{table_id}"'

        counts = self.query_manager.execute_read(query).iloc[0]
        row_count = int(counts["row_count"])

        profile = columns_df.copy()
        profile["row_count"] = row_count
        profile["non_null_count"] = profile["column_name"].map(counts).astype("int64")
        profile["null_count"] = profile["row_count"] - profile["non_null_count"]
        profile["fill_rate_pct"] = (
            round(profile["non_null_count"] / profile["row_count"] * 100, 2) if row_count > 0 else pd.NA
        )
        return profile
