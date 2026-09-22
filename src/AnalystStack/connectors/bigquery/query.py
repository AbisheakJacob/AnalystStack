"""Dedicated to executing SQL and moving data"""

import pandas as pd
from google.cloud import bigquery

from AnalystStack.connectors.bigquery.client import BigQueryClientWrapper
from AnalystStack.exceptions.errors import QueryExecutionError
from AnalystStack.utils.logging import get_logger

logger = get_logger(__name__)

_WRITE_DISPOSITIONS = {
    "append": bigquery.WriteDisposition.WRITE_APPEND,
    "replace": bigquery.WriteDisposition.WRITE_TRUNCATE,
    "fail": bigquery.WriteDisposition.WRITE_EMPTY,
}


class QueryManager:
    """Handles read and write data operations to BigQuery.

    `execute_read` runs through `AnalystStack.connectors.bigquery.client.BigQueryClientWrapper`'s
    SQLAlchemy ``Engine`` via ``pandas.read_sql`` -- a single query job per call, which is
    the right tool for reads of any size.

    `execute_write` does **not** use ``DataFrame.to_sql`` / DML `INSERT`. BigQuery has no
    efficient row-insert path: even with SQLAlchemy's multi-row batching, a write becomes
    one query job per ~1,000 rows, and each job pays several seconds of scheduling/polling
    overhead regardless of how small it is -- for 100K+ rows that adds up to many minutes,
    and it also burns BigQuery's DML mutation quota for something that should be free.
    Instead, `execute_write` uses the native ``google.cloud.bigquery.Client``'s
    ``load_table_from_dataframe`` (a single **load job**, not a query job), which is the
    warehouse's intended bulk-ingestion path and completes in roughly constant time
    regardless of row count.

    Args:
        client_wrapper: The `BigQueryClientWrapper` supplying the SQLAlchemy engine.
        gbq_project_id: The project the data lives in, used to build fully-qualified
            ``project.dataset.table`` references for writes. Never ``None`` in practice --
            `AnalystStack.connectors.bigquery.connector.GoogleBigQueryConnector` always
            falls this back to the billing/auth project if no separate data project is given.
    """

    def __init__(self, client_wrapper: BigQueryClientWrapper, gbq_project_id: str):
        self.wrapper = client_wrapper
        self.gbq_project_id = gbq_project_id

    def execute_read(self, query: str) -> pd.DataFrame:
        """Runs a SQL query and returns the result as a DataFrame.

        Args:
            query: A BigQuery Standard SQL query string.

        Returns:
            The query result as a DataFrame.

        Raises:
            AnalystStack.exceptions.errors.QueryExecutionError: If the query fails to
                execute.
        """
        try:
            logger.debug(f"Executing read query: {query[:100]}...")
            return pd.read_sql(query, self.wrapper.engine)
        except Exception as e:
            logger.exception("Query execution failed")
            raise QueryExecutionError(f"Query execution failed: {e}") from e

    def execute_write(
        self,
        df: pd.DataFrame,
        schema: str,
        table_id: str,
        if_exists: str = "append",
    ) -> None:
        """Bulk-loads a DataFrame into a fully-qualified BigQuery table via a load job.

        Runs as a single ``load_table_from_dataframe`` load job (see the class docstring
        for why this -- and not ``DataFrame.to_sql`` / DML `INSERT` -- is the right tool),
        so write time stays roughly constant regardless of row count. The destination
        table's schema is auto-detected from `df` and created if it doesn't already exist.

        Args:
            df: The DataFrame to write.
            schema: The BigQuery dataset the destination table lives in.
            table_id: The destination table name.
            if_exists: Behavior if the table already exists: ``"append"`` (default) adds
                rows, ``"replace"`` truncates the table first, and ``"fail"`` raises if the
                table already has any rows (BigQuery's ``WRITE_EMPTY`` disposition -- unlike
                pandas' ``to_sql``, this checks for existing *data*, not just table
                existence).

        Raises:
            ValueError: If `if_exists` is not one of ``"append"``, ``"replace"``, or
                ``"fail"``.
            AnalystStack.exceptions.errors.QueryExecutionError: If the load job fails.
        """
        table_ref = f"{self.gbq_project_id}.{schema}.{table_id}"

        if if_exists not in _WRITE_DISPOSITIONS:
            raise ValueError(f"Invalid if_exists value: {if_exists}")

        job_config = bigquery.LoadJobConfig(
            write_disposition=_WRITE_DISPOSITIONS[if_exists],
            autodetect=True,
        )

        try:
            logger.info(f"Loading {len(df)} rows into {table_ref} ({if_exists})...")
            load_job = self.wrapper.bigquery_client.load_table_from_dataframe(df, table_ref, job_config=job_config)
            load_job.result()  # Blocks until the load job finishes; raises on failure.
            logger.info(f"Load complete for {table_ref}.")
        except Exception as e:
            logger.exception(f"Failed to write DataFrame to {table_ref}")
            raise QueryExecutionError(f"Failed to write DataFrame to {table_ref}: {e}") from e
