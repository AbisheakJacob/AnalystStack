"""The Facade (The Final Connecter)

This is what your end-users will interact with. it inherits from BaseConnectory to fulfill the contract,
but it offloads the actual work to the managers
"""

import pandas as pd

from AnalystStack.config.settings import BigQuerySettings
from AnalystStack.connectors.base import BaseConnector

# Import the specialized managers
from AnalystStack.connectors.bigquery.client import BigQueryClientWrapper
from AnalystStack.connectors.bigquery.metadata import MetadataManager
from AnalystStack.connectors.bigquery.profiling import ProfilerManager
from AnalystStack.connectors.bigquery.query import QueryManager
from AnalystStack.exceptions.errors import ConfigurationError
from AnalystStack.utils.validation import validate_table_reference


class GoogleBigQueryConnector(BaseConnector):
    """Facade combining BigQuery client, query, metadata, and profiling logic.

    Reads and writes through a SQLAlchemy ``Engine`` using the ``sqlalchemy-bigquery``
    dialect, so `read_data` / `write_data` share the same ``pandas.read_sql`` /
    ``DataFrame.to_sql`` code path used by every other connector in this package (see
    `AnalystStack.connectors.base.BaseConnector`).

    Args:
        gcp_project_id: The GCP project used for billing/authentication -- the project the
            SQLAlchemy engine connects as. Falls back to the ``GCP_PROJECT_ID`` environment
            variable if omitted.
        gbq_project_id: The project the data actually lives in, if different from
            `gcp_project_id`. Falls back to the ``GBQ_PROJECT_ID`` environment variable, and
            then to `gcp_project_id` itself, if omitted -- it is never left as ``None``,
            since it's interpolated directly into every fully-qualified
            ``project.dataset.table`` reference this connector builds (metadata, profiling,
            and writes).
        credentials_path: Path to a service-account JSON key file. Falls back to the
            ``GOOGLE_APPLICATION_CREDENTIALS`` environment variable if omitted; if that is
            also unset, Application Default Credentials (ADC) are used instead.

    Raises:
        AnalystStack.exceptions.errors.ConfigurationError: If `gcp_project_id` is not
            provided and ``GCP_PROJECT_ID`` is not set in the environment.
        AnalystStack.exceptions.errors.ConnectionError: If the underlying SQLAlchemy engine
            fails to connect.

    Example:
        ```python
        from AnalystStack.connectors import GoogleBigQueryConnector

        bq = GoogleBigQueryConnector(
            gcp_project_id="my-gcp-project",  # billing / client project
            gbq_project_id="my-data-project",  # project the data lives in (optional)
            credentials_path="service-account.json",  # optional; uses ADC otherwise
        )

        df = bq.read_data("SELECT * FROM analytics.orders LIMIT 1000")
        bq.write_data(df, schema="analytics", table_id="orders_copy", if_exists="replace")

        print(bq.list_tables("analytics"))
        print(bq.list_columns("analytics", "orders"))
        print(bq.profile_columns("analytics", "orders"))
        ```
    """

    def __init__(
        self,
        gcp_project_id: str | None = None,
        gbq_project_id: str | None = None,
        credentials_path: str | None = None,
    ):
        # Fall back to environment settings if not explicitly provided
        settings = BigQuerySettings()
        self.gcp_project_id = gcp_project_id or settings.gcp_project_id
        self.credentials_path = credentials_path or settings.credentials_path

        if not self.gcp_project_id:
            raise ConfigurationError("A GCP project_id must be provided or set in environment variables.")

        # The data project defaults to the billing/auth project when not given separately --
        # never leave this as None, since it's interpolated directly into fully-qualified
        # `project.dataset.table` references (see query.py / metadata.py / profiling.py).
        self.gbq_project_id = gbq_project_id or settings.gbq_project_id or self.gcp_project_id

        # Initialize the underlying components
        self._client_wrapper = BigQueryClientWrapper(self.gcp_project_id, self.credentials_path)
        self._query_manager = QueryManager(self._client_wrapper, self.gbq_project_id)
        self._metadata_manager = MetadataManager(self._query_manager, self.gbq_project_id)
        self._profiler_manager = ProfilerManager(self._query_manager, self._metadata_manager, self.gbq_project_id)

    # --- Implement BaseConnector Abstract Methods ---

    def read_data(self, query: str) -> pd.DataFrame:
        """Executes a SQL query against BigQuery and returns the result as a DataFrame.

        Args:
            query: A BigQuery Standard SQL query string.

        Returns:
            The query result as a DataFrame.

        Raises:
            AnalystStack.exceptions.errors.QueryExecutionError: If the query fails to
                execute.
        """
        return self._query_manager.execute_read(query)

    def write_data(
        self,
        df: pd.DataFrame,
        schema: str,
        table_id: str,
        if_exists: str = "append",
    ) -> None:
        """Writes a DataFrame to a BigQuery table.

        Args:
            df: The DataFrame to write.
            schema: The BigQuery dataset the destination table lives in.
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
        """Lists every base table in a BigQuery dataset, with structural metadata.

        Args:
            schema: The BigQuery dataset to list tables from.

        Returns:
            A DataFrame with columns ``table_catalog``, ``table_schema``, ``table_name``,
            ``table_type``, ``row_count``, ``size_bytes``, ``created``, and ``last_altered``
            -- all exact for BigQuery, sourced from ``INFORMATION_SCHEMA.TABLES`` joined with
            the ``__TABLES__`` pseudo-table (a metadata-only lookup, no data scanned). Empty
            (but still carrying these columns) if the dataset has no base tables.

        Raises:
            AnalystStack.exceptions.errors.ValidationError: If `schema` is not a valid
                identifier.
            AnalystStack.exceptions.errors.QueryExecutionError: If the underlying
                ``INFORMATION_SCHEMA`` query fails.
        """
        return self._metadata_manager.fetch_tables(schema)

    def list_columns(self, schema: str, table_id: str) -> pd.DataFrame:
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
            AnalystStack.exceptions.errors.QueryExecutionError: If the underlying
                ``INFORMATION_SCHEMA`` query fails.
        """
        return self._metadata_manager.fetch_columns(schema, table_id)

    def profile_columns(self, schema: str, table_id: str) -> pd.DataFrame:
        """Profiles every column of a BigQuery table: structural metadata plus fill rate.

        Args:
            schema: The BigQuery dataset the table lives in.
            table_id: The table to profile.

        Returns:
            `list_columns`'s output, with four columns appended: ``row_count`` (the table's
            total row count, repeated on every row), ``non_null_count``, ``null_count``, and
            ``fill_rate_pct`` (0-100, rounded to 2 decimal places, e.g. ``98.5``). Empty (but
            still carrying these columns) if the table has no columns.

        Raises:
            AnalystStack.exceptions.errors.ValidationError: If `schema` or `table_id` is
                not a valid identifier.
            AnalystStack.exceptions.errors.QueryExecutionError: If the underlying query
                fails.
        """
        return self._profiler_manager.profile_columns(schema, table_id)
