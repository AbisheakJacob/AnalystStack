"""Fill-rate profiling for ClickHouse tables."""

import pandas as pd

from AnalystStack.connectors.clickhouse.metadata import MetadataManager
from AnalystStack.connectors.clickhouse.query import QueryManager
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


class ProfileManager:
    """Generates fill-rate statistics.

    Args:
        query_manager: Runs the generated profiling query.
        metadata_manager: Discovers the table's columns first.
    """

    def __init__(self, query_manager: QueryManager, metadata_manager: MetadataManager):
        self._query_manager = query_manager
        self._metadata_manager = metadata_manager

    def profile_columns(self, schema: str, table_id: str) -> pd.DataFrame:
        """Profiles every column of a ClickHouse table: structural metadata plus fill rate.

        Args:
            schema: The ClickHouse database the table lives in.
            table_id: The table to profile.

        Returns:
            `MetadataManager.fetch_columns` output with ``row_count`` (exact ``count()``),
            ``non_null_count``, ``null_count`` and ``fill_rate_pct`` (0-100, 2 decimals)
            appended. Empty (still carrying these columns) if the table has no columns.

        Raises:
            AnalystStack.exceptions.errors.ValidationError: If a name is not a valid identifier.
            AnalystStack.exceptions.errors.QueryExecutionError: If the underlying query fails.
        """
        validate_table_reference(schema, table_id)
        columns_df = self._metadata_manager.fetch_columns(schema, table_id)
        if columns_df.empty:
            return pd.DataFrame(columns=_PROFILE_COLUMNS)

        names = columns_df["column_name"].tolist()
        selects = [f"countIf(isNotNull(`{col}`)) AS `{col}`" for col in names]
        query = f"SELECT count() AS row_count,\n{',\n'.join(selects)}\nFROM {schema}.{table_id}"

        counts = self._query_manager.execute_read(query).iloc[0]
        row_count = int(counts["row_count"])

        profile = columns_df.copy()
        profile["row_count"] = row_count
        profile["non_null_count"] = profile["column_name"].map(counts).astype("int64")
        profile["null_count"] = profile["row_count"] - profile["non_null_count"]
        profile["fill_rate_pct"] = (
            round(profile["non_null_count"] / profile["row_count"] * 100, 2) if row_count > 0 else pd.NA
        )
        return profile
